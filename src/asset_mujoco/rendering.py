"""每种后端独立子进程；在导入 MuJoCo 前选择 MUJOCO_GL。"""
import json
import os
from pathlib import Path
import subprocess
import sys

def render_package(package,size):
    attempts=[]
    for backend in ("egl","osmesa"):
        env=dict(os.environ,MUJOCO_GL=backend,PYTHONPATH=str(Path(__file__).parents[1]))
        result=subprocess.run([sys.executable,"-B","-m","asset_mujoco.rendering",str(package),json.dumps(size)],env=env,capture_output=True,text=True,timeout=90)
        attempts.append({"backend":backend,"exit_code":result.returncode,"stderr":result.stderr[-4000:]})
        if result.returncode and not any(s in result.stderr for s in ("glGetError","Cannot initialize","EGL","OSMesa")):
            (package/"render_evidence.json").write_text(json.dumps({"status":"failed","attempts":attempts},indent=2))
            raise RuntimeError("RENDER_FAILED: "+result.stderr)
        if result.returncode==0:
            report=json.loads(result.stdout)
            report["attempts"]=attempts
            (package/"render_evidence.json").write_text(json.dumps(report,indent=2))
            return report
    (package/"render_evidence.json").write_text(json.dumps({"status":"unavailable","attempts":attempts},indent=2))
    raise RuntimeError("RENDER_UNAVAILABLE: "+str(attempts))

def worker(package,size):
    import mujoco
    import numpy as np
    from PIL import Image
    model=mujoco.MjModel.from_xml_path(str(package/"scene.xml"))
    data=mujoco.MjData(model)
    mujoco.mj_forward(model,data)
    out=package/"previews"
    out.mkdir(exist_ok=True)
    camera=mujoco.MjvCamera()
    camera.lookat[:]=[0,0,size[2]/2]
    camera.distance=max(size)*2.7
    option=mujoco.MjvOption()
    option.geomgroup[3]=0
    images=[]
    with mujoco.Renderer(model,512,512) as renderer:
        for name,azimuth,elevation,collision in (("front",-90,-10,False),("side",0,-10,False),("iso",-45,-25,False),("collision",-45,-25,True)):
            camera.azimuth=azimuth
            camera.elevation=elevation
            option.geomgroup[3]=int(collision)
            renderer.update_scene(data,camera=camera,scene_option=option)
            pixels=renderer.render()
            if not np.isfinite(pixels).all() or pixels.shape!=(512,512,3):
                raise ValueError("INVALID_RENDER")
            Image.fromarray(pixels).save(out/(name+".png"))
            images.append("previews/"+name+".png")
    return {"status":"passed","backend":os.environ["MUJOCO_GL"],"images":images,"appearance_review":"pending","mujoco":mujoco.__version__}

if __name__=="__main__":
    print(json.dumps(worker(Path(sys.argv[1]),json.loads(sys.argv[2]))))
