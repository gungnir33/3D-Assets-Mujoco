import hashlib,json,pathlib,subprocess,sys,tempfile,shutil
import asset_mujoco
from asset_mujoco.manifest import checked_report,fingerprint
repo=pathlib.Path('/home/mcl/workspace/3D-Assets-Mujoco')
root=pathlib.Path(tempfile.mkdtemp(prefix='m1_2_scope_fix_',dir=repo/'outputs'))
source='/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb'
keys=('compile','physics','render','appearance_review','contact_profile','validation_scope','followup_ground','application_force_limit','host_integration','robot_contact_safety','limitations','status')
summary={'root':str(root),'interpreter':sys.executable,'import_path':asset_mujoco.__file__,'profiles':{}}
for profile in ('preserve','engineering_static_v1'):
    cmd=[sys.executable,'-I','-m','asset_mujoco.acceptance','--input',source,'--output',str(root/profile),'--contact-profile',profile]
    run=subprocess.run(cmd,text=True,capture_output=True)
    (root/(profile+'.stdout.json')).write_text(run.stdout)
    (root/(profile+'.stderr.txt')).write_text(run.stderr)
    report=json.loads(run.stdout)
    package=pathlib.Path(report['package'])
    cli=subprocess.run([sys.executable,'-I','-m','asset_mujoco.cli','report',str(package)],text=True,capture_output=True)
    (root/(profile+'.report.json')).write_text(cli.stdout)
    disk=json.loads((package/'validation_report.json').read_text())
    read=json.loads(cli.stdout)
    equal=all(report[k]==disk[k]==read[k] for k in keys)
    summary['profiles'][profile]={'command':cmd,'exit_code':run.returncode,'package':str(package),'report_consistency':equal,'status':report['status'],'native':report['native'],'followup_ground':report['followup_ground'],'migration':report['migration'],'package_sha256':fingerprint(package)}
    assert equal and run.returncode==(5 if profile=='preserve' else 0)
    assert report['appearance_review']==report['host_integration']=='pending'
    assert report['migration']['status']=='passed'
cmd=[sys.executable,'-I','-m','asset_mujoco.cli','convert',source,'--output',str(root/'cli_convert'),'--source-up','y','--yaw-deg','180','--scale','.5','--contact-profile','engineering_static_v1']
run=subprocess.run(cmd,text=True,capture_output=True)
(root/'convert.stdout.json').write_text(run.stdout)
(root/'convert.stderr.txt').write_text(run.stderr)
converted=json.loads(run.stdout)
package=pathlib.Path(converted['package'])
disk=json.loads((package/'validation_report.json').read_text())
read=checked_report(package).model_dump()
summary['convert']={'command':cmd,'exit_code':run.returncode,'package':str(package),'consistent':all(converted[k]==disk[k]==read[k] for k in keys)}
assert run.returncode==0 and summary['convert']['consistent']
before=json.loads(pathlib.Path('/tmp/m1-2-scope-fix-b9mENe/before.json').read_text())
summary['before_snapshot_keys']=list(before)
(root/'real_results.json').write_text(json.dumps(summary,indent=2))
print(root)
