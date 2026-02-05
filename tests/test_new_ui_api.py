"""
Integration tests for the new UI Flask API (ace-step-ui compatibility layer).
Uses the real Flask app and real API implementations; no mocks.
Storage is redirected to a temp directory via cdmf_paths patch so CI/user data is not touched.
"""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def temp_user_dir():
    """Isolate test storage under a temp dir; real implementation, isolated data."""
    with tempfile.TemporaryDirectory(prefix="aceforge_test_") as d:
        yield Path(d)


@pytest.fixture(scope="module")
def app_client(temp_user_dir):
    """Create Flask test client with patched user dirs so API uses temp storage."""
    (temp_user_dir / "prefs").mkdir(parents=True, exist_ok=True)
    (temp_user_dir / "references").mkdir(parents=True, exist_ok=True)
    (temp_user_dir / "generated").mkdir(parents=True, exist_ok=True)

    import cdmf_paths
    orig_data = cdmf_paths.get_user_data_dir
    orig_pref = cdmf_paths.get_user_preferences_dir
    orig_default_out = getattr(cdmf_paths, "DEFAULT_OUT_DIR", None)
    orig_track_meta = getattr(cdmf_paths, "TRACK_META_PATH", None)

    def _data():
        return temp_user_dir

    def _pref():
        return temp_user_dir / "prefs"

    cdmf_paths.get_user_data_dir = _data
    cdmf_paths.get_user_preferences_dir = _pref
    cdmf_paths.DEFAULT_OUT_DIR = str(temp_user_dir / "generated")
    cdmf_paths.TRACK_META_PATH = temp_user_dir / "tracks_meta.json"

    try:
        from music_forge_ui import app
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client
    finally:
        cdmf_paths.get_user_data_dir = orig_data
        cdmf_paths.get_user_preferences_dir = orig_pref
        if orig_default_out is not None:
            cdmf_paths.DEFAULT_OUT_DIR = orig_default_out
        if orig_track_meta is not None:
            cdmf_paths.TRACK_META_PATH = orig_track_meta


# ---- Auth (stub) ----
def test_auth_auto(app_client):
    r = app_client.get("/api/auth/auto")
    assert r.status_code == 200
    data = r.get_json()
    assert "user" in data
    assert data["user"]["id"] == "local"
    assert isinstance(data["user"].get("username"), str) and len(data["user"]["username"]) > 0
    assert data.get("token") is None


# ---- Songs ----
def test_songs_list(app_client):
    r = app_client.get("/api/songs/")
    assert r.status_code == 200
    data = r.get_json()
    assert "songs" in data
    assert isinstance(data["songs"], list)


def test_songs_public(app_client):
    r = app_client.get("/api/songs/public")
    assert r.status_code == 200
    data = r.get_json()
    assert "songs" in data


def test_songs_public_featured(app_client):
    r = app_client.get("/api/songs/public/featured")
    assert r.status_code == 200
    data = r.get_json()
    assert "songs" in data


# ---- Generate (no ACE model; we only test API contract) ----
def test_generate_health(app_client):
    r = app_client.get("/api/generate/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("healthy") is True


def test_generate_endpoints(app_client):
    r = app_client.get("/api/generate/endpoints")
    assert r.status_code == 200
    data = r.get_json()
    assert "endpoints" in data
    assert "provider" in data["endpoints"]


def test_generate_history(app_client):
    r = app_client.get("/api/generate/history")
    assert r.status_code == 200
    data = r.get_json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


def test_generate_format_stub(app_client):
    r = app_client.post(
        "/api/generate/format",
        data=json.dumps({"caption": "test", "lyrics": "", "duration": 60}),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True


def test_generate_upload_audio(app_client):
    r = app_client.post(
        "/api/generate/upload-audio",
        data={"audio": (io.BytesIO(b"fake-wav-content"), "ref.wav")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "url" in data
    assert "key" in data
    assert "/audio/refs/" in data["url"]


def test_generate_create_job_validation(app_client):
    r = app_client.post(
        "/api/generate/",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert r.status_code == 400


def test_generate_create_job_success(app_client):
    r = app_client.post(
        "/api/generate/",
        data=json.dumps({
            "songDescription": "instrumental background music",
            "duration": 30,
            "instrumental": True,
        }),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "jobId" in data
    assert data.get("status") in ("queued", "running")
    assert "queuePosition" in data


def test_generate_create_job_no_trailing_slash(app_client):
    """POST /api/generate (no slash) must work — UI sends this; was 405 before fix."""
    r = app_client.post(
        "/api/generate",
        data=json.dumps({
            "songDescription": "test track",
            "duration": 30,
            "instrumental": True,
        }),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "jobId" in data
    assert data.get("status") in ("queued", "running")


def test_generate_status_not_found(app_client):
    r = app_client.get("/api/generate/status/nonexistent-uuid")
    assert r.status_code == 404


def test_generate_audio_query_required(app_client):
    r = app_client.get("/api/generate/audio")
    assert r.status_code == 400


# ---- Playlists ----
def test_playlists_list(app_client):
    r = app_client.get("/api/playlists/")
    assert r.status_code == 200
    data = r.get_json()
    assert "playlists" in data
    assert isinstance(data["playlists"], list)


def test_playlists_create(app_client):
    r = app_client.post(
        "/api/playlists/",
        data=json.dumps({"name": "Test", "description": "", "isPublic": True}),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "playlist" in data
    assert data["playlist"]["name"] == "Test"
    pid = data["playlist"]["id"]
    r2 = app_client.get(f"/api/playlists/{pid}")
    assert r2.status_code == 200
    assert r2.get_json().get("playlist", {}).get("id") == pid


def test_playlists_public_featured(app_client):
    r = app_client.get("/api/playlists/public/featured")
    assert r.status_code == 200
    data = r.get_json()
    assert "playlists" in data


# ---- Users (stubs) ----
def test_users_me(app_client):
    r = app_client.get("/api/users/me")
    assert r.status_code == 200
    data = r.get_json()
    assert data["user"]["id"] == "local"


def test_users_public_featured(app_client):
    r = app_client.get("/api/users/public/featured")
    assert r.status_code == 200
    data = r.get_json()
    assert "creators" in data


def test_users_username(app_client):
    r = app_client.get("/api/users/anyname")
    assert r.status_code == 200
    data = r.get_json()
    assert data["user"]["username"] == "anyname"


# ---- Contact (stub) ----
def test_contact(app_client):
    r = app_client.post(
        "/api/contact",
        data=json.dumps({"message": "test", "email": "test@test.com"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True or "message" in data or "id" in data


# ---- Reference tracks ----
def test_reference_tracks_list(app_client):
    r = app_client.get("/api/reference-tracks/")
    assert r.status_code == 200
    data = r.get_json()
    assert "tracks" in data
    assert isinstance(data["tracks"], list)


# ---- Audio route (app-level) ----
def test_audio_invalid_path(app_client):
    r = app_client.get("/audio/..%2Fetc%2Fpasswd")
    assert r.status_code in (400, 404)


def test_audio_not_found(app_client):
    r = app_client.get("/audio/nonexistent.wav")
    assert r.status_code == 404


# ---- Health (existing) ----
def test_healthz(app_client):
    r = app_client.get("/healthz")
    assert r.status_code == 200
    assert r.data.strip() == b"ok"
