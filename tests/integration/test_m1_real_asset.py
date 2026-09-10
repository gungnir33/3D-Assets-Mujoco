"""只读使用既有资产；不调用第一阶段 API、不写源目录。"""
import json
import os
from pathlib import Path
import shutil
import mujoco
import numpy as np
from PIL import Image
import pytest
import trimesh
from asset_mujoco.pipeline import convert
from asset_mujoco.contracts import ConversionRequest

def test_real_m1(tmp_path):
    source=Path(os.environ.get("ASSET_MUJOCO_REAL_INPUT","/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb"))
    if not source.is_file():
        pytest.skip("真实资产未提供，M1 不得据此声明通过")
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",name="penguin",source_up="y",yaw_deg=180,scale=.5,validation_level="full"))
    original=next(iter(trimesh.load(source,force="scene",process=False).geometry.values()))
    extracted=np.asarray(Image.open(package/"textures/visual_000.png"))
    assert np.array_equal(np.asarray(original.visual.material.baseColorTexture.convert("RGB")),extracted)
    visual=trimesh.load(package/"meshes/visual_000.obj",process=False)
    assert len(visual.faces)==len(original.faces)
    assert len(visual.vertices)==len(original.vertices)
    # 独立路径迁移后仍由原生引擎加载。
    moved=tmp_path/"relocated"
    shutil.copytree(package,moved)
    for filename in ("model.xml","scene.xml"):
        model=mujoco.MjModel.from_xml_path(str(moved/filename))
        mujoco.mj_forward(model,mujoco.MjData(model))
        assert model.ntex==1
        assert model.geom_matid[model.geom("visual_000").id]>=0
    state=json.loads((package/"validation_report.json").read_text())
    assert state["compile"]==state["physics"]==state["render"]=="passed"
    assert state["appearance_review"]=="pending"
    assert len(list((package/"previews").glob("*.png")))==4
