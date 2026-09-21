import json
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
import trimesh
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.manifest import checked_report,fingerprint,save_review
from asset_mujoco.pipeline import convert

HISTORY=Path(__file__).resolve().parents[2]/'outputs/m1_2_final_6im5gku8/engineering_static_v1/acceptance-5ljztt1b/packages/penguin_fb9002dbf5e8'
KEYS=('compile','physics','render','appearance_review','contact_profile','validation_scope',
      'followup_ground','application_force_limit','host_integration','robot_contact_safety','limitations','status')

@pytest.fixture
def legacy(tmp_path):
    if not HISTORY.is_dir():
        pytest.skip('historical original-GLB package unavailable; not replaced by a synthetic asset')
    package=tmp_path/'isolated-test-copy'
    shutil.copytree(HISTORY,package)
    return package

def invoke(*args):
    result=subprocess.run([sys.executable,'-B','-m','asset_mujoco.cli',*map(str,args)],text=True,capture_output=True)
    return result.returncode,json.loads(result.stdout)

def test_convert_failure_reports_same_scoped_facts(tmp_path):
    source=tmp_path/'cube.glb'; trimesh.creation.box().export(source)
    code,report=invoke('convert',source,'--output',tmp_path/'out','--validation-level','physics')
    assert code==5
    assert report['status']=='FAILED'
    _,read=invoke('report',report['package'])
    assert {k:report[k] for k in KEYS}=={k:read[k] for k in KEYS}

def test_convert_checks_evidence_instead_of_cached_pass(legacy,monkeypatch,capsys):
    import asset_mujoco.pipeline as pipeline
    from asset_mujoco.cli import main
    (legacy/'contact_result_manifest.json').write_text('{}')
    monkeypatch.setattr(pipeline,'convert',lambda request:legacy)
    source=legacy.parent/'source.glb'; trimesh.creation.box().export(source)
    code=main(['convert',str(source),'--output',str(legacy.parent/'unused')])
    report=json.loads(capsys.readouterr().out)
    assert report['status'] not in ('SCOPED_PHYSICS_VALIDATED','PHYSICS_VALIDATED')
    assert code==5

def test_acceptance_uses_bound_native_not_diagnostic_summary(legacy,tmp_path,monkeypatch):
    import asset_mujoco.acceptance as acceptance
    evidence=json.loads((legacy/'physics_evidence.json').read_text())
    evidence['native']['status']='failed'
    (legacy/'physics_evidence.json').write_text(json.dumps(evidence))
    monkeypatch.setattr(acceptance,'convert',lambda request:legacy)
    source=tmp_path/'original.glb'; trimesh.creation.box().export(source)
    report=acceptance.run_acceptance(source,tmp_path/'acceptance','engineering_static_v1')
    assert report['exit_code']==0
    assert report['native']['status']=='passed'
    _,read=invoke('report',legacy)
    assert {k:report[k] for k in KEYS}=={k:read[k] for k in KEYS}
    assert json.loads((Path(report['run_directory'])/'acceptance.json').read_text())==report

def assert_limits(report):
    assert report['contact_profile']=='engineering_static_v1'
    assert report['validation_scope']['case_id']=='native_asset_probe_v1'
    assert report['validation_scope']['required_pairs']==[['asset_collision','probe']]
    assert report['validation_scope']['evidence_status']=='verified'
    assert report['followup_ground']['status']=='failed'
    assert report['followup_ground']['mandatory_for_physics'] is False
    assert report['followup_ground']['comparison_threshold_m']==.005
    assert report['application_force_limit']=='not_specified'
    assert report['host_integration']=='pending'
    assert report['robot_contact_safety']=='not_validated'
    assert 'WHOLE_SCENE_NOT_VALIDATED' in report['limitations']
    assert 'FOLLOWUP_GROUND_FAILED' in report['limitations']

def test_legacy_report_is_scoped_and_read_only(legacy):
    before=fingerprint(legacy)
    code,report=invoke('report',legacy)
    assert code==0
    assert report['status']=='SCOPED_PHYSICS_VALIDATED'
    assert_limits(report)
    assert fingerprint(legacy)==before

