# Handles saving/loading project metadata & layer files.
# Manages folders in app/storage/.

import json, uuid, shutil
import os
import pickle
from pathlib import Path
from io import BytesIO

import cv2
from PIL import Image
from flask import session, current_app
from app.models import LayerStack

def _root() -> str:
    return current_app.config.get("STORAGE_ROOT")

def _pid() -> str:
    return uuid.uuid4().hex[:8]

def _p(root, pid) -> Path:
    p = Path(root) / pid
    (p / "layers").mkdir(parents=True, exist_ok=True)
    (p / "layer_snapshot").mkdir(parents=True, exist_ok=True)
    return p

def init_session():
    pid = new_project(current_app.config.get("STORAGE_ROOT"), "new project")
    session["pid"] = pid
    session["snapshot_index"] = -1 # Index to "snapshot_queue". Tells which file is current canvas
    session["change_number"] = -1 # Number used in filename. layers{}.pickle
    session["snapshot_queue"] = [] # List of "change_number". Ref to specific file for undo/redo

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

# Used for undo
def decrement_active_snapshot():
    i = session["snapshot_index"]
    if i == 0:
        return False

    session["snapshot_index"] -= 1
    return True

# Used for redo
def increment_active_snapshot():
    queue = session["snapshot_queue"]
    size = len(queue)
    i = session["snapshot_index"]

    if i == size -1:
        return

    session["snapshot_index"] += 1
    return


def _trim_queue(pid, snap_i, queue) -> tuple[int, list]:
    UNDO_STAGES = 10

    # Remove the oldest snapshot
    if len(queue)-1 > UNDO_STAGES:
        ref = queue[0]
        os.remove(f"{_root()}/{pid}/layer_snapshot/layers{ref}.pickle")
        queue.pop(0)
        snap_i -= 1

    # If current canvas is not last in queue, and a change is made,
    # remove succeeding
    if snap_i < len(queue) -1:

        refs_to_delete = queue[snap_i:]
        for i, ref in enumerate(refs_to_delete):
            os.remove(f"{_root()}/{pid}/layer_snapshot/layers{ref}.pickle")
        queue = queue[:snap_i]

    return snap_i, queue

def load_layers() -> LayerStack.LayerStack | None:
    pid = session["pid"]
    snap_i = session["snapshot_index"]
    queue = session["snapshot_queue"]
    pickle_ref = queue[snap_i]

    stack = LayerStack.LayerStack(0, 0)
    if stack.load_pickle(f"{_root()}/{pid}/layer_snapshot/layers{pickle_ref}.pickle"):
        return stack
    else:
        return None

def save_layers(stack: LayerStack.LayerStack) -> bool:
    # Save new copy of canvas in users storage
    pid = session["pid"]
    current_snap_index = session["snapshot_index"]
    current_change_number = session["change_number"]

    new_snap_index = current_snap_index + 1
    new_change_number = current_change_number + 1

    queue = session["snapshot_queue"]

    if stack.save_pickle(f"{_root()}/{pid}/layer_snapshot/layers{new_change_number}.pickle"):
        # Update which canvas is current (regards to undo/redo)

        current_snap_index = new_snap_index
        current_change_number = new_change_number

        current_snap_index, queue = _trim_queue(pid, current_snap_index, queue)
        queue.insert(new_snap_index, new_change_number)

        session["snapshot_index"] = current_snap_index
        session["change_number"] = current_change_number
        session["snapshot_queue"] = queue
        return True
    else:
        return False


# Turns selected layer into png to display on webpage
def redraw_selected_image(stack: LayerStack.LayerStack):
    i = stack.selected_layer()
    layer = stack.get_current_layer()
    img = layer.get_image()
    cv2.imwrite(f"{user_path()}/layers/Layer{i}.png", img)
    return

# Turns all image arrays into png to display on webpage
def redraw_all_images(stack: LayerStack.LayerStack):
    size = stack.size()
    for i in range(size):
        layer = stack.at(i)
        img = layer.get_image()
        cv2.imwrite(f"{user_path()}/layers/Layer{i}.png", img)
    return


def user_path() -> str:
    pid = session["pid"]
    return f"{_root()}/{pid}"

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
