import json
import struct
import numpy as np
import pytest
import trimesh
from PIL import Image
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.pipeline import convert
from asset_mujoco.scene import load_scene

def white_glb(path,factor):
    mesh=trimesh.creation.box()
    mesh.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(mesh.vertices),2)),
        material=trimesh.visual.material.PBRMaterial(baseColorTexture=Image.new("RGB",(4,4),"white")))
    def edit(tree):
        pbr=tree["materials"][0]["pbrMetallicRoughness"]
        if factor is None:
            pbr.pop("baseColorFactor",None)
        else:
            pbr["baseColorFactor"]=factor
    data=trimesh.exchange.gltf.export_glb(trimesh.Scene(mesh),tree_postprocessor=edit)
    path.write_bytes(data)
    count=struct.unpack_from("<I",data,12)[0]
    return json.loads(data[20:20+count])

@pytest.mark.parametrize("factor",[None,[1,1,1,1],[.5,1,1,1]])
def test_raw_factor_pixels_and_binding(tmp_path,factor):
    source=tmp_path/"white.glb"
    doc=white_glb(source,factor)
    if factor is None:
        assert "baseColorFactor" not in doc["materials"][0]["pbrMetallicRoughness"]
    before=source.read_bytes()
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",validation_level="compile"))
    pixel=Image.open(package/"textures/visual_000.png").getpixel((0,0))
    # 线性0.5转换为sRGB后为188；输入float因子不得量化成灰色默认值。
    assert pixel==((188,255,255) if factor==[.5,1,1,1] else (255,255,255))
    assert source.read_bytes()==before
    import mujoco
    model=mujoco.MjModel.from_xml_path(str(package/"model.xml"))
    assert model.geom_matid[model.geom("visual_000").id]>=0
    assert model.ntex==1

def test_no_material_remains_gray(tmp_path):
    source=tmp_path/"plain.glb"
    trimesh.creation.box().export(source)
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",validation_level="compile"))
    record=json.loads((package/"conversion_manifest.json").read_text())
    assert record["visuals"][0]["rgba"]==[180/255,180/255,180/255,1]
    assert record["visuals"][0]["texture"] is None

@pytest.mark.parametrize("color",[False,True])
def test_obj_source_colors_not_loader_defaults(tmp_path,color):
    suffix=" 1 0 0" if color else ""
    obj="\n".join("v "+v+suffix for v in ("0 0 0","1 0 0","0 1 0","0 0 1"))+"\nf 1 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n"
    source=tmp_path/"asset.obj"
    source.write_text(obj)
    request=ConversionRequest(input=source,output=tmp_path/"out",source_up="z",scale=1,validation_level="compile")
    if color:
        with pytest.raises(ValueError,match="顶点色"):
            load_scene(request)
    else:
        meshes,_=load_scene(request)
        assert len(meshes)==1
