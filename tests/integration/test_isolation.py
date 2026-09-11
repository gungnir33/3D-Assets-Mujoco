import importlib.util
import subprocess
import sys
from pathlib import Path

def test_environment_is_independent():
    assert sys.version_info[:2]==(3,10)
    name=Path(sys.prefix).name
    assert name=="asset_mujoco" or name.startswith("asset_mujoco_m1_1_rebuild")
    assert importlib.util.find_spec("local_3d_agent") is None
    assert importlib.util.find_spec("torch") is None

def test_remote():
    assert subprocess.check_output(["git","remote","get-url","origin"],text=True).strip()=="https://github.com/gungnir33/3D-Assets-Mujoco.git"

def test_ignore_scope():
    for name in ("tests/fixtures/a.xml","tests/fixtures/a.obj","tests/fixtures/a.png"):
        assert subprocess.run(["git","check-ignore","--no-index",name],capture_output=True).returncode==1
    assert subprocess.run(["git","check-ignore","--no-index","outputs/private.glb"],capture_output=True).returncode==0
