"""
Songs API for new UI. Maps AceForge tracks (configured output dir + TRACK_META_PATH) and
uploaded reference tracks to the Express song contract. No auth.
"""

import json
import time
from pathlib import Path
from flask import Blueprint, jsonify, request, send_from_directory

import cdmf_tracks
from cdmf_paths import get_output_dir, TRACK_META_PATH, get_user_data_dir

bp = Blueprint("api_songs", __name__)

# Prefix for reference-track ids so they don't clash with generated track filenames
REF_ID_PREFIX = "ref:"


def _refs_dir() -> Path:
    return get_user_data_dir() / "references"


def _track_meta() -> dict:
    return cdmf_tracks.load_track_meta()


def _save_track_meta(meta: dict) -> None:
    cdmf_tracks.save_track_meta(meta)


def _music_dir() -> Path:
    return Path(get_output_dir())


def _filename_to_id(name: str) -> str:
    """Use filename as song id for simplicity (stable, no extra store)."""
    return name


def _id_to_filename(song_id: str) -> str:
    """Id is filename for our implementation."""
    return song_id


def _song_from_filename(name: str, meta: dict) -> dict:
    """Build one song dict matching Express shape for the UI."""
    music_dir = _music_dir()
    path = music_dir / name
    info = meta.get(name, {})
    seconds = float(info.get("seconds") or 0.0)
    if seconds <= 0 and path.is_file():
        try:
            seconds = cdmf_tracks.get_audio_duration(path)
        except Exception:
            pass
    stem = path.stem if path.suffix else name
    # Audio URL: frontend expects /audio/... for playback
    audio_url = f"/audio/{name}"
    return {
        "id": _filename_to_id(name),
        "title": stem,
        "lyrics": info.get("lyrics") or "",
        "style": info.get("style") or stem,
        "caption": info.get("caption") or stem,
        "cover_url": info.get("cover_url"),
        "audio_url": audio_url,
        "duration": int(seconds) if seconds else None,
        "bpm": info.get("bpm"),
        "key_scale": info.get("key_scale"),
        "time_signature": info.get("time_signature"),
        "tags": info.get("tags") or [],
        "is_public": True,
        "like_count": 0,
        "view_count": info.get("view_count") or 0,
        "user_id": "local",
        "created_at": info.get("created") or (path.stat().st_mtime if path.is_file() else None),
        "creator": "Local",
    }


def _ref_song_created_at(filename: str) -> float:
    """Created_at for a ref track (file mtime or now) so UI sort works."""
    refs = _refs_dir()
    if filename and (refs / filename).is_file():
        return (refs / filename).stat().st_mtime
    return time.time()


