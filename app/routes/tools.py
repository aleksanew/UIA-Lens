# Endpoints for brush, eraser, bucket, and shape drawing tools.

from flask import Blueprint, jsonify

bp = Blueprint("tools", __name__)  # Bytt ut med riktig navn/funksjon

@bp.get("/_stub")
def _stub():
    return jsonify({"ok": False, "message": "Not implemented yet"}), 501
