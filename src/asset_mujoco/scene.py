"""只保留展开后的独立视觉副本，不焊接 UV 接缝。"""
import numpy as np
import trimesh
import io
from .inputs import inspect_input,RestrictedResolver,prepare_obj
from .transforms import normalization
from trimesh.exchange.gltf import load_glb
from trimesh.exchange.obj import load_obj

def load_scene(request):
    path=request.input.resolve(strict=True)
    resolver=RestrictedResolver(path.parent)
    data=resolver.get(path.name)
    path,raw=inspect_input(path,data)
    required_images=set()
    if path.suffix.lower()==".obj":
        data,required_images=prepare_obj(data,resolver)
    if raw is not None:
        decoded=load_glb(io.BytesIO(data),resolver=resolver,process=False,merge_primitives=False)
    else:
        # 必须拆开 (v,vt,vn) 组合；maintain_order=True 会折叠硬边/UV seam。
        decoded=load_obj(io.BytesIO(data),resolver=resolver,process=False,maintain_order=False,group_material=False)
    source_normals={}
    scene=trimesh.Scene(base_frame=decoded.get("base_frame","world"))
    for name,attributes in decoded["geometry"].items():
        normals=attributes.get("vertex_normals")
        if normals is not None:
            source_normals[name]=np.array(normals,dtype=float,copy=True)
        scene.geometry[name]=trimesh.Trimesh(**attributes)
    for edge in decoded["graph"]:
        scene.graph.update(**edge)
    if raw is not None:
        declared=sum("NORMAL" in p.get("attributes",{}) for mesh in raw.get("meshes",[]) for p in mesh.get("primitives",[]))
        if declared!=len(source_normals):
            raise ValueError("源 NORMAL 与解码结果不一致")
    elif any(line.startswith("vn ") for line in data.decode().splitlines()) and len(source_normals)!=len(scene.geometry):
        raise ValueError("源 OBJ 法线索引不完整或解码丢失")
    resolver.assert_valid()
    if required_images and not any(getattr(getattr(g.visual,"material",None),"image",None) is not None for g in scene.geometry.values()):
        raise ValueError("必需纹理未加载，不允许灰模回退")
    meshes=[]
    records=[]
    for node in scene.graph.nodes_geometry:
        transform,geometry=scene.graph[node]
        mesh=scene.geometry[geometry].copy()
        if not isinstance(mesh,trimesh.Trimesh) or not len(mesh.vertices) or not len(mesh.faces):
            raise ValueError("空或非三角网格")
        if not np.isfinite(mesh.vertices).all() or np.any(mesh.area_faces<=0):
            raise ValueError("非有限坐标或退化三角形")
        original_vertices=np.asarray(mesh.vertices).copy()
        original_faces=np.asarray(mesh.faces).copy()
        normals=source_normals.get(geometry)
        if normals is not None and (normals.shape!=original_vertices.shape or not np.isfinite(normals).all() or np.any(np.linalg.norm(normals,axis=1)<=0)):
            raise ValueError("源法线无效")
        mesh.vertices=trimesh.transform_points(original_vertices,transform)
        records.append((node,geometry,np.asarray(transform),original_vertices,original_faces,normals))
        meshes.append(mesh)
    if not meshes or sum(len(m.faces) for m in meshes)>5_000_000:
        raise ValueError("空 Scene 或超过面数限制")
    if raw:
        # 当前仅接受可逐 primitive 对应的实例，复杂映射显式失败。
        expected=sum(len(raw["meshes"][n["mesh"]]["primitives"]) for n in raw.get("nodes",[]) if "mesh" in n)
        if len(meshes)!=expected:
            raise ValueError("原始 primitive 与加载结果数量不一致")
    all_vertices=np.concatenate([m.vertices for m in meshes])
    matrix,size=normalization(all_vertices,request)
    provenance=[]
    for mesh,(node,geometry,world,vertices,faces,normals) in zip(meshes,records):
        combined=matrix@world
        linear=combined[:3,:3]
        if not np.isfinite(combined).all() or abs(np.linalg.det(linear))<1e-30:
            raise ValueError("不可逆几何变换")
        mesh.vertices=trimesh.transform_points(vertices,combined)
        mesh.faces=faces[:,::-1] if np.linalg.det(linear)<0 else faces
        if normals is None:
            transformed=np.asarray(mesh.vertex_normals).copy()
            origin="computed"
        else:
            transformed=normals@np.linalg.inv(linear)
            transformed/=np.linalg.norm(transformed,axis=1)[:,None]
            origin="source"
        # 独立显式数据，不依赖 copy/apply_transform 的缓存行为。
        mesh.metadata["export_normals"]=transformed
        mesh.metadata["normals_source"]=origin
        provenance.append({"node":node,"primitive_geometry":geometry,"normals_source":origin,
                           "count":len(transformed),"mapping":"vertex_and_face_corner_indices",
                           "combined_transform":combined.tolist(),"mirrored":bool(np.linalg.det(linear)<0)})
    return meshes,{"matrix":matrix.tolist(),"final_size_m":size.tolist(),"raw":raw,
                   "normal_provenance":provenance,
                   "input_dependencies":list(resolver.state["records"].values())}
