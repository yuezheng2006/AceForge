# Experimental UI: ace-step-ui Exploration

**Branch:** `experimental-ui`  
**Goal:** Evaluate [fspecii/ace-step-ui](https://github.com/fspecii/ace-step-ui) as a replacement/alternative UI for AceForge, retain our existing ACE-Step pipeline and add Voice Cloning, Stem Splitting, etc. later. Target: **macOS Apple Silicon only**, project remains **standalone** (no runtime dependency on external UI repo).

---

## 1. Clone Location and Setup

- **Temp clone (exploration):** Sibling directory to AceForge  
  `../ace-step-ui` → full path: `/Users/ethehot/Documents/git/ace-step-ui`  
  (Not committed inside AceForge; used only for inspection and possible copy of source.)

- **To run ace-step-ui locally (for tryout):**
  ```bash
  cd /path/to/ace-step-ui
  ./setup.sh   # or setup.bat on Windows
  # Set ACESTEP_PATH to ACE-Step-1.5 dir (or use their default sibling)
  ./start.sh   # Backend 3001 + Frontend 3000
  ```
  Open http://localhost:3000. Backend proxies `/api` and `/audio` to port 3001.

---

## 2. ace-step-ui Architecture Summary

| Layer        | Tech              | Role |
|-------------|-------------------|------|
| **Frontend**| React 18, TypeScript, Vite, TailwindCSS | SPA: Create, Library, Player, Playlists, Settings, Search |
| **Backend** | Express (Node), SQLite (better-sqlite3) | Auth, songs DB, playlists, generation job queue, audio storage, proxies |
| **ACE-Step**| External API or Python spawn | Music generation; UI expects **ACE-Step 1.5**-style HTTP API |

- **Frontend** talks only to the **Express server** (relative `API_BASE = ''`; Vite dev proxy forwards `/api`, `/audio`, `/editor`, `/blog` to backend).
- **Express** either:
  - Calls an **external ACE-Step API** at `ACESTEP_API_URL` (e.g. `http://localhost:8001`), or
  - Falls back to **spawning Python** from an ACE-Step-1.5 directory using `server/scripts/simple_generate.py`.

---

## 3. ACE-Step API Contract (What ace-step-ui Expects)

When the Express server uses “API mode”, it expects the following from the ACE-Step service:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Availability; response with `status === 'ok'` or `healthy === true` |
| `/release_task` | POST | Submit generation. Body: `prompt`, `lyrics`, `audio_duration`, `batch_size`, `inference_steps`, `guidance_scale`, `audio_format`, `vocal_language`, `use_random_seed`, `seed`, optional `bpm`, `key_scale`, `time_signature`, `reference_audio_path`, `src_audio_path`, `task_type`, repainting, thinking/LLM params, etc. |
| `/query_result` | POST | Poll with `{ task_id_list: [taskId] }`. Response: per-task `status` (0=processing, 1=done, 2=failed), `result` (e.g. array of `{ file }` paths or similar). |
| `/v1/audio?path=...` or path like `/v1/audio/...` | GET | Download generated audio file by path returned in result. |

- **Generation params** (from `server/src/services/acestep.ts` and Express `generate.ts`) include: simple vs custom mode, style/lyrics, instrumental, duration, BPM, key/time signature, inference steps, guidance scale, batch size, seed, thinking/LLM options, reference/source audio paths, repainting, audio cover strength, etc.
- **Our AceForge** uses the **original ACE-Step** pipeline in-process via `generate_ace.generate_track_ace()` and does **not** expose this HTTP API today.

---

## 4. Express API Surface (What the React App Calls)

The React app uses these backend routes (from `services/api.ts` and server routes):

- **Auth:** `/api/auth/auto`, `/api/auth/setup`, `/api/auth/me`, `/api/auth/logout`, `/api/auth/refresh`, `/api/auth/username` (PATCH).
- **Generation:**  
  `POST /api/generate` (body = GenerationParams),  
  `GET /api/generate/status/:jobId`,  
  `POST /api/generate/upload-audio`,  
  `GET /api/generate/audio?path=...`,  
  `GET /api/generate/history`,  
  `GET /api/generate/endpoints`,  
  `GET /api/generate/health`,  
  `GET /api/generate/debug/:taskId`,  
  `POST /api/generate/format` (LLM-style caption/lyrics formatting).
- **Songs:** CRUD, likes, privacy, play count, comments (e.g. `/api/songs`, `/api/songs/:id`, `/api/songs/liked/list`, etc.).
- **Playlists:** create, list, get, add/remove song, update, delete.
- **Users:** profile, public songs/playlists, featured, avatar/banner upload, follow.
- **Search:** `/api/search?q=...&type=...`
- **Contact:** `POST /api/contact`
- **Reference tracks:** `/api/reference-tracks`
- **Static:** `/audio/*` (generated files), `/editor` (AudioMass), `/demucs-web` (stem extraction).

All generation goes through Express; Express then calls the ACE-Step API (or Python script). The React app never talks to the ACE-Step API directly.

---

## 5. AceForge vs ace-step-ui (Relevant Differences)

| Aspect | AceForge (current) | ace-step-ui |
|--------|---------------------|-------------|
| **UI** | Single Jinja template + vanilla JS (cdmf_*.js), Flask serves HTML + static | React SPA, Vite build; dev proxy to Express |
| **Backend** | Flask (Waitress), port 5056 | Express, port 3001 |
| **ACE-Step** | In-process Python `generate_track_ace()` | External HTTP API (or Python spawn from ACE-Step-1.5) |
| **Auth** | None | JWT, SQLite users, username setup |
| **Songs/tracks** | File-based list from output dir, track metadata in JSON | SQLite `songs` table, storage abstraction |
| **Extra features** | Voice cloning (XTTS), Stem splitting (Demucs), MIDI (basic-pitch), LoRA training, presets | Stem extraction (Demucs web), AudioMass editor, Pexels video, playlists, likes |
| **Platform** | macOS .app (PyInstaller + pywebview) | Cross-platform Node + Python (ACE-Step 1.5) |

Important: ace-step-ui targets **ACE-Step 1.5** (separate repo/API). AceForge uses the **original ACE-Step** pipeline. Parameter names and API shape differ; an adapter would be required to map between them.

---

## 6. Integration Options for Standalone macOS

### Option A: Flask as “ACE-Step API” + keep Node (not standalone)

- Implement on Flask the 4 endpoints: `/health`, `/release_task`, `/query_result`, `/v1/audio`.
- Map `release_task` → our `generate_track_ace()` (and job store); `query_result` → our job state; `v1/audio` → serve from our output dir.
- Run ace-step-ui’s Express with `ACESTEP_API_URL=http://127.0.0.1:5056`.
- **Downside:** Requires Node at runtime for Express (auth, songs, playlists). Not a single-binary, standalone app.

### Option B: Embed React build + Flask compatibility API (recommended for standalone)

- Copy or submodule the **React source** into AceForge (e.g. `ui/` or `ace_step_ui/`).
- Build the React app with Vite (`npm run build`) so output is static files (e.g. `dist/`).
- Serve that build from Flask (e.g. `/` or `/app`), and add **Flask routes** that implement the subset of the Express API the React app needs:
  - **Auth:** e.g. `/api/auth/auto` (return single local user + token), `/api/auth/setup`, `/api/auth/me` (optional).
  - **Generate:** `POST /api/generate` → enqueue and call our `generate_track_ace()`; `GET /api/generate/status/:jobId` → return job status and result (audio URLs pointing at our track serving).
  - **Songs:** map to our tracks (list from output dir + metadata); implement GET list, GET one, PATCH, DELETE, and optionally “create” when generation finishes.
  - **Playlists:** optional; can start with “no playlists” and stub endpoints.
  - **Upload audio:** for reference/source audio, store under our output or a temp dir and return a path/URL the adapter understands.
  - **Format:** optional; can stub or call our lyrics/prompt helper if we have one.
- **Audio:** serve generated files under `/audio/` or same scheme as current track serving.
- **Editor / Demucs-web:** either serve static from Flask or keep as external; can add later.
- **Result:** Single process (Flask + pywebview), no Node at runtime, project stays standalone. We keep our ACE-Step pipeline and add Voice Cloning, Stem Splitting, MIDI, etc. as extra tabs or routes later.

### Option C: Run both servers (dev only)

- Run Flask (5056) and Express (3001); point Express at Flask for “ACE-Step API”.
- Good for quick UI tryout; not suitable for shipped .app without bundling Node.

---

## 7. Recommendation and Next Steps

- **Short term:** Keep the temp clone at `../ace-step-ui` for reference. On `experimental-ui` branch, decide whether to:
  - **Option B (recommended):** Add a directory in AceForge (e.g. `ui/`) containing the React source (copy or submodule) and a small build script (e.g. `npm ci && npm run build`). Add a Flask blueprint (or set of routes) that implements the minimal `/api` surface above and serves the built static files. Use an **adapter** in Flask that maps `release_task`-style params to our `generate_track_ace()` and our job/result shape.
- **Parameter mapping:** Our pipeline uses e.g. `prompt`, `lyrics`, `instrumental`, `target_seconds`, `steps`, `guidance_scale`, `seed`, `vocal_gain_db`, `instrumental_gain_db`, reference audio, LoRA. The adapter must map from ace-step-ui’s `GenerationParams` (style, lyrics, duration, inferenceSteps, guidanceScale, etc.) to our Python API and back (e.g. result audio URLs).
- **Later:** Add Voice Cloning, Stem Splitting, MIDI as additional UI sections or tabs, backed by existing AceForge Python modules; either by extending the React app or keeping a hybrid (e.g. React for “Create” + Library, Flask-rendered pages for tools).
- **macOS / Metal:** No change to current target; all heavy work remains in Python (ACE-Step, Demucs, etc.). React is front-end only.

---

## 8. Key Files in ace-step-ui (for reference)

| Path | Purpose |
|------|--------|
| `server/src/services/acestep.ts` | ACE-Step API client: `isApiAvailable()`, `submitToApi()`, `pollApiResult()`, `downloadAudioFromApi()`; fallback Python spawn; `GenerationParams` and job queue |
| `server/src/routes/generate.ts` | Express generate routes: POST create job, GET status, upload-audio, format, history, health, debug |
| `server/src/config/index.ts` | `ACESTEP_API_URL`, port, DB path, storage |
| `services/api.ts` | Frontend API client: auth, songs, generate, playlists, users, search |
| `components/CreatePanel.tsx` | Main generation form (simple/custom mode, style, lyrics, params) |
| `vite.config.ts` | Dev proxy: `/api`, `/audio`, `/editor` → 3001 |

---

**Implementation plan:** See **`docs/NEW_UI_IMPLEMENTATION_PLAN.md`** for the phased plan to port the UI in-tree, add Flask API compatibility, and integrate the UI build into local and PyInstaller builds (Option B, standalone, single port).

---

*Document created on branch `experimental-ui`. Clone used: [fspecii/ace-step-ui](https://github.com/fspecii/ace-step-ui) (sibling directory).*
