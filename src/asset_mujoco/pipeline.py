"""同文件系统 staging，先验证再原子发布；失败保留诊断。"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from .scene import load_scene
from .collision import hull
from .materials import export_visual
from .mjcf import document
from .contracts import ValidationResult

def atomic_publish(staging,final):
    libc=ctypes.CDLL(None,use_errno=True)
    # Linux renameat2 RENAME_NOREPLACE: 并发情况下也禁止覆盖。
    result=libc.renameat2(-100,os.fsencode(staging),-100,os.fsencode(final),1)
    if result:
        raise OSError(ctypes.get_errno(),"原子发布失败，未覆盖",str(final))

def convert(request):
    if request.collision_mode not in ("hull","none"):
        raise ValueError("复杂碰撞策略尚未实现（任务8）")
    started=time.monotonic()
    parent=request.output.resolve()
    parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix=".staging-",dir=parent))
    final=parent/(request.name+"_"+uuid.uuid4().hex[:12])
    try:
        meshes,info=load_scene(request)
        visuals=[]
        for i,mesh in enumerate(meshes):
            if len(mesh.vertices)<4:
                raise ValueError("VISUAL_MESH_UNSUPPORTED: 少于4顶点")
            item=export_visual(mesh,staging,i)
            item["shell"]=bool(np.linalg.matrix_rank(mesh.vertices-mesh.vertices.mean(axis=0))<3)
            visuals.append(item)
        if request.collision_mode=="hull":
            hull(meshes).export(staging/"meshes/collision.obj")
        for name,is_scene in (("model.xml",False),("scene.xml",True)):
            ET.ElementTree(document(request,visuals,info["final_size_m"],is_scene)).write(staging/name,encoding="utf-8",xml_declaration=True)
            model=mujoco.MjModel.from_xml_path(str(staging/name))
            mujoco.mj_forward(model,mujoco.MjData(model))
        result=ValidationResult(compile="passed",physics="not_applicable" if request.collision_mode=="none" else "not_run")
        metadata={"request":request.model_dump(mode="json"),"source_sha256":hashlib.sha256(request.input.read_bytes()).hexdigest(),
                  "transform":info["matrix"],"final_size_m":info["final_size_m"],"converter_mujoco":mujoco.__version__,
                  "host_compatibility":"pending","visuals":visuals,"hole_validation":"not_tested"}
        metadata["tolerances"]={"target":{"rtol":.02,"atol_m":1e-7},"geometry":{"rtol":1e-6,"atol_m":1e-7},"inertia":{"rtol":1e-8,"atol_kg_m2":1e-12}}
        metadata["physical_scale_verified"]=request.scale is not None or request.target_size_m is not None
        metadata["uniform_rule"]="dot(current_size,target_size)/dot(current_size,current_size)"
        metadata["material_approximations"]=["仅保留基础颜色/贴图；metallic、roughness 标量与 MuJoCo 光照并非完整 PBR 等价映射"]
        (staging/"conversion_manifest.json").write_text(json.dumps(metadata,indent=2))
        (staging/"validation_report.json").write_text(result.model_dump_json(indent=2))
        if request.validation_level!="compile":
            from .validation import validate_physics
            try:
                evidence=validate_physics(staging,request,info["final_size_m"])
            except Exception:
                result.physics="failed"
                (staging/"validation_report.json").write_text(result.model_dump_json(indent=2))
                raise
            (staging/"physics_evidence.json").write_text(json.dumps(evidence,indent=2))
            result.physics="passed"
            result.asset_physics_sha256=evidence["asset_sha256"]
        if request.validation_level=="full":
            from .rendering import render_package
            (staging/"validation_report.json").write_text(result.model_dump_json(indent=2))
            try:
                render_package(staging,info["final_size_m"])
            except Exception as error:
                result.render="unavailable" if "RENDER_UNAVAILABLE" in str(error) else "failed"
                (staging/"validation_report.json").write_text(result.model_dump_json(indent=2))
                raise
            result.render="passed"
        (staging/"validation_report.json").write_text(result.model_dump_json(indent=2))
        (staging/"conversion.log").write_text("duration_s="+str(time.monotonic()-started)+"\n")
        atomic_publish(staging,final)
        for name in ("model.xml","scene.xml"):
            model=mujoco.MjModel.from_xml_path(str(final/name))
            mujoco.mj_forward(model,mujoco.MjData(model))
        return final
    except Exception as error:
        if staging.exists():
            (staging/"failure.json").write_text(json.dumps({"error":str(error)}))
        raise
