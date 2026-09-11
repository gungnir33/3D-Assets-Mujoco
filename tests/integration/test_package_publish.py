import shutil
import mujoco
import trimesh
from asset_mujoco.pipeline import convert
from asset_mujoco.contracts import ConversionRequest

def test_portable_static(tmp_path):
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    req=ConversionRequest(input=source,output=tmp_path/"out",source_up="z",validation_level="compile")
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
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",source_up="z",body_mode="free",mass=2,inertia_mode="box_approx",validation_level="compile"))
    model=mujoco.MjModel.from_xml_path(str(package/"model.xml"))
    assert model.body_mass[1]==2
    assert model.njnt==1

def test_supplied_compiled_tensor(tmp_path):
    import numpy as np
    from asset_mujoco.contracts import SuppliedInertia
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    tensor=np.array([[2,.1,.2],[.1,2.5,.15],[.2,.15,3.]])
    supplied=SuppliedInertia(frame="normalized_body",reference="com",com_unit="m",inertia_unit="kg*m^2",com=[.1,.2,.3],tensor=tensor.tolist(),mass_kg=2,final_size_m=[1,1,1])
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",body_mode="free",mass=2,inertia_mode="supplied",supplied_inertia=supplied,yaw_deg=90,validation_level="compile"))
    model=mujoco.MjModel.from_xml_path(str(package/"model.xml"))
    rot=np.empty(9)
    mujoco.mju_quat2Mat(rot,model.body_iquat[1])
    rot=rot.reshape(3,3)
    np.testing.assert_allclose(rot@np.diag(model.body_inertia[1])@rot.T,tensor,rtol=1e-8,atol=1e-12)
    np.testing.assert_allclose(model.body_ipos[1],[.1,.2,.3])
