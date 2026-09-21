"""供应代理必须保留全部部件、共用视觉矩阵并拒绝不可信凸体。"""
import numpy as np
import pytest
import trimesh


def test_proxy_uses_visual_transform_once(tmp_path):
    from asset_mujoco.collision_proxy import load_collision_proxy
    source = tmp_path / 'proxy.glb'
    mesh = trimesh.creation.box(extents=[2, 1, 1])
    mesh.apply_translation([4, 0, 0])
    mesh.export(source)
    matrix = np.diag([2., 3., 4., 1.])
    matrix[:3, 3] = [10, 20, 30]
    result = load_collision_proxy(source, matrix)
    assert len(result.parts) == 1
    np.testing.assert_allclose(result.parts[0].mesh.bounds,
        [[16, 18.5, 28], [20, 21.5, 32]], atol=1e-7)


def test_open_part_not_silently_discarded(tmp_path):
    from asset_mujoco.collision_proxy import load_collision_proxy
    good, bad = trimesh.creation.box(), trimesh.creation.box()
    bad.update_faces(np.arange(len(bad.faces) - 1))
    bad.apply_translation([3, 0, 0])
    path = tmp_path / 'mixed.glb'
    trimesh.Scene([good, bad]).export(path)
    with pytest.raises(ValueError, match='COLLISION_PROXY'):
        load_collision_proxy(path, np.eye(4))


@pytest.mark.parametrize('defect', ['open', 'duplicate', 'inward', 'flat', 'concave', 'nan'])
def test_invalid_part_rejected(defect):
    from asset_mujoco.collision_proxy import validate_convex_part
    mesh = trimesh.creation.box()
    if defect == 'open':
        mesh.update_faces(np.arange(11))
    elif defect == 'duplicate':
        mesh.faces = np.vstack([mesh.faces, mesh.faces[0]])
    elif defect == 'inward':
        mesh.faces = mesh.faces[:, ::-1]
    elif defect == 'flat':
        mesh.vertices[:, 2] = 0
    elif defect == 'concave':
        mesh.vertices[0] = [0.2, 0.2, 0.2]
    else:
        mesh.vertices[0, 0] = np.nan
    with pytest.raises(ValueError, match='COLLISION_PROXY'):
        validate_convex_part(mesh)


def test_instances_are_not_welded_together_and_mirror_is_correct(tmp_path):
    from asset_mujoco.collision_proxy import load_collision_proxy
    scene = trimesh.Scene()
    scene.add_geometry(trimesh.creation.box(), geom_name='box', node_name='a')
    mirrored = np.diag([-2., 3., 4., 1.])
    mirrored[:3, 3] = [5, 0, 0]
    scene.graph.update(frame_to='b', frame_from='world', matrix=mirrored, geometry='box')
    path = tmp_path / 'instances.glb'
    scene.export(path)
    result = load_collision_proxy(path, np.eye(4))
    assert len(result.parts) == 2
    assert [p.node for p in result.parts] == ['a', 'b']
    np.testing.assert_allclose(result.parts[1].mesh.bounds, [[4, -1.5, -2], [6, 1.5, 2]])
    assert all(p.mesh.volume > 0 for p in result.parts)


def test_exact_seam_vertices_are_welded_only_in_proxy(tmp_path):
    from asset_mujoco.collision_proxy import load_collision_proxy
    box = trimesh.creation.box()
    split = trimesh.Trimesh(vertices=box.vertices[box.faces].reshape(-1, 3),
        faces=np.arange(36).reshape(-1, 3), process=False)
    path = tmp_path / 'seams.glb'
    split.export(path)
    original = path.read_bytes()
    result = load_collision_proxy(path, np.eye(4))
    assert len(result.parts) == 1 and len(result.parts[0].mesh.vertices) == 8
    assert path.read_bytes() == original
    assert result.weld_records


@pytest.mark.parametrize('kind', ['float', 'negative', 'outside'])
def test_invalid_indices_are_not_coerced(kind):
    from types import SimpleNamespace
    from asset_mujoco.collision_proxy import validate_convex_part
    box = trimesh.creation.box()
    faces = np.asarray(box.faces).copy()
    if kind == 'float':
        faces = faces.astype(float)
        faces[0, 0] += 0.5
    else:
        faces[0, 0] = -1 if kind == 'negative' else 99
    with pytest.raises(ValueError, match='COLLISION_PROXY_INVALID_INDICES'):
        validate_convex_part(SimpleNamespace(vertices=box.vertices, faces=faces))


