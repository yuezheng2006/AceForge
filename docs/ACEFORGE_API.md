# AceForge API Reference

This document describes the HTTP API exposed by AceForge for local clients (e.g. the bundled React UI, CLI tools, or third-party apps). The server runs locally; no authentication is required.

**Base URL (typical):** `http://127.0.0.1:5056` when running the app or dev server.

**Content type:** JSON for request/response bodies unless noted. Use `Content-Type: application/json` for POST/PATCH.

---

## Overview

- **REST-style JSON API** under `/api/*`: auth, songs, generation, playlists, users, preferences, reference tracks, search, contact.
- **Audio serving:** `GET /audio/<filename>` and `GET /audio/refs/<filename>` for playback.
- **Legacy / tools routes** (used by the UI for stem splitting, voice cloning, MIDI, training, model downloads): at root paths like `/progress`, `/train_lora`, `/stem_split`, `/voice_clone`, `/midi_generate`, `/models/*`.

---

## 1. Auth (`/api/auth`)

Local-only; no real login. All routes return a single local user (e.g. OS username).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/auth/auto` | Current user and token (token may be `null`) |
| GET | `/api/auth/me` | Current user (no token check) |
| POST | `/api/auth/setup` | Body: `{ "username": "..." }`. Stub; returns same as auto. |
| POST | `/api/auth/logout` | Stub; returns `{ "success": true }` |
| POST | `/api/auth/refresh` | Stub; returns same as auto |
| PATCH | `/api/auth/username` | Body: `{ "username": "..." }`. Stub; keeps OS username. |

**Example response (e.g. GET /api/auth/auto):**
```json
{
  "user": {
    "id": "local",
    "username": "YourOSUsername",
    "bio": null,
    "avatar_url": null,
    "banner_url": null,
    "isAdmin": false,
    "createdAt": null
  },
  "token": null
}
```

---

## 2. Songs (`/api/songs`)

Tracks from the configured output directory plus uploaded reference tracks. Song IDs for generated tracks are filenames; reference tracks use IDs prefixed with `ref:`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/songs` | List all songs (generated + reference). Response: `{ "songs": [ ... ] }` |
| GET | `/api/songs/public` | Same as list |
| GET | `/api/songs/public/featured` | Same as list, limited |
| GET | `/api/songs/<song_id>` | One song. Ref tracks: use ID without `ref:` prefix for lookup; response may use `ref:<id>`. |
| GET | `/api/songs/<song_id>/full` | Song + comments (stub comments: `[]`) |
| GET | `/api/songs/<song_id>/audio` | Redirect/serve audio file (generated track) |
| POST | `/api/songs` | Create song record (no-op for file-based tracks). Body: song object. Returns `{ "song": <body> }`, 201. |
| PATCH | `/api/songs/<song_id>` | Update metadata. Body: `{ "title"?, "style"?, "lyrics"? }`. Ref tracks: no-op. |
| DELETE | `/api/songs/<song_id>` | Delete file and metadata (or remove reference track if `ref:...`) |
| POST | `/api/songs/<song_id>/like` | Toggle like in metadata. Response: `{ "liked": true|false }` |
| GET | `/api/songs/liked/list` | Songs marked favorite. Response: `{ "songs": [ ... ] }` |
| PATCH | `/api/songs/<song_id>/privacy` | Stub. Response: `{ "isPublic": true }` |
| POST | `/api/songs/<song_id>/play` | Stub. Response: `{ "viewCount": 0 }` |
| GET | `/api/songs/<song_id>/comments` | Stub. Response: `{ "comments": [] }` |
| POST | `/api/songs/<song_id>/comments` | Stub. Body: `{ "content": "..." }`. Returns stub comment. |
| DELETE | `/api/songs/comments/<comment_id>` | Stub. Response: `{ "success": true }` |

**Song object shape (representative):**
```json
{
  "id": "filename.wav",
  "title": "Track title",
  "lyrics": "",
  "style": "genre",
  "caption": "genre",
  "cover_url": null,
  "audio_url": "/audio/filename.wav",
  "duration": 120,
  "bpm": null,
  "key_scale": null,
  "time_signature": null,
  "tags": [],
  "is_public": true,
  "like_count": 0,
  "view_count": 0,
  "user_id": "local",
  "created_at": 1234567890,
  "creator": "Local"
}
```

Reference tracks have `audio_url` like `/audio/refs/<filename>` and `id` may be returned as `ref:<uuid>` in some contexts.

---

## 3. Generation (`/api/generate`)

