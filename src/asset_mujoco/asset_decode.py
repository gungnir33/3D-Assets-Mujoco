"""视觉和碰撞代理共用的只读、受限资产解码。"""
from dataclasses import dataclass
from pathlib import Path
import io
import numpy as np
import trimesh
from trimesh.exchange.gltf import load_glb
from trimesh.exchange.obj import load_obj
from .inputs import inspect_input, RestrictedResolver, prepare_obj


@dataclass
class DecodedAsset:
    scene: trimesh.Scene
    source_normals: dict
    dependencies: list
    raw: dict | None


def decode_asset(path: Path) -> DecodedAsset:
    path = Path(path).resolve(strict=True)
    resolver = RestrictedResolver(path.parent)
    data = resolver.get(path.name)
    path, raw = inspect_input(path, data)
    required_images = set()
    if path.suffix.lower() == '.obj':
        data, required_images = prepare_obj(data, resolver)
    if raw is not None:
        decoded = load_glb(io.BytesIO(data), resolver=resolver, process=False, merge_primitives=False)
    else:
        decoded = load_obj(io.BytesIO(data), resolver=resolver, process=False,
                           maintain_order=False, group_material=False)
    source_normals = {}
    scene = trimesh.Scene(base_frame=decoded.get('base_frame', 'world'))
    for name, attributes in decoded['geometry'].items():
        # Trimesh 会把 faces 强制转 int64；必须在构造前拒绝源索引丢精度。
        faces = np.asarray(attributes.get('faces'))
        vertices = np.asarray(attributes.get('vertices'))
        if (faces.ndim != 2 or faces.shape[1] != 3 or faces.dtype.kind not in 'iu'
                or not len(faces) or faces.min() < 0 or vertices.ndim != 2
                or faces.max() >= len(vertices)):
            raise ValueError('INVALID_SOURCE_INDICES: expected valid integer triangle indices')
        normals = attributes.get('vertex_normals')
        if normals is not None:
            source_normals[name] = np.array(normals, dtype=float, copy=True)
        scene.geometry[name] = trimesh.Trimesh(**attributes)
    for edge in decoded['graph']:
        scene.graph.update(**edge)
    if raw is not None:
        declared = sum('NORMAL' in p.get('attributes', {}) for mesh in raw.get('meshes', [])
                       for p in mesh.get('primitives', []))
        if declared != len(source_normals):
            raise ValueError('源 NORMAL 与解码结果不一致')
    elif any(line.startswith('vn ') for line in data.decode().splitlines()) and len(source_normals) != len(scene.geometry):
        raise ValueError('源 OBJ 法线索引不完整或解码丢失')
    resolver.assert_valid()
    if required_images and not any(getattr(getattr(g.visual, 'material', None), 'image', None)
                                   is not None for g in scene.geometry.values()):
        raise ValueError('必需纹理未加载，不允许灰模回退')
    return DecodedAsset(scene, source_normals, list(resolver.state['records'].values()), raw)
