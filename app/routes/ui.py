# Renders HTML templates (e.g., / → index.html, /editor → editor.html).
from flask import Blueprint, current_app, jsonify

bp = Blueprint("ui", __name__)

@bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@bp.get("/routes")
def routes():
    base = "/api/v1"
    return jsonify({
        "files":  [f"{base}/files/new", f"{base}/files/open", f"{base}/files/save"],
        "layers": [f"{base}/layers/add", f"{base}/layers/remove", f"{base}/layers/list", f"{base}/layers/composite"],
        "select": [f"{base}/select/rect", f"{base}/select/lasso"],
        "filters":[f"{base}/filters/gaussian", f"{base}/filters/grayscale"],
        "tools":  [f"{base}/tools/brush", f"{base}/tools/eraser"],
        "health": f"{base}/health"
    })