def test_isolated_appearance_approval_cannot_expand_scope(legacy):
    original=fingerprint(HISTORY)
    save_review(legacy,'isolated-test-only','approved',['previews/iso.png'])
    code,report=invoke('report',legacy)
    assert code==0 and report['status']=='SCOPED_FULLY_VALIDATED'
    assert_limits(report)
    save_review(legacy,'isolated-test-only','rejected',['previews/iso.png'])
    rejected=checked_report(legacy)
    assert rejected.aggregate()=='SCOPED_PHYSICS_VALIDATED'
    assert rejected.appearance_review=='rejected'
    assert fingerprint(HISTORY)==original and checked_report(HISTORY).appearance_review=='pending'

def test_changed_review_content_does_not_erase_physics(legacy):
    save_review(legacy,'isolated-test-only','approved',['previews/iso.png'])
    with (legacy/'previews/iso.png').open('ab') as file:
        file.write(b'test mutation')
    result=checked_report(legacy)
    assert result.appearance_review=='pending'
    assert result.physics=='passed'
    assert result.aggregate()=='SCOPED_PHYSICS_VALIDATED'

@pytest.mark.parametrize('resource',['contact_scene.xml','contact_result_manifest.json','physics_native_evidence.json'])
def test_changed_or_missing_scope_evidence_cannot_pass(legacy,resource):
    (legacy/resource).unlink()
    result=checked_report(legacy)
    assert result.aggregate() not in ('FULLY_VALIDATED','PHYSICS_VALIDATED','SCOPED_FULLY_VALIDATED','SCOPED_PHYSICS_VALIDATED')
    assert result.validation_scope.evidence_status in ('missing','stale')
    assert result.evidence_issues

def test_scope_projection_tamper_is_not_trusted(legacy):
    before=checked_report(legacy).model_dump()
    before['scope_report_version']=1
    before['followup_ground']['status']='passed'
    (legacy/'validation_report.json').write_text(json.dumps(before))
    result=checked_report(legacy)
    assert result.aggregate()=='INVALID_EVIDENCE'
    assert result.validation_scope.evidence_status=='contradictory'
    assert result.followup_ground.status=='failed'

def test_legacy_missing_required_basis_is_unknown_not_not_tested(tmp_path):
    source=tmp_path/'plain.glb'; trimesh.creation.box().export(source)
    package=convert(ConversionRequest(input=source,output=tmp_path/'out',validation_level='compile'))
    report=checked_report(package)
    assert report.aggregate()=='COMPILE_VALIDATED'
    assert report.validation_scope.evidence_status=='declared'
    assert report.followup_ground.status=='unknown'

def test_relocation_preserves_scope_and_limits(legacy,tmp_path):
    moved=tmp_path/'relocated'; shutil.copytree(legacy,moved)
    before=checked_report(legacy).model_dump()
    after=checked_report(moved).model_dump()
    assert {k:before[k] for k in KEYS}=={k:after[k] for k in KEYS}
    assert after['status']=='SCOPED_PHYSICS_VALIDATED'

def test_new_package_persists_same_report_and_non_penguin_conditions(tmp_path):
    source=tmp_path/'non_penguin.glb'; trimesh.creation.box(extents=[.1,.1,.1]).export(source)
    code,report=invoke('convert',source,'--output',tmp_path/'out','--name','cube',
        '--contact-profile','engineering_static_v1','--validation-level','compile')
    assert code==0
    package=Path(report['package'])
    disk=json.loads((package/'validation_report.json').read_text())
    code,read=invoke('report',package)
    assert code==0
    for key in KEYS:
        assert report[key]==disk[key]==read[key]
    assert read['status']=='COMPILE_VALIDATED'
    assert read['validation_scope']['evidence_status']=='declared'
    assert 'penguin' not in read['validation_scope']['case_id']

def test_new_report_cannot_drop_version_to_evade_projection_check(tmp_path):
    source=tmp_path/'cube.glb'; trimesh.creation.box().export(source)
    package=convert(ConversionRequest(input=source,output=tmp_path/'out',validation_level='physics',
        contact_profile='engineering_static_v1'))
    path=package/'validation_report.json'; report=json.loads(path.read_text())
    report.pop('scope_report_version')
    report['followup_ground']['status']='passed'
    path.write_text(json.dumps(report))
    assert checked_report(package).aggregate()=='INVALID_EVIDENCE'

