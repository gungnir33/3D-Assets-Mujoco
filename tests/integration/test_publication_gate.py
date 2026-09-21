import json
import pytest
import trimesh
from pathlib import Path
import asset_mujoco.pipeline as pipeline
import asset_mujoco.validation as validation
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.manifest import checked_report,record_layer,refresh_report,compile_resources

@pytest.mark.parametrize('entrypoint',['python','cli'])
def test_real_scope_contradiction_blocks_python_publication(tmp_path,monkeypatch,capsys,entrypoint):
    source=tmp_path/'cube.glb'; trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/'out',contact_profile='engineering_static_v1')
    validate=validation.validate_physics
    def inject(package,request,size):
        result=validate(package,request,size)
        path=package/'contact_result_manifest.json'
        contact=json.loads(path.read_text()); contact['contact_profile']='preserve'
        path.write_text(json.dumps(contact))
        entry=json.loads((package/'evidence_manifest.json').read_text())['layers']['physics']
        entry=record_layer(package,'physics',entry['status'],entry['files'],entry['context'])
        # 模拟写入方自洽哈希但语义错误，实际checked_report应判contradictory。
        report=json.loads((package/'validation_report.json').read_text())
        report['asset_physics_sha256']=entry['sha256']
        (package/'validation_report.json').write_text(json.dumps(report))
        result['asset_sha256']=entry['sha256']
        return result
    monkeypatch.setattr(validation,'validate_physics',inject)
    calls=[]; publish=pipeline.atomic_publish
    def spy(staging,final):
        calls.append(final); return publish(staging,final)
    monkeypatch.setattr(pipeline,'atomic_publish',spy)
    if entrypoint=='python':
        with pytest.raises(pipeline.ValidationFailed) as caught:
            pipeline.convert(request)
        assert caught.value.code=='EVIDENCE_INVALID'
        assert caught.value.stage=='publication'
    else:
        from asset_mujoco.cli import main
        assert main(['convert',str(source),'--output',str(request.output),
                     '--contact-profile','engineering_static_v1'])==5
        output=json.loads(capsys.readouterr().out)
        assert output['error']['code']=='EVIDENCE_INVALID'
        assert output['status']=='INVALID_EVIDENCE'
    assert not calls and not list(request.output.glob('asset_*'))
    package=next(request.output.glob('.staging-*'))
    report=checked_report(package)
    assert report.physics=='passed'
    assert report.status=='INVALID_EVIDENCE'
    assert report.validation_scope.evidence_status=='contradictory'
    if entrypoint=='python':
        assert caught.value.package==package

def intercept_boundary(monkeypatch,mutation):
    # 在最终日志持久化时注入证据丢失，真实门槛必须重新核对磁盘。
    # 不替换checked_report/refresh_report或门槛，也不mock引擎。
    write=Path.write_text
    def inject(path,*args,**kwargs):
        result=write(path,*args,**kwargs)
        if path.name=='conversion.log':
            mutation(path.parent)
        return result
    monkeypatch.setattr(Path,'write_text',inject)
    calls=[]; publish=pipeline.atomic_publish
    def spy(staging,final):
        calls.append(final); return publish(staging,final)
    monkeypatch.setattr(pipeline,'atomic_publish',spy)
    return calls

@pytest.mark.parametrize('level,mutation,expected',[
    ('compile','compile_missing','EVIDENCE_INVALID'),
    ('compile','resource_changed','EVIDENCE_INVALID'),
    ('physics','physics_missing','VALIDATION_INCOMPLETE'),
    ('physics','resource_changed','EVIDENCE_INVALID'),
    ('full','physics_missing','VALIDATION_INCOMPLETE'),
    ('full','render_missing','VALIDATION_INCOMPLETE'),
    ('full','render_unavailable','RENDER_UNAVAILABLE'),
    ('full','resource_changed','EVIDENCE_INVALID'),
    ('compile','report_missing','EVIDENCE_INVALID'),
    ('physics','report_invalid','EVIDENCE_INVALID'),
])
def test_missing_layer_or_evidence_blocks_core_publish(tmp_path,monkeypatch,level,mutation,expected):
    source=tmp_path/'cube.glb'; trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/'out',validation_level=level,contact_profile='engineering_static_v1')
    def mutate(package):
        if mutation.startswith('report_'):
            path=package/'validation_report.json'
            if mutation=='report_missing':
                path.unlink()
            else:
                path.write_text('{broken')
            return
        if mutation=='resource_changed':
            path=package/'meshes/collision.obj'; path.write_text(path.read_text()+'\n# fault injection\n')
            return
        evidence=json.loads((package/'evidence_manifest.json').read_text())
        state=json.loads((package/'validation_report.json').read_text())
        layer=mutation.split('_')[0]
        if mutation=='render_unavailable':
            (package/'render_failure.json').write_text(json.dumps({'status':'unavailable','error':{'type':'RuntimeError','message':'injected unavailable'}}))
            record_layer(package,'render','unavailable',compile_resources(package)+['render_failure.json'],{'failure_evidence':'render_failure.json'})
            state['render']='unavailable'
        else:
            evidence['layers'].pop(layer,None)
            (package/'evidence_manifest.json').write_text(json.dumps(evidence))
            state[layer]='not_run'
        (package/'validation_report.json').write_text(json.dumps(state))
        refresh_report(package)
    calls=intercept_boundary(monkeypatch,mutate)
    with pytest.raises(pipeline.ValidationFailed) as caught:
        pipeline.convert(request)
    assert not calls and not list(request.output.glob('asset_*'))
    package=next(request.output.glob('.staging-*'))
    assert caught.value.package==package
    assert caught.value.code==expected and caught.value.stage=='publication'
    assert (package/'failure.json').is_file()
    if mutation.startswith('render_'):
        assert checked_report(package).status=='SCOPED_PHYSICS_VALIDATED'

@pytest.mark.parametrize('level,collision,expected',[
    ('compile','hull','COMPILE_VALIDATED'),('compile','none','VISUAL_ONLY'),
    ('physics','hull','SCOPED_PHYSICS_VALIDATED'),('full','hull','SCOPED_PHYSICS_VALIDATED'),
])
def test_normal_requested_levels_publish(tmp_path,level,collision,expected):
    source=tmp_path/'cube.glb'; trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/'out',validation_level=level,collision_mode=collision,
                              contact_profile='preserve' if collision=='none' else 'engineering_static_v1')
    package=pipeline.convert(request)
    assert package.is_dir() and not list(request.output.glob('.staging-*'))
    result=checked_report(package)
    assert result.status==expected and not result.evidence_issues
    assert result.appearance_review==result.host_integration=='pending'
    assert result.robot_contact_safety=='not_validated'
    assert json.loads((package/'validation_report.json').read_text())==result.model_dump()
