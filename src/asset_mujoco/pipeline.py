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
from .manifest import record_layer,compile_resources,EvidenceIOError,refresh_report,checked_report,write_evidence
from .contact_profiles import contact_scene,profile_manifest

class ValidationFailed(ValueError):
    def __init__(self,package,result,*,code='ASSET_CONTACT_FAILED',stage='physics',reason=None,exit_code=5):
        self.package=package
        self.result=result
        self.code=code
        self.stage=stage
        self.reason=reason or result.physics_error or '原始配置验收未通过'
        self.exit_code=exit_code
        super().__init__(f'{code}: {self.reason}；诊断目录 {package}')

def diagnostic_io_error(package,stage,original,persistence):
    error=EvidenceIOError(f'EVIDENCE_IO_ERROR: {stage}; original={type(original).__name__}: {original}; persistence={persistence}; 诊断目录 {package}')
    error.package=package
    error.stage=stage
    error.original_error={'type':type(original).__name__,'message':str(original)}
    error.persistence_error={'type':type(persistence).__name__,'message':str(persistence)}
    return error

def publication_report(package,request):
    """核心发布准入：从磁盘核对证据，不能用聚合标签代替请求层级。"""
    try:
        result=checked_report(package)
    except (OSError,ValueError,KeyError,TypeError) as error:
        result=ValidationResult(evidence_issues=['report: unreadable_evidence: '+str(error)])
        raise ValidationFailed(package,result,code='EVIDENCE_INVALID',stage='publication',
                               reason='无法核对最终报告: '+str(error)) from error
    def reject(code,reason,exit_code=5):
        raise ValidationFailed(package,result,code=code,stage='publication',reason=reason,exit_code=exit_code)
    if result.physics=='failed':
        reject('ASSET_CONTACT_FAILED',result.physics_error or '原生物理验收失败')
    if result.evidence_issues or result.status=='INVALID_EVIDENCE':
        reject('EVIDENCE_INVALID','; '.join(result.evidence_issues) or '范围或必需物理证据无效')
    if result.status=='FAILED':
        reject('VALIDATION_FAILED',result.render_error or '必需验证层失败')
    missing=[]
    if result.compile!='passed':
        missing.append('compile=passed')
    if request.collision_mode=='none':
        if result.physics!='not_applicable':
            missing.append('physics=not_applicable')
    elif request.validation_level in ('physics','full'):
        if result.physics!='passed':
            missing.append('physics=passed')
        if result.validation_scope.evidence_status!='verified':
            missing.append('validation_scope=verified')
    if request.validation_level=='full' and result.render!='passed':
        missing.append('render=passed')
    if missing:
        unavailable=request.validation_level=='full' and result.render=='unavailable'
        reject('RENDER_UNAVAILABLE' if unavailable else 'VALIDATION_INCOMPLETE',
               '请求'+request.validation_level+'未完成: '+', '.join(missing),7 if unavailable else 5)
    return result

def atomic_publish(staging,final):
    libc=ctypes.CDLL(None,use_errno=True)
    # Linux renameat2 RENAME_NOREPLACE: 并发情况下也禁止覆盖。
    result=libc.renameat2(-100,os.fsencode(staging),-100,os.fsencode(final),1)
    if result:
        raise OSError(ctypes.get_errno(),"原子发布失败，未覆盖",str(final))

