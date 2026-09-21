"""碰撞声明和实际验证共用的唯一部件/工况解析契约。"""
def resolve_collision_case(metadata: dict) -> dict:
    request = metadata['request']
    body, mode = request.get('body_mode'), request.get('collision_mode')
    if body not in ('static', 'free'):
        raise ValueError('COLLISION_SCOPE_INVALID_BODY')
    other = 'probe' if body == 'static' else 'ground'
    if mode != 'supplied':
        return {'case_id': 'native_asset_probe_v1' if body == 'static' else 'native_asset_ground_v1',
                'target_geom': None if mode == 'none' else 'asset_collision',
                'required_pairs': [] if mode == 'none' else [['asset_collision', other]],
                'collision_geoms': [] if mode == 'none' else ['asset_collision'], 'limitations': []}
    proxy = metadata['collision_proxy']
    parts, target = proxy['parts'], proxy['target_index']
    if proxy.get('schema_version') != 1 or not parts or len(parts) > 32:
        raise ValueError('COLLISION_SCOPE_INVALID_PARTS')
    for i, part in enumerate(parts):
        expected = {'index': i, 'geom_name': f'asset_collision_{i:03d}',
                    'mesh_name': f'collision_mesh_{i:03d}', 'file': f'meshes/collision_{i:03d}.obj'}
        if type(part.get('index')) is not int or any(part.get(k) != v for k, v in expected.items()):
            raise ValueError('COLLISION_SCOPE_INVALID_MAPPING')
    if target != request.get('validation_collision_part') or (target is not None and
            (type(target) is not int or not 0 <= target < len(parts))):
        raise ValueError('COLLISION_SCOPE_INVALID_TARGET')
    if target is None and request.get('validation_level', 'compile') != 'compile':
        raise ValueError('COLLISION_SCOPE_TARGET_REQUIRED')
    names = [p['geom_name'] for p in parts]
    selected = None if target is None else names[target]
    return {'case_id': 'native_supplied_part_probe_v1' if body == 'static' else 'native_supplied_part_ground_v1',
            'target_geom': selected, 'required_pairs': [] if selected is None else [[selected, other]],
            'collision_geoms': names, 'limitations': ['SELECTED_COLLISION_PART_ONLY']}


def validate_collision_mapping(root, metadata, filenames):
    """已绑定清单仍须与所有 XML 的实际 geom→mesh→file 关系一致。"""
    import hashlib
    import xml.etree.ElementTree as ET
    if metadata['request'].get('collision_mode') != 'supplied':
        return
    case = resolve_collision_case(metadata)
    for part in metadata['collision_proxy']['parts']:
        if hashlib.sha256((root / part['file']).read_bytes()).hexdigest() != part.get('sha256'):
            raise ValueError('COLLISION_SCOPE_RESOURCE_DIGEST_CONFLICT')
    for filename in filenames:
        xml = ET.parse(root / filename).getroot()
        all_geoms = [g.get('name') for g in xml.findall('.//geom')
                     if (g.get('name') or '').startswith('asset_collision')]
        if sorted(all_geoms) != sorted(case['collision_geoms']):
            raise ValueError('COLLISION_SCOPE_GEOM_SET_CONFLICT')
        for part in metadata['collision_proxy']['parts']:
            geoms = xml.findall(".//geom[@name='" + part['geom_name'] + "']")
            meshes = xml.findall("./asset/mesh[@name='" + part['mesh_name'] + "']")
            if (len(geoms) != 1 or len(meshes) != 1 or geoms[0].get('mesh') != part['mesh_name']
                    or meshes[0].get('file') != part['file']):
                raise ValueError('COLLISION_SCOPE_XML_MAPPING_CONFLICT')
