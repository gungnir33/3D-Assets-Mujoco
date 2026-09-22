"""串联输入契约，独立于第一阶段 Python 包；所有预检先于 POST。"""
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .contracts import ConversionRequest

MAX_JSON = 1024 * 1024
IMAGES = {'.png', '.jpg', '.jpeg', '.webp'}
MESHES = {'.glb', '.gltf', '.obj', '.ply', '.stl'}
ALLOWED_CONVERSION = {'name', 'source_up', 'yaw_deg', 'scale', 'target_size_m', 'scale_mode',
    'body_mode', 'collision_mode', 'contact_profile', 'validation_level', 'mass', 'inertia_mode',
    'supplied_inertia', 'collision_proxy_path', 'validation_collision_part'}


def parse_json(data: bytes) -> dict:
    if len(data) > MAX_JSON:
        raise ValueError('CHAIN_JSON_TOO_LARGE')
    def constant(value):
        raise ValueError('CHAIN_NONFINITE_JSON: ' + value)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('CHAIN_DUPLICATE_JSON_KEY: ' + key)
            result[key] = value
        return result
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('CHAIN_NONFINITE_JSON')
        return number
    result = json.loads(data.decode('utf-8'), parse_constant=constant, parse_float=finite_float,
                        object_pairs_hook=pairs)
    if not isinstance(result, dict):
        raise ValueError('CHAIN_JSON_OBJECT_REQUIRED')
    return result


def read_json(path: Path) -> dict:
    with Path(path).open('rb') as stream:
        return parse_json(stream.read(MAX_JSON + 1))


def local_file(value, base_dir, suffixes, limit=None):
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else Path(base_dir) / path).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in suffixes:
        raise ValueError('CHAIN_INVALID_LOCAL_FILE: ' + str(path))
    if limit is not None and path.stat().st_size > limit:
        raise ValueError('CHAIN_LOCAL_FILE_TOO_LARGE: ' + str(path))
    with path.open('rb'):
        pass
    return str(path)


class GenerationBase(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    texture: bool = True
    seed: int = Field(default=12345, ge=0, le=2**63 - 1)
    format: Literal['glb', 'obj'] = 'glb'
    face_count: int = Field(default=40000, ge=100, le=1_000_000)
    shape_steps: int = Field(default=50, ge=1, le=200)


class TextGeneration(GenerationBase):
    prompt: str = Field(min_length=1, max_length=1000)
    @field_validator('prompt')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('prompt must not be blank')
        return value.strip()


class ImageGeneration(GenerationBase):
    image: Path


class TextureGeneration(GenerationBase):
    mesh: Path
    condition_image: Path


def validate_generation(endpoint: str, payload: dict, base_dir: Path) -> dict:
    models = {'text': TextGeneration, 'image': ImageGeneration, 'texture': TextureGeneration}
    if endpoint not in models:
        raise ValueError('CHAIN_INVALID_ENDPOINT')
    result = models[endpoint].model_validate(payload).model_dump(mode='json')
    for field in ('image', 'condition_image', 'mesh'):
        if field in result:
            result[field] = local_file(result[field], base_dir, MESHES if field == 'mesh' else IMAGES,
                                       100 * 1024 * 1024)
    return result


def validate_conversion(config: dict, output_format: str, base_dir: Path) -> dict:
    if set(config) - ALLOWED_CONVERSION:
        raise ValueError('CHAIN_INVALID_CONVERSION_FIELDS')
    config = dict(config)
    if config.get('collision_mode') == 'decompose' or config.get('inertia_mode') == 'watertight':
        raise ValueError('CHAIN_UNIMPLEMENTED_CONVERSION_STRATEGY')
    if config.get('collision_proxy_path') is not None:
        config['collision_proxy_path'] = local_file(config['collision_proxy_path'], base_dir, {'.glb', '.obj'})
    request = ConversionRequest(input=Path('preflight.' + output_format), output=Path('preflight-output'), **config)
    return request.model_dump(mode='json', exclude={'input', 'output'})


def load_conversion_config(path: Path | None, output_format: str) -> dict:
    return validate_conversion(read_json(path) if path is not None else {}, output_format,
                               Path(path).resolve().parent if path is not None else Path.cwd())


def validate_response(data: dict, expected_format: str) -> tuple[dict, list[str]]:
    if not isinstance(data, dict) or not isinstance(data.get('job_id'), str) or not data['job_id'].strip():
        raise ValueError('CHAIN_INVALID_JOB_ID')
    if data.get('type') != expected_format:
        raise ValueError('CHAIN_OUTPUT_TYPE_MISMATCH')
    value = data.get('file')
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError('CHAIN_ABSOLUTE_OUTPUT_REQUIRED')
    file = local_file(value, Path.cwd(), {'.' + expected_format})
    metadata = data.get('metadata')
    warnings = []
    if not isinstance(metadata, str) or not Path(metadata).is_absolute():
        warnings.append('METADATA_MISSING_OR_INVALID_PATH')
    else:
        try:
            if not Path(metadata).is_file():
                raise ValueError('not a regular file')
            with Path(metadata).open('rb'):
                pass
        except (OSError, ValueError):
            warnings.append('METADATA_UNREADABLE')
    return {'job_id': data['job_id'], 'file': file, 'type': expected_format, 'metadata': metadata}, warnings


@dataclass
class ChainSettings:
    endpoint: str
    payload: dict
    conversion: dict
    output: Path
    base_url: str
    dry_run: bool = False
