import json,pathlib,hashlib,shutil,subprocess,sys
import numpy as np
from PIL import Image
repo=pathlib.Path('/home/mcl/workspace/3D-Assets-Mujoco')
root=repo/'outputs/m1_2_scope_fix_jnabps39'
data=json.loads((root/'real_results.json').read_text())
before=json.loads(pathlib.Path('/tmp/m1-2-scope-fix-b9mENe/before.json').read_text())
after=json.loads(pathlib.Path('/tmp/m1-2-scope-fix-b9mENe/after.json').read_text())
checks={k:before[k]==after[k] for k in ('dependencies','phase1_head','phase1_status','source_sha256','history')}
history={'preserve':repo/'outputs/m1_2_final_6im5gku8/preserve/acceptance-k618ipak/packages/.staging-wyvumrco','engineering_static_v1':repo/'outputs/m1_2_final_6im5gku8/engineering_static_v1/acceptance-5ljztt1b/packages/penguin_fb9002dbf5e8'}
comparisons={}
preview_differences={}
for profile,row in data['profiles'].items():
    package=pathlib.Path(row['package']); old=history[profile]
    comparison={str(p.relative_to(old)):p.read_bytes()==(package/p.relative_to(old)).read_bytes() for p in old.rglob('*') if p.is_file() and 'previews' not in p.relative_to(old).parts and (p.suffix in ('.obj','.png') or p.name in ('model.xml','scene.xml','contact_scene.xml','physics_native.xml','render_config.json'))}
    comparisons[profile]=comparison
    assert all(comparison.values()),comparison
    preview_differences[profile]={}
    for p in (old/'previews').glob('*.png'):
        delta=np.abs(np.asarray(Image.open(p)).astype(int)-np.asarray(Image.open(package/'previews'/p.name)).astype(int))
        preview_differences[profile][p.name]={'max_channel_delta':int(delta.max()),'mean_channel_delta':float(delta.mean()),'note':'independent native render; not a byte-identity acceptance requirement'}
assert all(checks.values()),checks
result={'protected_files_unchanged':checks,'historical_tracked_output_file_count':len(before['history']),'same_geometry_textures_xml_render_configuration':comparisons,'preview_differences':preview_differences,'source_sha256':after['source_sha256'],'dependencies':after['dependencies'],'head':after['head'],'branch':after['branch'],'remote':after['remote']}
(root/'protection_and_comparison.json').write_text(json.dumps(result,indent=2))
for name in ('before.json','after.json','installed-pytest.txt','final-installed-pytest.txt','review-red.txt','run_real.py','check_results.py','progress.md'):
    shutil.copyfile(pathlib.Path('/tmp/m1-2-scope-fix-b9mENe')/name,root/name)
run=subprocess.run([sys.executable,'-m','pip','check'],text=True,capture_output=True)
(root/'pip-check.stdout.txt').write_text(run.stdout)
(root/'pip-check.stderr.txt').write_text(run.stderr)
assert run.returncode==0
import asset_mujoco
installed=pathlib.Path(asset_mujoco.__file__).parent
sources=repo/'src/asset_mujoco'
matches={str(p.relative_to(sources)):p.read_bytes()==(installed/p.relative_to(sources)).read_bytes() for p in sources.rglob('*.py')}
assert all(matches.values())
(root/'installed-source-check.json').write_text(json.dumps({'executable':sys.executable,'import_path':str(installed),'matches':matches},indent=2))
print(json.dumps(result,indent=2))
