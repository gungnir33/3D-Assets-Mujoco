import json
import xml.etree.ElementTree as ET
import numpy as np
import pytest
import trimesh
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.pipeline import convert
from asset_mujoco.validation import run_contact_case

def make(tmp_path,profile='engineering_static_v1'):
    source=tmp_path/'box.glb'; trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/'out',source_up='z',
                              validation_level='compile',contact_profile=profile)
    return convert(request),request

def test_preserve_default_and_static_scope(tmp_path):
    base=dict(input=tmp_path/'a.glb',output=tmp_path/'out')
    assert ConversionRequest(**base).contact_profile=='preserve'
    with pytest.raises(ValueError,match='static.hull'):
        ConversionRequest(**base,contact_profile='engineering_static_v1',body_mode='free',mass=1,inertia_mode='box_approx')
    with pytest.raises(ValueError,match='static.hull'):
        ConversionRequest(**base,contact_profile='engineering_static_v1',collision_mode='none',validation_level='compile')

def test_explicit_delivery_and_native_resolution(tmp_path):
    package,request=make(tmp_path)
    root=ET.parse(package/'contact_scene.xml').getroot()
    for name in ('asset_collision','probe','ground'):
        geom=root.find(f".//geom[@name='{name}']")
        assert np.fromstring(geom.get('solref'),sep=' ')==pytest.approx([.006,1])
        assert np.fromstring(geom.get('solimp'),sep=' ')==pytest.approx([.9,.95,.001,.5,2])
        assert geom.get('priority') is None and geom.get('solmix') is None
    before=(package/'contact_scene.xml').read_bytes()
    report=run_contact_case(package,request,[1,1,1])
    assert report['profile_contract']['matched']
    assert report['first_resolved_contact']['solref']==pytest.approx([.006,1])
    assert ET.parse(package/'physics_native.xml').getroot().find('.//pair') is None
    assert (package/'contact_scene.xml').read_bytes()==before
    manifest=json.loads((package/'conversion_manifest.json').read_text())
    assert manifest['contact_profile']['id']=='engineering_static_v1'
    assert manifest['contact_profile']['application_force_limit']=='not_specified'

@pytest.mark.parametrize('field,value,expected',[('solref','0.02 1',[.013,1]),('solimp','0.8 0.95 0.001 0.5 2',[.85,.95,.001,.5,2])])
def test_unmatched_counterparty_records_actual_mixing(tmp_path,field,value,expected):
    package,request=make(tmp_path)
    path=package/'contact_scene.xml'; root=ET.parse(path).getroot()
    root.find(".//geom[@name='probe']").set(field,value)
    ET.ElementTree(root).write(path)
    report=run_contact_case(package,request,[1,1,1])
    assert report['status']=='failed'
    assert not report['profile_contract']['matched']
    assert report['first_resolved_contact'][field]==pytest.approx(expected)

@pytest.mark.parametrize('attrs',[{'contype':'0','conaffinity':'0'},{'pos':'10 0 0'}])
def test_profile_cannot_bypass_collision_filters_or_retarget(tmp_path,attrs):
    package,request=make(tmp_path)
    path=package/'contact_scene.xml'; root=ET.parse(path).getroot()
    root.find(".//geom[@name='asset_collision']").attrib.update(attrs)
    ET.ElementTree(root).write(path)
    report=run_contact_case(package,request,[1,1,1])
    assert report['status']=='failed' and report['contact_count']==0
    assert report['initial_position']==pytest.approx([0,0,1.225])

@pytest.mark.parametrize('resource,layer',[
    ('contact_scene.xml','compile'),('contact_result_manifest.json','physics')])
def test_profile_resources_are_bound_to_layered_evidence(tmp_path,resource,layer):
    from asset_mujoco.validation import validate_physics
    from asset_mujoco.manifest import checked_report
    package,request=make(tmp_path)
    validate_physics(package,request,[1,1,1])
    assert getattr(checked_report(package),layer)=='passed'
    with (package/resource).open('a') as file:
        file.write('\n ')
    assert getattr(checked_report(package),layer)!='passed'
    assert checked_report(package).evidence_issues
