import numpy as np
import trimesh
from PIL import Image
from asset_mujoco.materials import export_visual

def textured(color=(255,0,0),factor=(1,1,1,1)):
    mesh=trimesh.creation.box()
    uv=np.zeros((len(mesh.vertices),2))
    mat=trimesh.visual.material.PBRMaterial(baseColorTexture=Image.new("RGB",(8,8),color),baseColorFactor=factor)
    mesh.visual=trimesh.visual.TextureVisuals(uv=uv,material=mat)
    return mesh

def test_pure_color_and_uv_preserved(tmp_path):
    mesh=textured()
    mesh.visual.uv[:]=[-2,3]
    info=export_visual(mesh,tmp_path,0)
    img=Image.open(tmp_path/info["texture"])
    assert img.getpixel((0,0))==(255,0,0)
    obj=(tmp_path/info["mesh"]).read_text()
    assert "vt -2" in obj
    assert len(mesh.vertices)==8

def test_factor_once_and_shared_texture(tmp_path):
    a=textured((255,255,255),(.5,1,1,1))
    b=textured((255,255,255),(1,.5,1,1))
    x=export_visual(a,tmp_path,0)
    y=export_visual(b,tmp_path,1)
    assert x["rgba"]==[1,1,1,1]
    assert Image.open(tmp_path/x["texture"]).getpixel((0,0))!=Image.open(tmp_path/y["texture"]).getpixel((0,0))
    assert a.visual.material.baseColorTexture.getpixel((0,0))==(255,255,255)
