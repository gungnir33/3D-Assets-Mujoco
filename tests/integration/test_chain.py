import json
from pathlib import Path
import pytest
import trimesh


def settings_for(tmp_path, mock_server, level='compile', profile='preserve'):
    from asset_mujoco.chain_contracts import ChainSettings
    source = tmp_path / 'box.glb'
    trimesh.creation.box().export(source)
    url, calls, respond = mock_server
    respond(200, json.dumps(dict(job_id='synthetic-job', file=str(source), type='glb',
                                 metadata=str(tmp_path / 'missing.json'))).encode())
    return ChainSettings(endpoint='text', payload={'prompt': 'synthetic box'},
        conversion={'source_up': 'z', 'validation_level': level, 'contact_profile': profile},
        output=tmp_path / 'out', base_url=url)


def test_real_compile_chain_and_metadata_warning(tmp_path, mock_server):
    from asset_mujoco.chain import run_chain
    from asset_mujoco.manifest import checked_report, fingerprint
    settings = settings_for(tmp_path, mock_server)
    before = (tmp_path / 'box.glb').read_bytes()
    result = run_chain(settings)
    assert result['exit_code'] == 0
    assert result['phase1']['status'] == 'passed' and result['phase1']['warnings']
    assert result['phase2']['status'] == 'passed'
    package = Path(result['phase2']['package'])
    assert checked_report(package).status == 'COMPILE_VALIDATED'
    assert result['phase2']['fingerprint'] == fingerprint(package)
    assert not (package / 'chain_manifest.json').exists()
    assert json.loads((Path(result['run_directory']) / 'chain_manifest.json').read_text()) == result
    assert (tmp_path / 'box.glb').read_bytes() == before
    again = run_chain(settings)
    assert again['run_directory'] != result['run_directory']


def test_phase2_failure_preserves_generation(tmp_path, mock_server):
    from asset_mujoco.chain import run_chain
    settings = settings_for(tmp_path, mock_server, 'physics')
    result = run_chain(settings)
    assert result['phase1']['status'] == 'passed'
    assert result['phase2']['status'] == 'failed' and result['exit_code'] == 5
    assert result['phase1']['file'] == str(tmp_path / 'box.glb')
    assert result['recovery_argv'] and Path(result['phase2']['package']).is_dir()
    assert len([c for c in mock_server[1] if c['method'] == 'POST']) == 1


def test_dry_run_has_no_network_or_directory(tmp_path, monkeypatch):
    import socket
    from asset_mujoco.chain import run_chain
    from asset_mujoco.chain_contracts import ChainSettings
    def forbidden(*a, **kw):
        raise AssertionError('dry-run attempted DNS/network')
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    result = run_chain(ChainSettings('text', {'prompt': 'box'}, {}, tmp_path / 'none',
                                     'http://localhost:8080', True))
    assert result['exit_code'] == 0 and result['dry_run']
    assert not (tmp_path / 'none').exists()


def test_invalid_config_zero_http_calls(tmp_path, mock_server):
    from asset_mujoco.chain import run_chain
    settings = settings_for(tmp_path, mock_server)
    settings.conversion['input'] = 'forbidden.glb'
    result = run_chain(settings)
    assert result['exit_code'] == 2 and mock_server[1] == []
    assert not settings.output.exists()


def test_malformed_success_is_unknown_and_saved(tmp_path, mock_server):
    from asset_mujoco.chain import run_chain
    settings = settings_for(tmp_path, mock_server)
    mock_server[2](200, b'broken JSON')
    result = run_chain(settings)
    assert result['exit_code'] == 6 and result['phase1']['status'] == 'unknown'
    assert (Path(result['run_directory']) / 'phase1_response.json').read_bytes() == b'broken JSON'
    assert result['phase2']['status'] == 'not_run'


@pytest.mark.parametrize('fault,posts', [('request.json', 0), ('phase1_response.json', 1), ('final_manifest', 1)])
def test_persistence_failure_keeps_known_source(tmp_path, mock_server, monkeypatch, fault, posts):
    from asset_mujoco.chain import run_chain
    settings = settings_for(tmp_path, mock_server)
    original = Path.write_bytes
    def fail(path, data):
        if path.name == fault or (fault == 'final_manifest' and path.name == 'chain_manifest.json'
                and b'"status": "passed"' in data and b'"fingerprint"' in data):
            raise OSError('injected disk failure')
        return original(path, data)
    monkeypatch.setattr(Path, 'write_bytes', fail)
    result = run_chain(settings)
    assert result['exit_code'] == 3 and result['diagnostic_persisted'] is False
    assert len([c for c in mock_server[1] if c['method'] == 'POST']) == posts
    if posts:
        assert result['phase1']['status'] == 'passed'
        assert result['phase1']['file'] == str(tmp_path / 'box.glb')


