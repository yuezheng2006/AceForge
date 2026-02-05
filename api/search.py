"""
Search API stub for new UI. Local-only: searches tracks by title/style;
returns { songs, creators, playlists } to match Express contract.
"""

from flask import Blueprint, jsonify, request

bp = Blueprint("api_search", __name__)


@bp.route("", methods=["GET"], strict_slashes=False)
@bp.route("/", methods=["GET"], strict_slashes=False)
def search():
    """GET /api/search?q=...&type=songs|creators|playlists|all — search local tracks."""
    q = (request.args.get("q") or "").strip()
    type_ = request.args.get("type", "all")
    if not q:
        return jsonify({"songs": [], "creators": [], "playlists": []})

    # Defer to songs list and filter by title/style (simple substring)
    try:
        import cdmf_tracks
        from cdmf_paths import DEFAULT_OUT_DIR
        from pathlib import Path
        tracks = cdmf_tracks.list_music_files()
        meta = cdmf_tracks.load_track_meta()
        q_lower = q.lower()
        out = []
        for name in tracks:
            info = meta.get(name, {})
            title = (info.get("title") or name) if isinstance(info, dict) else name
            style = (info.get("style") or "") if isinstance(info, dict) else ""
            if q_lower in (title or "").lower() or q_lower in (style or "").lower() or q_lower in name.lower():
                stem = Path(name).stem if name else name
                out.append({
                    "id": name,
                    "title": title or stem,
                    "style": style or stem,
                    "audio_url": f"/audio/{name}",
                    "creator": "Local",
                    "user_id": "local",
                })
        songs = out
    except Exception:
        songs = []

    creators = [] if type_ in ("all", "creators") else []
    playlists = [] if type_ in ("all", "playlists") else []
    if type_ == "songs":
        creators = []
        playlists = []
    elif type_ == "creators":
        songs = []
        playlists = []
    elif type_ == "playlists":
        songs = []
        creators = []

    return jsonify({"songs": songs, "creators": creators, "playlists": playlists})
