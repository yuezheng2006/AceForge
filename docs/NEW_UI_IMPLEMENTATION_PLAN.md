# Standalone Port of ace-step-ui into AceForge — Implementation Plan

**Branch:** `experimental-ui`  
**Goal:** Embed the [ace-step-ui](https://github.com/fspecii/ace-step-ui) React frontend into AceForge with **no external dependency** on that repo after completion.

**Implementation status:** Not started. Phases 1–7 below are the execution order.


---

## Principles

- **Standalone:** All UI source lives inside AceForge (copied/ported once). No git submodule or npm dependency on `fspecii/ace-step-ui`.
- **Single server:** One Flask app on one port (e.g. 5056). Pywebview loads that URL. No separate Node or ACE-Step HTTP API process.
- **Local-only, no auth:** No authentication. We do not implement login, signup, JWT, or auth middleware. The app is single-user, local-only. The UI can be adjusted to remove auth flows (no username modal, no token); if the ported UI still calls `GET /api/auth/auto`, we provide a minimal stub that returns a fixed "user" so the app doesn't error, but no token or validation anywhere.
- **API parity:** Flask routes implement the same paths and JSON shapes the React app expects (from `services/api.ts` and Express routes), with no auth requirements.
- **Build integration:** Building the app (local and PyInstaller) runs the UI build step and bundles the built static files.
- **Storage in global app settings:** All persistent data for the new APIs/UI (generations, settings, playlists, reference uploads, job history, etc.) must use AceForge’s **global user directories** — not paths inside the app bundle or relative to the app. On macOS this is the standard app support and preferences locations; other platforms use the same abstraction via `cdmf_paths`.
- **Roadmap:** After the new UI is successfully integrated (Generation + shared library/player), the plan is to extend it to **Training, Stem Splitting, Voice Cloning, and Audio-to-MIDI** with the same shared player approach. That extension is a follow-on phase, not part of the initial Phases 1–7; see **Roadmap** section below.

---

## Storage: global app settings (macOS / cross‑platform)

All new API and UI persistence must go through **`cdmf_paths`** so that:

- **macOS:** User data lives under **`~/Library/Application Support/AceForge/`**; preferences/settings under **`~/Library/Preferences/com.audiohacking.AceForge/`** (or the bundle ID in use).
- **Windows/Linux:** Same pattern where supported; otherwise `cdmf_paths` falls back to app directory as it does today.

**Use these consistently:**

| What | Where (via cdmf_paths) |
|------|-------------------------|
| **Generated tracks** | Already: `get_user_data_dir() / "generated"` (DEFAULT_OUT_DIR). New API must use this for output; do not write under the app or cwd. |
| **Track metadata** | Already: `TRACK_META_PATH` (user data dir). Songs API reads/writes here. |
| **Playlists** | `get_user_data_dir() / "playlists.json"` (or similar). Not in app dir. |
| **Generation job history** | `get_user_data_dir() / "generation_jobs.json"` (or a subdir). File-backed job queue can live here. |
| **Reference uploads** | `get_user_data_dir() / "references"` — uploaded reference/source audio files. |
| **Reference metadata** | `get_user_data_dir() / "reference_tracks.json"` (or similar). |
| **User presets / new UI settings** | Prefer **`get_user_preferences_dir()`** for small settings (or extend `CONFIG_PATH` / `aceforge_config.json`); larger data in **`get_user_data_dir()`**. |
| **Optional auth stub state** | If we ever store anything for the auth stub: `get_user_data_dir()` or preferences dir. |

**Do not:** Store user data in `APP_DIR`, inside the .app bundle, or in the current working directory. Always use `cdmf_paths.get_user_data_dir()` or `get_user_preferences_dir()` (and existing constants like `DEFAULT_OUT_DIR`, `TRACK_META_PATH`) so behaviour is consistent with the rest of AceForge and respects OS conventions (e.g. macOS Application Support).

---

## Phase 1: Port UI Source Into Repo

### 1.1 Create `ui/` and copy frontend only

- **Directory:** `AceForge/ui/` (new).
- **Copy from clone** (one-time port from `../ace-step-ui` or similar):
  - Root: `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `index.tsx`, `App.tsx`, `types.ts`, `global.d.ts`, `metadata.json`.
  - Dirs: `components/`, `context/`, `services/` (frontend `api.ts`, `geminiService.ts` if used).
  - **Do not copy:** `server/`, `audiomass-editor/` (optional later), `docs/`, `setup.sh`, `start.sh`, etc.
- **Remove external reference:** In `ui/package.json`, ensure no dependency on the ace-step-ui repo (only public npm packages). Add a top-level comment or README in `ui/` stating: “Ported from fspecii/ace-step-ui; maintained in-tree. No external dependency on that repo.”

### 1.2 Configure Vite build for Flask

- **Base path:** In `ui/vite.config.ts`, set `base: '/'` so assets are requested at root (e.g. `/assets/...`). Flask will serve the app at `/` and assets under `/assets/` (or whatever Vite emits).
- **API proxy (dev only):** For local `bun run dev`, keep proxy target as `http://127.0.0.1:5056` (our Flask) so the React app talks to Flask during development. Update `vite.config.ts` so `server.proxy['/api']` and `server.proxy['/audio']` point to Flask port (5056), not 3001.
- **Build output:** Default Vite build outputs to `ui/dist/` (index.html + `assets/`). We will use this as the only production artifact.

### 1.3 Optional: Editor / Demucs static assets

- **Defer:** Do not copy `audiomass-editor/` or `server/public/demucs-web/` in Phase 1. We can add them in a later phase and serve from Flask at `/editor` and `/demucs-web`. The main Create/Library/Player flow does not require them for the first cut.

---

## Phase 2: Flask API Compatibility Layer

Implement Flask blueprints (or route modules) that mirror the Express API the React app calls. All under prefix `/api` and optionally `/audio`. No authentication: all routes are open; use file/JSON-based storage where needed.

### 2.1 Auth — removed (local-only, no auth)

- **No auth flow.** We do not implement login, signup, JWT, or any auth middleware.
- **Optional stub only:** If the ported React app still calls `GET /api/auth/auto` on load, implement a single route that returns a fixed payload so the app doesn’t 404: e.g. `{ user: { id: 'local', username: 'Local' }, token: null }`. No other auth routes (`/setup`, `/me`, `/logout`, `/refresh`, `/username`) are required; the UI should be updated to remove auth UI (username modal, login) so those are never called. No token is ever validated; no `Authorization` header is read.

### 2.2 Generation — `api_generate.py` (Blueprint)

- **Base path:** `/api/generate`
- **Routes:**
  - `POST /api/generate` — Body: ace-step-ui `GenerationParams` (JSON). Create a job (in-memory or file-backed queue under **`get_user_data_dir()`**), map params to our `generate_track_ace()` (see Phase 3), return `{ jobId, status: 'queued', queuePosition: 1 }`.
  - `GET /api/generate/status/:jobId` — Return `{ jobId, status, queuePosition?, etaSeconds?, result?, error? }`. When status is `succeeded`, `result` must include `audioUrls` (array of URLs the app can fetch, e.g. `/audio/...` or our track URL pattern).
  - `POST /api/generate/upload-audio` — Multipart file upload for reference/source audio. Save under **`get_user_data_dir() / "references"`**; return `{ url, key }` where `url` is the path the adapter will use (e.g. `/audio/refs/<filename>`).
  - `GET /api/generate/audio` — Query `?path=...`. Proxy or send file from our output dir (DEFAULT_OUT_DIR) or references dir (**`get_user_data_dir() / "references"`**) so the app can stream generated or uploaded audio.
  - `GET /api/generate/history` — Return list of recent jobs (e.g. last 50) from job store persisted under **`get_user_data_dir()`** (e.g. `generation_jobs.json` or equivalent).
  - `GET /api/generate/endpoints` — Return `{ endpoints: { provider: 'acestep-local', endpoint: ... } }`.
  - `GET /api/generate/health` — Return `{ healthy: true }` (and optionally check model presence).
  - `GET /api/generate/debug/:taskId` — Optional; return raw debug info for a task.
  - `POST /api/generate/format` — Body: caption, lyrics, bpm, duration, etc. Stub with 200 and same payload or call our lyrics/prompt helper if available; otherwise return placeholder.

**No auth:** All generation routes are open; no token or auth middleware.

### 2.3 Songs — `api_songs.py` (Blueprint)

- **Base path:** `/api/songs`
- **Data model:** Map “songs” to our tracks: list from `cdmf_tracks.list_music_files()` (output dir = **DEFAULT_OUT_DIR**, i.e. `get_user_data_dir() / "generated"` on macOS) and existing track metadata from **`TRACK_META_PATH`** (already in user data dir). Assign a stable `id` per track (e.g. filename-based or UUID stored in metadata). No user filtering — all tracks are the single local library.
- **Routes:**
  - `GET /api/songs` — List all songs (all tracks in output dir); return `{ songs: [...] }` with shape expected by the UI (id, title, lyrics, style, audio_url, duration, bpm, etc.).
  - `GET /api/songs/public` — Optional; return public songs (we can treat all as same user for now).
  - `GET /api/songs/public/featured` — Optional; subset or same list.
  - `GET /api/songs/:id` — One song by id; return `{ song }`. Resolve id to filename and metadata.
  - `GET /api/songs/:id/full` — Same as above plus optional `comments: []` (stub).
  - `GET /api/songs/:id/audio` — Stream the audio file for that song (or redirect to our track URL).
  - `POST /api/songs` — Create song record when generation completes (called by our adapter when we add a new track).
  - `PATCH /api/songs/:id` — Update metadata (title, style, etc.); persist to **`TRACK_META_PATH`** (global app settings).
  - `DELETE /api/songs/:id` — Delete file and metadata.
  - `POST /api/songs/:id/like` — Stub or minimal: toggle like in metadata; return `{ liked: boolean }`.
  - `GET /api/songs/liked/list` — Return songs marked liked.
  - `PATCH /api/songs/:id/privacy` — Stub or minimal (is_public).
  - `POST /api/songs/:id/play` — Stub; return `{ viewCount }`.
  - `GET /api/songs/:id/comments` — Return `{ comments: [] }`.
  - `POST /api/songs/:id/comments` — Stub 201 with a fake comment or 501.
  - `DELETE /api/songs/comments/:commentId` — Stub 200.

### 2.4 Playlists — `api_playlists.py` (Blueprint)

- **Storage:** One JSON file at **`get_user_data_dir() / "playlists.json"`** (global app settings). Structure: `{ "playlists": [ { id, name, description, is_public, song_ids: [] } ] }`. No user_id needed (local-only).
- **Routes:**
  - `POST /api/playlists` — Create playlist; append to store; return `{ playlist }`.
  - `GET /api/playlists` — List all playlists (single local user).
  - `GET /api/playlists/public/featured` — Optional; return [] or subset.
  - `GET /api/playlists/:id` — Get playlist with `songs` array (resolve song ids to song objects).
  - `POST /api/playlists/:id/songs` — Body `{ songId }`; add to playlist.
  - `DELETE /api/playlists/:id/songs/:songId` — Remove from playlist.
  - `PATCH /api/playlists/:id` — Update name/description.
  - `DELETE /api/playlists/:id` — Delete playlist.

### 2.5 Users — `api_users.py` (Blueprint)

- **Base path:** `/api/users`
- **No auth.** All routes are stubs or return fixed local data. No “current user” or token.
- **Routes:**
  - `GET /api/users/me` — Stub: return fixed `{ user: { id: 'local', username: 'Local', ... } }` (or 404 if UI doesn’t need it).
  - `GET /api/users/public/featured` — Return [] or a single fixed “creator” for display.
  - `GET /api/users/:username` — Return a fixed profile (same for any username; local app).
  - `GET /api/users/:username/songs` — Same as our full tracks list.
  - `GET /api/users/:username/playlists` — Same as our playlists list.
  - `PATCH /api/users/me` — Stub 200 (no-op or optional local display name).
  - `POST /api/users/me/avatar`, `POST /api/users/me/banner` — Stub 200.
  - `POST /api/users/:username/follow`, `GET /api/users/:username/followers`, `GET /api/users/:username/following`, `GET /api/users/:username/stats` — Stub (e.g. 200, [], zeros).

### 2.6 Search — `api_search.py` or part of main app

- **Route:** `GET /api/search?q=...&type=...` — Search our tracks (and optionally playlists) by title/style; return `{ songs, creators, playlists }` with the shape the UI expects.

### 2.7 Contact — `api_contact.py` (Blueprint)

- **Route:** `POST /api/contact` — Stub 200 and return `{ success: true, message: '...', id: '...' }` (no email or DB).

### 2.8 Reference tracks — `api_reference_tracks.py` (Blueprint)

- **Base path:** `/api/reference-tracks`
- **Storage:** Uploaded files in **`get_user_data_dir() / "references"`**; metadata in **`get_user_data_dir() / "reference_tracks.json"`** (global app settings). No user scoping.
- **Routes:**
  - `GET /api/reference-tracks` — List all reference tracks.
  - `POST /api/reference-tracks` — Upload audio; save file; return record with `audio_url`.
  - `PATCH /api/reference-tracks/:id` — Update tags/metadata.
  - `DELETE /api/reference-tracks/:id` — Delete file and record.

### 2.9 Static and non-API routes

- **`/audio/*`** — Serve generated and reference audio from **DEFAULT_OUT_DIR** (`get_user_data_dir() / "generated"` on macOS) and **`get_user_data_dir() / "references"`**. Reuse or extend existing track-serving logic so that `audioUrls` point to `/audio/<path>` and resolve to these paths on disk.
- **`/editor`**, **`/demucs-web`** — Defer or add later; serve static files from a folder if we port AudioMass/Demucs-web.

### 2.10 Top-level and health

- **`GET /health`** — Already have `/healthz`; add alias `/health` returning JSON `{ status: 'ok' }` or `{ healthy: true }` so any client expecting “health” is satisfied.
- **Existing:** Keep `/healthz`, `/loading`, `/logs/stream`, `/shutdown` as-is. New UI will use `/api/*` and `/audio/*`.

---

## Phase 3: Generation Adapter (AceForge backend)

### 3.1 Job queue and state

- **Job store under global app settings:** When `POST /api/generate` is called, create a job record with a unique `jobId` (UUID), status `queued`, and the received `GenerationParams`. Persist job state under **`get_user_data_dir()`** (e.g. `generation_jobs.json` or a small JSON file per job) so it survives restarts. Run generation in a background thread (or reuse existing pattern from `cdmf_generation`). Output files go to **DEFAULT_OUT_DIR** (`get_user_data_dir() / "generated"` on macOS). When `generate_track_ace()` finishes, update job to `succeeded` and set `result.audioUrls` to URLs the client can request (e.g. `/audio/<basename>.mp3`). On failure, set status `failed` and `error`.

### 3.2 Parameter mapping (GenerationParams → our pipeline)

- Map from ace-step-ui names to our Python API:
  - `prompt` / `songDescription` / `style` → our `prompt`
  - `lyrics` → our `lyrics`
  - `instrumental` → our `instrumental`
  - `duration` → our `target_seconds`
  - `inferenceSteps` → our `steps`
  - `guidanceScale` → our `guidance_scale`
  - `randomSeed`, `seed` → our `seed`
  - `bpm` → our `bpm`
  - `keyScale`, `timeSignature` → optional (we can add to prompt or ignore if not supported)
  - `referenceAudioUrl` / `reference_audio_path` → our reference audio file path (resolve upload path to disk)
  - `sourceAudioUrl` / `src_audio_path` → source for “audio cover” if we support it
  - `audioFormat` → our output format (wav/mp3)
  - `batchSize` — we can run one at a time and ignore or loop
- **Unsupported params:** thinking/LLM, repainting, etc. can be ignored or logged; do not break the request.

### 3.3 Result and audio URLs

- After generation, output is written to **DEFAULT_OUT_DIR** (global app settings). Set `result.audioUrls = [ '/audio/<filename>' ]` (or the path Flask serves under `/audio`). Ensure `GET /api/generate/audio?path=...` and/or `GET /audio/<path>` resolve to files under DEFAULT_OUT_DIR (and references dir) so the player can stream them.

### 3.4 Uploaded reference audio

- `POST /api/generate/upload-audio` saves the file under **`get_user_data_dir() / "references"`**; return a `url` that the adapter can resolve to that path when calling `generate_track_ace(reference_audio_path=...)`. Same for reference-tracks if used as reference. No storage inside the app or cwd.

---

## Phase 4: Serve the New UI from Flask (Single Port)

### 4.1 SPA at root

- **When “new UI” is enabled (default on experimental-ui):**
  - `GET /` → Serve `ui/dist/index.html` (or the built index from the path we bundle).
  - Static assets (JS, CSS) have paths like `/assets/...` (Vite default). Serve them from the same `dist` folder (e.g. `dist/assets/`).
- **Catch-all for SPA routing:** For any GET request that is not `/api`, `/audio`, `/health`, `/healthz`, `/loading`, `/logs`, `/shutdown`, and that does not match a file in the built app, return `index.html` so client-side routing works.

### 4.2 Where the built app lives

- **Development:** `ui/dist/` after `bun run build`. Flask can be configured with a second static folder or a dedicated route for the app root (e.g. `send_from_directory('ui/dist', 'index.html')` and static files from `ui/dist`).
- **Frozen app:** PyInstaller will bundle a copy of `ui/dist` (see Phase 5). At runtime, path comes from `sys._MEIPASS`; serve from `Path(sys._MEIPASS) / 'app'` or similar.

### 4.3 Loading screen

- Keep `/loading` serving the current `static/loading.html` that polls `/healthz` and redirects to `/`. So first load: open `/loading` in pywebview, then redirect to `/` (new UI) when server is ready.

### 4.4 Legacy UI (optional)

- We can keep the old Jinja UI under a route like `/legacy` for fallback or remove it in a later cleanup. Plan: implement new UI at `/`; legacy can remain at `/legacy` if we explicitly register it, or be removed once the new UI is stable.

---

## Phase 5: Build Integration

### 5.1 Prerequisites

- **Bun:** Required only at build time (local and CI) for the new UI. Document in README: “Building the app with the new UI requires Bun (https://bun.sh).”

### 5.2 Script: `scripts/build_ui.sh` (or `ui/build.sh`)

- **Location:** `AceForge/scripts/build_ui.sh` or `AceForge/ui/build.sh`.
- **Steps:**
  1. `cd` to `AceForge/ui`.
  2. `bun install` (or `bun install --frozen-lockfile` if using a lockfile).
  3. `bun run build`.
  4. Exit 0 only if `ui/dist/index.html` (and ideally `ui/dist/assets/`) exists.
- **Idempotent:** If `ui/` is missing, exit with a clear message (e.g. “ui/ not found; run from repo root after copying UI source”).

### 5.3 Integrate into `build_local.sh`

- **Before PyInstaller:** If directory `ui/` exists and `package.json` is present, run the UI build script. If the script fails, optionally fail the whole build or warn and continue (decide: fail so we don’t ship without UI).
- **After UI build:** PyInstaller should see `ui/dist` and include it in the bundle (see 5.4).

### 5.4 PyInstaller spec (`CDMF.spec`)

- **Add to `datas`:**
  - If `ui/dist` exists: `(str(ui_dist_dir), 'app')` so that the built app is placed at `app/` inside the bundle (e.g. under `_MEIPASS/app`).
- **In Flask:** When frozen, set the “app root” to `Path(sys._MEIPASS) / 'app'` and serve `index.html` and static assets from there. When not frozen, use `Path(__file__).parent / 'ui' / 'dist'` or the path from config.

### 5.5 .gitignore

- **Ignore:** `ui/node_modules/`, `ui/dist/` (so we don’t commit build artifacts). Optionally commit `ui/bun.lockb` for reproducible installs. Commit only source (components, services, package.json, vite.config.ts, etc.).

### 5.6 CI (optional)

- In GitHub Actions (e.g. `build-release.yml`), before PyInstaller: run Bun setup and `scripts/build_ui.sh` (or `cd ui && bun install && bun run build`). Ensure `ui/dist` is present so the spec can include it.

---

## Phase 6: File and Module Layout (Summary)

```
AceForge/
  ui/                          # React app source (ported; auth removed from UI)
    package.json
    vite.config.ts
    index.html
    index.tsx
    App.tsx
    components/
    context/
    services/
    dist/                      # Build output (gitignored)
  scripts/
    build_ui.sh
  api_auth.py                  # Optional: single stub GET /api/auth/auto only (no JWT, no other routes)
  api_generate.py              # Blueprint: /api/generate (no auth)
  api_songs.py                 # Blueprint: /api/songs (no auth)
  api_playlists.py             # Blueprint: /api/playlists (no auth)
  api_users.py                 # Blueprint: /api/users (stubs, no auth)
  api_reference_tracks.py      # Blueprint: /api/reference-tracks (no auth)
  api_contact.py               # Blueprint: /api/contact (stub)
  api_search.py                # or in music_forge_ui: /api/search
  music_forge_ui.py            # Register blueprints; serve SPA from / and /app/*
  static/                      # Existing (loading, legacy if kept)
  ...
  build_local.sh               # Calls scripts/build_ui.sh then PyInstaller
  CDMF.spec                    # datas: (ui/dist, 'app')
```

---

## Phase 7: Order of Implementation (Suggested)

1. **Phase 1** — Create `ui/`, copy frontend source, adjust Vite base and proxy. When porting the UI, remove auth flows (username modal, login, token usage) so the app is local-only.
2. **Phase 2.1** — No auth blueprint. Optionally add a single stub: `GET /api/auth/auto` → `{ user: { id: 'local', username: 'Local' }, token: null }` only if the UI still calls it and we don’t change the front end yet.
3. **Phase 2.2 + Phase 3** — Generate blueprint + adapter (POST generate, job queue, map params to `generate_track_ace`, status, upload-audio, audio proxy, history, health). No auth on any route.
4. **Phase 2.3** — Songs blueprint (map tracks to songs, list/get/create/update/delete, stub likes/comments). No auth.
5. **Phase 4** — Serve `ui/dist` at `/` and assets; SPA fallback.
6. **Phase 5** — `build_ui.sh`, integrate into `build_local.sh`, update `CDMF.spec` and Flask app root for frozen.
7. **Phase 2.4–2.8** — Playlists, users, search, contact, reference-tracks (stubs or simple impl; no auth).
8. **Phase 6** — Finalize file layout and any renames (e.g. group API modules in an `api/` package if desired).

---

## Roadmap: Extend new UI to all AceForge features (post–Phase 7)

Once the new UI is successfully integrated and Generation + shared library/player work end-to-end, the plan is to **extend the same UI** to support the rest of AceForge’s capabilities. This is a follow-on phase, not a prerequisite for the initial port.

**Goal:** One app, one shared player and library. Every feature that produces audio (or MIDI) feeds into the same library and can be played/managed from the same player.

| Feature | Backend (existing) | New UI / API extension |
|--------|----------------------|-------------------------|
| **Generation** | `generate_ace.py`, `cdmf_generation.py` | Core of Phase 2–3 (Create panel, job status, library). |
| **Training (LoRA)** | `cdmf_training.py`, `cdmf_trainer.py` | New section or tab: dataset config, LoRA params, start/pause/cancel; outputs or checkpoints can be surfaced in library if applicable. |
| **Stem Splitting** | `cdmf_stem_splitting.py`, `cdmf_stem_splitting_bp.py` | New section: upload audio, choose 2/4/6 stem, run; results (stems) appear in **shared library** and are playable in the **same player**. |
| **Voice Cloning** | `cdmf_voice_cloning.py`, `cdmf_voice_cloning_bp.py` | New section: reference clip + text → TTS; output appears in **shared library** and **same player**. |
| **Audio to MIDI** | `cdmf_midi_generation.py`, `cdmf_midi_generation_bp.py` | New section: upload audio → MIDI; output appears in **shared library** and **same player** (MIDI playback as today). |

**Shared player approach:** The existing ace-step-ui front end has a single “Library” and “Player”. All AceForge outputs (generated tracks, stem files, voice-clone clips, MIDI files) should be represented in that same library and playable from that same player. Backend: continue using the same output/track surface (e.g. DEFAULT_OUT_DIR and TRACK_META_PATH, or a unified “tracks” API that includes all types). Front end: extend the library to show source/type (e.g. “Generation”, “Stem”, “Voice”, “MIDI”) and reuse the same player for audio and MIDI.

**Order (suggested):** After Generation + library + player are solid: add Stem Splitting and Voice Cloning (both produce audio for the shared player), then Audio to MIDI (shared player already supports MIDI in current AceForge), then Training (LoRA) as the most complex.

This roadmap is **not** part of the current implementation order (Phases 1–7). It is the intended tail once the new UI is successfully working inside AceForge.

---

## Success Criteria

- AceForge runs as a single process (Flask + pywebview); no separate JS runtime or extra ports at run time (Bun only for building the UI).
- New UI loads at `/` after `/loading` redirect; no login. User can create a generation (simple or custom), see job status, and play the result from the library.
- Build: `./build_local.sh` runs the UI build and produces an .app that serves the new UI.
- No dependency on the fspecii/ace-step-ui repository after the one-time port; all code lives under AceForge.
- All new UI/API persistence (generations, playlists, reference uploads, job history, settings) uses global app settings via **`cdmf_paths`** (e.g. on macOS: `~/Library/Application Support/AceForge/` and `~/Library/Preferences/...`), not directories inside the app or cwd.

---

## References

- ace-step-ui Express API: `server/src/routes/*.ts`, `server/src/index.ts`
- ace-step-ui frontend API client: `services/api.ts`
- AceForge paths (global app settings): **`cdmf_paths.py`** — `get_user_data_dir()`, `get_user_preferences_dir()`, `DEFAULT_OUT_DIR`, `TRACK_META_PATH`, etc.
- AceForge generation: `generate_ace.py`, `cdmf_generation.py`
- AceForge tracks: `cdmf_tracks.py`
- Exploration doc: `docs/EXPERIMENTAL_UI_EXPLORATION.md`
