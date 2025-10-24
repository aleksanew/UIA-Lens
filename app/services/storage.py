# Handles saving/loading project metadata & layer files.
# Manages folders in app/storage/.

import json, uuid, shutil
import pickle
from pathlib import Path
from io import BytesIO
from PIL import Image

from app.models.LayerStack import LayerStack


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

def copy_project(root: str, old_pid: str, new_name: str) -> str:
    old_path = Path(root) / old_pid
    if not old_path.exists():
        raise FileNotFoundError(f"Project {old_pid} not found")

    new_pid = _pid()
    new_path = _p(root, new_pid)

    shutil.copytree(old_path, new_path, dirs_exist_ok=True)

    meta_path = new_path / "project.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        meta["id"] = new_pid
        meta["name"] = new_name
        meta_path.write_text(json.dumps(meta))

    return new_pid

def list_projects(root: str) -> list[dict]:
    root_path = Path(root)
    projects = []

    for project_dir in root_path.iterdir():
        meta_path = project_dir / "project.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
                projects.append(meta)
    return projects

# Legg til flere etterhvert
