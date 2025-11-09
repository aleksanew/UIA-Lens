from flask import Blueprint, jsonify, request
from app.services import storage

bp = Blueprint("layers", __name__)


@bp.get("/get_layers")
def get_layers():
    # load canvas from pickle in new storage folder
    # save id in session
    stack = storage.load_layers()
    data = stack.get_as_json()
    return jsonify(data), 200

# Toggle visibility of layer i
@bp.post("/update_visibility")
def update_visibility():
    stack = storage.load_layers()
    try:
        data = request.get_json()
        index = data.get("index")
        if index >= stack.size():
            return jsonify({"error": "Index out of range"}), 500
        stack.toggle_visible_at(index)
        storage.save_layers(stack)
        return jsonify({"status": "ok", "index": index}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Change active layer
@bp.post("/update_active")
def update_active():
    stack = storage.load_layers()
    try:
        data = request.get_json()
        index = data.get("index")
        if index >= stack.size():
            return jsonify({"error": "Index out of range"}), 500
        stack.select_layer(index)
        storage.save_layers(stack)
        return jsonify({"status": "ok", "index": index}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Creates new layer
@bp.post("/add_layer")
def add_layer():
    stack = storage.load_layers()
    stack.create_layer()
    storage.redraw_selected_image(stack)
    storage.save_layers(stack)
    return jsonify({"status": "ok"}), 200

# Deletes layer at i
@bp.post("/delete_layer")
def delete_layer():
    stack = storage.load_layers()
    stack.delete_selected_layer()
    storage.save_layers(stack)
    return jsonify({"status": "ok"}), 200

# Duplicates layer i, and adds new layer at i+1
@bp.post("/duplicate_layer")
def duplicate_layer():
    stack = storage.load_layers()
    stack.duplicate_selected_layer()
    storage.redraw_selected_image(stack)
    storage.save_layers(stack)
    return jsonify({"status": "ok"}), 200

# Rename currently selected layer
@bp.post("/rename_layer")
def rename_layer():
    stack = storage.load_layers()
    try:
        data = request.get_json()
        new_name = data.get("name")
        layer = stack.get_current_layer()
        layer.rename(new_name)
        storage.save_layers(stack)
        return jsonify({"status": "ok", "name": new_name}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500