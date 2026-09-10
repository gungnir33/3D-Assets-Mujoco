import os
import subprocess
import sys

def test_invalid_cli_exit():
    run=subprocess.run([sys.executable,"-B","-m","asset_mujoco.cli","convert","missing.glb","--output","/tmp/test-cli","--scale","-1"],env=dict(os.environ,PYTHONPATH="src"),capture_output=True,text=True)
    assert run.returncode==2
    assert '"error"' in run.stdout
