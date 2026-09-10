import xml.etree.ElementTree as ET
import copy
import os
from pathlib import Path
import numpy as np
from .inertia import box_inertia,supplied_inertia

def values(items):
    return " ".join(format(float(x),".17g") for x in items)

def check_host_compiler(root):
    compiler=root.find("compiler")
    if compiler is None:
        return
    for key,value in compiler.attrib.items():
        if (key in ("meshdir","texturedir","assetdir") and value) or (key in ("fusestatic","balanceinertia") and value=="true") or (key=="inertiafromgeom" and value=="true"):
            raise ValueError("HOST_COMPILER_CONFLICT: "+key+"="+value)

def merge_host(root,package,prefix,output_parent):
    """仅用于自建最小宿主；有 defaults 时保守拒绝继承语义变化。"""
    check_host_compiler(root)
    if root.find("default") is not None:
        raise ValueError("HOST_COMPILER_CONFLICT: default inheritance")
    source=ET.parse(Path(package)/"model.xml").getroot()
    existing={node.get("name") for node in root.iter() if node.get("name")}
    incoming=[node.get("name") for node in source.iter() if node.get("name")]
    if any(prefix+name in existing for name in incoming):
        raise ValueError("HOST_COMPILER_CONFLICT: duplicate name")
    prepared=[]
    for tag in ("asset","worldbody"):
        section=source.find(tag)
        for original in section:
            item=copy.deepcopy(original)
            for node in item.iter():
                for key in ("name","mesh","material","texture"):
                    if key in node.attrib:
                        node.set(key,prefix+node.get(key))
                if "file" in node.attrib:
                    node.set("file",os.path.relpath(Path(package)/node.get("file"),output_parent))
            prepared.append((tag,item))
    for tag,item in prepared:
        target=root.find(tag)
        if target is None:
            target=ET.SubElement(root,tag)
        target.append(item)

def document(request,visuals,size,scene=False):
    root=ET.Element("mujoco",model=request.name)
    ET.SubElement(root,"compiler",angle="radian",inertiafromgeom="false")
    if scene:
        ET.SubElement(ET.SubElement(root,"visual"),"global",offwidth="512",offheight="512")
        option=ET.SubElement(root,"option",timestep="0.002")
        ET.SubElement(option,"flag",energy="enable",autoreset="disable")
    asset=ET.SubElement(root,"asset")
    world=ET.SubElement(root,"worldbody")
    body=ET.SubElement(world,"body",name=request.name)
    if request.body_mode=="free":
        ET.SubElement(body,"freejoint",name=request.name+"_free")
        if request.inertia_mode=="box_approx":
            com=np.array([0,0,size[2]/2])
            tensor=box_inertia(request.mass,size)
        elif request.inertia_mode=="supplied":
            com,tensor=supplied_inertia(request.supplied_inertia,request.mass,size)
        else:
            raise ValueError("watertight 属于任务8，尚未实现")
        from scipy.spatial.transform import Rotation
        eigen,rotation=np.linalg.eigh(tensor)
        if np.linalg.det(rotation)<0:
            rotation[:,0]*=-1
        xyzw=Rotation.from_matrix(rotation).as_quat()
        ET.SubElement(body,"inertial",pos=values(com),mass=str(request.mass),
                      diaginertia=values(eigen),quat=values(xyzw[[3,0,1,2]]))
    for item in visuals:
        attrs={"name":item["name"],"file":item["mesh"]}
        if item.get("shell"):
            attrs["inertia"]="shell"
        ET.SubElement(asset,"mesh",attrs)
        mat={"name":item["name"]+"_mat","rgba":values(item["rgba"]),"specular":"0","shininess":"0"}
        if item["texture"]:
            ET.SubElement(asset,"texture",name=item["name"]+"_tex",type="2d",file=item["texture"])
            mat.update(texture=item["name"]+"_tex",texuniform="false")
        ET.SubElement(asset,"material",mat)
        ET.SubElement(body,"geom",name=item["name"],type="mesh",mesh=item["name"],material=mat["name"],mass="0",contype="0",conaffinity="0",group="2")
    if request.collision_mode=="hull":
        ET.SubElement(asset,"mesh",name="collision_mesh",file="meshes/collision.obj")
        ET.SubElement(body,"geom",name="asset_collision",type="mesh",mesh="collision_mesh",mass="0",contype="1",conaffinity="1",group="3",rgba="0 1 0 .25")
    if scene:
        ET.SubElement(world,"geom",name="ground",type="plane",size="5 5 .1",rgba=".65 .65 .65 1")
        ET.SubElement(world,"light",pos="2 -3 5",dir="-2 3 -5")
    return root
