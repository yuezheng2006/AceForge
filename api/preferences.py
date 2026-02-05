"""
Preferences API for new UI. Load/save app-wide settings from aceforge_config.json.
GET /api/preferences — return full config (output_dir, models_folder, ui_zoom, module settings).
PATCH /api/preferences — merge partial config and save.
No auth (local-only).
"""

import os
from pathlib import Path

from flask import Blueprint, jsonify, request

from cdmf_paths import load_config, save_config

bp = Blueprint("api_preferences", __name__)


def _deep_merge(base: dict, update: dict) -> dict:
    """Merge update into base recursively. base is mutated and returned."""
    for k, v in update.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


@bp.route("", methods=["GET"], strict_slashes=False)
@bp.route("/", methods=["GET"], strict_slashes=False)
def get_preferences():
    """GET /api/preferences — return current app preferences (global + per-module)."""
    config = load_config()
    return jsonify(config)


@bp.route("", methods=["PATCH"], strict_slashes=False)
@bp.route("/", methods=["PATCH"], strict_slashes=False)
def update_preferences():
    """PATCH /api/preferences — merge partial preferences and save."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400
    config = load_config()
    _deep_merge(config, data)
    save_config(config)
    # So ACE-Step and HuggingFace use the new models folder immediately
    if "models_folder" in data and data["models_folder"]:
        try:
            os.environ["HF_HOME"] = str(Path(data["models_folder"]).resolve())
        except Exception:
            pass
    return jsonify(config)
