import builtins
import hashlib
import os
from pathlib import Path
import pytest
from PIL import Image
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.scene import load_scene

OBJ="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nvt 0 0\nvt 1 0\nvt 0 1\nvt 1 1\nusemtl paint\nf 1/1 3/3 2/2\nf 1/1 2/2 4/4\nf 2/2 3/3 4/4\nf 3/3 1/1 4/4\n"

def request(path):
    return ConversionRequest(input=path,output=path.parent/"out",source_up="z",scale=1,validation_level="compile")

def test_tab_mtl_and_indented_texture_record_dependencies(tmp_path):
    root=tmp_path/"input"
    (root/"materials").mkdir(parents=True)
    Image.new("RGB",(2,2),"white").save(root/"materials/white.png")
    (root/"materials/paint.mtl").write_text("newmtl paint\nKd 1 1 1\n  map_Kd white.png\n")
    path=root/"model.obj"
    path.write_text("mtllib\tmaterials/paint.mtl\n"+OBJ)
    meshes,info=load_scene(request(path))
    image=meshes[0].visual.material.image
    assert image.getpixel((0,0))==(255,255,255)
    dependencies=info["input_dependencies"]
    assert {Path(d["path"]).name for d in dependencies}=={"model.obj","paint.mtl","white.png"}
    assert all(len(d["sha256"])==64 for d in dependencies)

@pytest.mark.parametrize("reference",["../outside.png","link.png"])
def test_outside_bytes_never_read(tmp_path,monkeypatch,reference):
    root=tmp_path/"input"
    root.mkdir()
    outside=tmp_path/"outside.png"
    Image.new("RGB",(2,2),"red").save(outside)
    (root/"link.png").symlink_to(outside)
    (root/"paint.mtl").write_text("newmtl paint\n  map_Kd "+reference+"\n")
    path=root/"model.obj"
    path.write_text("mtllib\tpaint.mtl\n"+OBJ)
    opened=[]
    real_open=builtins.open
    def observe(file,*args,**kwargs):
        if isinstance(file,(str,Path)) and Path(file).resolve()==outside:
            opened.append(str(file))
        return real_open(file,*args,**kwargs)
    monkeypatch.setattr(builtins,"open",observe)
    outside_identity=(outside.stat().st_dev,outside.stat().st_ino)
    real_read=os.read
    def observe_read(fd,count):
        info=os.fstat(fd)
        if (info.st_dev,info.st_ino)==outside_identity:
            opened.append("outside_fd_read")
        return real_read(fd,count)
    monkeypatch.setattr(os,"read",observe_read)
    with pytest.raises(ValueError):
        load_scene(request(path))
    assert opened==[]

def test_resolver_latches_rejection_and_cannot_fallback(tmp_path):
    from asset_mujoco.inputs import RestrictedResolver
    root=tmp_path/"input"
    root.mkdir()
    (tmp_path/"outside.mtl").write_text("private synthetic material")
    resolver=RestrictedResolver(root)
    with pytest.raises(ValueError):
        resolver.get("../outside.mtl")
    with pytest.raises(ValueError):
        resolver.assert_valid()

def test_regular_textured_obj(tmp_path):
    Image.new("RGB",(2,2),(240,20,30)).save(tmp_path/"color.png")
    (tmp_path/"paint.mtl").write_text("newmtl paint\nKd 1 1 1\nmap_Kd color.png\n")
    path=tmp_path/"model.obj"
    path.write_text("mtllib paint.mtl\n"+OBJ)
    meshes,info=load_scene(request(path))
    assert meshes[0].visual.material.image.getpixel((0,0))==(240,20,30)
    assert len(info["input_dependencies"])==3

def test_missing_texture_must_not_become_gray(tmp_path):
    path=tmp_path/"model.obj"
    path.write_text("mtllib\tpaint.mtl\n"+OBJ)
    (tmp_path/"paint.mtl").write_text("newmtl paint\n  map_Kd missing.png\n")
    with pytest.raises(ValueError):
        load_scene(request(path))
