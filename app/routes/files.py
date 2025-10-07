# Endpoints for new/open/save project operations.
# Example: /api/files/new, /api/files/save

from flask import Blueprint, jsonify

bp = Blueprint("files", __name__)  # Bytt ut med riktig navn/funksjon

@bp.get("/_stub")
def _stub():
    return jsonify({"ok": False, "message": "Not implemented yet"}), 501