def test_main_request_and_simple_options_are_exclusive(tmp_path, capsys):
    from asset_mujoco.chain import main
    file = tmp_path / 'request.json'
    file.write_text('{"endpoint":"text","payload":{"prompt":"box"}}')
    assert main(['--request', str(file), '--seed', '12', '--output', str(tmp_path / 'out'), '--dry-run']) == 2
    assert json.loads(capsys.readouterr().out)['exit_code'] == 2


@pytest.mark.parametrize('error,code', [(FileNotFoundError('missing'), 2),
    (ValueError('generic conversion'), 3), (ValueError('XML Element invalid'), 4),
    (ValueError('RENDER_FAILED injected'), 5), (ValueError('RENDER_UNAVAILABLE injected'), 7)])
def test_phase2_exit_codes_and_source_survive(tmp_path, mock_server, monkeypatch, error, code):
    import asset_mujoco.chain as chain
    settings = settings_for(tmp_path, mock_server)
    def fail(request):
        raise error
    monkeypatch.setattr(chain, 'convert', fail)
    report = chain.run_chain(settings)
    assert report['exit_code'] == code and report['phase1']['status'] == 'passed'
    assert report['phase2']['status'] == 'failed' and report['recovery_argv']
    assert len([c for c in mock_server[1] if c['method'] == 'POST']) == 1


def test_full_candidate_real_conversion_and_relocation(tmp_path, mock_server):
    import shutil
    import mujoco
    from asset_mujoco.chain import run_chain
    from asset_mujoco.manifest import checked_report, fingerprint
    result = run_chain(settings_for(tmp_path, mock_server, 'full', 'engineering_static_v1'))
    assert result['exit_code'] == 0
    validation = result['phase2']['validation']
    assert validation['compile'] == validation['physics'] == validation['render'] == 'passed'
    assert validation['status'] == 'SCOPED_PHYSICS_VALIDATED'
    assert validation['appearance_review'] == 'pending' and validation['host_integration'] == 'pending'
    moved = tmp_path / 'moved'
    shutil.copytree(result['phase2']['package'], moved)
    for xml in ('model.xml', 'scene.xml', 'contact_scene.xml'):
        model = mujoco.MjModel.from_xml_path(str(moved / xml))
        mujoco.mj_forward(model, mujoco.MjData(model))
    assert checked_report(moved).model_dump() == validation
    assert fingerprint(moved) == result['phase2']['fingerprint']


def test_recovery_command_reuses_source_without_post(tmp_path, mock_server):
    import subprocess
    from asset_mujoco.chain import run_chain
    report = run_chain(settings_for(tmp_path, mock_server))
    posts = len([c for c in mock_server[1] if c['method'] == 'POST'])
    recovery = subprocess.run(report['recovery_argv'], capture_output=True, text=True, timeout=30)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    assert json.loads(recovery.stdout)['compile'] == 'passed'
    assert len([c for c in mock_server[1] if c['method'] == 'POST']) == posts


def test_http_error_remains_distinct_from_converter(tmp_path, mock_server):
    from asset_mujoco.chain import run_chain
    settings = settings_for(tmp_path, mock_server)
    mock_server[2](422, b'{"detail":[{"msg":"invalid"}]}')
    result = run_chain(settings)
    assert result['exit_code'] == 6 and result['phase1']['status'] == 'failed'
    assert result['phase1']['error']['details'] == [{'msg': 'invalid'}]
    assert result['phase2']['status'] == 'not_run'


def test_request_json_paths_are_relative_to_request(tmp_path, capsys):
    from PIL import Image
    from asset_mujoco.chain import main
    folder = tmp_path / 'request-dir'
    folder.mkdir()
    Image.new('RGB', (2, 2)).save(folder / 'input.png')
    request = folder / 'request.json'
    request.write_text('{"endpoint":"image","payload":{"image":"input.png"}}')
    code = main(['--request', str(request), '--output', str(tmp_path / 'out'), '--dry-run'])
    assert code == 0
    assert json.loads(capsys.readouterr().out)['request']['payload']['image'] == str(folder / 'input.png')


