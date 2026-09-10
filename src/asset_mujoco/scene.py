"""只保留展开后的独立视觉副本，不焊接 UV 接缝。"""
import numpy as np
import trimesh
from .inputs import inspect_input
from .transforms import normalization

def load_scene(request):
    path,raw=inspect_input(request.input)
    scene=trimesh.load(path,force="scene",process=False,maintain_order=True)
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
    return meshes,{"matrix":matrix.tolist(),"final_size_m":size.tolist(),"raw":raw}
