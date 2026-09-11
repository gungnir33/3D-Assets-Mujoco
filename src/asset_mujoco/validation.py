"""原始碰撞配置是验收；强制 contact pair 只属于独立 benchmark。"""
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from .manifest import asset_signature

def check_state(model,data,step,expected_time):
    arrays=(data.qpos,data.qvel,data.qacc,data.energy)
    if not all(np.isfinite(a).all() for a in arrays):
        raise ValueError("NONFINITE_STATE first_step="+str(step))
    if not np.isclose(data.time,expected_time,rtol=1e-8,atol=1e-10):
        raise ValueError("TIME_RESET_OR_DRIFT first_step="+str(step))
    if np.any(data.warning.number):
        raise ValueError("SIMULATION_WARNING first_step="+str(step)+" counters="+str(data.warning.number))

def run_contact_case(package,request,size,*,benchmark=False,initial_position=None):
    root=ET.parse(package/"scene.xml").getroot()
    world=root.find("worldbody")
    if request.body_mode=="static":
        radius=max(size)*.025
        initial_position=list(initial_position) if initial_position is not None else [0,0,size[2]+max(size)*.2+radius]
        body=ET.SubElement(world,"body",name="probe_body",pos=" ".join(map(str,initial_position)))
        ET.SubElement(body,"freejoint")
        inertia=.4*.1*radius**2
        ET.SubElement(body,"inertial",pos="0 0 0",mass=".1",diaginertia=f"{inertia} {inertia} {inertia}")
        ET.SubElement(body,"geom",name="probe",type="sphere",size=str(radius),mass=".1")
        pair=("asset_collision","probe")
    else:
        body=world.find("body")
        initial_position=list(initial_position) if initial_position is not None else [0,0,max(size)*.1]
        body.set("pos"," ".join(map(str,initial_position)))
        pair=("asset_collision","ground")
    if root.find(".//pair") is not None:
        raise ValueError("原始配置验收不接受已有强制接触 pair")
    if benchmark:
        contact=ET.SubElement(root,"contact")
        ET.SubElement(contact,"pair",geom1=pair[0],geom2=pair[1],solref=".004 1",solimp=".99 .99 .001")
    kind="benchmark" if benchmark else "native"
    testfile=package/("physics_"+kind+".xml")
    ET.ElementTree(root).write(testfile)
    model=mujoco.MjModel.from_xml_path(str(testfile))
    if not model.opt.enableflags & int(mujoco.mjtEnableBit.mjENBL_ENERGY):
        raise ValueError("能量计算未启用")
    if not model.opt.disableflags & int(mujoco.mjtDisableBit.mjDSBL_AUTORESET):
        raise ValueError("autoreset 未禁用")
    if model.opt.enableflags & int(mujoco.mjtEnableBit.mjENBL_OVERRIDE):
        raise ValueError("不接受全局接触参数 override")
    data=mujoco.MjData(model)
    check_state(model,data,0,0)
    mujoco.mj_forward(model,data)
    check_state(model,data,0,0)
    ids={model.geom(name).id for name in pair}
    count=0
    first_contact=None
    last_contact=None
    resolved_contact=None
    worst=0.
    abnormal=None
    error=None
    step=0
    limit=min(.005,.02*size[2])
    for step in range(1,1001):
        try:
            mujoco.mj_step(model,data)
            check_state(model,data,step,step*model.opt.timestep)
        except ValueError as exc:
            abnormal=abnormal or step
            error=str(exc)
            break
        for contact in data.contact:
            if {int(contact.geom1),int(contact.geom2)}==ids:
                if first_contact is None:
                    first_contact=step
                    resolved_contact={k:getattr(contact,k).tolist() for k in ("solref","solimp","friction")}
                last_contact=step
                count+=1
                worst=min(worst,float(contact.dist))
                if (step<=1 or -float(contact.dist)>limit) and abnormal is None:
                    abnormal=step
    if count==0 or first_contact<=1:
        error=error or "ASSET_CONTACT_FAILED: 预期接触未发生或初始已穿透"
        abnormal=abnormal or step
    if -worst>limit:
        error=error or "ASSET_CONTACT_FAILED: penetration="+str(-worst)
    geoms={}
    for name in pair:
        i=model.geom(name).id
        geoms[name]={k:np.asarray(getattr(model,"geom_"+k)[i]).tolist() for k in ("contype","conaffinity","friction","solref","solimp","pos")}
    return {"kind":kind,"status":"failed" if error else "passed","error":error,
            "steps":step,"dt":model.opt.timestep,"time":data.time,"expected_pair":list(pair),
            "initial_position":initial_position,"resolved_geoms":geoms,"first_resolved_contact":resolved_contact,
            "contact_count":count,"first_contact_step":first_contact,"last_contact_step":last_contact,"max_penetration_m":-worst,
            "penetration_limit_m":limit,"warning_counts":data.warning.number.tolist(),"first_abnormal_step":abnormal,
            "final_qpos":data.qpos.tolist(),"final_qvel":data.qvel.tolist(),"final_energy":data.energy.tolist(),
            "fixture":testfile.name,"mujoco":mujoco.__version__,
            "fixture_contact":{"solref":[.004,1],"solimp":[.99,.99,.001]} if benchmark else None}

def validate_physics(package,request,size):
    native=run_contact_case(package,request,size)
    benchmark=run_contact_case(package,request,size,benchmark=True)
    return {"status":native["status"],"native":native,"benchmark":benchmark,
            "asset_sha256":asset_signature(package)}
