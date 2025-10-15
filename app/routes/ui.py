# Renders HTML templates (e.g., / → index.html, /editor → editor.html).

from flask import Blueprint, current_app, jsonify, render_template, session, redirect, url_for

from app.models import LayerStack
from app.services import storage

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


@bp.get("/")
def index():
    return render_template("index.html")

@bp.get("/editor")
def editor():
    pid = session["pid"]
    stack = LayerStack.LayerStack(0, 0)
    stack.load_pickle(f"users/{pid}/layers.pickle")
    data = stack.get_as_json()
    # TODO: render images
    return render_template("editor.html", data=data)


@bp.get("/open_new_project")
def open_new_project():
    # create empty canvas in new storage folder
    # save id in session
    pid = storage.new_project("users", "new project")
    session["pid"] = pid
    # TODO: layer size based on user input
    stack = LayerStack.LayerStack(500, 500)
    stack.add_base_layers()
    stack.save_pickle(f"users/{pid}/layers.pickle")
    return redirect(url_for("ui.editor"))


@bp.get("/open_loaded_project")
def open_loaded_project():
    # create empty canvas in new storage folder
    # save id in session
    pid = storage.new_project("users", "new project")
    session["pid"] = pid
    # TODO: FILE: get pickle file from user and save under users/pid

    return redirect(url_for("ui.editor"))

