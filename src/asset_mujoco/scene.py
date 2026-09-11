"""只保留展开后的独立视觉副本，不焊接 UV 接缝。"""
import numpy as np
import trimesh
import io
from .inputs import inspect_input,RestrictedResolver,prepare_obj
from .transforms import normalization

def load_scene(request):
    path=request.input.resolve(strict=True)
    resolver=RestrictedResolver(path.parent)
    data=resolver.get(path.name)
    path,raw=inspect_input(path,data)
    required_images=set()
    if path.suffix.lower()==".obj":
        data,required_images=prepare_obj(data,resolver)
    scene=trimesh.load(io.BytesIO(data),file_type=path.suffix[1:].lower(),resolver=resolver,force="scene",process=False,maintain_order=True)
    resolver.assert_valid()
    if required_images and not any(getattr(getattr(g.visual,"material",None),"image",None) is not None for g in scene.geometry.values()):
        raise ValueError("必需纹理未加载，不允许灰模回退")
    meshes=[]
    for node in scene.graph.nodes_geometry:
        transform,geometry=scene.graph[node]
        mesh=scene.geometry[geometry].copy()
        if not isinstance(mesh,trimesh.Trimesh) or not len(mesh.vertices) or not len(mesh.faces):
            raise ValueError("空或非三角网格")
        if not np.isfinite(mesh.vertices).all() or np.any(mesh.area_faces<=0):
            raise ValueError("非有限坐标或退化三角形")
        mesh.apply_transform(transform)
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
    for mesh in meshes:
        mesh.apply_transform(matrix)
    return meshes,{"matrix":matrix.tolist(),"final_size_m":size.tolist(),"raw":raw,
                   "input_dependencies":list(resolver.state["records"].values())}