def _load_reference_tracks_as_songs() -> list:
    """Load reference_tracks.json and return song-shaped dicts for the library/player."""
    meta_path = get_user_data_dir() / "reference_tracks.json"
    records = []
    if meta_path.is_file():
        try:
            with meta_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            records = data if isinstance(data, list) else []
        except Exception:
            pass
    # Also scan references/ so uploads appear even if JSON is missing or out of sync
    refs = _refs_dir()
    seen_ids = {r.get("id") for r in records if r.get("id")}
    if refs.is_dir():
        for f in refs.iterdir():
            if f.is_file() and f.suffix.lower() in (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"):
                name = f.name
                ref_id = f.stem
                if ref_id not in seen_ids:
                    seen_ids.add(ref_id)
                    records.append({
                        "id": ref_id,
                        "filename": name,
                        "storage_key": name,
                        "audio_url": f"/audio/refs/{name}",
                        "duration": None,
                        "file_size_bytes": f.stat().st_size,
                        "tags": ["uploaded"],
                    })
    out = []
    for r in records:
        ref_id = r.get("id") or ""
        filename = r.get("filename") or r.get("storage_key") or ""
        stem = Path(filename).stem if filename else ref_id or "Reference"
        audio_url = (r.get("audio_url") or "").strip()
        if not audio_url:
            continue
        tags = list(r.get("tags") or [])
        if "uploaded" not in tags:
            tags.append("uploaded")
        created_at = _ref_song_created_at(filename)
        out.append({
            "id": REF_ID_PREFIX + ref_id,
            "title": stem,
            "lyrics": "",
            "style": "Reference",
            "caption": stem,
            "cover_url": None,
            "audio_url": audio_url,
            "duration": r.get("duration"),
            "bpm": None,
            "key_scale": None,
            "time_signature": None,
            "tags": tags,
            "is_public": True,
            "like_count": 0,
            "view_count": 0,
            "user_id": "local",
            "created_at": created_at,
            "creator": "Local",
        })
    return out


@bp.route("", methods=["GET"], strict_slashes=False)
@bp.route("/", methods=["GET"], strict_slashes=False)
def list_songs():
    """GET /api/songs — generated tracks + uploaded reference tracks (no auth)."""
    tracks = cdmf_tracks.list_music_files()
    meta = _track_meta()
    songs = [_song_from_filename(name, meta) for name in tracks]
    songs.extend(_load_reference_tracks_as_songs())
    return jsonify({"songs": songs})


@bp.route("/public", methods=["GET"])
def list_public():
    """GET /api/songs/public — same as list (all local)."""
    return list_songs()


@bp.route("/public/featured", methods=["GET"])
def list_featured():
    """GET /api/songs/public/featured — same as list, limited."""
    tracks = cdmf_tracks.list_music_files()
    meta = _track_meta()
    songs = [_song_from_filename(name, meta) for name in tracks[:20]]
    songs.extend(_load_reference_tracks_as_songs())
    return jsonify({"songs": songs})


def _get_reference_song_by_id(ref_id: str):
    """Return one song dict for ref:id or None if not found."""
    meta_path = get_user_data_dir() / "reference_tracks.json"
    if not meta_path.is_file():
        return None
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        records = data if isinstance(data, list) else []
    except Exception:
        return None
    for r in records:
        if (r.get("id") or "") == ref_id:
            filename = r.get("filename") or r.get("storage_key") or ""
            stem = Path(filename).stem if filename else ref_id or "Reference"
            audio_url = (r.get("audio_url") or "").strip()
            if not audio_url:
                return None
            tags = list(r.get("tags") or [])
            if "uploaded" not in tags:
                tags.append("uploaded")
            filename = r.get("filename") or r.get("storage_key") or ""
            created_at = _ref_song_created_at(filename)
            return {
                "id": REF_ID_PREFIX + ref_id,
                "title": stem,
                "lyrics": "",
                "style": "Reference",
                "caption": stem,
                "cover_url": None,
                "audio_url": audio_url,
                "duration": r.get("duration"),
                "bpm": None,
                "key_scale": None,
                "time_signature": None,
                "tags": tags,
                "is_public": True,
                "like_count": 0,
                "view_count": 0,
                "user_id": "local",
                "created_at": created_at,
                "creator": "Local",
            }
    return None


@bp.route("/<song_id>", methods=["GET"])
def get_song(song_id: str):
    """GET /api/songs/:id — one song by id (filename or ref:uuid)."""
    if song_id.startswith(REF_ID_PREFIX):
        ref_id = song_id[len(REF_ID_PREFIX) :]
        song = _get_reference_song_by_id(ref_id)
        if song:
            return jsonify({"song": song})
        return jsonify({"error": "Song not found"}), 404
    filename = _id_to_filename(song_id)
    tracks = cdmf_tracks.list_music_files()
    if filename not in tracks:
        return jsonify({"error": "Song not found"}), 404
    meta = _track_meta()
    song = _song_from_filename(filename, meta)
    return jsonify({"song": song})


@bp.route("/<song_id>/full", methods=["GET"])
def get_song_full(song_id: str):
    """GET /api/songs/:id/full — song plus comments (stub comments)."""
    r = get_song(song_id)
    if isinstance(r, tuple):
        return r
    data = r.get_json()
    data["comments"] = []
    return jsonify(data)


@bp.route("/<song_id>/audio", methods=["GET"])
def get_song_audio(song_id: str):
    """GET /api/songs/:id/audio — stream audio file."""
    filename = _id_to_filename(song_id)
    music_dir = _music_dir()
    path = music_dir / filename
    if not path.is_file():
        return jsonify({"error": "Song not found"}), 404
    return send_from_directory(music_dir, filename, as_attachment=False)


@bp.route("", methods=["POST"], strict_slashes=False)
@bp.route("/", methods=["POST"], strict_slashes=False)
def create_song():
    """POST /api/songs — create song record (e.g. after generation). Called by adapter."""
    data = request.get_json(silent=True) or {}
    # We don't persist to a separate DB; tracks are files. So create is no-op for listing.
    # Generation adapter will write the file to configured output dir and metadata to TRACK_META_PATH.
    return jsonify({"song": data}), 201


@bp.route("/<song_id>", methods=["PATCH"])
def update_song(song_id: str):
    """PATCH /api/songs/:id — update metadata (title, style, etc.); ref tracks are read-only."""
    if song_id.startswith(REF_ID_PREFIX):
        ref_id = song_id[len(REF_ID_PREFIX) :]
        song = _get_reference_song_by_id(ref_id)
        if song:
            return jsonify({"song": song})  # no-op for refs
        return jsonify({"error": "Song not found"}), 404
    filename = _id_to_filename(song_id)
    music_dir = _music_dir()
    if not (music_dir / filename).is_file():
        return jsonify({"error": "Song not found"}), 404
    meta = _track_meta()
    entry = meta.get(filename, {})
    data = request.get_json(silent=True) or {}
    if "title" in data:
        entry["title"] = str(data["title"])[: 500]
    if "style" in data:
        entry["style"] = str(data["style"])[: 500]
    if "lyrics" in data:
        entry["lyrics"] = str(data["lyrics"])[: 10000]
    meta[filename] = entry
    _save_track_meta(meta)
    song = _song_from_filename(filename, meta)
    return jsonify({"song": song})


def _delete_reference_track(ref_id: str):
    """Remove ref from reference_tracks.json and delete file. Returns True if found and removed."""
    meta_path = get_user_data_dir() / "reference_tracks.json"
    refs_dir = get_user_data_dir() / "references"
    if not meta_path.is_file():
        return False
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        records = data if isinstance(data, list) else []
    except Exception:
        return False
    for i, r in enumerate(records):
        if (r.get("id") or "") == ref_id:
            filename = r.get("filename") or r.get("storage_key")
            if filename:
                path = refs_dir / filename
                if path.is_file():
                    try:
                        path.unlink()
                    except OSError:
                        pass
            records.pop(i)
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            with meta_path.open("w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            return True
    return False


@bp.route("/<song_id>", methods=["DELETE"])
def delete_song(song_id: str):
    """DELETE /api/songs/:id — delete file and metadata (or reference track)."""
    if song_id.startswith(REF_ID_PREFIX):
        ref_id = song_id[len(REF_ID_PREFIX) :]
        if _delete_reference_track(ref_id):
            return jsonify({"success": True})
        return jsonify({"error": "Song not found"}), 404
    filename = _id_to_filename(song_id)
    path = _music_dir() / filename
    if not path.is_file():
        return jsonify({"error": "Song not found"}), 404
    try:
        path.unlink()
    except OSError as e:
        return jsonify({"error": str(e)}), 500
    meta = _track_meta()
    meta.pop(filename, None)
    _save_track_meta(meta)
    return jsonify({"success": True})


@bp.route("/<song_id>/like", methods=["POST"])
def toggle_like(song_id: str):
    """POST /api/songs/:id/like — stub: toggle like in metadata."""
    filename = _id_to_filename(song_id)
    meta = _track_meta()
    entry = meta.get(filename, {})
    liked = not entry.get("favorite", False)
    entry["favorite"] = liked
    meta[filename] = entry
    _save_track_meta(meta)
    return jsonify({"liked": liked})


@bp.route("/liked/list", methods=["GET"])
def list_liked():
    """GET /api/songs/liked/list — songs marked favorite."""
    tracks = cdmf_tracks.list_music_files()
    meta = _track_meta()
    songs = [
        _song_from_filename(name, meta)
        for name in tracks
        if meta.get(name, {}).get("favorite")
    ]
    return jsonify({"songs": songs})


@bp.route("/<song_id>/privacy", methods=["PATCH"])
def update_privacy(song_id: str):
    """PATCH /api/songs/:id/privacy — stub (all local public)."""
    return jsonify({"isPublic": True})


@bp.route("/<song_id>/play", methods=["POST"])
def track_play(song_id: str):
    """POST /api/songs/:id/play — stub."""
    return jsonify({"viewCount": 0})


@bp.route("/<song_id>/comments", methods=["GET"])
def get_comments(song_id: str):
    """GET /api/songs/:id/comments — stub."""
    return jsonify({"comments": []})


@bp.route("/<song_id>/comments", methods=["POST"])
def add_comment(song_id: str):
    """POST /api/songs/:id/comments — stub."""
    return jsonify({"comment": {"id": "stub", "content": ""}}), 201


@bp.route("/comments/<comment_id>", methods=["DELETE"])
def delete_comment(comment_id: str):
    """DELETE /api/songs/comments/:commentId — stub."""
    return jsonify({"success": True})
