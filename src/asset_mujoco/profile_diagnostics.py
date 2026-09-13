"""M1.2固定少量独立实验；不改变正式配置或其验收状态。"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET
import numpy as np
from .contact_diagnostics import configure_fixture, trace_fixture, sha
from .manifest import compile_resources, write_evidence, checked_report

CASES = [
    {'name': 'baseline'},
    {'name': 'dt_001', 'dt': .001},
    {'name': 'dt_0005', 'dt': .0005},
    {'name': 'analytic_plane', 'geometry': 'tangent_plane'},
    {'name': 'offset_x_005', 'offset_x_m': .05},
    {'name': 'mass_02', 'mass_kg': .2},
    {'name': 'radius_12', 'radius_multiplier': 1.2},
    {'name': 'counterparty_mismatch', 'probe_solref': [.02, 1]},
]


def run_profile_diagnostics(package, output):
    package = Path(package).resolve()
    state = checked_report(package)
    if state.evidence_issues:
        raise ValueError('source package evidence is stale')
    reference = json.loads((package/'physics_native_evidence.json').read_text())['native']
    if reference.get('profile_contract', {}).get('id') != 'engineering_static_v1':
        raise ValueError('requires an engineering_static_v1 package')
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='profile-diagnostic-', dir=output))
    source = package/'contact_scene.xml'
    resources = compile_resources(package)
    write_evidence(root, 'experiment_plan.json', {
        'diagnostic': True, 'contact_profile': 'engineering_static_v1',
        'cases': CASES, 'total_time_s': 2., 'threshold_m': reference['penetration_limit_m'],
        'source': str(package), 'source_hashes': {p: sha(package/p) for p in resources},
        'application_force_limit': 'not_specified',
        'limits': 'individual observed conditions only; no material or robot safety calibration',
        'analytic_geometry': 'infinite plane tangent at baseline first contact; curvature and finite boundary differ',
        'mass_radius': 'sphere explicit inertia updated consistently; initial position otherwise unchanged',
        'mismatch': 'probe only .02; delivered asset and ground remain .006; not a compliant profile case',
    })
    results = []; plane = None
    for config in CASES:
        directory = root/config['name']; directory.mkdir()
        for relative in resources:
            dest = directory/relative; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(package/relative, dest)
        fixture = directory/'fixture.xml'
        configure_fixture(source, fixture, config, plane)
        xml = ET.parse(fixture); body = xml.find(".//body[@name='probe_body']")
        probe = body.find("geom[@name='probe']")
        if 'offset_x_m' in config:
            pos = np.fromstring(body.get('pos'), sep=' '); pos[0] += config['offset_x_m']
            body.set('pos', ' '.join(map(str, pos)))
        if 'mass_kg' in config or 'radius_multiplier' in config:
            radius = float(probe.get('size')) * config.get('radius_multiplier', 1)
            mass = config.get('mass_kg', float(body.find('inertial').get('mass')))
            probe.set('size', str(radius)); probe.set('mass', str(mass))
            body.find('inertial').set('mass', str(mass))
            body.find('inertial').set('diaginertia', ' '.join([str(.4*mass*radius**2)]*3))
        if 'probe_solref' in config:
            probe.set('solref', ' '.join(map(str, config['probe_solref'])))
        xml.write(fixture)
        write_evidence(directory, 'experiment_config.json', dict(config, diagnostic=True,
            plane=plane if config.get('geometry') else None))
        try:
            summary = trace_fixture(fixture, directory, total_time=2., limit=reference['penetration_limit_m'])
            summary['execution_status'] = 'completed'
        except Exception as error:
            summary = {'diagnostic': True, 'execution_status': 'error',
                       'error': {'type': type(error).__name__, 'message': str(error)}}
            write_evidence(directory, 'contact_summary.json', summary)
        results.append({'name': config['name'], 'directory': str(directory), 'summary': summary})
        write_evidence(directory, 'output_hashes.json', {
            str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob('*')) if p.is_file()})
        write_evidence(root, 'diagnosis.json', {'diagnostic': True, 'directory': str(root), 'results': results})
        if config['name'] == 'baseline':
            matched = (summary.get('execution_status') == 'completed' and
                       abs(summary['max_penetration_m']-reference['max_penetration_m']) <= 1e-10 and
                       summary['first_contact_step'] == reference['first_contact_step'])
            if not matched:
                raise ValueError('BASELINE_MISMATCH: stop; see '+str(directory))
            contact = summary['first_contact']
            normal = np.array(contact['normal_world']) * (1 if contact['geom1'] == 'asset_collision' else -1)
            plane = {'point_world': (np.array(contact['point_world_m'])-normal*contact['dist_m']/2).tolist(),
                     'normal_world': normal.tolist()}
    return {'directory': str(root), 'diagnostic': True, 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_profile_diagnostics(args.package, args.output), ensure_ascii=False))


if __name__ == '__main__':
    main()
