import numpy as np
import pytest
import trimesh
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.scene import load_scene
from asset_mujoco.materials import export_visual

N=np.array([1.,2.,3.])/np.sqrt(14)

def source_scene(path,case,with_normals=True):
    mesh=trimesh.creation.box()
    mesh.vertex_normals=np.tile(N,(len(mesh.vertices),1))
    scene=trimesh.Scene()
    if case=="parent_child":
        parent=np.array([[0,-1,0,2],[1,0,0,1],[0,0,1,3],[0,0,0,1]],float)
        scene.graph.update(frame_to="parent",matrix=parent)
        scene.add_geometry(mesh,node_name="child",parent_node_name="parent",transform=np.diag([2,1,3,1]))
    else:
        matrix=np.diag([-1,1,1,1]) if case=="mirror" else np.eye(4)
        scene.add_geometry(mesh,node_name="object",transform=matrix)
    path.write_bytes(trimesh.exchange.gltf.export_glb(scene,include_normals=with_normals))
    return mesh

@pytest.mark.parametrize("case,kwargs,linear",[
    ("identity",{},np.eye(3)),
    ("rotation",{"source_up":"y","yaw_deg":90},[[0,0,1],[1,0,0],[0,1,0]]),
    ("nonuniform",{"target_size_m":[2,3,4],"scale_mode":"fit_axes"},np.diag([2,3,4])),
    ("mirror",{},np.diag([-1,1,1])),
    ("parent_child",{"target_size_m":[4,6,6],"scale_mode":"fit_axes"},[[0,-4,0],[6,0,0],[0,0,6]]),
])
def test_source_normals_load_transform_export(tmp_path,case,kwargs,linear):
    source=tmp_path/"custom.glb"
    original=source_scene(source,case)
    args=dict(input=source,output=tmp_path/"out",source_up="z",validation_level="compile")
    args.update(kwargs)
    meshes,info=load_scene(ConversionRequest(**args))
    exported=export_visual(meshes[0],tmp_path,0)
    lines=(tmp_path/exported["mesh"]).read_text().splitlines()
    normals=np.array([[float(x) for x in line.split()[1:]] for line in lines if line.startswith("vn ")])
    expected=np.linalg.inv(np.array(linear,dtype=float)).T@N
    expected/=np.linalg.norm(expected)
    np.testing.assert_allclose(normals,np.tile(expected,(len(normals),1)),rtol=1e-6,atol=2e-7)
    faces=[[token.split("/") for token in line.split()[1:]] for line in lines if line.startswith("f ")]
    assert all(int(token[0])==int(token[2]) for face in faces for token in face)
    emitted=np.array([[int(token[0])-1 for token in face] for face in faces])
    expected_faces=original.faces[:,::-1] if np.linalg.det(linear)<0 else original.faces
    np.testing.assert_array_equal(emitted,expected_faces)
    assert info["normal_provenance"][0]["normals_source"]=="source"

def test_missing_normals_marked_computed(tmp_path):
    source=tmp_path/"plain.glb"
    source_scene(source,"identity",with_normals=False)
    meshes,info=load_scene(ConversionRequest(input=source,output=tmp_path/"out",source_up="z",validation_level="compile"))
    exported=export_visual(meshes[0],tmp_path,0)
    assert info["normal_provenance"][0]["normals_source"]=="computed"
    assert "vn " in (tmp_path/exported["mesh"]).read_text()

def test_obj_corner_normals_and_uv_seams_preserved(tmp_path):
    source=tmp_path/"seams.obj"
    source.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nvt 0 0\nvt 1 0\nvt 0 1\nvt .5 .5\nvn 0 0 1\nvn 0 1 0\nf 1/1/1 2/2/1 3/3/1\nf 1/4/2 4/2/2 2/3/2\n")
    meshes,_=load_scene(ConversionRequest(input=source,output=tmp_path/"out",source_up="z",scale=1,validation_level="compile"))
    item=export_visual(meshes[0],tmp_path,0)
    rows=(tmp_path/item["mesh"]).read_text().splitlines()
    normals=np.array([[float(x) for x in row.split()[1:]] for row in rows if row.startswith("vn ")])
    uv=np.array([[float(x) for x in row.split()[1:]] for row in rows if row.startswith("vt ")])
    corners=[[tuple(map(int,t.split("/"))) for t in row.split()[1:]] for row in rows if row.startswith("f ")]
    assert len(normals)==6
    np.testing.assert_allclose(normals[[t[2]-1 for t in corners[0]]],[[0,0,1]]*3,atol=2e-7)
    np.testing.assert_allclose(normals[[t[2]-1 for t in corners[1]]],[[0,1,0]]*3,atol=2e-7)
    np.testing.assert_allclose(uv[corners[0][0][1]-1],[0,0])
    np.testing.assert_allclose(uv[corners[1][0][1]-1],[.5,.5])
