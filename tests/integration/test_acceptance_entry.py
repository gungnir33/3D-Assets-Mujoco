import json
import os
import subprocess
import sys
import trimesh

def invoke(source,output):
    return subprocess.run([sys.executable,'-B','-m','asset_mujoco.acceptance','--input',str(source),'--output',str(output)],
                          capture_output=True,text=True,env=os.environ.copy())

def test_acceptance_missing_input_is_not_executed(tmp_path):
    result=invoke(tmp_path/'missing.glb',tmp_path/'out')
    assert result.returncode==2
    report=json.loads(result.stdout)
    assert report['automatic_validation']=='not_executed'
    assert report['reason']=='REAL_INPUT_UNAVAILABLE'

def test_acceptance_real_engine_failure_exits_nonzero(tmp_path):
    source=tmp_path/'box.glb'
    trimesh.creation.box().export(source)
    result=invoke(source,tmp_path/'out')
    assert result.returncode==5
    report=json.loads(result.stdout)
    assert report['automatic_validation']=='failed'
    assert report['compile']==report['render']=='passed'
    assert report['physics']=='failed'
    assert report['migration']['status']=='passed'
    assert report['appearance_review']=='pending'
    assert report['host_integration']=='pending'

def test_engineering_acceptance_explicit_profile_and_migration(tmp_path):
    source=tmp_path/'box.glb'
    trimesh.creation.box().export(source)
    result=subprocess.run([sys.executable,'-B','-m','asset_mujoco.acceptance',
        '--input',str(source),'--output',str(tmp_path/'out'),
        '--contact-profile','engineering_static_v1'],capture_output=True,text=True)
    assert result.returncode==0, result.stdout+result.stderr
    report=json.loads(result.stdout)
    assert report['contact_profile']=='engineering_static_v1'
    assert report['native']['profile_contract']['matched'] is True
    assert report['migration']['status']=='passed'
    assert len(report['migration']['xml'])==6
    assert report['appearance_review']==report['host_integration']=='pending'
