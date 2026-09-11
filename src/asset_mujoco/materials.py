"""可视资源独立导出；不焊接，不简化，颜色因子仅应用一次。"""
from pathlib import Path
import numpy as np
from PIL import Image
from trimesh.visual.material import PBRMaterial

def export_visual(mesh,root,index):
    root=Path(root)
    (root/"meshes").mkdir(exist_ok=True)
    (root/"textures").mkdir(exist_ok=True)
    name="visual_%03d"%index
    uv=getattr(mesh.visual,"uv",None)
    mat=getattr(mesh.visual,"material",None)
    image=getattr(mat,"baseColorTexture",None)
    if image is None:
        image=getattr(mat,"image",None)
    factor=getattr(mat,"baseColorFactor",None)
    if factor is None:
        factor=[1,1,1,1] if isinstance(mat,PBRMaterial) else getattr(mat,"diffuse",[180,180,180,255])
    factor=np.asarray(factor,dtype=float)
    if factor.max()>1:
        factor=factor/255
    if factor.shape!=(4,) or not np.isfinite(factor).all():
        raise ValueError("无效材质颜色")
    result={"name":name,"mesh":"meshes/"+name+".obj","rgba":factor.tolist(),"texture":None}
    if image is not None:
        if uv is None or len(uv)!=len(mesh.vertices) or not np.isfinite(uv).all():
            raise ValueError("纹理缺有效 TEXCOORD_0")
        if image.width*image.height>64_000_000:
            raise ValueError("纹理解码尺寸超限")
        rgb=np.asarray(image.convert("RGB"),dtype=float)/255
        linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)*factor[:3]
        rgb=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
        result["texture"]="textures/"+name+".png"
        Image.fromarray(np.rint(np.clip(rgb,0,1)*255).astype("uint8")).save(root/result["texture"])
        result["rgba"]=[1,1,1,1]
    lines=["v "+" ".join(format(float(x),".17g") for x in v) for v in mesh.vertices]
    if uv is not None:
        lines+=["vt "+" ".join(format(float(x),".17g") for x in v) for v in uv]
    normals=mesh.metadata.get("export_normals")
    if normals is None:
        normals=mesh.vertex_normals
    lines+=["vn "+" ".join(format(float(x),".17g") for x in v) for v in normals]
    for face in mesh.faces:
        tokens=[f"{i+1}/{i+1}/{i+1}" if uv is not None else f"{i+1}//{i+1}" for i in face]
        lines.append("f "+" ".join(tokens))
    (root/result["mesh"]).write_text("\n".join(lines)+"\n")
    return result
