import os
import subprocess
import sys

def test_invalid_cli_exit():
    run=subprocess.run([sys.executable,"-B","-m","asset_mujoco.cli","convert","missing.glb","--output","/tmp/test-cli","--scale","-1"],env=dict(os.environ,PYTHONPATH="src"),capture_output=True,text=True)
    assert run.returncode==2
    assert '"error"' in run.stdout

def test_changed_asset_invalidates_physics_report(tmp_path):
    import json
    import trimesh
    from asset_mujoco.pipeline import convert
    from asset_mujoco.contracts import ConversionRequest,ValidationResult
    from asset_mujoco.validation import run_contact_case
    from asset_mujoco.manifest import asset_signature,record_layer,compile_resources,checked_report
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/"out",source_up="z",validation_level="compile")
    package=convert(request)
    native=run_contact_case(package,request,[1,1,1],initial_position=[0,0,1.026])
    assert native["status"]=="passed"
    (package/"physics_evidence.json").write_text(json.dumps({"status":"passed","native":native}))
    record_layer(package,"physics","passed",compile_resources(package)+["physics_native.xml","physics_evidence.json"],
                 {"required_case":"native","initial_position":[0,0,1.026]})
    digest=json.loads((package/'evidence_manifest.json').read_text())['layers']['physics']['sha256']
    state=ValidationResult(compile="passed",physics="passed",asset_physics_sha256=digest)
    (package/"validation_report.json").write_text(state.model_dump_json())
    assert checked_report(package).physics=="passed"
    with (package/"model.xml").open("a") as file:
        file.write("<!-- changed -->")
    run=subprocess.run([sys.executable,"-B","-m","asset_mujoco.cli","report",str(package)],env=dict(os.environ,PYTHONPATH="src"),capture_output=True,text=True)
    assert json.loads(run.stdout)["physics"]!="passed"
