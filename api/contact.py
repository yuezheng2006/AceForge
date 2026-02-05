"""
Contact API stub for new UI. No email/DB; returns success.
"""

from flask import Blueprint, jsonify

bp = Blueprint("api_contact", __name__)


@bp.route("", methods=["POST"], strict_slashes=False)
@bp.route("/", methods=["POST"], strict_slashes=False)
def submit():
    return jsonify({"success": True, "message": "Received", "id": "local"})
