import json
from pathlib import Path
import pytest


def test_defaults_and_prompt_limit(tmp_path):
    from asset_mujoco.chain_contracts import validate_generation
    data = validate_generation('text', {'prompt': 'red barrier'}, tmp_path)
    assert data == dict(prompt='red barrier', texture=True, seed=12345, format='glb',
                        face_count=40000, shape_steps=50)
    for prompt in (' ', 'x' * 1001):
        with pytest.raises(ValueError):
            validate_generation('text', {'prompt': prompt}, tmp_path)


@pytest.mark.parametrize('payload', [{'format': 'fbx'}, {'seed': -1}, {'shape_steps': 201},
    {'face_count': 99}, {'extra': 1}, {'seed': float('nan')}])
def test_bad_generation_rejected(tmp_path, payload):
    from asset_mujoco.chain_contracts import validate_generation
    with pytest.raises(ValueError):
        validate_generation('text', {'prompt': 'box'} | payload, tmp_path)


@pytest.mark.parametrize('config', [{'input': 'private.glb'}, {'output': 'other'},
    {'scale': 1, 'target_size_m': [1, 1, 1]}, {'contact_profile': 'unknown'}, {'seed': 4}])
def test_invalid_conversion_before_generation(tmp_path, config):
    from asset_mujoco.chain_contracts import load_conversion_config
    path = tmp_path / 'convert.json'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_conversion_config(path, 'glb')


@pytest.mark.parametrize('text', ['{"a":NaN}', '{"a":1,"a":2}', '[]', '{"a":Infinity}', '{"a":1e999}'])
def test_json_rejects_ambiguous_values(tmp_path, text):
    from asset_mujoco.chain_contracts import read_json
    file = tmp_path / 'input.json'
    file.write_text(text)
    with pytest.raises(ValueError):
        read_json(file)


def test_images_texture_and_proxy_resolve_relative_to_config(tmp_path):
    from PIL import Image
    from asset_mujoco.chain_contracts import validate_generation, load_conversion_config
    Image.new('RGB', (2, 2)).save(tmp_path / 'image.png')
    (tmp_path / 'mesh.glb').write_bytes(b'format validation belongs to converter')
    for endpoint, payload in [('image', {'image': 'image.png'}),
                              ('texture', {'mesh': 'mesh.glb', 'condition_image': 'image.png'})]:
        result = validate_generation(endpoint, payload, tmp_path)
        for key in payload:
            assert result[key] == str(tmp_path / payload[key])
    file = tmp_path / 'config.json'
    file.write_text(json.dumps(dict(collision_mode='supplied', collision_proxy_path='mesh.glb',
                                   validation_level='compile')))
    assert load_conversion_config(file, 'glb')['collision_proxy_path'] == str(tmp_path / 'mesh.glb')


def test_obj_requires_declared_up_and_scale(tmp_path):
    from asset_mujoco.chain_contracts import load_conversion_config
    with pytest.raises(ValueError):
        load_conversion_config(None, 'obj')
    file = tmp_path / 'config.json'
    file.write_text('{"source_up":"y","scale":1}')
    assert load_conversion_config(file, 'obj')['scale'] == 1


def test_metadata_warning_is_not_asset_failure(tmp_path):
    from asset_mujoco.chain_contracts import validate_response
    file = tmp_path / 'model.glb'
    file.write_bytes(b'glb checked by converter')
    source, warnings = validate_response(dict(job_id='job', file=str(file), type='glb', metadata={}), 'glb')
    assert source['file'] == str(file) and warnings
    for change in ({'file': 'relative.glb'}, {'file': str(tmp_path)}, {'type': 'obj'}, {'job_id': ''}):
        with pytest.raises(ValueError):
            validate_response(dict(job_id='job', file=str(file), type='glb') | change, 'glb')


@pytest.mark.parametrize('config', [{'collision_mode': 'decompose'},
    {'body_mode': 'free', 'mass': 1, 'inertia_mode': 'watertight'}])
def test_unimplemented_conversion_rejected_before_post(tmp_path, config):
    from asset_mujoco.chain_contracts import load_conversion_config
    file = tmp_path / 'config.json'
    file.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_conversion_config(file, 'glb')


def test_size_and_regular_file_boundaries(tmp_path):
    from asset_mujoco.chain_contracts import validate_generation, read_json
    large = tmp_path / 'large.png'
    with large.open('wb') as stream:
        stream.truncate(100 * 1024 * 1024 + 1)
    with pytest.raises(ValueError):
        validate_generation('image', {'image': str(large)}, tmp_path)
    directory = tmp_path / 'directory.png'
    directory.mkdir()
    with pytest.raises(ValueError):
        validate_generation('image', {'image': str(directory)}, tmp_path)
    large_json = tmp_path / 'large.json'
    large_json.write_text('{"a":"' + 'x' * (1024 * 1024) + '"}')
    with pytest.raises(ValueError):
        read_json(large_json)
