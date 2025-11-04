from flask import Blueprint, jsonify, request, session, current_app
from app.models.LayerStack import LayerStack
from app.services.tools import tool_brush, tool_eraser, tool_bucket, bgr_to_hex, _ensure_bgra, tool_text, tool_shape
from app.services import storage
import os
import cv2
import numpy as np

bp = Blueprint("tools", __name__)

# Load LayerStack, validate selected layer
def _root() -> str:
    return current_app.config.get("STORAGE_ROOT")

def _active_png_path(pid:str, idx: int) -> str:
    path = os.path.join(_root(), pid, "layers", f"Layer{idx}.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

# Ensure layer PNG exists, create if missing
def _ensure_layer_png(pid, stack, idx):
    layer_path = _active_png_path(pid, idx)
    if not os.path.exists(layer_path):
        layer = stack.get_current_layer()
        arr = layer.get_image()
        if arr is None:
            h, w = stack.shape()
            arr = np.zeros((h, w, 4), dtype=np.uint8)
        if arr.ndim == 2:
            arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGRA)
        elif arr.shape[2] == 3:
            bgra = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)
            bgra[:, :, :3] = arr
            arr = bgra
        cv2.imwrite(layer_path, arr)
    return layer_path

def _update_and_save(stack, layer_path):
    img = cv2.imread(layer_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return jsonify({"error": f"Failed to reload edited PNG: {layer_path}"}), 500
    
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    elif img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    
    stack.get_current_layer().update(img)
    if storage.save_layers(stack):
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"status": "error"}), 400

@bp.post("/stroke")
def stroke():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "Not logged in / missing pid"}), 401

    data = request.get_json() or {}
    tool = data.get("tool", "brush")
    color = data.get("color", "#000000")
    points = data.get("points") or []
    brush_type = data.get("brush_type", "hard")

    try:
        size = int(data.get("size", 5))
    except (TypeError, ValueError):
        size = 5

    if len(points) < 2:
        return jsonify({"error": "Need at least two points"}), 400

    # Load stack
    stack = storage.load_layers()

    # Ensure PNG exists
    idx = stack.selected_layer()
    layer_path = _ensure_layer_png(pid, stack, idx)

    # Execute tool
    try:
        if tool == "eraser":
            layer = stack.get_current_layer()
            is_background = (layer.name().lower() == "background")
            tool_eraser(layer_path, size, points, is_background=is_background)
        else:
            tool_brush(layer_path, color, size, points, brush_type=brush_type)
    except Exception as e:
        return jsonify({"error": f"Tool '{tool}' failed: {e}"}), 500

    return _update_and_save(stack, layer_path)

@bp.post("/dropper")
def dropper():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "Not logged in / missing pid"}), 401

    data = request.get_json() or {}
    try:
        x, y = map(int, (data["x"], data["y"]))
    except Exception:
        return jsonify({"error": "x and y must be integers"}), 400

    stack = storage.load_layers()
    layer_path = _ensure_layer_png(pid, stack, stack.selected_layer())

    # Les bilde og sørg for BGRA-format
    img = _ensure_bgra(cv2.imread(layer_path, cv2.IMREAD_UNCHANGED))
    if img is None:
        return jsonify({"error": f"Could not open {layer_path}"}), 500

    h, w = img.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return jsonify({"error": f"point out of bounds ({x},{y}) for size {w}x{h}"}), 400

    b, g, r, a = map(int, img[y, x])
    return jsonify({"hex": bgr_to_hex(b, g, r), "rgba": [r, g, b, a]}), 200


@bp.post("/bucket_fill")
def bucket_fill():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "Not logged in / missing pid"}), 401

    data = request.get_json() or {}
    color = data.get("color", "#000000")
    start_point = data.get("start_point")

    # Validate input
    if not (isinstance(start_point, (list, tuple)) and len(start_point) == 2):
        return jsonify({"error": "start_point must be [x, y]"}), 400

    stack = storage.load_layers()
    idx = stack.selected_layer()
    layer_path = _ensure_layer_png(pid, stack, idx)

    # Bounds check
    probe = cv2.imread(layer_path, cv2.IMREAD_UNCHANGED)
    if probe is None:
        return jsonify({"error": f"Failed to open {layer_path}"}), 500
    
    h, w = probe.shape[:2]
    x, y = map(int, start_point)
    if not (0 <= x < w and 0 <= y < h):
        return jsonify({"error": f"start_point out of bounds: ({x},{y})"}), 400

    # Execute bucket fill
    try:
        tool_bucket(layer_path, color, [x, y])
    except Exception as e:
        return jsonify({"error": f"Bucket failed: {e}"}), 500

    return _update_and_save(stack, layer_path)

@bp.post("/shape")
def shape():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "Not logged in / missing pid"}), 401

    data = request.get_json() or {}
    shape = data.get("shape")
    start = data.get("start")
    end = data.get("end")
    points = data.get("points")
    fill = data.get("fill")
    stroke = data.get("stroke", "#000000")

    try:
        stroke_width = int(data.get("strokeWidth", 2))
        fill_alpha = int(data.get("fillAlpha", 255))
        stroke_alpha = int(data.get("strokeAlpha", 255))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric value for stroke/fill alpha/width"}), 400

    if shape in ("rect", "ellipse", "line"):
        if not (isinstance(start, (list, tuple)) and isinstance(end, (list, tuple)) and len(start) == 2 and len(end) == 2):
            return jsonify({"error": "start and end must be [x, y]"}), 400
    elif shape == "polygon":
        if not (isinstance(points, list) and len(points) >= 3 and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in points)):
            return jsonify({"error": "points must be list of [x, y]"}), 400
        else:
            return jsonify({"error": "Invalid shape"}), 400

    stack = storage.load_layers()
    idx = stack.selected_layer()
    layer_path = _ensure_layer_png(pid, stack, idx)

    try:
        tool_shape(
            image_path=layer_path,
            shape=shape,
            start=start,
            end=end,
            points=points,
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            fill_alpha=fill_alpha,
            stroke_alpha=stroke_alpha,
        )
    except Exception as e:
        return jsonify({"error": f"Tool '{shape}' failed: {e}"}), 500

    return _update_and_save(stack, layer_path)

@bp.post("/text")
def text():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "Not logged in / missing pid"}), 401

    data = request.get_json() or {}
    text = data.get("text")
    origin = data.get("origin")

    if not text or not (isinstance(origin, (list, tuple)) and len(origin) == 2):
        return jsonify({"error": "origin must be [x, y]"}), 400

    color = data.get("color", "#000000")
    font = data.get("font", "sans")
    align = data.get("align", "left")

    try:
        size = float(data.get("size", 1.0))
        thickness = int(data.get("thickness", 2))
        outline = data.get("outline")
        outline_thickness = int(data.get("outlineThickness", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric value for outline/thickness"}), 400

    stack = storage.load_layers()
    idx = stack.selected_layer()
    layer_path = _ensure_layer_png(pid, stack, idx)

    try:
        tool_text(
            image_path=layer_path,
            text=text,
            origin=origin,
            color=color,
            size=size,
            thickness=thickness,
            font=font,
            align=align,
            outline=outline,
            outline_thickness=outline_thickness,
        )
    except Exception as e:
        return jsonify({"error": f"Tool '{text}' failed: {e}"}), 500

    return _update_and_save(stack, layer_path)


#TODO make buttons gray
@bp.post("/undo")
def undo():


    return jsonify({"status": "ok"}), 200


@bp.post("/redo")
def redo():


    return jsonify({"status": "ok"}), 200