import shutil
import mujoco
import trimesh
from asset_mujoco.pipeline import convert
from asset_mujoco.contracts import ConversionRequest

def test_portable_static(tmp_path):
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    req=ConversionRequest(input=source,output=tmp_path/"out",source_up="z")
    first=convert(req)
    second=convert(req)
    assert first!=second and first.is_dir()
    shutil.copytree(first,tmp_path/"moved")
    for name in ("model.xml","scene.xml"):
        model=mujoco.MjModel.from_xml_path(str(tmp_path/"moved"/name))
        mujoco.mj_forward(model,mujoco.MjData(model))
        assert model.njnt==0
    assert ".staging" not in (first/"conversion_manifest.json").read_text()

def test_free_inertial(tmp_path):
    source=tmp_path/"box.glb"
    trimesh.creation.box(extents=[1,2,3]).export(source)
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",source_up="z",body_mode="free",mass=2,inertia_mode="box_approx"))
    model=mujoco.MjModel.from_xml_path(str(package/"model.xml"))
    assert model.body_mass[1]==2
    assert model.njnt==1
