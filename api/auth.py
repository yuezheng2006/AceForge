"""
Auth API stub for new UI. Local-only, no real auth.
GET /api/auth/auto returns a local user (OS username) so the React app starts straight into the UI.
Contract: { user: { id, username, ... }, token }.
"""

import getpass
import os
from flask import Blueprint, jsonify

bp = Blueprint("api_auth", __name__)


def _local_username() -> str:
    """Use macOS/system username when available, else 'Local'."""
    try:
        return (getpass.getuser() or os.environ.get("USER") or os.environ.get("USERNAME") or "Local").strip() or "Local"
    except Exception:
        return "Local"


def _local_user():
    """Single user dict for all auth/user stubs."""
    return {
        "id": "local",
        "username": _local_username(),
        "bio": None,
        "avatar_url": None,
        "banner_url": None,
        "isAdmin": False,
        "createdAt": None,
    }


@bp.route("/auto", methods=["GET"])
def auto():
    """Return local user (OS username). No token; app does not support login."""
    user = _local_user()
    return jsonify({"user": user, "token": None})


@bp.route("/me", methods=["GET"])
def me():
    """Stub: always return local user (no token check)."""
    return jsonify({"user": _local_user()})


@bp.route("/setup", methods=["POST"])
def setup():
    """Stub: no-op; UI can call after 'first run'. Return same as auto."""
    return jsonify({"user": _local_user(), "token": None})


@bp.route("/logout", methods=["POST"])
def logout():
    """Stub: no-op; local app has no session."""
    return jsonify({"success": True})


@bp.route("/refresh", methods=["POST"])
def refresh():
    """Stub: return same as auto (no refresh token)."""
    return jsonify({"user": _local_user(), "token": None})


@bp.route("/username", methods=["PATCH"])
def update_username():
    """Stub: accept body.username but keep OS username for display."""
    return jsonify({"user": _local_user(), "token": None})


# For api.users: single snapshot so "from api.auth import LOCAL_USER" works
LOCAL_USER = _local_user()
