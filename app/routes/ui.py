# Renders HTML templates (e.g., / → index.html, /editor → editor.html).

from flask import Blueprint, current_app, jsonify, render_template, session

from app.services.storage import new_project

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

#added for testing, not sure if 100% correct implementation
@bp.get("/")
def index():
    return render_template("index.html")

@bp.get("/editor")
def editor():
    return render_template("editor.html")

@bp.get("/new_project")
def open_new_project():
    # create empty canvas in new storage folder
    # save id in session
    pid = new_project("abc", "new project")
    session["pid"] = pid

    return render_template("editor.html")

@bp.get("/load_project")
def open_loaded_project():
    # load canvas from pickle in new storage folder
    # save id in session
    return render_template("editor.html")

@bp.get("/get_layers")
def get_layers():
    # load canvas from pickle in new storage folder
    # save id in session
    return jsonify({
        "selected_layer" : 0,
        "layers" : [
            {"name": "Background", "visible" : 1, "filename" : "bg.png"},
            {"name": "Layer 1", "visible" : 1, "filename" : "l1.png"},
            {"name": "Layer 2", "visible" : 1, "filename" : "l2.png"}
        ]
        }), 200
