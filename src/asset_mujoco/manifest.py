"""内容寻址的人工审查；不信任缓存的 approved。"""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone

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
