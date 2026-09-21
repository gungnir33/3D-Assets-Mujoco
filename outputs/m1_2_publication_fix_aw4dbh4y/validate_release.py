import contextlib,hashlib,io,json,pathlib,shutil,subprocess,sys,tempfile
from unittest.mock import patch
import importlib.metadata as versions
import asset_mujoco
import asset_mujoco.pipeline as pipeline
import asset_mujoco.validation as validation
from asset_mujoco.cli import main
from asset_mujoco.manifest import checked_report,fingerprint,record_layer
import trimesh

repo=pathlib.Path('/home/mcl/workspace/3D-Assets-Mujoco')
scratch=pathlib.Path('/tmp/m1-2-publication-a3A6qA')
root=pathlib.Path(tempfile.mkdtemp(prefix='m1_2_publication_fix_',dir=repo/'outputs'))
source=pathlib.Path('/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb')
installed=pathlib.Path(asset_mujoco.__file__).parent
matches={str(p.relative_to(repo/'src/asset_mujoco')):p.read_bytes()==(installed/p.relative_to(repo/'src/asset_mujoco')).read_bytes() for p in (repo/'src/asset_mujoco').rglob('*.py')}
assert all(matches.values())
result={'output_root':str(root),'executable':sys.executable,'import_path':str(installed),'source_matches':matches,
        'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
        'dependencies':{k:versions.version(k) for k in ('mujoco','trimesh','numpy','Pillow','pydantic','pytest','scipy')},'real':{},'fault_injection':{}}
keys=('compile','physics','render','appearance_review','contact_profile','validation_scope','followup_ground','limitations','status','render_error')
for profile in ('preserve','engineering_static_v1'):
    cmd=[sys.executable,'-I','-m','asset_mujoco.acceptance','--input',str(source),'--output',str(root/profile),'--contact-profile',profile]
    run=subprocess.run(cmd,text=True,capture_output=True)
    (root/(profile+'.stdout.json')).write_text(run.stdout)
    (root/(profile+'.stderr.txt')).write_text(run.stderr)
    data=json.loads(run.stdout); package=pathlib.Path(data['package'])
    query=subprocess.run([sys.executable,'-I','-m','asset_mujoco.cli','report',str(package)],text=True,capture_output=True)
    (root/(profile+'.report.json')).write_text(query.stdout)
    disk=json.loads((package/'validation_report.json').read_text()); report=json.loads(query.stdout)
    assert all(data[k]==disk[k]==report[k] for k in keys)
    assert run.returncode==query.returncode==(5 if profile=='preserve' else 0)
    assert data['migration']['status']=='passed'
    assert data['appearance_review']==data['host_integration']=='pending'
    assert data['followup_ground']['status']=='failed' and data['followup_ground']['mandatory_for_physics'] is False
    published=[p.name for p in package.parent.iterdir() if p.is_dir() and not p.name.startswith('.')]
    assert (not published) if profile=='preserve' else (package.name in published)
    result['real'][profile]={'command':cmd,'exit_code':run.returncode,'report_exit_code':query.returncode,
        'published_directories':published,'package':str(package),'fingerprint':fingerprint(package),
        'report_consistent':True,'result':data}

cube=root/'synthetic_box.glb'; trimesh.creation.box().export(cube)
original_validate=validation.validate_physics
for kind in ('render_unavailable','render_failed','diagnostic_io','scope_contradiction'):
    parent=root/'fault_injection'/kind
    capture=io.StringIO()
    def fail_render(package,size):
        native=json.loads((package/'physics_native_evidence.json').read_text())['native']
        assert native['status']=='passed'
        raise RuntimeError(('RENDER_FAILED' if kind=='render_failed' else 'RENDER_UNAVAILABLE')+': explicit synthetic injection')
    def conflicting(package,request,size):
        evidence=original_validate(package,request,size)
        path=package/'contact_result_manifest.json'; item=json.loads(path.read_text())
        item['contact_profile']='preserve'; path.write_text(json.dumps(item))
        entry=json.loads((package/'evidence_manifest.json').read_text())['layers']['physics']
        entry=record_layer(package,'physics',entry['status'],entry['files'],entry['context'])
        path=package/'validation_report.json'; item=json.loads(path.read_text())
        item['asset_physics_sha256']=entry['sha256']; path.write_text(json.dumps(item))
        evidence['asset_sha256']=entry['sha256']
        return evidence
    write=pathlib.Path.write_text
    def io_failure(path,*args,**kwargs):
        if path.name=='render_failure.json':
            raise OSError('explicit synthetic diagnostic storage outage')
        return write(path,*args,**kwargs)
    with contextlib.ExitStack() as stack:
        publisher=stack.enter_context(patch.object(pipeline,'atomic_publish',wraps=pipeline.atomic_publish))
        if kind=='scope_contradiction':
            stack.enter_context(patch.object(validation,'validate_physics',conflicting))
        else:
            stack.enter_context(patch('asset_mujoco.rendering.render_package',fail_render))
        if kind=='diagnostic_io':
            stack.enter_context(patch.object(pathlib.Path,'write_text',io_failure))
        with contextlib.redirect_stdout(capture):
            code=main(['convert',str(cube),'--output',str(parent),'--contact-profile','engineering_static_v1'])
        assert publisher.call_count==0
    output=json.loads(capture.getvalue()); package=pathlib.Path(output['package'])
    assert package.exists() and not list(parent.glob('asset_*'))
    (parent/'convert.stdout.json').write_text(capture.getvalue())
    disk=json.loads((package/'validation_report.json').read_text()); report=checked_report(package).model_dump()
    (parent/'checked_report.json').write_text(json.dumps(report,indent=2))
    expected={'render_unavailable':7,'render_failed':5,'diagnostic_io':3,'scope_contradiction':5}[kind]
    assert code==expected and report['physics']=='passed'
    if kind.startswith('render_'):
        assert disk==report and report['validation_scope']['evidence_status']=='verified' and not report['evidence_issues']
    result['fault_injection'][kind]={'exit_code':code,'atomic_publish_calls':0,'package':str(package),'stdout':output,'disk':disk,'checked':report}

before=json.loads((scratch/'before.json').read_text())
def git(path,*args):
    return subprocess.check_output(['git','-C',str(path),*args],text=True).strip()
phase=pathlib.Path('/home/mcl/workspace/3D-Assets-Agent')
protection={'history_count':len(before['history']),
    'history_unchanged':all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==v for p,v in before['history'].items()),
    'phase1_head_unchanged':git(phase,'rev-parse','HEAD')==before['phase1_head'],
    'phase1_status_unchanged':git(phase,'status','--short')==before['phase1_status'],
    'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
assert protection['history_unchanged'] and protection['phase1_head_unchanged'] and protection['phase1_status_unchanged']
assert protection['input_sha256']==before['source_sha256']
result['protection']=protection
(root/'release_evidence.json').write_text(json.dumps(result,indent=2))
shutil.copyfile(scratch/'before.json',root/'before.json')
shutil.copyfile(scratch/'validate_release.py',root/'validate_release.py')
print(root)
