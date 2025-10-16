# Endpoints for adding/removing/renaming/compositing image layers.

from flask import Blueprint, jsonify, session, request, redirect, url_for
from app.models import LayerStack

bp = Blueprint("layers", __name__)

# Maybe unused
@bp.get("/get_layers")
def get_layers():
    # load canvas from pickle in new storage folder
    # save id in session
    pid = session["pid"]
    stack = LayerStack.LayerStack(0, 0)
    stack.load_pickle(f"users/{pid}/layers.pickle")
    data = stack.get_as_json()
    return jsonify(data), 200

# Toggle visibility of layer i
@bp.post("/update_visibility")
def update_visibility():
    pid = session["pid"]
    stack = LayerStack.LayerStack(0, 0)
    stack.load_pickle(f"users/{pid}/layers.pickle")
    try:
        data = request.get_json()
        index = data.get("index")
        if index >= stack.size():
            return jsonify({"error": "Index out of range"}), 500
        stack.toggle_visible_at(index)
        stack.save_pickle(f"users/{pid}/layers.pickle")
        return jsonify({"status": "ok", "index": index}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Change active layer
@bp.post("/update_active")
def update_active():
    pid = session["pid"]
    stack = LayerStack.LayerStack(0, 0)
    stack.load_pickle(f"users/{pid}/layers.pickle")
    try:
        data = request.get_json()
        index = data.get("index")
        if index >= stack.size():
            return jsonify({"error": "Index out of range"}), 500
        stack.select_layer(index)
        stack.save_pickle(f"users/{pid}/layers.pickle")
        return jsonify({"status": "ok", "index": index}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Creates new layer
@bp.post("/add_layer")
def add_layer():
    pid = session["pid"]
    stack = LayerStack.LayerStack(0, 0)
    stack.load_pickle(f"users/{pid}/layers.pickle")
    stack.create_layer()
    stack.save_pickle(f"users/{pid}/layers.pickle")
    return jsonify({"status": "ok"}), 200

# Deletes layer at i
@bp.post("/delete_layer")
def delete_layer():
    pid = session["pid"]
    stack = LayerStack.LayerStack(0, 0)
    stack.load_pickle(f"users/{pid}/layers.pickle")
    stack.delete_selected_layer()
    stack.save_pickle(f"users/{pid}/layers.pickle")
    return jsonify({"status": "ok"}), 200

# Duplicates layer i, and adds new layer at i+1
@bp.post("/duplicate_layer")
def duplicate_layer():
    pid = session["pid"]
    stack = LayerStack.LayerStack(0, 0)
    stack.load_pickle(f"users/{pid}/layers.pickle")
    stack.duplicate_selected_layer()
    stack.save_pickle(f"users/{pid}/layers.pickle")
    return jsonify({"status": "ok"}), 200

# Rename currently selected layer
@bp.post("/rename_layer")
def rename_layer():
    pid = session["pid"]
    stack = LayerStack.LayerStack(0, 0)
    stack.load_pickle(f"users/{pid}/layers.pickle")
    try:
        data = request.get_json()
        new_name = data.get("name")
        layer = stack.get_current_layer()
        layer.rename(new_name)
        stack.save_pickle(f"users/{pid}/layers.pickle")
        return jsonify({"status": "ok", "name": new_name}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500