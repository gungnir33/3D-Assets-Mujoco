import pytest
from asset_mujoco.inputs import validate_glb_features, resource_path

@pytest.mark.parametrize("doc",[
 {"extensionsUsed":["KHR_draco_mesh_compression"]},
 {"skins":[{}]},
 {"meshes":[{"primitives":[{"attributes":{"POSITION":0,"COLOR_0":1}}]}]},
 {"meshes":[{"primitives":[{"attributes":{"POSITION":0},"targets":[{}]}]}]},
 {"materials":[{"alphaMode":"BLEND"}]},
 {"textures":[{"sampler":0}],"samplers":[{"wrapS":33071}]},
])
def test_raw_unsupported_rejected(doc):
    with pytest.raises(ValueError):
        validate_glb_features(doc)

def test_plain_supported():
    validate_glb_features({"meshes":[{"primitives":[{"attributes":{"POSITION":0,"TEXCOORD_0":1}}]}]})

def test_traversal(tmp_path):
    with pytest.raises(ValueError):
        resource_path(tmp_path,"../private.png")
