"""单次本地生成 HTTP → 现有转换 API；来源和恢复记录始终在包外。"""
import argparse
from contextlib import redirect_stdout
import hashlib
import json
from pathlib import Path
import shlex
import sys
import tempfile
from .chain_contracts import (ChainSettings, validate_generation, validate_conversion,
    load_conversion_config, validate_response, read_json, parse_json)
from .chain_http import LocalGenerationClient, Phase1Error, validate_base_url
from .cli import conversion_exit_code
from .contracts import ConversionRequest
from .manifest import checked_report, fingerprint, EvidenceIOError
from .pipeline import convert, publication_report


def _write_json(path, data):
    Path(path).write_bytes(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False).encode())


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def build_recovery_argv(source: Path, conversion: dict, run: Path) -> list[str]:
    argv = [sys.executable, '-m', 'asset_mujoco.cli', 'convert', str(source),
            '--output', str(run / 'recovery_packages')]
    for key, flag in (('name','--name'), ('source_up','--source-up'), ('yaw_deg','--yaw-deg'),
        ('scale','--scale'), ('scale_mode','--scale-mode'), ('body_mode','--body-mode'),
        ('collision_mode','--collision-mode'), ('contact_profile','--contact-profile'),
        ('validation_level','--validation-level'), ('mass','--mass'), ('inertia_mode','--inertia-mode'),
        ('collision_proxy_path','--collision-proxy'), ('validation_collision_part','--validation-collision-part')):
        if conversion.get(key) is not None:
            argv.extend([flag, str(conversion[key])])
    if conversion.get('target_size_m') is not None:
        argv.extend(['--target-size-m', *map(str, conversion['target_size_m'])])
    if conversion.get('supplied_inertia') is not None:
        path = run / 'recovery_inertia.json'
        _write_json(path, conversion['supplied_inertia'])
        argv.extend(['--supplied-inertia', str(path)])
    return argv


def _empty_report():
    return {'schema_version': 1, 'run_directory': None, 'phase1': {'status': 'not_run'},
            'phase2': {'status': 'not_run'}, 'recovery_argv': [], 'exit_code': 2}


def _source(raw, expected_format):
    source, warnings = validate_response(parse_json(raw), expected_format)
    return {'status': 'passed', **source, 'warnings': warnings, 'sha256': _hash(source['file'])}


