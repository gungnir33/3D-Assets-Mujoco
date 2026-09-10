"""在调用者所选解释器中做真实编译，兼容 Python 3.8；仅写临时目录。"""
import json
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco

CUBE=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
SIDES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]

def mesh_xml(asset,name,vertices,faces,strategy):
    attrs={"name":name,"vertex":" ".join(str(x) for v in vertices for x in v),
           "face":" ".join(str(x) for f in faces for x in f)}
    if strategy=="shell":
        attrs["inertia"]="shell"
    ET.SubElement(asset,"mesh",attrs)

def run():
    rows=[]
    with tempfile.TemporaryDirectory(prefix="asset-mujoco-probe-") as folder:
        for strategy in ("default","shell"):
            for case in ("box","six_material_faces","triangle","plane_with_collision"):
                root=ET.Element("mujoco")
                asset=ET.SubElement(root,"asset")
                body=ET.SubElement(ET.SubElement(root,"worldbody"),"body")
                ET.SubElement(body,"freejoint")
                ET.SubElement(body,"inertial",pos="0 0 0",mass="2",diaginertia="1 1 1")
                groups=[]
                if case=="box":
                    groups=[(CUBE,[(s[0],s[1],s[2]) for s in SIDES]+[(s[0],s[2],s[3]) for s in SIDES])]
                elif case=="six_material_faces":
                    groups=[([CUBE[i] for i in s],[(0,1,2),(0,2,3)]) for s in SIDES]
                elif case=="triangle":
                    groups=[([(0,0,0),(1,0,0),(0,1,0)],[(0,1,2)])]
                else:
                    groups=[([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[(0,1,2),(0,2,3)])]
                    ET.SubElement(body,"geom",type="box",size=".5 .5 .1",mass="0")
                for i,(vertices,faces) in enumerate(groups):
                    name="visual_"+str(i)
                    mesh_xml(asset,name,vertices,faces,strategy)
                    ET.SubElement(asset,"material",name="mat"+str(i),rgba="1 0 0 1")
                    ET.SubElement(body,"geom",type="mesh",mesh=name,material="mat"+str(i),mass="0",contype="0",conaffinity="0")
                path=Path(folder)/(case+"_"+strategy+".xml")
                ET.ElementTree(root).write(path)
                row={"version":mujoco.__version__,"case":case,"strategy":strategy,
                     "syntax":"unknown","compile":"failed","forward":"not_run","effect":"not_tested"}
                try:
                    model=mujoco.MjModel.from_xml_path(str(path))
                    row["syntax"]="supported"
                    row["compile"]="passed"
                    mujoco.mj_forward(model,mujoco.MjData(model))
                    row["forward"]="passed"
                    row["explicit_mass"]=float(model.body_mass[1])
                    row["explicit_inertia"]=model.body_inertia[1].tolist()
                except Exception as error:
                    row["error"]=str(error)
                    row["syntax"]="unsupported" if "Schema violation" in str(error) else "supported"
                rows.append(row)
    return {"mujoco":mujoco.__version__,"module":mujoco.__file__,"rows":rows}

if __name__=="__main__":
    print(json.dumps(run(),indent=2))