@pytest.mark.parametrize('key,value',[('contact_profile','preserve'),('followup_ground',{'status':'passed'})])
def test_hash_valid_but_semantically_conflicting_contact_record_is_rejected(legacy,key,value):
    from asset_mujoco.manifest import record_layer
    path=legacy/'contact_result_manifest.json'; record=json.loads(path.read_text())
    record[key]=value; path.write_text(json.dumps(record))
    entry=json.loads((legacy/'evidence_manifest.json').read_text())['layers']['physics']
    # 仅在隔离副本模拟“生产者写出了矛盾事实但文件hash完整”的情况。
    new=record_layer(legacy,'physics','passed',entry['files'],entry['context'])
    path=legacy/'validation_report.json'; state=json.loads(path.read_text())
    state['asset_physics_sha256']=new['sha256']; path.write_text(json.dumps(state))
    report=checked_report(legacy)
    assert report.aggregate()=='INVALID_EVIDENCE'
    assert report.validation_scope.evidence_status=='contradictory'

def test_failed_native_retains_reason_when_benchmark_passes(tmp_path):
    from asset_mujoco.pipeline import ValidationFailed
    source=tmp_path/'cube.glb'; trimesh.creation.box().export(source)
    with pytest.raises(ValidationFailed) as failed:
        convert(ConversionRequest(input=source,output=tmp_path/'out',validation_level='physics'))
    package=failed.value.package
    result=checked_report(package)
    assert json.loads((package/'benchmark_evidence.json').read_text())['status']=='passed'
    assert result.aggregate()=='FAILED' and result.physics_error
    assert result.contact_profile=='preserve'
    assert result.validation_scope.evidence_status=='verified'

def test_visual_only_declares_no_required_physical_pair(tmp_path):
    source=tmp_path/'cube.glb'; trimesh.creation.box().export(source)
    package=convert(ConversionRequest(input=source,output=tmp_path/'out',validation_level='compile',collision_mode='none'))
    result=checked_report(package)
    assert result.aggregate()=='VISUAL_ONLY' and result.physics=='not_applicable'
    assert not result.validation_scope.required_pairs

@pytest.mark.parametrize('cached',['not_run','not_applicable','passed'])
def test_cached_layer_cannot_hide_native_failure(tmp_path,cached):
    from asset_mujoco.pipeline import ValidationFailed
    source=tmp_path/'cube.glb'; trimesh.creation.box().export(source)
    with pytest.raises(ValidationFailed) as caught:
        convert(ConversionRequest(input=source,output=tmp_path/'out',validation_level='physics'))
    package=caught.value.package
    path=package/'validation_report.json'; report=json.loads(path.read_text())
    report['physics']=cached
    path.write_text(json.dumps(report))
    result=checked_report(package)
    assert result.physics=='failed' and result.status=='FAILED'
    assert 'penetration=' in result.physics_error
    code,read=invoke('report',package)
    assert code==5 and read['physics']=='failed'

@pytest.mark.parametrize('mutation',['name','timestep','position','forced_pair'])
def test_hash_valid_fixture_contradiction_rejected(legacy,mutation):
    import xml.etree.ElementTree as ET
    from asset_mujoco.manifest import record_layer
    path=legacy/'physics_native.xml'; tree=ET.parse(path)
    if mutation=='name':
        tree.find(".//geom[@name='probe']").set('name','not_probe')
    elif mutation=='timestep':
        tree.find('option').set('timestep','0.01')
    elif mutation=='position':
        tree.find(".//body[@name='probe_body']").set('pos','9 9 9')
    else:
        ET.SubElement(ET.SubElement(tree.getroot(),'contact'),'pair',geom1='asset_collision',geom2='probe')
    tree.write(path)
    evidence=json.loads((legacy/'evidence_manifest.json').read_text())['layers']['physics']
    entry=record_layer(legacy,'physics',evidence['status'],evidence['files'],evidence['context'])
    report=json.loads((legacy/'validation_report.json').read_text())
    report['asset_physics_sha256']=entry['sha256']
    (legacy/'validation_report.json').write_text(json.dumps(report))
    result=checked_report(legacy)
    assert result.status=='INVALID_EVIDENCE'
    assert result.validation_scope.evidence_status=='contradictory'
