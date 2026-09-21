"""仅接受用户提供的闭合凸部件；不修复、不简化、不替换为凸包。"""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import ConvexHull, QhullError
from .asset_decode import decode_asset


@dataclass
class ProxyPart:
    index: int
    node: str
    geometry: str
    first_face: int
    mesh: trimesh.Trimesh
    checks: dict


@dataclass
class CollisionProxy:
    parts: list[ProxyPart]
    dependencies: list[dict]
    transform: list
    weld_records: list[dict]


def _reject(reason):
    raise ValueError('COLLISION_PROXY_' + reason)


def _arrays(mesh):
    vertices, faces = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices) or not np.isfinite(vertices).all():
        _reject('INVALID_VERTICES')
    if (faces.ndim != 2 or faces.shape[1] != 3 or not len(faces)
            or faces.dtype.kind not in 'iu' or faces.min() < 0 or faces.max() >= len(vertices)):
        _reject('INVALID_INDICES')
    return vertices, faces


def _components(faces):
    """按共享边分组，包含开放及非法分量，不使用 only_watertight。"""
    edge_faces = {}
    adjacency = [set() for _ in faces]
    for i, face in enumerate(faces):
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge = tuple(sorted((int(a), int(b))))
            for other in edge_faces.get(edge, []):
                adjacency[i].add(other)
                adjacency[other].add(i)
            edge_faces.setdefault(edge, []).append(i)
    unseen = set(range(len(faces)))
    groups = []
    while unseen:
        todo = [min(unseen)]
        group = []
        while todo:
            i = todo.pop()
            if i not in unseen:
                continue
            unseen.remove(i)
            group.append(i)
            todo.extend(adjacency[i] & unseen)
        groups.append(np.array(sorted(group), dtype=int))
    return groups


