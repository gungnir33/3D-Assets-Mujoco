import json
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
import pytest

XML='''<mujoco><option timestep="0.002"><flag energy="enable" autoreset="disable"/></option>
<worldbody><geom name="asset_collision" type="plane" size="2 2 .1"/>
<body name="probe_body" pos="0 0 .225"><freejoint/><geom name="probe" type="sphere" size=".025" mass=".1"/></body>
</worldbody></mujoco>'''

def test_trace_matches_unmodified_engine_and_same_time_state(tmp_path):
    from asset_mujoco.contact_diagnostics import trace_fixture
    fixture=tmp_path/'fixture.xml'
    fixture.write_text(XML)
    before=fixture.read_bytes()
    result=trace_fixture(fixture,tmp_path,total_time=2,limit=.005)
    rows=[json.loads(line) for line in (tmp_path/'contact_trace.jsonl').read_text().splitlines()]
    assert len(rows)==1000 and rows[0]['contacts']==[]
    assert rows[0]['sample_time_s']==0 and rows[-1]['integrated_time_s']==pytest.approx(2)
    first=next(r for r in rows if r['contacts'])
    c=first['contacts'][0]
    assert c['normal_relative_velocity_m_s']==pytest.approx(first['qvel'][2],abs=1e-12)
    assert c['normal_relative_velocity_m_s']<0
    assert c['normal_world']==pytest.approx([0,0,1])
    assert c['force_world_on_geom2_N'][2]>0
    assert c['force_contact_frame_N_Nm'][0]==pytest.approx(c['force_world_on_geom2_N'][2])
    assert all(r['checks']['state_finite'] and r['checks']['time_valid'] for r in rows)
    model=mujoco.MjModel.from_xml_path(str(fixture)); data=mujoco.MjData(model)
    mujoco.mj_forward(model,data)
    distances=[]
    for step in range(1,1001):
        mujoco.mj_step(model,data)
        distances.extend((float(c.dist),step) for c in data.contact)
    worst=min(distances)
    assert result['max_penetration_m']==pytest.approx(-worst[0],abs=1e-12)
    assert result['max_penetration_step']==worst[1]
    assert result['first_contact_step']<result['first_exceedance_step']<=result['max_penetration_step']
    assert result['contact_exists'] and result['numerically_stable']
    assert not result['threshold_passed']
    assert fixture.read_bytes()==before
    assert result['hashes']['contact_trace.jsonl']

def test_controls_change_only_named_parameters(tmp_path):
    from asset_mujoco.contact_diagnostics import configure_fixture,trace_fixture
    source=tmp_path/'source.xml'; source.write_text(XML)
    target=tmp_path/'fixture.xml'
    configure_fixture(source,target,{'dt':.001})
    result=trace_fixture(target,tmp_path,total_time=2,limit=.005)
    assert result['steps']==2000 and result['total_time_s']==pytest.approx(2)
    configure_fixture(source,target,{'solref':[.01,1]})
    root=ET.parse(target).getroot()
    assert root.find('option').get('timestep')=='0.002'
    for name in ('asset_collision','probe'):
        geom=root.find(f".//geom[@name='{name}']")
        assert geom.get('solref')=='0.01 1'
        assert geom.get('solimp') is None
    assert root.find('.//pair') is None
    configure_fixture(source,target,{'solimp':[.95,.95,.001,.5,2]})
    root=ET.parse(target).getroot()
    assert root.find(".//geom[@name='probe']").get('solref') is None
    assert source.read_text()==XML

def test_trace_no_contact_never_reports_threshold_pass(tmp_path):
    from asset_mujoco.contact_diagnostics import trace_fixture
    fixture=tmp_path/'fixture.xml'
    fixture.write_text(XML.replace('size="2 2 .1"','size="2 2 .1" contype="0" conaffinity="0"'))
    result=trace_fixture(fixture,tmp_path,total_time=.1,limit=.005)
    assert not result['contact_exists'] and not result['threshold_passed']
    assert result['first_contact_step'] is None

def test_suite_keeps_all_cases_and_stops_on_baseline_mismatch(tmp_path):
    import trimesh
    from asset_mujoco.contact_diagnostics import run_diagnostics
    from asset_mujoco.contracts import ConversionRequest
    from asset_mujoco.pipeline import convert
    from asset_mujoco.validation import validate_physics
    from asset_mujoco.manifest import fingerprint
    source=tmp_path/'box.glb'; trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/'converted',source_up='z',validation_level='compile')
    package=convert(request)
    validate_physics(package,request,[1,1,1])
    original=fingerprint(package)
    result=run_diagnostics(package,tmp_path/'experiments')
    assert len(result['results'])==8 and fingerprint(package)==original
    assert all(row['summary']['execution_status']=='completed' for row in result['results'])
    baseline=result['results'][0]['summary']
    plane=result['results'][3]['summary']
    assert plane['first_contact']['normal_relative_velocity_m_s']==pytest.approx(baseline['first_contact']['normal_relative_velocity_m_s'],abs=1e-12)
    for row in result['results']:
        assert (Path(row['directory'])/'output_hashes.json').is_file()
    # 故意更改临时合成包的参考值：不得继续扫描并假装基线一致。
    path=package/'physics_evidence.json'
    report=json.loads(path.read_text()); report['native']['max_penetration_m']=0
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='BASELINE_MISMATCH'):
        run_diagnostics(package,tmp_path/'mismatch')
    run=next((tmp_path/'mismatch').iterdir())
    assert len(json.loads((run/'diagnosis.json').read_text())['results'])==1
