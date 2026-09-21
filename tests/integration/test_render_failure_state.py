import json
from pathlib import Path
import pytest
import trimesh
import asset_mujoco.pipeline as pipeline
import asset_mujoco.rendering as rendering
from asset_mujoco.cli import main
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.manifest import checked_report,EvidenceIOError

def setup_case(tmp_path,monkeypatch,message):
    source=tmp_path/'box.glb'
    trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/'out',contact_profile='engineering_static_v1')
    calls=[]
    publish=pipeline.atomic_publish
    def spy(staging,final):
        calls.append(final)
        return publish(staging,final)
    monkeypatch.setattr(pipeline,'atomic_publish',spy)
    def fail(package,size):
        # 真实native必须已经执行并持久化，不用mock代替物理验收。
        native=json.loads((package/'physics_native_evidence.json').read_text())['native']
        assert native['status']=='passed'
        raise RuntimeError(message)
    monkeypatch.setattr(rendering,'render_package',fail)
    return request,calls

@pytest.mark.parametrize('message,state,status',[
    ('RENDER_UNAVAILABLE: injected backend outage','unavailable','SCOPED_PHYSICS_VALIDATED'),
    ('RENDER_FAILED: injected worker failure','failed','FAILED'),
])
def test_render_error_preserves_complete_verified_state(tmp_path,monkeypatch,message,state,status):
    request,calls=setup_case(tmp_path,monkeypatch,message)
    with pytest.raises(Exception,match=message) as caught:
        pipeline.convert(request)
    assert not calls and not list(request.output.glob('asset_*'))
    package=next(request.output.glob('.staging-*'))
    disk=json.loads((package/'validation_report.json').read_text())
    read=checked_report(package).model_dump()
    for report in (disk,read):
        assert report['compile']==report['physics']=='passed'
        assert report['render']==state
        assert report['validation_scope']['evidence_status']=='verified'
        assert report['contact_profile']=='engineering_static_v1'
        assert report['status']==status
        assert not report['evidence_issues']
        assert message in report['render_error']
        assert report['appearance_review']=='pending'
    assert disk==read
    assert caught.value.package==package

@pytest.mark.parametrize('message,code,state',[
    ('RENDER_UNAVAILABLE: injected backend outage',7,'unavailable'),
    ('RENDER_FAILED: injected worker failure',5,'failed'),
])
def test_render_cli_preserves_report_and_exit(tmp_path,monkeypatch,capsys,message,code,state):
    request,calls=setup_case(tmp_path,monkeypatch,message)
    assert main(['convert',str(request.input),'--output',str(request.output),
                 '--contact-profile','engineering_static_v1'])==code
    report=json.loads(capsys.readouterr().out)
    assert report['physics']=='passed' and report['render']==state
    assert report['validation_scope']['evidence_status']=='verified'
    assert report['error']['stage']=='render'
    assert message in report['error']['message']
    assert Path(report['package']).is_dir() and not calls
    query=main(['report',report['package']])
    read=json.loads(capsys.readouterr().out)
    assert query==(0 if state=='unavailable' else 5)
    assert read['physics']=='passed' and not read['evidence_issues']

@pytest.mark.parametrize('failed_file',['validation_report.json','failure.json'])
def test_render_diagnostic_io_retains_both_causes(tmp_path,monkeypatch,failed_file):
    message='RENDER_UNAVAILABLE: original backend outage'
    request,calls=setup_case(tmp_path,monkeypatch,message)
    write=Path.write_text
    def fail(path,*args,**kwargs):
        if path.name==failed_file and (path.parent/'physics_native_evidence.json').exists():
            # validation报告只在渲染异常写入时故障，native持久化阶段不故障。
            content=args[0] if args else kwargs.get('data','')
            if failed_file=='failure.json' or 'original backend outage' in content:
                raise OSError('injected diagnostic disk full')
        return write(path,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',fail)
    with pytest.raises(EvidenceIOError) as caught:
        pipeline.convert(request)
    assert message in str(caught.value) and 'disk full' in str(caught.value)
    assert caught.value.__cause__ is not None
    assert not calls and not list(request.output.glob('asset_*'))
    package=next(request.output.glob('.staging-*'))
    assert checked_report(package).physics=='passed'
    assert (package/'physics_native_evidence.json').is_file()

def test_acceptance_render_unavailable_never_counts_full_pass(tmp_path,monkeypatch):
    from asset_mujoco.acceptance import run_acceptance
    request,calls=setup_case(tmp_path,monkeypatch,'RENDER_UNAVAILABLE: acceptance injection')
    report=run_acceptance(request.input,tmp_path/'acceptance','engineering_static_v1')
    assert report['automatic_validation']=='failed'
    assert report['exit_code']!=0 and not calls
    assert report['physics']=='passed' and report['render']=='unavailable'
    assert report['validation_scope']['evidence_status']=='verified'
