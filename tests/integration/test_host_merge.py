import xml.etree.ElementTree as ET
import pytest
from asset_mujoco.mjcf import check_host_compiler, merge_host

@pytest.mark.parametrize("attributes",[{"angle":"radian"},{"inertiafromgeom":"false"},{"balanceinertia":"false"}])
def test_safe_nondefault(attributes):
    root=ET.Element("mujoco")
    ET.SubElement(root,"compiler",attributes)
    before=ET.tostring(root)
    check_host_compiler(root)
    assert ET.tostring(root)==before

def test_real_host_compile_nondefault(tmp_path):
    import mujoco
    import trimesh
    from asset_mujoco.pipeline import convert
    from asset_mujoco.contracts import ConversionRequest
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",body_mode="free",mass=2,inertia_mode="box_approx"))
    root=ET.fromstring('<mujoco><compiler angle="radian" inertiafromgeom="false"/><option timestep=".003"/><worldbody/></mujoco>')
    merge_host(root,package,"object_",tmp_path)
    path=tmp_path/"host.xml"
    ET.ElementTree(root).write(path)
    model=mujoco.MjModel.from_xml_path(str(path))
    mujoco.mj_forward(model,mujoco.MjData(model))
    assert model.opt.timestep==.003
    assert model.body_mass[model.body("object_asset").id]==2

@pytest.mark.parametrize("attributes",[{"inertiafromgeom":"true"},{"fusestatic":"true"},{"meshdir":"elsewhere"},{"texturedir":"elsewhere"},{"balanceinertia":"true"}])
def test_conflict_not_silently_changed(attributes):
    root=ET.Element("mujoco")
    ET.SubElement(root,"compiler",attributes)
    before=ET.tostring(root)
    with pytest.raises(ValueError,match="HOST_COMPILER_CONFLICT"):
        check_host_compiler(root)
    assert ET.tostring(root)==before
