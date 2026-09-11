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
    from asset_mujoco.manifest import asset_signature
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    request=ConversionRequest(input=source,output=tmp_path/"out",source_up="z",validation_level="compile")
    package=convert(request)
    native=run_contact_case(package,request,[1,1,1],initial_position=[0,0,1.026])
    assert native["status"]=="passed"
    (package/"physics_evidence.json").write_text(json.dumps({"status":"passed","native":native}))
    state=ValidationResult(compile="passed",physics="passed",asset_physics_sha256=asset_signature(package))
    (package/"validation_report.json").write_text(state.model_dump_json())
    with (package/"model.xml").open("a") as file:
        file.write("<!-- changed -->")
    run=subprocess.run([sys.executable,"-B","-m","asset_mujoco.cli","report",str(package)],env=dict(os.environ,PYTHONPATH="src"),capture_output=True,text=True)
    assert json.loads(run.stdout)["physics"]!="passed"