ACE-Step text-to-music (and related tasks). Jobs are queued and run one at a time.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/generate` | Start a generation job. Returns `jobId`, `status`, `queuePosition`. |
| GET | `/api/generate/status/<job_id>` | Job status and result when done |
| POST | `/api/generate/upload-audio` | Upload audio (multipart form field `audio`). Saves to references dir and library. Returns `{ "url", "key" }`. |
| GET | `/api/generate/audio` | Query: `?path=...`. Serve file from output or references dir. |
| GET | `/api/generate/history` | Last 50 jobs. Response: `{ "jobs": [ ... ] }` |
| GET | `/api/generate/endpoints` | Response: `{ "endpoints": { "provider": "acestep-local", "endpoint": "local" } }` |
| GET | `/api/generate/health` | Response: `{ "healthy": true }` |
| GET | `/api/generate/debug/<task_id>` | Raw job info (debug) |
| POST | `/api/generate/format` | Stub; echoes caption, lyrics, bpm, duration, keyScale, timeSignature |

**POST /api/generate body (main fields):**
- `customMode`: boolean. If false, `songDescription` is required.
- `songDescription` or `style`: text prompt (caption).
- `lyrics`: optional lyrics (or "[inst]" for instrumental).
- `instrumental`: boolean (default true).
- `duration`: seconds (15–240).
- `inferenceSteps`: int (e.g. 55).
- `guidanceScale`: float (e.g. 6.0).
- `seed`: int; if `randomSeed` is true, server may override with random.
- `taskType`: `"text2music"` | `"retake"` | `"repaint"` | `"extend"` | `"cover"` | `"audio2audio"`.
- `referenceAudioUrl`, `sourceAudioUrl`: URLs like `/audio/refs/...` or `/audio/<filename>` for reference/cover.
- `audioCoverStrength` / `ref_audio_strength`: 0–1.
- `repaintingStart`, `repaintingEnd`: for repaint task.
- `title`: base name for output file.
- `outputDir` / `output_dir`: optional; else uses app default.
- `keyScale`, `timeSignature`, `vocalLanguage`, `bpm`: optional.

**Response (POST):** `{ "jobId": "<uuid>", "status": "queued", "queuePosition": 1 }`

**Status response:** `{ "jobId", "status": "queued"|"running"|"succeeded"|"failed", "queuePosition"?, "etaSeconds"?, "result"?, "error"? }`. On success, `result` includes e.g. `audioUrls`, `duration`, `status`.

---

## 4. Playlists (`/api/playlists`)

Stored in user data as JSON. No auth.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/playlists` | List playlists. Response: `{ "playlists": [ ... ] }` |
| POST | `/api/playlists` | Create. Body: `{ "name", "description"?, "isPublic"?: true }`. Response: `{ "playlist": { "id", "name", "description", "is_public", "song_ids": [] } }` |
| GET | `/api/playlists/public/featured` | Stub. Response: `{ "playlists": [] }` |
| GET | `/api/playlists/<playlist_id>` | One playlist. Response: `{ "playlist", "songs": [] }` (songs not expanded) |
| POST | `/api/playlists/<playlist_id>/songs` | Add song. Body: `{ "songId": "..." }`. Response: `{ "success": true }` |
| DELETE | `/api/playlists/<playlist_id>/songs/<song_id>` | Remove song. Response: `{ "success": true }` |
| PATCH | `/api/playlists/<playlist_id>` | Update. Body: `{ "name"?, "description"? }`. Response: `{ "playlist" }` |
| DELETE | `/api/playlists/<playlist_id>` | Delete playlist. Response: `{ "success": true }` |

---

## 5. Users (`/api/users`)

Stubs for local single-user. All return the same local user or empty lists.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/users/me` | Current user |
| GET | `/api/users/public/featured` | `{ "creators": [] }` |
| GET | `/api/users/<username>` | User profile (local user with optional username override) |
| GET | `/api/users/<username>/songs` | Same as GET /api/songs |
| GET | `/api/users/<username>/playlists` | Same as GET /api/playlists |
| PATCH | `/api/users/me` | Stub. Returns local user |
| POST | `/api/users/me/avatar` | Stub. Returns `{ "user", "url": null }` |
| POST | `/api/users/me/banner` | Stub. Returns `{ "user", "url": null }` |
| POST | `/api/users/<username>/follow` | Stub. Returns `{ "following": false, "followerCount": 0 }` |
| GET | `/api/users/<username>/followers` | `{ "followers": [] }` |
| GET | `/api/users/<username>/following` | `{ "following": [] }` |
| GET | `/api/users/<username>/stats` | `{ "followerCount": 0, "followingCount": 0, "isFollowing": false }` |

---

## 6. Preferences (`/api/preferences`)

App-wide settings (paths, UI zoom, optional module config). Stored in `aceforge_config.json`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/preferences` | Full config object. Keys may include: `output_dir`, `models_folder`, `ui_zoom`, `stem_split`, `voice_clone`, `midi_gen`, `training`. |
| PATCH | `/api/preferences` | Merge partial object and save. Returns full config. Example: `{ "output_dir": "/path", "models_folder": "/path", "ui_zoom": 90 }`. |

