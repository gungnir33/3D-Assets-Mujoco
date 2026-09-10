import numpy as np
import trimesh
from asset_mujoco.collision import hull

def test_original_vertices_enclosed():
    mesh=trimesh.creation.icosphere(subdivisions=2)
    collision=hull([mesh])
    points=mesh.vertices
    distances=(points[:,None,:]-collision.triangles_center[None,:,:])*collision.face_normals[None,:,:]
    assert distances.sum(axis=2).max()<1e-7
