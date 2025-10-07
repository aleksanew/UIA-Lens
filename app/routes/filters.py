# Endpoints for image filters (blur, sharpen, grayscale, etc.).

from flask import Blueprint, jsonify

bp = Blueprint("filters", __name__)  # Bytt ut med riktig navn/funksjon

@bp.get("/_stub")
def _stub():
    return jsonify({"ok": False, "message": "Not implemented yet"}), 501
