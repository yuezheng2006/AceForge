# New UI API Audit — AceForge Flask vs UI (ace-step-ui contract)

This document lists **every API call the React UI makes** and the **Flask backend route** that handles it. All routes must support the exact path and method the UI uses (no trailing slash required).

## Summary of fixes applied

- **POST /api/generate** was returning **405 Method Not Allowed** because the blueprint only registered `"/"` → `/api/generate/` (trailing slash). The UI sends `POST /api/generate`. Fixed by adding `@bp.route("", methods=["POST"], strict_slashes=False)` in `api/generate.py`.
- **Auth stubs** added so no UI path 404s: `GET /api/auth/me`, `POST /api/auth/setup`, `POST /api/auth/logout`, `POST /api/auth/refresh`, `PATCH /api/auth/username`. All return local user or success.
- **GET /api/search** added in `api/search.py` (stub: searches local tracks by title/style, returns `{ songs, creators, playlists }`).
- **Reference-tracks** response shape aligned with UI: GET returns `{ tracks: [...] }`, POST returns `{ track: { id, audio_url, ... }, url, key }`.
- **Index routes** (no trailing slash): added `""` + `strict_slashes=False` for generate, playlists (GET/POST), songs (GET/POST), contact (POST), reference-tracks (GET/POST), search (GET).

---

## 1. Auth — `ui/services/api.ts` → `api/auth.py`

| UI call | Method | Backend route | Status |
|--------|--------|----------------|--------|
| `authApi.auto()` | GET | `/api/auth/auto` | ✅ Returns `{ user, token: null }` |
| `authApi.setup(username)` | POST | `/api/auth/setup` | ✅ Stub: same as auto |
| `authApi.me(token)` | GET | `/api/auth/me` | ✅ Stub: `{ user }` |
| `authApi.logout()` | POST | `/api/auth/logout` | ✅ Stub: `{ success: true }` |
| `authApi.refresh(token)` | POST | `/api/auth/refresh` | ✅ Stub: same as auto |
| `authApi.updateUsername(username, token)` | PATCH | `/api/auth/username` | ✅ Stub: `{ user, token }` |

---

## 2. Songs — `ui/services/api.ts` → `api/songs.py`

| UI call | Method | Backend route | Status |
|--------|--------|----------------|--------|
| `songsApi.getMySongs(token)` | GET | `/api/songs` | ✅ `""` + `"/"` |
| `songsApi.getPublicSongs(limit, offset)` | GET | `/api/songs/public?limit=&offset=` | ✅ |
| `songsApi.getFeaturedSongs()` | GET | `/api/songs/public/featured` | ✅ |
| `songsApi.getSong(id, token)` | GET | `/api/songs/:id` | ✅ |
| `songsApi.getSongFull(id, token)` | GET | `/api/songs/:id/full` | ✅ |
| `songsApi.createSong(song, token)` | POST | `/api/songs` | ✅ `""` + `"/"` |
| `songsApi.updateSong(id, updates, token)` | PATCH | `/api/songs/:id` | ✅ |
| `songsApi.deleteSong(id, token)` | DELETE | `/api/songs/:id` | ✅ |
| `songsApi.toggleLike(id, token)` | POST | `/api/songs/:id/like` | ✅ Stub |
| `songsApi.getLikedSongs(token)` | GET | `/api/songs/liked/list` | ✅ |
| `songsApi.updatePrivacy(id, isPublic, token)` | PATCH | `/api/songs/:id/privacy` | ✅ Stub |
| `songsApi.recordPlay(id, token)` | POST | `/api/songs/:id/play` | ✅ Stub |
| `songsApi.getComments(id, token)` | GET | `/api/songs/:id/comments` | ✅ Stub |
| `songsApi.addComment(id, content, token)` | POST | `/api/songs/:id/comments` | ✅ Stub |
| `songsApi.deleteComment(commentId, token)` | DELETE | `/api/songs/comments/:commentId` | ✅ Stub |

---

## 3. Generate — `ui/services/api.ts` → `api/generate.py`

| UI call | Method | Backend route | Status |
|--------|--------|----------------|--------|
| `generateApi.startGeneration(params, token)` | POST | `/api/generate` | ✅ **Fixed** `""` + `"/"` |
| `generateApi.getStatus(jobId, token)` | GET | `/api/generate/status/:jobId` | ✅ |
| `generateApi.getHistory(token)` | GET | `/api/generate/history` | ✅ |
| `generateApi.uploadAudio(file, token)` | POST | `/api/generate/upload-audio` | ✅ |
| `generateApi.formatInput(params, token)` | POST | `/api/generate/format` | ✅ Stub |
| (audio playback) | GET | `/api/generate/audio?path=...` or `/audio/:filename` | ✅ App-level `/audio/<path>` |

