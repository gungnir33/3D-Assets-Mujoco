import json
from pathlib import Path
import pytest
import trimesh
import yaml
from pydantic import ValidationError
from asset_mujoco.cli import main
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.pipeline import convert

def test_default_full_does_not_silently_downgrade(tmp_path,monkeypatch,capsys):
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    def unavailable(*args):
        raise RuntimeError("RENDER_UNAVAILABLE: synthetic unavailable backend")
    monkeypatch.setattr("asset_mujoco.rendering.render_package",unavailable)
    assert main(["convert",str(source),"--output",str(tmp_path/"out")])==7
    assert "RENDER_UNAVAILABLE" in capsys.readouterr().out
    assert main(["convert",str(source),"--output",str(tmp_path/"out"),"--validation-level","compile"])==0
    assert json.loads(capsys.readouterr().out)["status"]=="COMPILE_VALIDATED"

def test_config_and_api_defaults_are_full():
    defaults=yaml.safe_load((Path(__file__).parents[2]/"config/default.yaml").read_text())["defaults"]
    assert defaults["validation_level"]=="full"
    assert ConversionRequest(input="x.glb",output="out").validation_level=="full"

def test_visual_only_requires_explicit_compile():
    with pytest.raises(ValidationError):
        ConversionRequest(input="x.glb",output="out",collision_mode="none")
    assert ConversionRequest(input="x.glb",output="out",collision_mode="none",validation_level="compile").validation_level=="compile"

@pytest.mark.parametrize("kwargs,source",[({"scale":.5},"user_multiplier"),({"target_size_m":[2,2,2]},"user_target_size"),({},"format_default")])
def test_user_scale_is_not_verified_measurement(tmp_path,kwargs,source):
    path=tmp_path/"box.glb"
    trimesh.creation.box().export(path)
    package=convert(ConversionRequest(input=path,output=tmp_path/"out",validation_level="compile",**kwargs))
    record=json.loads((package/"conversion_manifest.json").read_text())
    assert record["physical_scale_verified"] is False
    assert record["scale_evidence"]["source"]==source
    assert record["scale_evidence"]["confirmation"] is None
