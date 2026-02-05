"""
Reference tracks API for new UI. Uploads in get_user_data_dir() / references/;
metadata in reference_tracks.json. No auth.
"""

import json
import uuid
from pathlib import Path
from flask import Blueprint, jsonify, request, send_from_directory

from cdmf_paths import get_user_data_dir

bp = Blueprint("api_reference_tracks", __name__)


def _refs_dir() -> Path:
    d = get_user_data_dir() / "references"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _meta_path() -> Path:
    return get_user_data_dir() / "reference_tracks.json"


def _load_meta() -> list:
    p = _meta_path()
    if not p.is_file():
        return []
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_meta(records: list) -> None:
    _meta_path().parent.mkdir(parents=True, exist_ok=True)
    with _meta_path().open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


@bp.route("/", methods=["GET"])
@bp.route("", methods=["GET"], strict_slashes=False)
def list_refs():
    """GET /api/reference-tracks — return { tracks: [...] } for UI (CreatePanel expects data.tracks)."""
    return jsonify({"tracks": _load_meta()})


@bp.route("/", methods=["POST"])
@bp.route("", methods=["POST"], strict_slashes=False)
def upload_ref():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file"}), 400
    f = request.files["audio"]
    if not f.filename:
        return jsonify({"error": "No filename"}), 400
    ext = Path(f.filename).suffix.lower() or ".audio"
    ref_id = str(uuid.uuid4())
    safe_name = f"{ref_id}{ext}"
    path = _refs_dir() / safe_name
    f.save(str(path))
    url = f"/audio/refs/{safe_name}"
    track = {
        "id": ref_id,
        "filename": safe_name,
        "storage_key": safe_name,
        "audio_url": url,
        "duration": None,
        "file_size_bytes": path.stat().st_size if path.is_file() else None,
        "tags": ["uploaded"],
    }
    records = _load_meta()
    records.append(track)
    _save_meta(records)
    # UI (CreatePanel) expects data.track with at least audio_url
    return jsonify({"track": track, "url": url, "key": safe_name})


@bp.route("/<ref_id>", methods=["PATCH"])
def update_ref(ref_id: str):
    data = request.get_json(silent=True) or {}
    records = _load_meta()
    for r in records:
        if r.get("id") == ref_id:
            if "tags" in data:
                r["tags"] = data["tags"] if isinstance(data["tags"], list) else []
            _save_meta(records)
            return jsonify(r)
    return jsonify({"error": "Not found"}), 404


@bp.route("/<ref_id>", methods=["DELETE"])
def delete_ref(ref_id: str):
    records = _load_meta()
    for i, r in enumerate(records):
        if r.get("id") == ref_id:
            safe_name = r.get("filename") or r.get("storage_key")
            if safe_name:
                path = _refs_dir() / safe_name
                if path.is_file():
                    path.unlink()
            records.pop(i)
            _save_meta(records)
            return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404
