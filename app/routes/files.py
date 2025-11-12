# Endpoints for new, open, save as, export

from flask import Blueprint, jsonify, request, session, current_app, send_file
import os, json, io, zipfile, re
import cv2
import numpy as np
from app.models import LayerStack
from app.services import storage

bp = Blueprint("files", __name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

def _root() -> str:
    return current_app.config.get("STORAGE_ROOT")

def get_user_path(pid: str):
    return os.path.join(_root(), pid)

def get_project_json_path(pid: str):
    return os.path.join(get_user_path(pid), "project.json")

def _load_image_from_upload(file_storage):
    data = np.frombuffer(file_storage.read(), dtype=np.uint8)
    if data.size == 0:
        return None
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    elif img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img

# new project is handled by fileops.js/ui.py

@bp.route("/open", methods=["POST"])
def open_project():
    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
    
    # create new temporary project to hold uploaded content
    pid = storage.new_project(_root(), "uploaded_project")
    session["pid"] = pid
    user_path = get_user_path(pid)
    os.makedirs(user_path, exist_ok=True)

    save_path = os.path.join(user_path, uploaded_file.filename)
    uploaded_file.save(save_path)

    # If a pickle is uploaded, treat as project state and prepare images
    try:
        filename_lower = uploaded_file.filename.lower()
        name_no_ext, ext = os.path.splitext(uploaded_file.filename)
        if filename_lower.endswith(".pickle"):
            # Move to canonical name and generate images
            canonical_pickle = os.path.join(user_path, "layers.pickle")
            if save_path != canonical_pickle:
                os.replace(save_path, canonical_pickle)
            stack = LayerStack.LayerStack(0, 0)
            if stack.load_pickle(canonical_pickle):
                layers_dir = os.path.join(user_path, "layers")
                os.makedirs(layers_dir, exist_ok=True)
                storage.redraw_all_images(stack)
                # Ensure metadata exists (minimal schema)
                meta_path = get_project_json_path(pid)
                meta = {"id": pid, "name": name_no_ext or "uploaded", "layers": []}
                with open(meta_path, "w") as f:
                    json.dump(meta, f, indent=4)
            else:
                return jsonify({
                    "status": "error",
                    "message": "Failed to load uploaded pickle"
                }), 400
        elif ext.lower() in [".zip"]:
            # Import packaged project: extract zip into project folder
            import zipfile
            try:
                with zipfile.ZipFile(save_path, 'r') as z:
                    for member in z.infolist():
                        member_name = member.filename.replace("\\", "/")
                        if member_name.startswith('/') or '..' in member_name:
                            continue  # skip unsafe paths
                        dest_path = os.path.join(user_path, member_name)
                        dest_dir = os.path.dirname(dest_path)
                        os.makedirs(dest_dir, exist_ok=True)
                        if member.is_dir():
                            os.makedirs(dest_path, exist_ok=True)
                        else:
                            with z.open(member, 'r') as src, open(dest_path, 'wb') as dst:
                                dst.write(src.read())
            finally:
                # Remove uploaded zip after extraction
                try:
                    os.remove(save_path)
                except Exception:
                    pass

            # Normalize metadata id to this pid
            meta_path = get_project_json_path(pid)
            if os.path.exists(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                except Exception:
                    meta = {"id": pid, "name": name_no_ext or "imported", "layers": []}
            else:
                meta = {"id": pid, "name": name_no_ext or "imported", "layers": []}
            meta["id"] = pid
            if "layers" not in meta:
                meta["layers"] = []
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=4)

            # Validate pickle exists (exported zips include it). If missing, error.
            if not os.path.exists(os.path.join(user_path, "layers.pickle")):
                return jsonify({"status": "error", "message": "Imported zip missing layers.pickle"}), 400

        elif ext.lower() in IMAGE_EXTENSIONS:
            # Import an image as a new project: background + image layer
            img = cv2.imread(save_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                return jsonify({"status": "error", "message": "Failed to read uploaded image"}), 400
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
            elif img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            h, w = img.shape[:2]

            # Build stack sized to image, add background + one layer with the image
            stack = LayerStack.LayerStack(h, w)
            stack.add_base_layers()  # selects the new transparent layer
            layer = stack.get_current_layer()
            layer.update(img)

            layers_dir = os.path.join(user_path, "layers")
            os.makedirs(layers_dir, exist_ok=True)
            storage.redraw_all_images(stack)
            stack.save_pickle(os.path.join(user_path, "layers.pickle"))

            # Write metadata (minimal schema)
            meta_path = get_project_json_path(pid)
            meta = {"id": pid, "name": name_no_ext or "uploaded_image", "layers": []}
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=4)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Open failed: {e}"}), 400

    return jsonify({
        "status": "success",
        "message": "Project uploaded and loaded",
        "pid": pid,
        "filename": uploaded_file.filename
    })

@bp.route("/save-as", methods=["POST"])
def save_as_project():
    data = request.get_json() or {}
    new_name = data.get("name", "copy")
    duplicate = bool(data.get("duplicate", False))

    old_pid = session.get("pid")
    if not old_pid:
        return jsonify({"status": "error", "message": "No project to copy"}), 400
    
    # If duplicate requested, create a new project id and switch to it
    if duplicate:
        new_pid = storage.copy_project(_root(), old_pid, new_name)
        session["pid"] = new_pid
        return jsonify({
            "status": "success",
            "message": f"Project duplicated as '{new_name}'",
            "new_pid": new_pid
        })

    # Default behavior: rename current project (no copy)
    try:
        old_meta = storage.open_project(_root(), old_pid)
        # Normalize and keep only supported fields
        meta_id = old_meta.get("id") or old_meta.get("pid") or old_pid
        layers = old_meta.get("layers", [])
        new_meta = {"id": meta_id, "name": new_name, "layers": layers}
        storage.save_project(_root(), new_meta)
        return jsonify({
            "status": "success",
            "message": f"Project renamed to '{new_name}'",
            "pid": old_pid
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@bp.route("/recent", methods=["GET"])
def recent_projects():
    try:
        projects = storage.list_projects(_root())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success", "projects": projects})


@bp.route("/open_by_pid", methods=["POST"])
def open_by_pid():
    data = request.get_json() or {}
    pid = data.get("pid")
    if not pid:
        return jsonify({"status": "error", "message": "Missing pid"}), 400

    # Validate project exists
    try:
        meta = storage.open_project(_root(), pid)
    except FileNotFoundError:
        return jsonify({"status": "error", "message": f"Project '{pid}' not found"}), 404

    # Ensure layer images exist (generate if missing)
    user_path = get_user_path(pid)
    pickle_path = os.path.join(user_path, "layers.pickle")
    layers_dir = os.path.join(user_path, "layers")
    try:
        os.makedirs(layers_dir, exist_ok=True)
        need_images = len([n for n in os.listdir(layers_dir) if n.lower().endswith('.png')]) == 0
        if need_images and os.path.exists(pickle_path):
            stack = LayerStack.LayerStack(0, 0)
            if stack.load_pickle(pickle_path):
                storage.redraw_all_images(stack)
    except Exception:
        pass

    session["pid"] = pid
    return jsonify({"status": "success", "message": "Project opened", "project": meta, "pid": pid})


def _safe_filename(name: str, fallback: str) -> str:
    base = name or fallback
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", str(base)).strip("-._")
    return base or fallback


@bp.get("/export")
def export_project():
    export_type = (request.args.get("type") or "zip").lower()
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "No active project"}), 400

    user_path = get_user_path(pid)
    if not os.path.isdir(user_path):
        return jsonify({"error": "Project directory not found"}), 404

    meta_path = get_project_json_path(pid)
    meta = {"id": pid, "name": pid, "layers": []}
    if os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                loaded = json.load(f)
                meta["id"] = loaded.get("id") or loaded.get("pid") or pid
                meta["name"] = loaded.get("name") or pid
                meta["layers"] = loaded.get("layers", [])
        except Exception:
            pass

    project_name = _safe_filename(meta.get("name"), pid)
    pickle_path = os.path.join(user_path, "layers.pickle")

    if export_type == "png":
        stack = storage.load_layers()
        if stack is None:
            if not os.path.exists(pickle_path):
                return jsonify({"error": "Project data missing"}), 400
            stack = LayerStack.LayerStack(0, 0)
            if not stack.load_pickle(pickle_path):
                return jsonify({"error": "Failed to load project state"}), 500

        flattened = stack.get_collapsed_stack_as_image()
        ok, buffer = cv2.imencode(".png", flattened)
        if not ok:
            return jsonify({"error": "Failed to encode image"}), 500

        mem = io.BytesIO(buffer.tobytes())
        mem.seek(0)
        return send_file(
            mem,
            mimetype="image/png",
            as_attachment=True,
            download_name=f"{project_name}.png",
        )

    # Default: export zip package
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # project.json (ensure minimal schema)
        zf.writestr("project.json", json.dumps({
            "id": meta.get("id", pid),
            "name": meta.get("name", pid),
            "layers": meta.get("layers", []),
        }))

        # include layers.pickle
        if os.path.exists(pickle_path):
            zf.write(pickle_path, arcname="layers.pickle")

        # include layers/*.png
        layers_dir = os.path.join(user_path, "layers")
        if os.path.isdir(layers_dir):
            for name in sorted(os.listdir(layers_dir)):
                if name.lower().endswith('.png'):
                    zf.write(os.path.join(layers_dir, name), arcname=os.path.join("layers", name))

    mem.seek(0)
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name=f"{project_name}.zip")


