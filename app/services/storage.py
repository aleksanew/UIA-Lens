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

def _snapshot_dir(pid: str) -> Path:
    path = Path(_root()) / pid / "layer_snapshot"
    path.mkdir(parents=True, exist_ok=True)
    return path

def _legacy_pickle_path(pid: str) -> Path:
    return Path(_root()) / pid / "layers.pickle"

def _snapshot_refs(pid: str) -> list[int]:
    refs: list[int] = []
    for candidate in _snapshot_dir(pid).glob("layers*.pickle"):
        suffix = candidate.stem.replace("layers", "", 1)
        if suffix.isdigit():
            refs.append(int(suffix))
    refs.sort()
    return refs

def _set_snapshot_session(pid: str, queue: list[int], snap_index: int, change_number: int) -> None:
    session["snapshot_pid"] = pid
    session["snapshot_queue"] = queue
    session["snapshot_index"] = snap_index
    session["change_number"] = change_number

def _ensure_snapshot_session(pid: str, *, force: bool = False) -> None:
    needs_reset = (
        force
        or session.get("snapshot_pid") != pid
        or "snapshot_queue" not in session
        or "snapshot_index" not in session
        or "change_number" not in session
    )
    if not needs_reset:
        return

    snapshot_dir = _snapshot_dir(pid)
    refs = _snapshot_refs(pid)
    if refs:
        _set_snapshot_session(pid, refs, len(refs) - 1, refs[-1])
        return

    legacy = _legacy_pickle_path(pid)
    if legacy.exists():
        target = snapshot_dir / "layers0.pickle"
        if not target.exists():
            shutil.copy2(legacy, target)
        _set_snapshot_session(pid, [0], 0, 0)
        return

    _set_snapshot_session(pid, [], -1, -1)

def init_session():
    pid = new_project(current_app.config.get("STORAGE_ROOT"), "new project")
    session["pid"] = pid
    _set_snapshot_session(pid, [], -1, -1) # Prepare undo/redo session state

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
    pid = session.get("pid")
    if not pid:
        return None

    _ensure_snapshot_session(pid)

    snap_i = session.get("snapshot_index", -1)
    queue = session.get("snapshot_queue") or []
    snapshot_path = None

    if queue and 0 <= snap_i < len(queue):
        ref = queue[snap_i]
        candidate = _snapshot_dir(pid) / f"layers{ref}.pickle"
        if candidate.exists():
            snapshot_path = candidate
        else:
            # Snapshot metadata is stale; rebuild from disk and try again.
            _ensure_snapshot_session(pid, force=True)
            queue = session.get("snapshot_queue") or []
            snap_i = session.get("snapshot_index", -1)
            if queue and 0 <= snap_i < len(queue):
                ref = queue[snap_i]
                candidate = _snapshot_dir(pid) / f"layers{ref}.pickle"
                if candidate.exists():
                    snapshot_path = candidate

    stack = LayerStack.LayerStack(0, 0)

    if snapshot_path and stack.load_pickle(str(snapshot_path)):
        return stack

    legacy_path = _legacy_pickle_path(pid)
    if legacy_path.exists() and stack.load_pickle(str(legacy_path)):
        return stack

    return None

def save_layers(stack: LayerStack.LayerStack) -> bool:
    # Save new copy of canvas in users storage
    pid = session.get("pid")
    if not pid:
        return False

    _ensure_snapshot_session(pid)

    current_snap_index = session.get("snapshot_index", -1)
    current_change_number = session.get("change_number", -1)

    new_snap_index = current_snap_index + 1
    new_change_number = current_change_number + 1

    queue = list(session.get("snapshot_queue") or [])

    snapshot_path = _snapshot_dir(pid) / f"layers{new_change_number}.pickle"

    if stack.save_pickle(str(snapshot_path)):
        canonical_pickle = Path(_root()) / pid / "layers.pickle"
        stack.save_pickle(str(canonical_pickle))
        # Update which canvas is current (regards to undo/redo)

        current_snap_index = new_snap_index
        current_change_number = new_change_number

        current_snap_index, queue = _trim_queue(pid, current_snap_index, queue)
        queue.insert(new_snap_index, new_change_number)

        session["snapshot_index"] = current_snap_index
        session["change_number"] = current_change_number
        session["snapshot_queue"] = queue
        session["snapshot_pid"] = pid
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
