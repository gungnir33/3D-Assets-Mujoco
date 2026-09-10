import pytest
from pydantic import ValidationError
from asset_mujoco.contracts import ConversionRequest, ValidationResult

def test_static_optional_inertia():
    assert ConversionRequest(input="x.glb", output="out").inertia_mode is None

@pytest.mark.parametrize("kw", [{"body_mode":"free"}, {"scale":1,"target_size_m":[1,1,1]}, {"yaw_deg":float("nan")}, {"collision_mode":"none","validation_level":"full"}])
def test_bad_contract(kw):
    with pytest.raises(ValidationError):
        ConversionRequest(input="x.glb", output="out", **kw)

def test_visual_only_roundtrip():
    r = ValidationResult(compile="passed", physics="not_applicable")
    assert ValidationResult.model_validate_json(r.model_dump_json()).aggregate() == "VISUAL_ONLY"

def test_physics_requires_asset_evidence():
    r = ValidationResult(compile="passed", physics="passed")
    assert r.aggregate() == "INVALID_EVIDENCE"
    r.asset_physics_sha256 = "a"*64
    assert r.aggregate() == "PHYSICS_VALIDATED"
    r.render = "passed"
    assert r.aggregate() != "FULLY_VALIDATED"
