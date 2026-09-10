import numpy as np
import trimesh
from scipy.spatial import ConvexHull

def hull(meshes):
    vertices=np.concatenate([mesh.vertices for mesh in meshes])
    if np.any(np.ptp(vertices,axis=0)<=0):
        raise ValueError("hull 碰撞要求非平面三维几何")
    result=trimesh.convex.convex_hull(vertices)
    equations=ConvexHull(result.vertices).equations
    for start in range(0,len(vertices),2048):
        if np.max(vertices[start:start+2048]@equations[:,:3].T+equations[:,3])>1e-7:
            raise ValueError("凸包未包含全部原始视觉顶点")
    if not result.is_watertight or result.volume<=0:
        raise ValueError("无效凸包")
    return result
