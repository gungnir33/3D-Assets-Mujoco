import json
import shutil
import xml.etree.ElementTree as ET
import numpy as np
import pytest
import trimesh
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.pipeline import convert, ValidationFailed
from asset_mujoco.manifest import checked_report
from asset_mujoco.validation import run_contact_case


def package_with_proxy(tmp_path, target=0):
    visual, proxy = tmp_path / 'v.glb', tmp_path / 'p.glb'
    trimesh.creation.box().export(visual)
    scene = trimesh.Scene()
    for i, x in enumerate([0, 3]):
        box = trimesh.creation.box()
        box.apply_translation([x, 0, 0])
        scene.add_geometry(box, node_name=f'n{i}', geom_name=f'g{i}')
    scene.export(proxy)
    request = ConversionRequest(input=visual, output=tmp_path / 'out', source_up='z',
        collision_mode='supplied', collision_proxy_path=proxy, validation_collision_part=target,
        validation_level='compile')
    package = convert(request)
    return package, request


def test_nonselected_contact_cannot_replace_target(tmp_path):
    package, request = package_with_proxy(tmp_path, 1)
    native = run_contact_case(package, request, [1, 1, 1])
    assert native['expected_pair'] == ['asset_collision_001', 'probe']
    assert native['status'] == 'failed' and native['contact_count'] == 0
    assert native['contact_statistics']['per_collision_part']['asset_collision_000']['contact_records'] > 0
    np.testing.assert_allclose(native['initial_position'], [0, 0, 1.225], rtol=0, atol=1e-14)


@pytest.mark.parametrize('mutation', ['bits', 'position'])
def test_selected_collision_disabled_fails_without_reaim(tmp_path, mutation):
    package, request = package_with_proxy(tmp_path)
    root = ET.parse(package / 'scene.xml')
    geom = root.find(".//geom[@name='asset_collision_000']")
    if mutation == 'bits':
        geom.set('contype', '0')
        geom.set('conaffinity', '0')
    else:
        geom.set('pos', '9 0 0')
    root.write(package / 'scene.xml')
    native = run_contact_case(package, request, [1, 1, 1])
    assert native['status'] == 'failed' and native['contact_count'] == 0
    np.testing.assert_allclose(native['initial_position'], [0, 0, 1.225], rtol=0, atol=1e-14)


def test_supplied_native_evidence_and_migration(tmp_path):
    package, compile_request = package_with_proxy(tmp_path)
    request = compile_request.model_copy(update={'validation_level': 'physics'})
    try:
        current = convert(request)
    except ValidationFailed as error:
        current = error.package
    report = checked_report(current)
    native = json.loads((current / 'physics_native_evidence.json').read_text())['native']
    assert native['expected_pair'] == ['asset_collision_000', 'probe']
    assert native['contact_count'] > 0
    assert report.physics == native['status']
    assert report.validation_scope.evidence_status == 'verified'
    assert report.validation_scope.case_id == 'native_supplied_part_probe_v1'
    assert 'SELECTED_COLLISION_PART_ONLY' in report.limitations
    assert not report.evidence_issues
    relocated = tmp_path / 'moved'
    shutil.copytree(current, relocated)
    assert checked_report(relocated).model_dump() == report.model_dump()
    path = relocated / 'meshes/collision_001.obj'
    path.write_text(path.read_text() + '\n# changed non-target\n')
    changed = checked_report(relocated)
    assert changed.evidence_issues and changed.compile != 'passed'


