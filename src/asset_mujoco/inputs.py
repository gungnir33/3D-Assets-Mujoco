"""在加载器之前检查源特性，禁止静默丢失信息。"""
import json
import struct
import hashlib
import io
import os
import stat
from pathlib import Path
from urllib.parse import unquote,urlsplit
from trimesh.resolvers import Resolver

class RestrictedResolver(Resolver):
    """所有实际读取都经过边界检查；缓存的是本次读取的固定快照。"""
    def __init__(self,root,namespace="",state=None):
        self.root=Path(root).resolve(strict=True)
        self.base=(self.root/namespace).resolve()
        if not self.base.is_relative_to(self.root):
            raise ValueError("资源 namespace 越界")
        self.parent=str(self.base)
        self.state=state if state is not None else {"cache":{},"records":{},"errors":[],"overrides":{}}

    def path(self,key):
        name=unquote(str(key).strip())
        if urlsplit(name).scheme or urlsplit(name).netloc or Path(name).is_absolute():
            raise ValueError("禁止远程或绝对资源路径")
        resolved=(self.base/name).resolve(strict=True)
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise ValueError("资源越界或非普通文件")
        return resolved

    def get(self,key):
        try:
            path=self.path(key)
            relative=path.relative_to(self.root).as_posix()
            if relative not in self.state["cache"]:
                # 逐级 O_NOFOLLOW，避免边界检查与实际读取之间的符号链接替换。
                fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
                try:
                    for part in Path(relative).parts[:-1]:
                        child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                        os.close(fd)
                        fd=child
                    file_fd=os.open(Path(relative).name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
                    try:
                        info=os.fstat(file_fd)
                        if not stat.S_ISREG(info.st_mode) or info.st_size>512*1024**2:
                            raise ValueError("资源类型或大小超限")
                        chunks=[]
                        while True:
                            block=os.read(file_fd,1024*1024)
                            if not block:
                                break
                            chunks.append(block)
                            if sum(map(len,chunks))>512*1024**2:
                                raise ValueError("资源读取超限")
                        data=b"".join(chunks)
                    finally:
                        os.close(file_fd)
                finally:
                    os.close(fd)
                self.state["cache"][relative]=data
                self.state["records"][relative]={"path":str(path),"sha256":hashlib.sha256(data).hexdigest(),"size":len(data)}
            return self.state["overrides"].get(relative,self.state["cache"][relative])
        except (OSError,ValueError) as error:
            self.state["errors"].append(str(error))
            raise ValueError("INPUT_RESOURCE_REJECTED: "+str(error)) from error

    def write(self,name,data):
        raise ValueError("只读 resolver")

    def namespaced(self,namespace):
        base=(self.base/namespace).resolve()
        if not base.is_relative_to(self.root):
            raise ValueError("资源 namespace 越界")
        return RestrictedResolver(self.root,str(base.relative_to(self.root)),self.state)

    def keys(self):
        return list(self.state["cache"])

    def assert_valid(self):
        if self.state["errors"]:
            raise ValueError("加载器曾拒绝依赖，不允许灰模回退: "+str(self.state["errors"]))

def prepare_obj(data,resolver):
    """规范化引用语法及 MTL 相对目录；真实资源仍由受限 resolver 读取。"""
    from PIL import Image
    text=data.decode("utf-8-sig").replace("\\\n","")
    output=[]
    mtls=[]
    used=set()
    for line in text.splitlines():
        parts=line.strip().split(maxsplit=1)
        if not parts:
            continue
        key=parts[0]
        if key=="mtllib":
            if len(parts)!=2:
                raise ValueError("空 mtllib")
            mtls.append(parts[1])
        if key=="usemtl":
            used.add(parts[1])
        output.append(" ".join(parts))
    if len(mtls)>1:
        raise ValueError("第一版仅支持单个 mtllib，不静默丢弃其它文件")
    known=set()
    required_images=set()
    for name in mtls:
        contents=resolver.get(name).decode("utf-8-sig")
        path=resolver.path(name)
        local=resolver.namespaced(str(path.parent.relative_to(resolver.root)))
        lines=[]
        for line in contents.splitlines():
            parts=line.strip().split(maxsplit=1)
            if not parts:
                continue
            key=parts[0].lower()
            if key=="newmtl":
                known.add(parts[1])
            if key.startswith("map_") or key in ("bump","disp","decal","refl"):
                if key!="map_kd":
                    raise ValueError("不支持附加 MTL 纹理，不静默丢失")
                image_data=local.get(parts[1])
                with Image.open(io.BytesIO(image_data)) as img:
                    if img.width*img.height>64_000_000:
                        raise ValueError("纹理解码尺寸超限")
                    img.load()
                relative=local.path(parts[1]).relative_to(resolver.root).as_posix()
                parts=["map_Kd",relative]
                required_images.add(relative)
            lines.append(" ".join(parts))
        resolver.state["overrides"][path.relative_to(resolver.root).as_posix()]=("\n".join(lines)+"\n").encode()
    if not used.issubset(known):
        raise ValueError("usemtl 引用缺少材质定义")
    return ("\n".join(output)+"\n").encode(),required_images

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
        if mat.get("pbrMetallicRoughness",{}).get("metallicRoughnessTexture"):
            raise ValueError("基础模式不支持 metallicRoughnessTexture")
        if mat.get("alphaMode","OPAQUE")!="OPAQUE" or mat.get("extensions"):
            raise ValueError("不支持透明或扩展材质")
        tex=mat.get("pbrMetallicRoughness",{}).get("baseColorTexture",{})
        if tex.get("texCoord",0)!=0 or tex.get("extensions"):
            raise ValueError("不支持额外 UV 或纹理变换")
        if any(mat.get(k) for k in ("normalTexture","occlusionTexture","emissiveTexture")):
            raise ValueError("基础模式不支持附加材质纹理")
    for sampler in doc.get("samplers",[]):
        if "magFilter" in sampler or "minFilter" in sampler:
            raise ValueError("显式纹理过滤器尚未完成效果验证")
        if sampler.get("wrapS",10497)!=10497 or sampler.get("wrapT",10497)!=10497:
            raise ValueError("仅支持 repeat sampler")

def inspect_input(path,data=None):
    path=Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size>512*1024**2:
        raise ValueError("非普通文件或超过输入大小限制")
    if path.suffix.lower()==".glb":
        data=path.read_bytes() if data is None else data
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
        resolver=RestrictedResolver(path.parent)
        prepare_obj(resolver.get(path.name) if data is None else data,resolver)
        return path,None
    raise ValueError("仅支持 GLB/OBJ")