@bp.get("/properties")
def project_properties():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "No active project"}), 400

    user_path = get_user_path(pid)
    meta = {"id": pid, "name": pid, "layers": []}
    meta_path = get_project_json_path(pid)
    if os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                loaded = json.load(f)
                meta["id"] = loaded.get("id") or loaded.get("pid") or pid
                meta["name"] = loaded.get("name") or pid
                meta["layers"] = loaded.get("layers", [])
        except Exception:
            pass

    stack = storage.load_layers()
    if stack is None:
        pickle_path = os.path.join(get_user_path(pid), "layers.pickle")
        if os.path.exists(pickle_path):
            stack = LayerStack.LayerStack(0, 0)
            try:
                if not stack.load_pickle(pickle_path):
                    stack = None
            except Exception:
                stack = None

    total_size = 0
    def _safe_size(path: str) -> int:
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    total_size += _safe_size(meta_path)
    total_size += _safe_size(os.path.join(user_path, "layers.pickle"))

    layers_dir = os.path.join(user_path, "layers")
    if os.path.isdir(layers_dir):
        for name in os.listdir(layers_dir):
            if name.lower().endswith(".png"):
                total_size += _safe_size(os.path.join(layers_dir, name))

    props = {
        "name": meta.get("name", pid),
        "layer_count": len(meta.get("layers", [])),
        "canvas": None,
        "file_size_bytes": total_size,
        "pixel_stats": None,
    }

    pixel_stats = None
    if stack:
        height, width = stack.shape()
        props["canvas"] = {"width": width, "height": height}
        props["layer_count"] = stack.size()

        flattened = stack.get_collapsed_stack_as_image()
        if flattened is not None and flattened.size:
            # BGRA -> RGBA for presentation
            rgba = flattened[:, :, [2, 1, 0, 3]]
            means = np.mean(rgba, axis=(0, 1))
            mins = np.min(rgba, axis=(0, 1))
            maxs = np.max(rgba, axis=(0, 1))
            pixel_stats = {
                "mean": [round(float(v), 2) for v in means],
                "min": [int(v) for v in mins],
                "max": [int(v) for v in maxs],
                "channels": ["R", "G", "B", "A"],
            }

    props["pixel_stats"] = pixel_stats

    return jsonify({"status": "success", "project": props})