@pytest.mark.parametrize('mode', ['box_approx', 'supplied'])
def test_free_inertia_is_independent_of_collision_proxy(tmp_path, mode):
    import mujoco
    package, base = package_with_proxy(tmp_path)
    inertia = None
    if mode == 'supplied':
        inertia = dict(frame='normalized_body', reference='com', com_unit='m', inertia_unit='kg*m^2',
                       com=[0, 0, .5], tensor=[[.3, 0, 0], [0, .3, 0], [0, 0, .3]],
                       mass_kg=2, final_size_m=[1, 1, 1])
    values = []
    for collision in ('hull', 'supplied'):
        options = base.model_dump() | dict(body_mode='free', mass=2, inertia_mode=mode,
            supplied_inertia=inertia, collision_mode=collision)
        if collision == 'hull':
            options.update(collision_proxy_path=None, validation_collision_part=None)
        current = convert(ConversionRequest(**options))
        model = mujoco.MjModel.from_xml_path(str(current / 'model.xml'))
        mujoco.mj_forward(model, mujoco.MjData(model))
        body = model.body(base.name).id
        values.append([np.asarray(getattr(model, key)[body]) for key in
                       ('body_mass', 'body_ipos', 'body_inertia', 'body_iquat')])
    for old, new in zip(*values):
        np.testing.assert_allclose(old, new, rtol=1e-8, atol=1e-12)


@pytest.mark.parametrize('mutation', ['target', 'mapping', 'fixture'])
def test_semantic_collision_conflict_even_with_consistent_hashes(tmp_path, mutation):
    from asset_mujoco.manifest import record_layer, compile_resources, refresh_report
    package, request = package_with_proxy(tmp_path)
    if mutation == 'fixture':
        tree = ET.parse(package / 'model.xml')
        tree.find(".//geom[@name='asset_collision_000']").set('mesh', 'collision_mesh_001')
        tree.write(package / 'model.xml')
    else:
        path = package / 'conversion_manifest.json'
        metadata = json.loads(path.read_text())
        if mutation == 'target':
            metadata['collision_proxy']['target_index'] = 1
        else:
            metadata['collision_proxy']['parts'][1]['geom_name'] = 'asset_collision_000'
        path.write_text(json.dumps(metadata))
    record_layer(package, 'compile', 'passed', compile_resources(package), {'synthetic_fault_injection': True})
    report = refresh_report(package)
    assert report.validation_scope.evidence_status == 'contradictory'
    assert report.evidence_issues


def test_free_proxy_observations_do_not_claim_force_on_probe(tmp_path):
    package, base = package_with_proxy(tmp_path)
    request = ConversionRequest(**(base.model_dump() | dict(body_mode='free', mass=1,
                                                           inertia_mode='box_approx')))
    package = convert(request)
    native = run_contact_case(package, request, [1, 1, 1])
    assert native['expected_pair'] == ['asset_collision_000', 'ground']
    observations = native['contact_statistics']['per_collision_part']
    assert observations['asset_collision_000']['contact_records'] > 0
    for name, stats in observations.items():
        assert stats['force_object'] == name
        assert 'world_impulse_on_probe_N_s' not in stats


def test_installed_proxy_cli_reports_actual_full_outcome(tmp_path):
    import subprocess
    import sys
    package, base = package_with_proxy(tmp_path)
    command = [sys.executable, '-I', '-B', '-m', 'asset_mujoco.cli', 'convert', str(base.input),
               '--output', str(tmp_path / 'cli'), '--source-up', 'z', '--collision-mode', 'supplied',
               '--collision-proxy', str(base.collision_proxy_path), '--validation-collision-part', '0',
               '--validation-level', 'full']
    run = subprocess.run(command, capture_output=True, text=True, timeout=120)
    result = json.loads(run.stdout)
    assert result['compile'] == 'passed' and result['render'] == 'passed'
    assert result['validation_scope']['evidence_status'] == 'verified'
    assert result['validation_scope']['required_pairs'] == [['asset_collision_000', 'probe']]
    assert result['physics'] in ('passed', 'failed')
    assert run.returncode == (0 if result['physics'] == 'passed' else 5)
    report = subprocess.run([sys.executable, '-I', '-B', '-m', 'asset_mujoco.cli', 'report', result['package']],
                            capture_output=True, text=True, timeout=30)
    queried = json.loads(report.stdout)
    for key in ('compile', 'physics', 'render', 'validation_scope', 'limitations', 'status'):
        assert queried[key] == result[key]