def test_evidence_io_error_preserves_persistence_failure(tmp_path, mock_server, monkeypatch):
    import asset_mujoco.chain as chain
    from asset_mujoco.manifest import EvidenceIOError
    settings = settings_for(tmp_path, mock_server)
    def fail(request):
        error = EvidenceIOError('disk failure')
        error.original_error = {'type': 'ValueError', 'message': 'original render failure'}
        error.persistence_error = {'type': 'OSError', 'message': 'disk failure'}
        raise error
    monkeypatch.setattr(chain, 'convert', fail)
    result = chain.run_chain(settings)
    assert result['exit_code'] == 3 and result['phase1']['status'] == 'passed'
    assert result['diagnostic_persisted'] is False
    assert result['phase2']['error']['original_error']['message'] == 'original render failure'


@pytest.mark.parametrize('endpoint', ['text', 'image', 'texture'])
@pytest.mark.parametrize('entry', ['module', 'script'])
def test_installed_entry_http_contract(tmp_path, mock_server, endpoint, entry):
    import subprocess
    import sys
    from PIL import Image
    settings = settings_for(tmp_path, mock_server)
    image = tmp_path / 'condition.png'
    Image.new('RGB', (2, 2), 'white').save(image)
    config = tmp_path / 'convert.json'
    config.write_text(json.dumps({'source_up': 'z', 'validation_level': 'compile'}))
    program = ['-m', 'asset_mujoco.chain'] if entry == 'module' else [str(Path(__file__).resolve().parents[2] / 'scripts/chain.py')]
    flags = {'text': ['--prompt', 'a synthetic box'], 'image': ['--image', str(image)],
             'texture': ['--mesh', str(tmp_path / 'box.glb'), '--condition-image', str(image)]}[endpoint]
    run = subprocess.run([sys.executable, '-I', '-B', *program, *flags,
        '--conversion-config', str(config), '--output', str(tmp_path / 'cli-output'),
        '--base-url', settings.base_url], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    report = json.loads(run.stdout)
    assert report['phase2']['validation']['status'] == 'COMPILE_VALIDATED'
    post = [c for c in mock_server[1] if c['method'] == 'POST']
    assert len(post) == 1 and post[0]['path'] == '/generate/' + endpoint
    payload = post[0]['payload']
    assert payload['format'] == 'glb' and payload['seed'] == 12345
    key = {'text': 'prompt', 'image': 'image', 'texture': 'condition_image'}[endpoint]
    assert payload[key] == ('a synthetic box' if endpoint == 'text' else str(image))


def test_installed_supplied_chain_relative_proxy(tmp_path, mock_server):
    import subprocess
    import sys
    settings = settings_for(tmp_path, mock_server)
    config = tmp_path / 'convert.json'
    config.write_text(json.dumps({'source_up': 'z', 'validation_level': 'compile',
        'collision_mode': 'supplied', 'collision_proxy_path': 'box.glb', 'validation_collision_part': 0}))
    run = subprocess.run([sys.executable, '-I', '-B', '-m', 'asset_mujoco.chain',
        '--prompt', 'synthetic proxy match', '--conversion-config', str(config),
        '--output', str(tmp_path / 'cli-output'), '--base-url', settings.base_url],
        capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(run.stdout)
    manifest = json.loads((Path(result['phase2']['package']) / 'conversion_manifest.json').read_text())
    assert manifest['collision_proxy']['target_index'] == 0
    assert result['phase2']['validation']['validation_scope']['required_pairs'] == [['asset_collision_000', 'probe']]


def test_recovery_argv_preserves_supplied_inertia_and_target(tmp_path):
    from asset_mujoco.chain import build_recovery_argv
    config = {'name': 'asset', 'source_up': 'y', 'yaw_deg': 180, 'scale': .5,
        'body_mode': 'free', 'mass': 2, 'inertia_mode': 'supplied',
        'supplied_inertia': {'example': 'written unchanged; validated elsewhere'},
        'collision_mode': 'supplied', 'collision_proxy_path': '/proxy path/proxy.glb',
        'validation_collision_part': 2, 'validation_level': 'compile', 'contact_profile': 'preserve'}
    argv = build_recovery_argv(Path('/source path/model.glb'), config, tmp_path)
    assert '/source path/model.glb' in argv and '/proxy path/proxy.glb' in argv
    assert argv[argv.index('--validation-collision-part') + 1] == '2'
    inertia = Path(argv[argv.index('--supplied-inertia') + 1])
    assert json.loads(inertia.read_text()) == config['supplied_inertia']