def test_too_many_parts_rejected(tmp_path):
    from asset_mujoco.collision_proxy import load_collision_proxy
    scene = trimesh.Scene()
    for i in range(33):
        scene.add_geometry(trimesh.creation.box(), node_name=f'n{i:02d}', geom_name=f'g{i:02d}')
    path = tmp_path / 'many.glb'
    scene.export(path)
    with pytest.raises(ValueError, match='COLLISION_PROXY_BUDGET_EXCEEDED'):
        load_collision_proxy(path, np.eye(4))


@pytest.mark.parametrize('budget', ['vertices', 'faces'])
def test_part_budget_is_enforced(budget):
    from types import SimpleNamespace
    from asset_mujoco.collision_proxy import validate_convex_part
    box = trimesh.creation.box()
    vertices = np.tile(box.vertices, (1251, 1)) if budget == 'vertices' else box.vertices
    faces = np.tile(box.faces, (4167, 1)) if budget == 'faces' else box.faces
    with pytest.raises(ValueError, match='COLLISION_PROXY_BUDGET_EXCEEDED'):
        validate_convex_part(SimpleNamespace(vertices=vertices, faces=faces))


def test_parent_child_transform_and_stable_order(tmp_path):
    from asset_mujoco.collision_proxy import load_collision_proxy
    outputs = []
    for order in [('b', 'a'), ('a', 'b')]:
        scene = trimesh.Scene()
        parent = np.eye(4)
        parent[:3, 3] = [10, 20, 30]
        scene.graph.update(frame_to='parent', frame_from='world', matrix=parent)
        for name in order:
            child = np.diag([2., 3., 4., 1.])
            child[:3, 3] = [1, 2, 3]
            scene.add_geometry(trimesh.creation.box(), node_name=name, geom_name=name,
                               parent_node_name='parent', transform=child)
        path = tmp_path / (''.join(order) + '.glb')
        scene.export(path)
        result = load_collision_proxy(path, np.eye(4))
        assert [p.node for p in result.parts] == ['a', 'b']
        np.testing.assert_allclose(result.parts[0].mesh.bounds, [[10, 20.5, 31], [12, 23.5, 35]])
        outputs.append([p.mesh.vertices.tolist() for p in result.parts])
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize('kind', ['mtl_parent', 'mtl_symlink', 'texture_parent', 'texture_symlink'])
def test_proxy_dependency_escape_is_rejected_before_read(tmp_path, monkeypatch, kind):
    import os
    from asset_mujoco.collision_proxy import load_collision_proxy
    root = tmp_path / 'input'
    root.mkdir()
    outside = tmp_path / 'secret'
    outside.write_bytes(b'not allowed to read')
    target = outside.stat()
    real_read = os.read
    reads = []
    def watched(fd, count):
        info = os.fstat(fd)
        if (info.st_dev, info.st_ino) == (target.st_dev, target.st_ino):
            reads.append(True)
        return real_read(fd, count)
    monkeypatch.setattr(os, 'read', watched)
    (root / 'link').symlink_to(outside)
    if kind.startswith('mtl'):
        reference = '../secret' if kind.endswith('parent') else 'link'
    else:
        reference = 'material.mtl'
        texture = '../secret' if kind.endswith('parent') else 'link'
        (root / reference).write_text('newmtl M\n  map_Kd ' + texture + '\n')
    obj = root / 'proxy.obj'
    obj.write_text('mtllib\t' + reference + '\nusemtl M\n' + trimesh.creation.box().export(file_type='obj'))
    with pytest.raises(ValueError):
        load_collision_proxy(obj, np.eye(4))
    assert reads == []


def test_proxy_valid_texture_dependency_hashes(tmp_path):
    import hashlib
    from PIL import Image
    from asset_mujoco.collision_proxy import load_collision_proxy
    sub = tmp_path / 'resources'
    sub.mkdir()
    Image.new('RGB', (2, 2), 'white').save(sub / 'white.png')
    (sub / 'material.mtl').write_text('newmtl M\n  map_Kd white.png\n')
    box = trimesh.creation.box().export(file_type='obj')
    path = tmp_path / 'proxy.obj'
    path.write_text('mtllib\tresources/material.mtl\nusemtl M\n' + box)
    result = load_collision_proxy(path, np.eye(4))
    assert len(result.parts) == 1
    records = {entry['path']: entry['sha256'] for entry in result.dependencies}
    for file in (path, sub / 'material.mtl', sub / 'white.png'):
        assert records[str(file)] == hashlib.sha256(file.read_bytes()).hexdigest()
