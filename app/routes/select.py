# Endpoints for selection operations.
# Example: /api/v1/select/rect, /api/v1/select/freeform, etc.

from flask import Blueprint, jsonify, request
from ..services.imaging import rectangular_select, freeform_select, polygonal_select, magic_lasso_select # actual functions

bp = Blueprint("select", __name__) # Blueprint for selection routes (dont really understand how this works cuz web app doesnt load when i use these routes)

# 4 routes for 4 selection types
@bp.post("/rect")
def rect():
    data = request.json # get json data from request
    if not data or 'image_id' not in data or 'coords' not in data:
        return jsonify({"error": "Missing image_id or coords (x1, y1, x2, y2)"}), 400 # error if missing data
    try:
        mask_data = rectangular_select(data['image_id'], data['coords']) # call function from imaging.py
        return jsonify({"mask": mask_data}), 200 # return mask data as json
    except Exception as e:
        return jsonify({"error": str(e)}), 500 # error if exception

# Same comments apply except its path instead of coords
@bp.post("/freeform")
def freeform():
    data = request.json 
    if not data or 'image_id' not in data or 'path' not in data:
        return jsonify({"error": "Missing image_id or path (list of [x,y] points)"}), 400
    try:
        mask_data = freeform_select(data['image_id'], data['path'])
        return jsonify({"mask": mask_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Same comments apply except its vertices instead of path
@bp.post("/polygonal")
def polygonal():
    data = request.json
    if not data or 'image_id' not in data or 'vertices' not in data:
        return jsonify({"error": "Missing image_id or vertices (list of [x,y] points)"}), 400
    try:
        mask_data = polygonal_select(data['image_id'], data['vertices'])
        return jsonify({"mask": mask_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Currently not very magic and more just bad, plan to improve it.
# Uses seed points to try to snap to edges using Canny, but it's bad.
@bp.post("/magic-lasso")
def magic_lasso():
    data = request.json
    if not data or 'image_id' not in data or 'seed_points' not in data:
        return jsonify({"error": "Missing image_id or seed_points (list of [x,y] for path snapping)"}), 400
    try:
        mask_data = magic_lasso_select(data['image_id'], data['seed_points'])
        return jsonify({"mask": mask_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500