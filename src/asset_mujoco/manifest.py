"""内容寻址的人工审查；不信任缓存的 approved。"""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
import xml.etree.ElementTree as ET

def content_manifest(root,paths):
    """稳定的包相对路径→内容哈希；不允许越界、链接或缺失文件。"""
    root=Path(root).resolve()
    files={}
    for relative in sorted(set(paths)):
        path=root/relative
        resolved=path.resolve(strict=True)
        if not resolved.is_relative_to(root) or resolved!=path or not resolved.is_file():
            raise ValueError("无效包内资源: "+relative)
        files[relative]=hashlib.sha256(resolved.read_bytes()).hexdigest()
    return files

def compile_resources(root):
    paths={"model.xml","scene.xml","conversion_manifest.json"}
    for name in ("model.xml","scene.xml"):
        tree=ET.parse(Path(root)/name)
        compiler=tree.getroot().find("compiler")
        for node in tree.iter():
            if "file" in node.attrib:
                directory=""
                if compiler is not None:
                    directory=compiler.get("meshdir" if node.tag=="mesh" else "texturedir","")
                paths.add((Path(directory)/node.get("file")).as_posix())
    return sorted(paths)

def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def record_layer(root,layer,status,paths,context):
    """只在真正完成相应引擎检查后调用；report 绝不调用。"""
    root=Path(root)
    target=root/"evidence_manifest.json"
    document=json.loads(target.read_text()) if target.exists() else {"schema_version":2,"layers":{}}
    entry={"status":status,"files":content_manifest(root,paths),"context":context}
    entry["sha256"]=_digest(entry)
    document["layers"][layer]=entry
    target.write_text(json.dumps(document,indent=2))
    return entry

def checked_report(root):
    from .contracts import ValidationResult
    root=Path(root)
    result=ValidationResult.model_validate_json((root/"validation_report.json").read_text())
    target=root/"evidence_manifest.json"
    try:
        document=json.loads(target.read_text())
        if document.get("schema_version")!=2:
            raise ValueError("不支持的证据格式")
    except (OSError,ValueError):
        document={"layers":{}}
    for layer in ("compile","physics","render"):
        state=getattr(result,layer)
        if state not in ("passed","failed"):
            continue
        entry=document.get("layers",{}).get(layer)
        valid=False
        if entry and entry.get("files") and entry.get("status")==state:
            try:
                body={key:entry[key] for key in ("status","files","context")}
                valid=entry.get("sha256")==_digest(body) and content_manifest(root,entry["files"])==entry["files"]
                required={"model.xml","scene.xml","conversion_manifest.json"}
                if layer=="physics":
                    required|={"physics_native.xml","physics_evidence.json"}
                if layer=="render":
                    required|={"render_config.json","render_evidence.json","previews/front.png","previews/side.png","previews/iso.png","previews/collision.png"}
                valid=valid and required.issubset(entry["files"])
                if layer=="physics" and state=="passed":
                    evidence=json.loads((root/"physics_evidence.json").read_text())
                    valid=valid and evidence.get("native",{}).get("status")=="passed"
            except (OSError,ValueError,KeyError):
                valid=False
        if not valid:
            setattr(result,layer,"not_run")
            result.evidence_issues.append(layer+": missing_or_stale_evidence")
    if result.compile!="passed":
        for layer in ("physics","render"):
            if getattr(result,layer)=="passed":
                setattr(result,layer,"not_run")
    review=root/"appearance_review.json"
    result.appearance_review=review_status(root,json.loads(review.read_text())) if review.exists() else "pending"
    if result.evidence_issues:
        result.appearance_review="pending"
    return result

def asset_signature(root):
    root=Path(root)
    digest=hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative=path.relative_to(root)
        if path.is_file() and relative.parts[0]!="previews" and path.suffix in (".xml",".obj",".png"):
            digest.update(relative.as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()

def fingerprint(root):
    root=Path(root)
    entries=[]
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("包内禁止符号链接")
        if path.is_file() and path.relative_to(root).as_posix() not in ("appearance_review.json","aggregate_status.json"):
            entries.append((path.relative_to(root).as_posix(),hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(entries,separators=(",",":")).encode()).hexdigest()

def review_status(root, review):
    if not review.get("reviewer") or not review.get("timestamp") or not review.get("images"):
        return "pending"
    if review.get("package_content_sha256") != fingerprint(root):
        return "pending"
    return review.get("decision") if review.get("decision") in ("approved","rejected") else "pending"

def save_review(root,reviewer,decision,images):
    root=Path(root)
    if not reviewer.strip() or decision not in ("approved","rejected") or not images:
        raise ValueError("人工审核必须有审核人、结论和查看图片")
    hashes={}
    for relative in images:
        path=(root/relative).resolve(strict=True)
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("审核图片越界")
        hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
    file=root/"appearance_review.json"
    previous=json.loads(file.read_text()) if file.exists() else None
    history=[]
    if previous:
        history=previous.pop("history",[])+[previous]
    record={"schema_version":1,"reviewer":reviewer,"timestamp":datetime.now(timezone.utc).isoformat(),
            "decision":decision,"images":hashes,"package_content_sha256":fingerprint(root),"history":history}
    file.write_text(json.dumps(record,indent=2))
    return record
