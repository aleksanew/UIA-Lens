# Endpoints for adding/removing/renaming/compositing image layers.

from flask import Blueprint, jsonify

bp = Blueprint("layers", __name__)  # Bytt ut med riktig navn/funksjon

@bp.get("/_stub")
def _stub():
    return jsonify({"ok": False, "message": "Not implemented yet"}), 501
