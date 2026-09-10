import json
import shutil
import numpy as np
import pytest
import trimesh
from asset_mujoco.pipeline import convert
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.validation import check_state

def test_current_asset_physics(tmp_path):
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",validation_level="physics"))
    evidence=json.loads((package/"physics_evidence.json").read_text())
    assert evidence["steps"]==1000
    assert evidence["contact_count"]>0
    assert evidence["expected_pair"]==["asset_collision","probe"]
    assert len(evidence["asset_sha256"])==64

def test_nonfinite_or_reset_fails():
    import mujoco
    model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><freejoint/><geom type="sphere" size=".1"/></body></worldbody></mujoco>')
    data=mujoco.MjData(model)
    data.qpos[0]=np.nan
    with pytest.raises(ValueError):
        check_state(model,data,0,0)
    data.qpos[0]=0
    with pytest.raises(ValueError):
        check_state(model,data,1,model.opt.timestep)

def test_full_synthetic(tmp_path):
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",validation_level="full"))
    assert (package/"previews/iso.png").is_file()
    assert json.loads((package/"validation_report.json").read_text())["render"]=="passed"