def validate_convex_part(mesh: trimesh.Trimesh) -> dict:
    vertices, faces = _arrays(mesh)
    if len(vertices) > 10000 or len(faces) > 50000:
        _reject('BUDGET_EXCEEDED')
    extent = np.ptp(vertices, axis=0)
    eps = float(1e-7 + 1e-6 * extent.max())
    centered = vertices - vertices.mean(axis=0)
    if extent.min() <= 10 * eps or np.linalg.svd(centered, compute_uv=False)[-1] <= eps:
        _reject('NUMERICALLY_AMBIGUOUS')
    if len(np.unique(np.sort(faces, axis=1), axis=0)) != len(faces):
        _reject('DUPLICATE_FACE')
    edges = np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    unique, inverse, counts = np.unique(np.sort(edges, axis=1), axis=0,
                                       return_inverse=True, return_counts=True)
    signs = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    if np.any(counts != 2) or np.any(np.bincount(inverse, weights=signs) != 0):
        _reject('NOT_CLOSED_OR_INCONSISTENT')
    if len(vertices) - len(unique) + len(faces) != 2 or len(_components(faces)) != 1:
        _reject('INVALID_TOPOLOGY')
    triangles = centered[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    norms = np.linalg.norm(cross, axis=1)
    if np.any(norms <= eps * eps):
        _reject('DEGENERATE_FACE')
    normals = cross / norms[:, None]
    volume = float(np.einsum('ij,ij->i', triangles[:, 0], cross).sum() / 6)
    if volume <= 0:
        _reject('NONPOSITIVE_VOLUME')
    max_distance = -np.inf
    for start in range(0, len(faces), 128):
        stop = start + 128
        offsets = np.einsum('ij,ij->i', triangles[start:stop, 0], normals[start:stop])
        distances = centered @ normals[start:stop].T - offsets
        max_distance = max(max_distance, float(distances.max()))
        if max_distance > eps:
            _reject('NONCONVEX')
    try:
        hull = ConvexHull(centered)
    except QhullError as error:
        raise ValueError('COLLISION_PROXY_NUMERICALLY_AMBIGUOUS') from error
    volume_tolerance = float(1e-6 * hull.volume + eps * hull.area)
    if abs(volume - hull.volume) > volume_tolerance:
        _reject('HULL_VOLUME_MISMATCH')
    # 每个源顶点位于独立凸包支持边界上，不接受隐藏内部顶点。
    support = np.full(len(centered), -np.inf)
    for start in range(0, len(hull.equations), 128):
        eq = hull.equations[start:start + 128]
        support = np.maximum(support, (centered @ eq[:, :3].T + eq[:, 3]).max(axis=1))
    if np.any(np.abs(support) > eps):
        _reject('HULL_SUPPORT_MISMATCH')
    return {'closed': True, 'convex': True, 'volume_m3': volume,
            'distance_tolerance_m': eps, 'volume_tolerance_m3': volume_tolerance,
            'max_outside_distance_m': max_distance, 'hull_volume_m3': float(hull.volume)}


def load_collision_proxy(path: Path, global_transform: np.ndarray) -> CollisionProxy:
    decoded = decode_asset(path)
    matrix = np.asarray(global_transform, dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all() or not np.allclose(matrix[3], [0, 0, 0, 1]):
        _reject('INVALID_TRANSFORM')
    parts, records = [], []
    total_faces = 0
    for node in sorted(decoded.scene.graph.nodes_geometry):
        world, geometry = decoded.scene.graph[node]
        source = decoded.scene.geometry[geometry]
        vertices, faces = _arrays(source)
        total_faces += len(faces)
        if total_faces > 50000:
            _reject('BUDGET_EXCEEDED')
        welded, inverse = np.unique(vertices, axis=0, return_inverse=True)
        faces = inverse[faces]
        records.append({'node': node, 'geometry': geometry, 'tolerance': 0,
                        'vertices_before': len(vertices), 'vertices_after': len(welded)})
        combined = matrix @ np.asarray(world)
        determinant = np.linalg.det(combined[:3, :3])
        if not np.isfinite(combined).all() or abs(determinant) < 1e-30:
            _reject('INVALID_TRANSFORM')
        transformed = trimesh.transform_points(welded, combined)
        if determinant < 0:
            faces = faces[:, ::-1]
        for indices in _components(faces):
            selected = faces[indices]
            used, remap = np.unique(selected, return_inverse=True)
            part = trimesh.Trimesh(vertices=transformed[used], faces=remap.reshape(-1, 3), process=False)
            checks = validate_convex_part(part)
            parts.append(ProxyPart(len(parts), node, geometry, int(indices[0]), part, checks))
            if len(parts) > 32:
                _reject('BUDGET_EXCEEDED')
    if not parts:
        _reject('EMPTY')
    return CollisionProxy(parts, decoded.dependencies, matrix.tolist(), records)


def export_collision_proxy(proxy: CollisionProxy, root: Path) -> dict:
    import hashlib
    root = Path(root)
    (root / 'meshes').mkdir(parents=True, exist_ok=True)
    parts = []
    for part in proxy.parts:
        relative = f'meshes/collision_{part.index:03d}.obj'
        part.mesh.export(root / relative)
        parts.append({'index': part.index, 'node': part.node, 'geometry': part.geometry,
            'first_face': part.first_face, 'bounds_m': part.mesh.bounds.tolist(),
            'vertices': len(part.mesh.vertices), 'faces': len(part.mesh.faces), 'checks': part.checks,
            'file': relative, 'sha256': hashlib.sha256((root / relative).read_bytes()).hexdigest(),
            'geom_name': f'asset_collision_{part.index:03d}',
            'mesh_name': f'collision_mesh_{part.index:03d}'})
    return {'schema_version': 1, 'source_dependencies': proxy.dependencies,
            'transform': proxy.transform, 'weld_records': proxy.weld_records,
            'parts': parts, 'collision_fidelity': 'user_supplied'}
