import hashlib,json,pathlib,shutil
repo=pathlib.Path('/home/mcl/workspace/3D-Assets-Mujoco')
scratch=pathlib.Path('/tmp/m1-2-publication-a3A6qA')
root=repo/'outputs/m1_2_publication_fix_yanu7ij1'
new=json.loads((root/'release_evidence.json').read_text())
old=json.loads((repo/'outputs/m1_2_scope_fix_jnabps39/real_results.json').read_text())
comparison={}
for profile,row in new['real'].items():
    previous=pathlib.Path(old['profiles'][profile]['package'])
    current=pathlib.Path(row['package'])
    items=[p for p in previous.rglob('*') if p.is_file() and 'previews' not in p.relative_to(previous).parts and (p.suffix in ('.obj','.png') or p.name in ('model.xml','scene.xml','contact_scene.xml','physics_native.xml','render_config.json'))]
    comparison[profile]={str(p.relative_to(previous)):hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256((current/p.relative_to(previous)).read_bytes()).hexdigest() for p in items}
    assert all(comparison[profile].values())
before=json.loads((scratch/'before.json').read_text()); after=json.loads((scratch/'after.json').read_text())
protection={k:before[k]==after[k] for k in ('dependencies','phase1_head','phase1_status','source_sha256','history')}
assert all(protection.values())
(root/'protection_and_geometry.json').write_text(json.dumps({'protected':protection,'history_count':len(before['history']),'unchanged_geometry_textures_xml_render_config':comparison},indent=2))
for name in ('before.json','after.json','baseline.txt','confirmed-red.txt','gate-red.txt','gate-and-io-red.txt','render-green.txt','matrix-final.txt','review-red.txt','review-green.txt','source-suite.txt','installed-suite.txt','final-installed-suite.txt','pip-check.stdout.txt','pip-check.stderr.txt','progress.md','archive.py'):
    shutil.copyfile(scratch/name,root/name)
print(json.dumps(protection))
