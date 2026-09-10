"""在加载器之前检查源特性，禁止静默丢失信息。"""
import json
import struct
from pathlib import Path
from urllib.parse import unquote,urlsplit

def resource_path(root,uri):
    root=Path(root).resolve()
    if urlsplit(uri).scheme or urlsplit(uri).netloc:
        raise ValueError("禁止远程资源")
    path=(root/unquote(uri)).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("资源越界或缺失")
    return path

def validate_glb_features(doc):
    if doc.get("extensionsRequired") or doc.get("extensionsUsed"):
        raise ValueError("当前基线不支持 GLB 扩展")
    if doc.get("skins") or doc.get("animations"):
        raise ValueError("不支持骨骼或动画")
    for mesh in doc.get("meshes",[]):
        for p in mesh.get("primitives",[]):
            if p.get("mode",4)!=4 or p.get("targets") or p.get("extensions"):
                raise ValueError("仅支持无 morph 的三角形 primitive")
            if set(p.get("attributes",{}))-{"POSITION","NORMAL","TEXCOORD_0"}:
                raise ValueError("不支持顶点色、额外 UV 或其它属性")
    for mat in doc.get("materials",[]):
        if mat.get("alphaMode","OPAQUE")!="OPAQUE" or mat.get("extensions"):
            raise ValueError("不支持透明或扩展材质")
        tex=mat.get("pbrMetallicRoughness",{}).get("baseColorTexture",{})
        if tex.get("texCoord",0)!=0 or tex.get("extensions"):
            raise ValueError("不支持额外 UV 或纹理变换")
        if any(mat.get(k) for k in ("normalTexture","occlusionTexture","emissiveTexture")):
            raise ValueError("基础模式不支持附加材质纹理")
    for sampler in doc.get("samplers",[]):
        if sampler.get("wrapS",10497)!=10497 or sampler.get("wrapT",10497)!=10497:
            raise ValueError("仅支持 repeat sampler")

def inspect_input(path):
    path=Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size>512*1024**2:
        raise ValueError("非普通文件或超过输入大小限制")
    if path.suffix.lower()==".glb":
        data=path.read_bytes()
        if len(data)<20:
            raise ValueError("GLB 头不完整")
        magic,version,total=struct.unpack_from("<4sII",data)
        length,kind=struct.unpack_from("<II",data,12)
        if magic!=b"glTF" or version!=2 or total!=len(data) or kind!=0x4e4f534a or 20+length>total:
            raise ValueError("GLB 结构无效")
        doc=json.loads(data[20:20+length])
        validate_glb_features(doc)
        for resource in doc.get("buffers",[])+doc.get("images",[]):
            uri=resource.get("uri")
            if uri and not uri.startswith("data:"):
                resource_path(path.parent,uri)
        return path,doc
    if path.suffix.lower()==".obj":
        for line in path.read_text().splitlines():
            if line.startswith("mtllib "):
                mtl=resource_path(path.parent,line[7:].strip())
                for entry in mtl.read_text().splitlines():
                    if entry.startswith("map_"):
                        resource_path(mtl.parent,entry.split(maxsplit=1)[1])
        return path,None
    raise ValueError("仅支持 GLB/OBJ")