def convert(request):
    if request.collision_mode not in ("hull","none","supplied"):
        raise ValueError("复杂碰撞策略尚未实现（任务8）")
    if request.collision_mode=='supplied' and request.validation_level!='compile':
        raise ValueError('COLLISION_PROXY_PHYSICS_PENDING: 尚未接入显式部件验证')
    started=time.monotonic()
    parent=request.output.resolve()
    parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix=".staging-",dir=parent))
    final=parent/(request.name+"_"+uuid.uuid4().hex[:12])
    try:
        meshes,info=load_scene(request)
        collisions,proxy_manifest=None,None
        if request.collision_mode=='supplied':
            from .collision_proxy import load_collision_proxy,export_collision_proxy
            proxy=load_collision_proxy(request.collision_proxy_path,np.asarray(info['matrix']))
            if request.validation_collision_part is not None and request.validation_collision_part>=len(proxy.parts):
                raise ValueError('COLLISION_PROXY_TARGET_OUT_OF_RANGE')
            proxy_manifest=export_collision_proxy(proxy,staging)
            proxy_manifest['target_index']=request.validation_collision_part
            collisions=proxy_manifest['parts']
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
            ET.ElementTree(document(request,visuals,info["final_size_m"],is_scene,collisions)).write(staging/name,encoding="utf-8",xml_declaration=True)
            model=mujoco.MjModel.from_xml_path(str(staging/name))
            mujoco.mj_forward(model,mujoco.MjData(model))
        if request.contact_profile!='preserve':
            fixture=contact_scene(ET.parse(staging/'scene.xml').getroot(),info['final_size_m'],request.contact_profile)
            ET.ElementTree(fixture).write(staging/'contact_scene.xml')
            model=mujoco.MjModel.from_xml_path(str(staging/'contact_scene.xml'))
            mujoco.mj_forward(model,mujoco.MjData(model))
        result=ValidationResult(compile="passed",physics="not_applicable" if request.collision_mode=="none" else "not_run")
        metadata={"request":request.model_dump(mode="json"),"source_sha256":info["input_dependencies"][0]["sha256"],
                  "transform":info["matrix"],"final_size_m":info["final_size_m"],"converter_mujoco":mujoco.__version__,
                  "host_compatibility":"pending","visuals":visuals,"hole_validation":"not_tested"}
        metadata["tolerances"]={"target":{"rtol":.02,"atol_m":1e-7},"geometry":{"rtol":1e-6,"atol_m":1e-7},"inertia":{"rtol":1e-8,"atol_kg_m2":1e-12}}
        metadata["scope_reporting_version"]=1
        metadata["physical_scale_verified"]=False
        metadata['contact_profile']=profile_manifest(request.contact_profile)
        metadata["scale_evidence"]={
            "source":"user_multiplier" if request.scale is not None else "user_target_size" if request.target_size_m is not None else "format_default",
            "multiplier":request.scale,"target_size_m":request.target_size_m,
            "applied":True,"confirmation":None}
        metadata["uniform_rule"]="dot(current_size,target_size)/dot(current_size,current_size)"
        metadata["material_approximations"]=["仅保留基础颜色/贴图；metallic、roughness 标量与 MuJoCo 光照并非完整 PBR 等价映射"]
        metadata["input_dependencies"]=info["input_dependencies"]
        metadata["normal_provenance"]=info["normal_provenance"]
        if proxy_manifest is not None:
            metadata['collision_proxy']=proxy_manifest
        metadata["source_sha256"]=info["input_dependencies"][0]["sha256"]
        (staging/"conversion_manifest.json").write_text(json.dumps(metadata,indent=2))
        resources=compile_resources(staging)
        record_layer(staging,"compile","passed",resources,{"mujoco":mujoco.__version__,"forward":True})
        (staging/"validation_report.json").write_text(result.model_dump_json(indent=2))
        result=refresh_report(staging)
        if request.validation_level!="compile":
            from .validation import validate_physics
            try:
                validate_physics(staging,request,info["final_size_m"])
            except OSError as error:
                if isinstance(error,EvidenceIOError):
                    raise
                raise EvidenceIOError(f'EVIDENCE_IO_ERROR: physics persistence: {error}') from error
            # native已持久化完整范围，不能只更新旧对象的physics/hash。
            result=checked_report(staging)
        if request.validation_level=="full":
            from .rendering import render_package
            (staging/"validation_report.json").write_text(result.model_dump_json(indent=2))
            try:
                render_report=render_package(staging,info["final_size_m"])
            except Exception as error:
                result.render="unavailable" if "RENDER_UNAVAILABLE" in str(error) else "failed"
                result.render_error=str(error)
                try:
                    write_evidence(staging,'render_failure.json',{'status':result.render,'stage':'render',
                        'error':{'type':type(error).__name__,'message':str(error)}})
                    record_layer(staging,'render',result.render,resources+['render_failure.json'],
                        {'mujoco':mujoco.__version__,'failure_evidence':'render_failure.json'})
                    write_evidence(staging,'validation_report.json',result.model_dump())
                    result=checked_report(staging)
                except OSError as persistence:
                    raise diagnostic_io_error(staging,'render.diagnostics',error,persistence) from error
                if isinstance(error,OSError):
                    raise diagnostic_io_error(staging,'render',error,error) from error
                raise ValidationFailed(staging,result,code='RENDER_UNAVAILABLE' if result.render=='unavailable' else 'RENDER_FAILED',
                    stage='render',reason=str(error),exit_code=7 if result.render=='unavailable' else 5) from error
            result.render="passed"
            try:
                record_layer(staging,"render","passed",resources+["render_config.json","render_evidence.json"]+render_report["images"],
                             {"mujoco":mujoco.__version__,"backend":render_report["backend"]})
            except OSError as error:
                raise diagnostic_io_error(staging,'render.evidence',error,error) from error
        (staging/"validation_report.json").write_text(result.model_dump_json(indent=2))
        result=refresh_report(staging)
        (staging/"conversion.log").write_text("duration_s="+str(time.monotonic()-started)+"\n")
        result=publication_report(staging,request)
        atomic_publish(staging,final)
        for name in ("model.xml","scene.xml"):
            model=mujoco.MjModel.from_xml_path(str(final/name))
            mujoco.mj_forward(model,mujoco.MjData(model))
        return final
    except Exception as error:
        if staging.exists():
            try:
                diagnostic={'error':str(error),'type':type(error).__name__,'stage':getattr(error,'stage','conversion')}
                if isinstance(error,ValidationFailed):
                    diagnostic.update(code=error.code,result=error.result.model_dump())
                if isinstance(error,EvidenceIOError):
                    diagnostic.update(original_error=getattr(error,'original_error',None),persistence_error=getattr(error,'persistence_error',None))
                write_evidence(staging,'failure.json',diagnostic)
            except OSError as persistence:
                raise diagnostic_io_error(staging,'failure.diagnostics',error,persistence) from error
        raise
