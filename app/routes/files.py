# Endpoints for new/open/save project operations.
# Example: /api/files/new, /api/files/save

from flask import Blueprint, jsonify, request
import os

bp = Blueprint("files", __name__)

# --- Placeholder for in-memory "current file" (just for now)
current_file = {
    "name": None,
    "path": None,
    "unsaved_changes": False
}

@bp.route("/new", methods=["POST"])
def new_file():
    # Later: reset canvas, clear current image, etc.
    current_file["name"] = "untitled.png"
    current_file["path"] = None
    current_file["unsaved_changes"] = False
    return jsonify({
        "status": "success",
        "message": "New file created",
        "file": current_file
    })

@bp.route("/open", methods=["POST"])
def open_file():
    data = request.get_json() or {}
    file_path = data.get("path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "File not found"}), 404
    
    current_file["name"] = os.path.basename(file_path)
    current_file["path"] = file_path
    current_file["unsaved_changes"] = False
    return jsonify({
        "status": "success",
        "message": f"Opened file: {file_path}",
        "file": current_file
    })

@bp.route("/save", methods=["POST"])
def save_file():
    # Later: actually write image data to file
    if not current_file["name"]:
        return jsonify({"status": "error", "message": "No file to save"}), 400
    
    current_file["unsaved_changes"] = False
    return jsonify({
        "status": "success",
        "message": f"File '{current_file['name']}' saved successfully"
    })

@bp.route("/save-as", methods=["POST"])
def save_as_file():
    data = request.get_json() or {}
    new_path = data.get("path")
    if not new_path:
        return jsonify({"status": "error", "message": "Missing file path"}), 400
    
    current_file["path"] = new_path
    current_file["name"] = os.path.basename(new_path)
    current_file["unsaved_changes"] = False
    return jsonify({
        "status": "success",
        "message": f"File saved as '{new_path}'",
        "file": current_file
    })

@bp.route("/properties", methods=["GET"])
def file_properties():
    if not current_file["name"]:
        return jsonify({"status": "error", "message": "No file currently open"}), 400
    
    # Later: extract image size, format, etc.
    props = {
        "name": current_file["name"],
        "path": current_file["path"],
        "unsaved_changes": current_file["unsaved_changes"]
    }
    return jsonify({
        "status": "success",
        "properties": props
    })

@bp.route("/quit", methods=["POST"])
def quit_application():
    # Later: handle cleanup, save prompts, etc.
    current_file["name"] = None
    current_file["path"] = None
    current_file["unsaved_changes"] = False
    return jsonify({
        "status": "success",
        "message": "Application closed successfully"
    })