@bp.post("/import-layer")
def import_layer():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "No active project"}), 400

    uploaded_file = request.files.get("file")
    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    _, ext = os.path.splitext(uploaded_file.filename)
    ext = (ext or "").lower()
    if ext not in IMAGE_EXTENSIONS:
        return jsonify({"error": f"Unsupported image type '{ext}'"}), 400

    stack = storage.load_layers()
    if stack is None:
        pickle_path = os.path.join(get_user_path(pid), "layers.pickle")
        stack = LayerStack.LayerStack(0, 0)
        if not (os.path.exists(pickle_path) and stack.load_pickle(pickle_path)):
            return jsonify({"error": "Failed to load current project"}), 500

    img = _load_image_from_upload(uploaded_file)
    if img is None:
        return jsonify({"error": "Failed to read uploaded image"}), 400

    height, width = stack.shape()
    if height <= 0 or width <= 0:
        height, width = img.shape[:2]
    if img.shape[0] != height or img.shape[1] != width:
        img = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA if img.shape[0] > height or img.shape[1] > width else cv2.INTER_LINEAR)

    stack.create_layer()
    layer = stack.get_current_layer()
    layer.update(img)
    layer_name = os.path.splitext(uploaded_file.filename)[0] or layer.name()
    layer.rename(layer_name)

    storage.redraw_selected_image(stack)
    storage.save_layers(stack)

    return jsonify({
        "status": "success",
        "message": f"Layer '{layer_name}' added",
        "layer": {
            "name": layer_name,
            "index": stack.selected_layer()
        }
    })
