import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import asset_mujoco
from asset_mujoco.contact_diagnostics import trace_fixture
from asset_mujoco.manifest import compile_resources, checked_report, fingerprint

repo=Path('/home/mcl/workspace/3D-Assets-Mujoco')
root=Path(tempfile.mkdtemp(prefix='m1_2_final_',dir=repo/'outputs'))
print(root,flush=True)
shutil.copyfile(__file__,root/'reproduce_final_checks.py')
for suffix in ('txt','stderr'):
    shutil.copyfile('/tmp/mujoco-m1-2-t6KswA/install-final.'+suffix,root/('install.'+suffix))
env=os.environ.copy(); env.pop('PYTHONPATH',None); env['PYTHONNOUSERSITE']='1'
def command(name,args,cwd='/tmp'):
    started=time.monotonic()
    result=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True)
    (root/(name+'.stdout')).write_text(result.stdout)
    (root/(name+'.stderr')).write_text(result.stderr)
    entry={'command':args,'cwd':str(cwd),'exit_code':result.returncode,'duration_s':time.monotonic()-started}
    print(name,entry['exit_code'],flush=True)
    return result,entry
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
source=repo/'src/asset_mujoco'; installed=Path(asset_mujoco.__file__).parent
matches={str(p.relative_to(source)): {'sha256':sha(p),'installed_sha256':sha(installed/p.relative_to(source))}
         for p in source.rglob('*.py')}
assert all(v['sha256']==v['installed_sha256'] for v in matches.values())
evidence={'root':str(root),'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
          'installed_module':str(installed),'source_installation_match':matches,
          'python':sys.version,'dependencies':{k:metadata.version(k) for k in ('mujoco','trimesh','numpy','Pillow','pytest','pydantic','scipy')},
          'commands':{},'appearance_review':'pending','host_integration':'pending','application_force_limit':'not_specified'}
for name,args,cwd in [
    ('pip_check',[sys.executable,'-I','-m','pip','check'],'/tmp'),
    ('freeze',[sys.executable,'-I','-m','pip','freeze'],'/tmp'),
    ('pytest',[sys.executable,'-B','-m','pytest','-p','no:cacheprovider','-o','pythonpath=','--import-mode=importlib','-q','-rs'],repo),
]:
    result,evidence['commands'][name]=command(name,args,cwd)
    if result.returncode:
        raise RuntimeError(name+' failed; see '+str(root))
for profile in ('preserve','engineering_static_v1'):
    args=[sys.executable,'-I','-m','asset_mujoco.acceptance','--contact-profile',profile,'--output',str(root/profile)]
    result,evidence['commands'][profile]=command(profile,args)
    evidence[profile]=json.loads(result.stdout)
    if result.returncode != (5 if profile=='preserve' else 0):
        raise RuntimeError('Unexpected acceptance result; see '+str(root))
candidate=Path(evidence['engineering_static_v1']['package'])
args=[sys.executable,'-I','-m','asset_mujoco.profile_diagnostics','--package',str(candidate),'--output',str(root/'experiments')]
result,evidence['commands']['experiments']=command('experiments',args)
if result.returncode:
    raise RuntimeError('diagnostics failed')
evidence['experiments']=json.loads(result.stdout)
preserve=Path(evidence['preserve']['package'])
directory=root/'preserve_trace'; directory.mkdir()
for name in compile_resources(preserve):
    dest=directory/name; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(preserve/name,dest)
shutil.copyfile(preserve/'physics_native.xml',directory/'fixture.xml')
evidence['preserve_trace']=trace_fixture(directory/'fixture.xml',directory)
assert abs(evidence['preserve_trace']['max_penetration_m']-evidence['preserve']['native']['max_penetration_m'])<1e-12
assert checked_report(candidate).physics=='passed'
evidence['candidate_fingerprint_after_diagnostics']=fingerprint(candidate)
assert evidence['candidate_fingerprint_after_diagnostics']==evidence['engineering_static_v1']['package_sha256']
evidence['before']=json.loads(Path('/tmp/mujoco-m1-2-t6KswA/before.json').read_text())
result,evidence['commands']['protection_snapshot']=command('protection_snapshot',[
    sys.executable,'-I','/tmp/mujoco-contact-diagnosis-txK7uw/snapshot.py'])
evidence['after']=json.loads(result.stdout)
evidence['protection_checks']={k:evidence['before'][k]==evidence['after'][k]
    for k in ('phase1_head','phase1_status','source_sha256','history','dependencies')}
assert all(evidence['protection_checks'].values())
(root/'final_evidence.json').write_text(json.dumps(evidence,indent=2))
hashes={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
(root/'output_hashes.json').write_text(json.dumps(hashes,indent=2))
print(json.dumps({'root':str(root),'checks':evidence['protection_checks'],'complete':True}),flush=True)