def run_chain(settings: ChainSettings) -> dict:
    report = _empty_report()
    try:
        payload = validate_generation(settings.endpoint, settings.payload, Path.cwd())
        config = dict(settings.conversion)
        # validate_conversion 返回现有转换 seed 缺省；外部 JSON 白名单不开放它。
        if config.get('seed') == 12345:
            config.pop('seed')
        conversion = validate_conversion(config, payload['format'], Path.cwd())
        base_url = validate_base_url(settings.base_url)
        output = Path(settings.output).expanduser().resolve()
        if output.exists() and not output.is_dir():
            raise ValueError('CHAIN_OUTPUT_PARENT_NOT_DIRECTORY')
        if settings.dry_run:
            report.update(exit_code=0, dry_run=True, request={'endpoint': settings.endpoint,
                'payload': payload, 'conversion': conversion, 'base_url': base_url, 'output': str(output)})
            return report
    except (OSError, ValueError, TypeError) as error:
        report['error'] = {'code': 'INVALID_INPUT', 'message': str(error)}
        return report
    run = None
    stage = 'create_run'
    raw = None
    try:
        output.mkdir(parents=True, exist_ok=True)
        run = Path(tempfile.mkdtemp(prefix='chain_', dir=output))
        report['run_directory'] = str(run)
        client = LocalGenerationClient(base_url)
        stage = 'health'
        client.health()
        stage = 'request'
        _write_json(run / 'request.json', {'endpoint': settings.endpoint, 'payload': payload,
                    'conversion': conversion, 'base_url': base_url})
        stage = 'post'
        raw = client.generate(settings.endpoint, payload)
        stage = 'response'
        try:
            (run / 'phase1_response.json').write_bytes(raw)
        except OSError:
            # 原始响应无法保存时仍尽力在 stdout 保留已知成功来源，不重试生成。
            try:
                report['phase1'] = _source(raw, payload['format'])
            except (OSError, ValueError, TypeError):
                report['phase1']['status'] = 'unknown'
            raise
        try:
            report['phase1'] = _source(raw, payload['format'])
        except (OSError, ValueError, TypeError) as error:
            raise Phase1Error('INVALID_GENERATION_RESPONSE', str(error), http_status=200,
                              raw_body=raw, result_unknown=True) from error
        stage = 'phase1_manifest'
        _write_json(run / 'chain_manifest.json', report)
        stage = 'recovery'
        source = Path(report['phase1']['file'])
        report['recovery_argv'] = build_recovery_argv(source, conversion, run)
        report['recovery_command'] = shlex.join(report['recovery_argv'])
        stage = 'convert'
        request = ConversionRequest(input=source, output=run / 'packages', **conversion)
        with redirect_stdout(sys.stderr):
            package = convert(request)
            validation = publication_report(package, request)
        report['phase2'] = {'status': 'passed', 'package': str(package),
                            'validation': validation.model_dump(), 'fingerprint': fingerprint(package)}
        report['exit_code'] = 0
    except Phase1Error as error:
        report['phase1'] = {'status': 'unknown' if error.result_unknown else 'failed',
                            'error': error.as_dict()}
        report['exit_code'] = 6
        if run is not None and error.raw_body and raw is None:
            try:
                (run / 'phase1_response.json').write_bytes(error.raw_body)
            except OSError as persistence:
                report.update(exit_code=3, diagnostic_persisted=False,
                              error={'code': 'DIAGNOSTIC_IO_ERROR', 'stage': 'error_response',
                                     'message': str(persistence), 'original_error': error.as_dict()})
    except Exception as error:
        if stage == 'convert':
            package = getattr(error, 'package', None)
            if package is None:
                candidates = list((run / 'packages').glob('.staging-*'))
                package = candidates[0] if len(candidates) == 1 else None
            phase = {'status': 'failed', 'package': str(package) if package else None,
                     'diagnostic_parent': str(run / 'packages'),
                     'error': {'code': getattr(error, 'code', type(error).__name__),
                               'stage': getattr(error, 'stage', stage), 'message': str(error)}}
            if package is not None:
                try:
                    phase['validation'] = checked_report(package).model_dump()
                except (OSError, ValueError, KeyError, TypeError) as check_error:
                    phase['report_error'] = str(check_error)
                    if getattr(error, 'result', None) is not None:
                        phase['validation'] = error.result.model_dump()
            report['phase2'] = phase
            report['exit_code'] = conversion_exit_code(error)
            if isinstance(error, EvidenceIOError):
                report['diagnostic_persisted'] = False
                phase['error'].update(code='EVIDENCE_IO_ERROR',
                    original_error=getattr(error, 'original_error', None),
                    persistence_error=getattr(error, 'persistence_error', None))
        else:
            report.update(exit_code=3, diagnostic_persisted=False,
                          error={'code': 'DIAGNOSTIC_IO_ERROR', 'stage': stage,
                                 'type': type(error).__name__, 'message': str(error)})
    if run is not None:
        try:
            _write_json(run / 'chain_manifest.json', report)
        except (OSError, ValueError) as error:
            original = report.get('error') or report.get('phase2', {}).get('error') or report.get('phase1', {}).get('error')
            report.update(exit_code=3, diagnostic_persisted=False, error={
                'code': 'DIAGNOSTIC_IO_ERROR', 'stage': 'final_manifest', 'message': str(error),
                'original_error': original})
    return report


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None) -> int:
    parser = _Parser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for field in ('prompt', 'image', 'mesh', 'request'):
        group.add_argument('--' + field)
    parser.add_argument('--condition-image')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--base-url', default='http://127.0.0.1:8080')
    parser.add_argument('--conversion-config', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--face-count', type=int)
    parser.add_argument('--shape-steps', type=int)
    parser.add_argument('--format', choices=['glb', 'obj'])
    parser.add_argument('--no-texture', dest='texture', action='store_false', default=None)
    try:
        args = parser.parse_args(argv)
        options = {k: getattr(args, k) for k in ('seed','face_count','shape_steps','format','texture')
                   if getattr(args, k) is not None}
        if args.request:
            if options or args.condition_image:
                raise ValueError('--request cannot be combined with generation shorthand options')
            file = Path(args.request).expanduser().resolve(strict=True)
            document = read_json(file)
            if set(document) != {'endpoint', 'payload'}:
                raise ValueError('request JSON requires only endpoint and payload')
            endpoint = document['endpoint']
            payload = validate_generation(endpoint, document['payload'], file.parent)
        else:
            if args.condition_image and not args.mesh:
                raise ValueError('--condition-image requires --mesh')
            endpoint = 'text' if args.prompt is not None else 'image' if args.image else 'texture'
            field = 'prompt' if endpoint == 'text' else 'image' if endpoint == 'image' else 'mesh'
            payload = {field: getattr(args, field), **options}
            if endpoint == 'texture':
                if not args.condition_image:
                    raise ValueError('--mesh requires --condition-image')
                payload['condition_image'] = args.condition_image
            payload = validate_generation(endpoint, payload, Path.cwd())
        conversion = load_conversion_config(args.conversion_config, payload['format'])
        result = run_chain(ChainSettings(endpoint, payload, conversion, args.output, args.base_url, args.dry_run))
    except (OSError, ValueError, TypeError) as error:
        result = _empty_report()
        result['error'] = {'code': 'INVALID_INPUT', 'message': str(error)}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
