import json
import shutil
import numpy as np
import pytest
import trimesh
from asset_mujoco.pipeline import convert, ValidationFailed
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.validation import check_state

def test_current_asset_physics(tmp_path):
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    with pytest.raises(ValidationFailed) as exc:
        convert(ConversionRequest(input=source,output=tmp_path/"out",validation_level="physics"))
    package=exc.value.package
    combined=json.loads((package/"physics_evidence.json").read_text())
    evidence=combined["native"]
    assert evidence["steps"]==1000
    assert evidence["contact_count"]>0
    assert evidence["expected_pair"]==["asset_collision","probe"]
    assert len(combined["asset_sha256"])==64
    assert combined["status"]=="failed"
    assert combined["benchmark"]["status"]=="passed"
    assert evidence["max_penetration_m"]>evidence["penetration_limit_m"]

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
    with pytest.raises(ValidationFailed) as exc:
        convert(ConversionRequest(input=source,output=tmp_path/"out",validation_level="full"))
    package=exc.value.package
    assert (package/"previews/iso.png").is_file()
    assert json.loads((package/"validation_report.json").read_text())["render"]=="passed"
