import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

@pytest.mark.parametrize("backend",["egl","osmesa"])
def test_native_four_color(backend):
    env=dict(os.environ,MUJOCO_GL=backend)
    proc=subprocess.run([sys.executable,"-B",str(Path(__file__).parents[2]/"scripts/probe_render.py")],env=env,capture_output=True,text=True,timeout=60)
    if proc.returncode and ("glGetError" in proc.stderr or "Cannot initialize" in proc.stderr):
        pytest.skip(backend+" 不可用或探测失败: "+proc.stderr[-700:])
    assert proc.returncode==0,proc.stderr
    assert json.loads(proc.stdout)["status"]=="passed"
