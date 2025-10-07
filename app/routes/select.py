# Endpoints for selection tools (rectangle, lasso, magic wand, etc.).

from flask import Blueprint, jsonify

bp = Blueprint("select", __name__)  # Bytt ut med riktig navn/funksjon

@bp.get("/_stub")
def _stub():
    return jsonify({"ok": False, "message": "Not implemented yet"}), 501
