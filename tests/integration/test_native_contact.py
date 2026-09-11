import xml.etree.ElementTree as ET
import trimesh
import pytest
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.pipeline import convert
from asset_mujoco.validation import validate_physics

def box_package(tmp_path):
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/"out",source_up="z",validation_level="compile")
    return convert(request),request

def change_collision(package,**attrs):
    path=package/"scene.xml"
    root=ET.parse(path).getroot()
    geom=root.find(".//geom[@name='asset_collision']")
    geom.attrib.update(attrs)
    ET.ElementTree(root).write(path)

def test_native_contact_not_forced(tmp_path):
    package,request=box_package(tmp_path)
    report=validate_physics(package,request,[1,1,1])
    assert report["native"]["contact_count"]>0
    assert report["native"]["steps"]==1000
    root=ET.parse(package/"physics_native.xml").getroot()
    assert root.find(".//pair") is None
    assert report["native"]["max_penetration_m"]>0

def test_disabled_collision_fails_even_if_benchmark_passes(tmp_path):
    package,request=box_package(tmp_path)
    change_collision(package,contype="0",conaffinity="0")
    report=validate_physics(package,request,[1,1,1])
    assert report["native"]["status"]=="failed"
    assert report["native"]["contact_count"]==0
    assert report["benchmark"]["status"]=="passed"
    assert report["status"]=="failed"

def test_moved_collision_does_not_retarget_probe(tmp_path):
    package,request=box_package(tmp_path)
    change_collision(package,pos="10 0 0")
    report=validate_physics(package,request,[1,1,1])
    assert report["native"]["status"]=="failed"
    assert report["native"]["contact_count"]==0
    assert report["native"]["initial_position"]==pytest.approx([0,0,1.225],abs=1e-15)

def test_native_gentle_contact_can_pass(tmp_path):
    from asset_mujoco.validation import run_contact_case
    package,request=box_package(tmp_path)
    report=run_contact_case(package,request,[1,1,1],initial_position=[0,0,1.026])
    assert report["status"]=="passed"
    assert report["contact_count"]>0
    assert report["max_penetration_m"]<=.005

def test_pipeline_does_not_promote_benchmark(tmp_path):
    from asset_mujoco.pipeline import ValidationFailed
    package,request=box_package(tmp_path)
    with pytest.raises(ValidationFailed) as exc:
        convert(request.model_copy(update={"validation_level":"physics"}))
    assert exc.value.result.physics=="failed"
