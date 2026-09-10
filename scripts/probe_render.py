"""MUJOCO_GL 必须由父进程在启动本脚本之前设置。"""
import json
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import mujoco

def run():
    with tempfile.TemporaryDirectory(prefix="asset-render-") as folder:
        root=Path(folder)
        pixels=np.zeros((64,64,3),dtype=np.uint8)
        pixels[:32,:32]=[255,0,0]
        pixels[:32,32:]=[0,255,0]
        pixels[32:,:32]=[0,0,255]
        pixels[32:,32:]=[255,255,0]
        Image.fromarray(pixels).save(root/"uv.png")
        xml='''<mujoco><asset>
        <texture name="tex" type="2d" file="uv.png"/>
        <material name="mat" texture="tex" texuniform="false" rgba="1 1 1 1" emission="1" specular="0"/>
        <mesh name="plane" inertia="shell" vertex="-1 -1 0 1 -1 0 1 1 0 -1 1 0"
        face="0 1 2 0 2 3" texcoord="0 0 1 0 1 1 0 1"/>
        </asset><worldbody><geom type="mesh" mesh="plane" material="mat" contype="0" conaffinity="0"/>
        </worldbody></mujoco>'''
        (root/"scene.xml").write_text(xml)
        model=mujoco.MjModel.from_xml_path(str(root/"scene.xml"))
        data=mujoco.MjData(model)
        mujoco.mj_forward(model,data)
        camera=mujoco.MjvCamera()
        camera.lookat[:]=[0,0,0]
        camera.distance=3.5
        camera.azimuth=90
        camera.elevation=-90
        with mujoco.Renderer(model,256,256) as renderer:
            renderer.update_scene(data,camera=camera)
            frame=renderer.render()
        samples=[frame[y,x,:3].tolist() for y,x in [(90,90),(90,165),(165,90),(165,165)]]
        dominant=[tuple(np.asarray(v)>100) for v in samples]
        assert set(dominant)=={(True,False,False),(False,True,False),(False,False,True),(True,True,False)},samples
        return {"status":"passed","version":mujoco.__version__,"samples":samples,"positions_yx":[[90,90],[90,165],[165,90],[165,165]]}

if __name__=="__main__":
    print(json.dumps(run()))
