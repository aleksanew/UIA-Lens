# Handles saving/loading project metadata & layer files.
# Manages folders in app/storage/.

import json, uuid
from pathlib import Path
from io import BytesIO
from PIL import Image

def _pid() -> str:
    return uuid.uuid4().hex[:8]

def _p(root, pid) -> Path:
    p = Path(root) / pid
    (p / "layers").mkdir(parents=True, exist_ok=True)
    return p

def new_project(root: str, name: str) -> str:
    pid = _pid()
    p = _p(root, pid)
    meta = {"id": pid, "name": name, "layers": []}
    (p/"project.json").write_text(json.dumps(meta))
    return pid

def open_project(root: str, pid: str) -> dict:
    p = Path(root) / pid / "project.json"
    return json.loads(p.read_text())

def save_project(root: str, meta: dict) -> None:
    p = Path(root) / meta["id"] / "project.json"
    p.write_text(json.dumps(meta))

# Legg til flere etterhvert