---

## 4. Playlists — `ui/services/api.ts` → `api/playlists.py`

| UI call | Method | Backend route | Status |
|--------|--------|----------------|--------|
| `playlistsApi.getMyPlaylists(token)` | GET | `/api/playlists` | ✅ `""` + `"/"` |
| `playlistsApi.create(name, description, isPublic, token)` | POST | `/api/playlists` | ✅ `""` + `"/"` |
| `playlistsApi.getPlaylist(id, token)` | GET | `/api/playlists/:id` | ✅ |
| `playlistsApi.getFeaturedPlaylists()` | GET | `/api/playlists/public/featured` | ✅ |
| `playlistsApi.addSong(playlistId, songId, token)` | POST | `/api/playlists/:playlistId/songs` body `{ songId }` | ✅ |
| `playlistsApi.removeSong(playlistId, songId, token)` | DELETE | `/api/playlists/:playlistId/songs/:songId` | ✅ |
| `playlistsApi.update(id, updates, token)` | PATCH | `/api/playlists/:id` | ✅ |
| `playlistsApi.delete(id, token)` | DELETE | `/api/playlists/:id` | ✅ |

---

## 5. Users — `ui/services/api.ts` → `api/users.py`

| UI call | Method | Backend route | Status |
|--------|--------|----------------|--------|
| `usersApi.getProfile(username, token)` | GET | `/api/users/:username` | ✅ |
| `usersApi.getPublicSongs(username)` | GET | `/api/users/:username/songs` | ✅ |
| `usersApi.getPublicPlaylists(username)` | GET | `/api/users/:username/playlists` | ✅ |
| `usersApi.getFeaturedCreators()` | GET | `/api/users/public/featured` | ✅ |
| `usersApi.updateProfile(updates, token)` | PATCH | `/api/users/me` | ✅ Stub |
| `usersApi.uploadAvatar(file, token)` | POST | `/api/users/me/avatar` | ✅ Stub |
| `usersApi.uploadBanner(file, token)` | POST | `/api/users/me/banner` | ✅ Stub |
| `usersApi.follow(username, token)` | POST | `/api/users/:username/follow` | ✅ Stub |
| `usersApi.getFollowers(username)` | GET | `/api/users/:username/followers` | ✅ Stub |
| `usersApi.getFollowing(username)` | GET | `/api/users/:username/following` | ✅ Stub |
| `usersApi.getStats(username, token)` | GET | `/api/users/:username/stats` | ✅ Stub |

---

## 6. Reference tracks — `ui/components/CreatePanel.tsx` (fetch) → `api/reference_tracks.py`

| UI call | Method | Backend route | Status |
|--------|--------|----------------|--------|
| `fetch('/api/reference-tracks')` | GET | `/api/reference-tracks` | ✅ Returns `{ tracks: [...] }` |
| `fetch('/api/reference-tracks', { method: 'POST', body: formData })` | POST | `/api/reference-tracks` | ✅ Returns `{ track, url, key }` |
| `fetch('/api/reference-tracks/:id', { method: 'DELETE' })` | DELETE | `/api/reference-tracks/:id` | ✅ |

CreatePanel also uses `PATCH /api/reference-tracks/:id` (tags) — ✅ implemented.

---

## 7. Search — `ui/services/api.ts` → `api/search.py`

| UI call | Method | Backend route | Status |
|--------|--------|----------------|--------|
| `searchApi.search(query, type)` | GET | `/api/search?q=...&type=...` | ✅ New; searches local tracks |

---

## 8. Contact — `ui/services/api.ts` → `api/contact.py`

| UI call | Method | Backend route | Status |
|--------|--------|----------------|--------|
| `contactApi.submit(data)` | POST | `/api/contact` | ✅ `""` + `"/"` stub |

---

## 9. Optional / not implemented

| UI usage | Method | Path | Note |
|----------|--------|------|------|
| VideoGeneratorModal (proxy image) | GET | `/api/proxy/image?url=...` | Not in Flask; optional feature |
| VideoGeneratorModal (Pexels) | GET | `/api/pexels/photos?query=...`, `/api/pexels/videos?query=...` | Not in Flask; optional |

---

## Running the audit tests

```bash
pytest tests/test_new_ui_api.py -v
```

The test `test_generate_create_job_no_trailing_slash` asserts that `POST /api/generate` (no trailing slash) returns 200.
