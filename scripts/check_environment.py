"""只读清单；不安装、不导入第一阶段模型。"""
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
import mujoco

def git(*args):
    return subprocess.check_output(["git",*args],text=True).strip()

def main():
    first=Path("/home/mcl/workspace/3D-Assets-Agent")
    assets=sorted(first.glob("assets/20260909_210*/model.glb"))
    report={
        "python":platform.python_version(),"prefix":sys.prefix,
        "converter_mujoco":mujoco.__version__,"mujoco_file":mujoco.__file__,
        "host_compatibility":"pending",
        "first_stage_commit":git("-C",str(first),"rev-parse","HEAD"),
        "first_stage_status":git("-C",str(first),"status","--porcelain"),
        "assets":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in assets},
    }
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
