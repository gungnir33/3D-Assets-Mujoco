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
    from asset_mujoco.contracts import ConversionRequest
    source=tmp_path/"box.glb"
    trimesh.creation.box().export(source)
    package=convert(ConversionRequest(input=source,output=tmp_path/"out",validation_level="physics"))
    with (package/"model.xml").open("a") as file:
        file.write("<!-- changed -->")
    run=subprocess.run([sys.executable,"-B","-m","asset_mujoco.cli","report",str(package)],env=dict(os.environ,PYTHONPATH="src"),capture_output=True,text=True)
    assert json.loads(run.stdout)["physics"]!="passed"
