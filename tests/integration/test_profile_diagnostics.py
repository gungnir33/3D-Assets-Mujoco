import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
import trimesh
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.pipeline import convert
from asset_mujoco.validation import validate_physics
from asset_mujoco.manifest import fingerprint


def test_profile_diagnostics_preserves_package_and_records_all_cases(tmp_path):
    from asset_mujoco.profile_diagnostics import run_profile_diagnostics
    source=tmp_path/'box.glb'; trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/'packages',source_up='z',
        validation_level='compile',contact_profile='engineering_static_v1')
    package=convert(request)
    validate_physics(package,request,[1,1,1])
    before=fingerprint(package)
    result=run_profile_diagnostics(package,tmp_path/'diagnostics')
    assert fingerprint(package)==before
    assert len(result['results'])==8
    cases={row['name']:row for row in result['results']}
    assert cases['dt_001']['summary']['steps']==2000
    assert cases['dt_0005']['summary']['steps']==4000
    assert all(r['summary']['total_time_s']==pytest.approx(2) for r in result['results'])
    assert cases['counterparty_mismatch']['summary']['first_contact']['solref']==pytest.approx([.013,1])
    for name,expected in [('mass_02',.2),('radius_12',.1)]:
        assert cases[name]['summary']['probe_mass_kg']==expected
    radius=ET.parse(Path(cases['radius_12']['directory'])/'fixture.xml').getroot()
    inertia=radius.find('.//inertial')
    assert float(inertia.get('diaginertia').split()[0])==pytest.approx(.4*.1*.03**2)
    plan=json.loads((Path(result['directory'])/'experiment_plan.json').read_text())
    assert plan['application_force_limit']=='not_specified'
    assert all(r['summary']['diagnostic'] for r in result['results'])
    assert result['exit_code']==0 and result['execution_status']=='completed'
    assert all(json.loads((Path(r['directory'])/'contact_summary.json').read_text())['execution_status']=='completed' for r in result['results'])

def test_nonbaseline_execution_error_keeps_remaining_cases_and_exits_nonzero(tmp_path,monkeypatch,capsys):
    import asset_mujoco.profile_diagnostics as diagnostics
    source=tmp_path/'box.glb'; trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/'packages',source_up='z',
        validation_level='compile',contact_profile='engineering_static_v1')
    package=convert(request)
    validate_physics(package,request,[1,1,1])
    monkeypatch.setattr(diagnostics,'CASES',[
        {'name':'baseline'}, {'name':'invalid_dt','dt':.003}, {'name':'after_error','mass_kg':.2}])
    monkeypatch.setattr('sys.argv',['profile_diagnostics','--package',str(package),'--output',str(tmp_path/'diagnostics')])
    assert diagnostics.main()==5
    result=json.loads(capsys.readouterr().out)
    assert result['execution_status']=='completed_with_errors'
    assert result['exit_code']==5
    assert [r['summary']['execution_status'] for r in result['results']]==['completed','error','completed']
    saved=json.loads((Path(result['directory'])/'diagnosis.json').read_text())
    assert saved['execution_status']=='completed_with_errors'
    assert saved['results'][1]['summary']['error']['type']=='ValueError'
