"""只保留展开后的独立视觉副本，不焊接 UV 接缝。"""
import numpy as np
import trimesh
from .asset_decode import decode_asset
from .transforms import normalization

def load_scene(request):
    decoded=decode_asset(request.input)
    scene,source_normals,raw=decoded.scene,decoded.source_normals,decoded.raw
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
                   "input_dependencies":decoded.dependencies}
