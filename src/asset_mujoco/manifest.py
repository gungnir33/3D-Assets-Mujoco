"""内容寻址的人工审查；不信任缓存的 approved。"""
import hashlib
import json
from pathlib import Path

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
    if review.get("package_content_sha256") != fingerprint(root):
        return "pending"
    return review.get("decision") if review.get("decision") in ("approved","rejected") else "pending"
