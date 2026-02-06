"""
Playlists API for new UI. Stored in get_user_data_dir() / playlists.json.
No auth. Contract matches Express.
"""

import json
import uuid
from pathlib import Path
from flask import Blueprint, jsonify, request

from cdmf_paths import get_user_data_dir

bp = Blueprint("api_playlists", __name__)


def _playlists_path() -> Path:
    return get_user_data_dir() / "playlists.json"


def _load_playlists() -> list:
    p = _playlists_path()
    if not p.is_file():
        return []
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_playlists(playlists: list) -> None:
    _playlists_path().parent.mkdir(parents=True, exist_ok=True)
    with _playlists_path().open("w", encoding="utf-8") as f:
        json.dump(playlists, f, indent=2)


@bp.route("", methods=["GET"], strict_slashes=False)
@bp.route("/", methods=["GET"], strict_slashes=False)
def list_playlists():
    return jsonify({"playlists": _load_playlists()})


@bp.route("", methods=["POST"], strict_slashes=False)
@bp.route("/", methods=["POST"], strict_slashes=False)
def create_playlist():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip() or "Untitled"
    description = (data.get("description") or "").strip()
    is_public = data.get("isPublic", True)
    playlists = _load_playlists()
    pid = str(uuid.uuid4())
    playlists.append({
        "id": pid,
        "name": name,
        "description": description,
        "is_public": is_public,
        "song_ids": [],
    })
    _save_playlists(playlists)
    return jsonify({"playlist": playlists[-1]})


@bp.route("/public/featured", methods=["GET"])
def list_featured():
    return jsonify({"playlists": []})


@bp.route("/<playlist_id>", methods=["GET"])
def get_playlist(playlist_id: str):
    playlists = _load_playlists()
    for p in playlists:
        if p.get("id") == playlist_id:
            return jsonify({"playlist": p, "songs": []})
    return jsonify({"error": "Playlist not found"}), 404


@bp.route("/<playlist_id>/songs", methods=["POST"])
def add_song_to_playlist(playlist_id: str):
    data = request.get_json(silent=True) or {}
    song_id = data.get("songId")
    if not song_id:
        return jsonify({"error": "songId required"}), 400
    playlists = _load_playlists()
    for p in playlists:
        if p.get("id") == playlist_id:
            ids = p.get("song_ids") or []
            if song_id not in ids:
                ids.append(song_id)
                p["song_ids"] = ids
                _save_playlists(playlists)
            return jsonify({"success": True})
    return jsonify({"error": "Playlist not found"}), 404


@bp.route("/<playlist_id>/songs/<song_id>", methods=["DELETE"])
def remove_song_from_playlist(playlist_id: str, song_id: str):
    playlists = _load_playlists()
    for p in playlists:
        if p.get("id") == playlist_id:
            ids = p.get("song_ids") or []
            if song_id in ids:
                ids.remove(song_id)
                p["song_ids"] = ids
                _save_playlists(playlists)
            return jsonify({"success": True})
    return jsonify({"error": "Playlist not found"}), 404


@bp.route("/<playlist_id>", methods=["PATCH"])
def update_playlist(playlist_id: str):
    data = request.get_json(silent=True) or {}
    playlists = _load_playlists()
    for p in playlists:
        if p.get("id") == playlist_id:
            if "name" in data:
                p["name"] = str(data["name"])[: 200]
            if "description" in data:
                p["description"] = str(data["description"])[: 2000]
            _save_playlists(playlists)
            return jsonify({"playlist": p})
    return jsonify({"error": "Playlist not found"}), 404


@bp.route("/<playlist_id>", methods=["DELETE"])
def delete_playlist(playlist_id: str):
    playlists = _load_playlists()
    for i, p in enumerate(playlists):
        if p.get("id") == playlist_id:
            playlists.pop(i)
            _save_playlists(playlists)
            return jsonify({"success": True})
    return jsonify({"error": "Playlist not found"}), 404
