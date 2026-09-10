import hashlib
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

def validate_physics(package,request,size):
    root=ET.parse(package/"scene.xml").getroot()
    world=root.find("worldbody")
    if request.body_mode=="static":
        radius=max(size)*.025
        body=ET.SubElement(world,"body",name="probe_body",pos=f"0 0 {size[2]+max(size)*.2+radius}")
        ET.SubElement(body,"freejoint")
        inertia=.4*.1*radius**2
        ET.SubElement(body,"inertial",pos="0 0 0",mass=".1",diaginertia=f"{inertia} {inertia} {inertia}")
        ET.SubElement(body,"geom",name="probe",type="sphere",size=str(radius),mass=".1")
        pair=("asset_collision","probe")
    else:
        body=world.find("body")
        body.set("pos","0 0 "+str(max(size)*.1))
        pair=("asset_collision","ground")
    contact=ET.SubElement(root,"contact")
    ET.SubElement(contact,"pair",geom1=pair[0],geom2=pair[1],solref=".004 1",solimp=".99 .99 .001")
    testfile=package/"physics_fixture.xml"
    ET.ElementTree(root).write(testfile)
    model=mujoco.MjModel.from_xml_path(str(testfile))
    if not model.opt.enableflags & int(mujoco.mjtEnableBit.mjENBL_ENERGY):
        raise ValueError("能量计算未启用")
    if not model.opt.disableflags & int(mujoco.mjtDisableBit.mjDSBL_AUTORESET):
        raise ValueError("autoreset 未禁用")
    data=mujoco.MjData(model)
    check_state(model,data,0,0)
    mujoco.mj_forward(model,data)
    check_state(model,data,0,0)
    ids={model.geom(name).id for name in pair}
    count=0
    first_contact=None
    worst=0.
    for step in range(1,1001):
        mujoco.mj_step(model,data)
        check_state(model,data,step,step*model.opt.timestep)
        for contact in data.contact:
            if {int(contact.geom1),int(contact.geom2)}==ids:
                if first_contact is None:
                    first_contact=step
                count+=1
                worst=min(worst,float(contact.dist))
    if count==0 or first_contact<=1:
        raise ValueError("ASSET_CONTACT_FAILED: 预期接触未发生或初始已穿透")
    limit=min(.005,.02*size[2])
    if -worst>limit:
        raise ValueError("ASSET_CONTACT_FAILED: penetration="+str(-worst))
    return {"steps":1000,"dt":model.opt.timestep,"time":data.time,"expected_pair":list(pair),
            "contact_count":count,"first_contact_step":first_contact,"max_penetration_m":-worst,
            "warning_counts":data.warning.number.tolist(),"first_abnormal_step":None,
            "asset_sha256":asset_signature(package),"mujoco":mujoco.__version__,
            "fixture_contact":{"solref":[.004,1],"solimp":[.99,.99,.001]}}