---

## 7. Reference tracks (`/api/reference-tracks`)

Upload and manage reference audio (for generation and library). Stored under user data `references/` and `reference_tracks.json`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reference-tracks` | List. Response: `{ "tracks": [ { "id", "filename", "storage_key", "audio_url", "duration", "file_size_bytes", "tags" } ] }` |
| POST | `/api/reference-tracks` | Upload (multipart form field `audio`). Response: `{ "track", "url", "key" }` |
| PATCH | `/api/reference-tracks/<ref_id>` | Update. Body: `{ "tags": [ ... ] }`. Response: updated track. |
| DELETE | `/api/reference-tracks/<ref_id>` | Delete file and metadata. Response: `{ "success": true }` |

---

## 8. Search (`/api/search`)

Simple local search over tracks (title/style/filename).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/search?q=<query>&type=all|songs|creators|playlists` | Response: `{ "songs": [ ... ], "creators": [ ... ], "playlists": [ ... ] }`. Local: creators/playlists usually empty. |

---

## 9. Contact (`/api/contact`)

Stub; no email or DB.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/contact` | Body: arbitrary. Response: `{ "success": true, "message": "Received", "id": "local" }` |

---

## 10. Audio serving (app-level)

Not under `/api/`. Used for playback by the UI.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/audio/<filename>` | Serve file from configured **output** directory (generated tracks). |
| GET | `/audio/refs/<filename>` | Serve file from user data **references** directory. |

Paths must not contain `..` or leading `/`. Returns 400 for invalid path, 404 if file not found.

---

## 11. Legacy / tools routes (root paths)

Used by the bundled UI for stem splitting, voice cloning, MIDI generation, LoRA training, and model downloads. These are registered without an `/api` prefix.

### Progress (generation / long-running tasks)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/progress` | Current job progress. Response: `{ "fraction", "done", "error", "stage"?, "current"?, "total"? }` |

### ACE-Step and other models
| Method | Path | Description |
|--------|------|-------------|
| GET | `/models/status` | ACE-Step model status. Response: `{ "ok", "ready", "state", "message"? }` |
| POST | `/models/ensure` | Ensure ACE-Step models are downloaded (start download if needed). |
| GET | `/models/folder` | Get configured models folder path. |
| POST | `/models/folder` | Set models folder (body or form). |
| GET | `/models/stem_split/status` | Demucs/stem-split model status. |
| POST | `/models/stem_split/ensure` | Ensure stem-split models. |
| GET | `/models/voice_clone/status` | Voice-clone (TTS) model status. |
| POST | `/models/voice_clone/ensure` | Ensure voice-clone models. |
| GET | `/models/midi_gen/status` | MIDI (basic-pitch) model status. |
| POST | `/models/midi_gen/ensure` | Ensure MIDI models. |

### Stem splitting
| Method | Path | Description |
|--------|------|-------------|
| POST | `/stem_split` | Form data: audio file and options (e.g. stem count, mode, device, export format). May return JSON or HTML. |

### Voice cloning
| Method | Path | Description |
|--------|------|-------------|
| POST | `/voice_clone` | Form data: audio and options. May return JSON or HTML. |

### MIDI generation
| Method | Path | Description |
|--------|------|-------------|
| POST | `/midi_generate` | Form data: audio and options. May return JSON or HTML. |

### LoRA training
| Method | Path | Description |
|--------|------|-------------|
| GET | `/train_lora/status` | Training status. Response: `{ "running"?, "paused"?, "progress"?, "current_step"?, "max_steps"?, "current_epoch"?, "max_epochs"?, "last_message"?, "returncode"? }` |
| GET | `/train_lora/configs` | Available configs. Response: `{ "ok", "configs": [ { "file", "label" } ], "default"? }` |
| POST | `/train_lora` | Start training (form data). May return HTML. |
| POST | `/train_lora/pause` | Pause training. |
| POST | `/train_lora/resume` | Resume training. |
| POST | `/train_lora/cancel` | Cancel training. |

Other legacy routes (e.g. `/music/<path>`, `/tracks.json`, `/tracks/meta`, `/user_presets`, `/tracks/rename`, `/tracks/delete`, `/generate` POST for legacy form, `/lyrics/*`, `/mufun/*`, `/dataset_mass_tag`) exist for the classic UI or internal use; see source if you need them.

---

## Errors

- API routes under `/api/*` return JSON on error, e.g. `{ "error": "Message" }` with HTTP 4xx/5xx.
- Legacy routes may return HTML or plain text on failure; check `Content-Type` and handle accordingly.

---

## CORS and credentials

The server is intended for local use. The bundled UI uses relative URLs and `credentials: 'include'`. For other local clients, same-origin or explicit CORS may apply depending on deployment.
