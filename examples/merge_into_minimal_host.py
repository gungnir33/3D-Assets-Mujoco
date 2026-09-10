"""仅创建新的示例 XML，绝不覆盖已有文件。"""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from asset_mujoco.mjcf import merge_host

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("output",type=Path)
args=parser.parse_args()
root=ET.fromstring('<mujoco><compiler angle="radian" inertiafromgeom="false"/><option timestep=".003"/><worldbody/></mujoco>')
merge_host(root,args.package.resolve(),"example_",args.output.resolve().parent)
with args.output.open("xb") as file:
    ET.ElementTree(root).write(file,encoding="utf-8",xml_declaration=True)
