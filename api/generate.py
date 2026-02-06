"""
Generation API for new UI. Maps ace-step-ui GenerationParams to generate_track_ace();
job queue stored under get_user_data_dir(). No auth. Real implementation (no mocks).
"""

import json
import logging
import threading
import time
import uuid
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file

from cdmf_paths import get_output_dir, get_user_data_dir, load_config
from cdmf_tracks import list_lora_adapters
from cdmf_generation_job import GenerationCancelled
import cdmf_state
from generate_ace import register_job_progress_callback

bp = Blueprint("api_generate", __name__)

# In-memory job store (key: jobId, value: { status, params, result?, error?, startTime, queuePosition? })
_jobs: dict = {}
_jobs_lock = threading.Lock()
# Queue order for queuePosition
_job_order: list = []
# One worker at a time (must use 'global _generation_busy' in any function that assigns to it)
_generation_busy = False
# Current running job id (for cancel); set by worker, read by cancel endpoint
_current_job_id: str | None = None
# Job ids for which cancel was requested (cooperative stop)
_cancel_requested: set = set()


def _is_cancel_requested(job_id: str) -> bool:
    with _jobs_lock:
        return job_id in _cancel_requested


def _refs_dir() -> Path:
    d = get_user_data_dir() / "references"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _jobs_path() -> Path:
    return get_user_data_dir() / "generation_jobs.json"


def _resolve_audio_url_to_path(url: str) -> str | None:
    """Convert /audio/filename or /audio/refs/filename (or full URL) to absolute path."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    # Allow full-origin URLs from the UI (e.g. http://127.0.0.1:5056/audio/refs/xxx)
    if "://" in url and "/audio/" in url:
        url = "/audio/" + url.split("/audio/", 1)[-1]
    if url.startswith("/audio/refs/"):
        name = url.replace("/audio/refs/", "", 1).split("?")[0]
        path = _refs_dir() / name
        return str(path) if path.is_file() else None
    if url.startswith("/audio/"):
        name = url.replace("/audio/", "", 1).split("?")[0]
        path = Path(get_output_dir()) / name
        return str(path) if path.is_file() else None
    return None


def _on_job_progress(
    fraction: float,
    stage: str,
    steps_current: int | None,
    steps_total: int | None,
    eta_seconds: float | None,
) -> None:
    """Update current job's progress (called from generate_ace tqdm wrapper). Uses thread-local job id so parallel workers update the correct job."""
    with _jobs_lock:
        jid = cdmf_state.get_current_generation_job_id()
        if jid is None:
            return
        job = _jobs.get(jid)
        if not job:
            return
        job["progressPercent"] = round(fraction * 100.0, 1)
        if steps_total is not None:
            job["progressSteps"] = f"{steps_current or 0}/{steps_total}"
        if eta_seconds is not None:
            job["progressEta"] = round(eta_seconds, 1)
        job["progressStage"] = stage or ""


# Register so generate_ace's tqdm wrapper reports progress into the current job
register_job_progress_callback(_on_job_progress)


def _run_generation(job_id: str) -> None:
    """Background: run generate_track_ace and update job."""
    global _generation_busy, _current_job_id
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job or job.get("status") != "queued":
            return
        job["status"] = "running"
        job["progressPercent"] = 0.0
        job["progressSteps"] = None
        job["progressEta"] = None
        job["progressStage"] = ""
        _current_job_id = job_id

    cdmf_state.set_current_generation_job_id(job_id)
    cancel_check = lambda: _is_cancel_requested(job_id)
    try:
        from generate_ace import generate_track_ace

        params = job.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        # Map ace-step-ui GenerationParams to our API (support full UI payload including duration=-1, seed=-1, bpm=0)
        custom_mode = bool(params.get("customMode", False))
        task = (params.get("taskType") or "text2music").strip().lower()
        allowed_tasks = ("text2music", "retake", "repaint", "extend", "cover", "audio2audio", "lego", "extract", "complete")
        if task not in allowed_tasks:
            task = "text2music"
        # Single style/caption field drives all text conditioning (ACE-Step caption).
        # Simple mode: songDescription. Advanced mode: style. Both can have key, time sig, vocal language.
        prompt = (params.get("style") or "").strip() if custom_mode else (params.get("songDescription") or "").strip()
        key_scale = (params.get("keyScale") or "").strip()
        time_sig = (params.get("timeSignature") or "").strip()
        vocal_lang = (params.get("vocalLanguage") or "").strip().lower()
        extra_bits = []
        if key_scale:
            extra_bits.append(f"key {key_scale}")
        if time_sig:
            extra_bits.append(f"time signature {time_sig}")
        if vocal_lang and vocal_lang not in ("unknown", ""):
            extra_bits.append(f"vocal language {vocal_lang}")
        if extra_bits:
            prompt = f"{prompt}, {', '.join(extra_bits)}" if prompt else ", ".join(extra_bits)
        # When user explicitly chose English, reinforce in caption so model conditions on it
        if vocal_lang == "en" and prompt:
            if not prompt.lower().startswith("english"):
                prompt = f"English vocals, {prompt}"
        if not prompt:
            # For cover/audio2audio, default encourages transformation while keeping structure; otherwise generic instrumental
            if task in ("cover", "audio2audio", "retake"):
                prompt = "transform style while preserving structure, re-interpret with new character"
            else:
                prompt = "instrumental background music"
        lyrics = (params.get("lyrics") or "").strip()
        instrumental = bool(params.get("instrumental", True))
        try:
            d = params.get("duration")
            duration = float(d if d is not None else 60)
        except (TypeError, ValueError):
            duration = 60
        # UI may send duration=-1 or 0; clamp to valid range (15–240s)
        duration = max(15, min(240, duration))
        # Guide: 65 steps + CFG 4.0 for best quality; low CFG reduces artifacts (see community guide).
        try:
            steps = int(params.get("inferenceSteps") or 65)
        except (TypeError, ValueError):
            steps = 65
        steps = max(1, min(100, steps))
        try:
            guidance_scale = float(params.get("guidanceScale") or 4.0)
        except (TypeError, ValueError):
            guidance_scale = 4.0
        # Base/SFT models benefit from higher guidance (docs: 5.0-9.0 typical)
        _dit = (load_config() or {}).get("ace_step_dit_model") or "turbo"
        if _dit in ("base", "sft") and guidance_scale < 5.0:
            guidance_scale = 5.0
        try:
            seed = int(params.get("seed") or 0)
        except (TypeError, ValueError):
            seed = 0
        random_seed = params.get("randomSeed", True)
        if random_seed:
            import random
            seed = random.randint(0, 2**31 - 1)
        bpm = params.get("bpm")
        if bpm is not None:
            try:
                bpm = float(bpm)
                if bpm <= 0:
                    bpm = None
            except (TypeError, ValueError):
                bpm = None
        title = (params.get("title") or "Untitled").strip() or "Track"
        reference_audio_url = (params.get("referenceAudioUrl") or params.get("reference_audio_path") or "").strip()
        source_audio_url = (params.get("sourceAudioUrl") or params.get("src_audio_path") or "").strip()
        # For cover/retake use source-first (song to cover); for style/reference use reference-first
        if task in ("cover", "retake"):
            resolved = _resolve_audio_url_to_path(source_audio_url) if source_audio_url else None
            src_audio_path = resolved or (_resolve_audio_url_to_path(reference_audio_url) if reference_audio_url else None)
        else:
            resolved = _resolve_audio_url_to_path(reference_audio_url) if reference_audio_url else None
            src_audio_path = resolved or (_resolve_audio_url_to_path(source_audio_url) if source_audio_url else None)

        # When reference/source audio is provided, enable Audio2Audio so ACE-Step uses it (cover/retake/repaint).
        # See docs/ACE-Step-INFERENCE.md: audio_cover_strength 1.0 = strong adherence; 0.5–0.8 = more caption influence.
        audio2audio_enable = bool(src_audio_path)
        ref_default = 0.8 if task in ("cover", "retake", "audio2audio") else 0.7
        ref_audio_strength = float(params.get("audioCoverStrength") or params.get("ref_audio_strength") or ref_default)
        ref_audio_strength = max(0.0, min(1.0, ref_audio_strength))

        # Repaint segment (for task=repaint); -1 means end of audio (converted to duration in generate_track_ace).
        try:
            repaint_start = float(params.get("repaintingStart") or params.get("repaint_start") or 0)
        except (TypeError, ValueError):
            repaint_start = 0.0
        try:
            repaint_end = float(params.get("repaintingEnd") or params.get("repaint_end") or -1)
        except (TypeError, ValueError):
            repaint_end = -1.0
        # -1 means "end of audio"; generate_track_ace converts to target duration

        # LoRA adapter (optional): path or folder name under custom_lora
        lora_name_or_path = (params.get("loraNameOrPath") or params.get("lora_name_or_path") or "").strip()
        try:
            lora_weight = float(params.get("loraWeight") or params.get("lora_weight") or 0.75)
        except (TypeError, ValueError):
            lora_weight = 0.75
        lora_weight = max(0.0, min(2.0, lora_weight))

        # Thinking / LM / CoT (passed through so pipeline or future LM path can use them)
        thinking = bool(params.get("thinking", False))
        use_cot_metas = bool(params.get("useCotMetas", True))
        use_cot_caption = bool(params.get("useCotCaption", True))
        use_cot_language = bool(params.get("useCotLanguage", True))
        try:
            lm_temperature = float(params.get("lmTemperature") or params.get("lm_temperature") or 0.85)
        except (TypeError, ValueError):
            lm_temperature = 0.85
        lm_temperature = max(0.0, min(2.0, lm_temperature))
        try:
            lm_cfg_scale = float(params.get("lmCfgScale") or params.get("lm_cfg_scale") or 2.0)
        except (TypeError, ValueError):
            lm_cfg_scale = 2.0
        try:
            lm_top_k = int(params.get("lmTopK") or params.get("lm_top_k") or 0)
        except (TypeError, ValueError):
            lm_top_k = 0
        try:
            lm_top_p = float(params.get("lmTopP") or params.get("lm_top_p") or 0.9)
        except (TypeError, ValueError):
            lm_top_p = 0.9
        lm_negative_prompt = (params.get("lmNegativePrompt") or params.get("lm_negative_prompt") or "NO USER INPUT").strip()

        # Log model tag for quality tracking (from job or config)
        with _jobs_lock:
            j = _jobs.get(job_id)
            dit_tag = (j.get("dit_model") or "turbo") if j else "turbo"
            lm_tag = (j.get("lm_model") or "1.7B") if j else "1.7B"
        logging.info("[API generate] Using dit=%s, lm=%s", dit_tag, lm_tag)
        if src_audio_path:
            logging.info("[API generate] Using reference audio: %s (task=%s, audio2audio=%s)", src_audio_path, task, audio2audio_enable)
        else:
            logging.info("[API generate] No reference audio; text2music only")

        out_dir_str = params.get("outputDir") or params.get("output_dir") or get_output_dir()
        out_dir = Path(out_dir_str)
        out_dir.mkdir(parents=True, exist_ok=True)

        # ACE-Step params aligned with docs/ACE-Step-INFERENCE.md:
        # caption/style, lyrics, src_audio (→ ref_audio_input for cover/retake), audio_cover_strength,
        # task, repainting_*; guidance_scale 7.0 when using reference improves adherence.
        summary = generate_track_ace(
            genre_prompt=prompt,
            lyrics=lyrics,
            instrumental=instrumental,
            negative_prompt="",
            target_seconds=duration,
            fade_in_seconds=0.5,
            fade_out_seconds=0.5,
            seed=seed,
            out_dir=out_dir,
            basename=title[:200],
            steps=steps,
            guidance_scale=guidance_scale,
            bpm=bpm,
            src_audio_path=src_audio_path,
            task=task,
            audio2audio_enable=audio2audio_enable,
            ref_audio_strength=ref_audio_strength,
            repaint_start=repaint_start,
            repaint_end=repaint_end,
            vocal_gain_db=0.0,
            instrumental_gain_db=0.0,
            lora_name_or_path=lora_name_or_path or None,
            lora_weight=lora_weight,
            cancel_check=cancel_check,
            vocal_language=vocal_lang or "",
            thinking=thinking,
            use_cot_metas=use_cot_metas,
            use_cot_caption=use_cot_caption,
            use_cot_language=use_cot_language,
            lm_temperature=lm_temperature,
            lm_cfg_scale=lm_cfg_scale,
            lm_top_k=lm_top_k,
            lm_top_p=lm_top_p,
            lm_negative_prompt=lm_negative_prompt,
        )

        wav_path = summary.get("wav_path")
        if isinstance(wav_path, Path):
            path = wav_path
        else:
            path = Path(str(wav_path))
        filename = path.name
        audio_url = f"/audio/{filename}"
        actual_seconds = float(summary.get("actual_seconds") or duration)

        with _jobs_lock:
            job = _jobs.get(job_id)
            if job:
                job["status"] = "succeeded"
                job["result"] = {
                    "audioUrls": [audio_url],
                    "duration": int(actual_seconds),
                    "bpm": bpm,
                    "keyScale": params.get("keyScale"),
                    "timeSignature": params.get("timeSignature"),
                    "status": "succeeded",
                }
    except GenerationCancelled:
        logging.info("Generation job %s cancelled by user", job_id)
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job:
                job["status"] = "cancelled"
                job["error"] = "Cancelled by user"
    except Exception as e:
        logging.exception("Generation job %s failed", job_id)
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job:
                job["status"] = "failed"
                job["error"] = str(e)
    finally:
        cdmf_state.set_current_generation_job_id(None)
        _generation_busy = False
        with _jobs_lock:
            _current_job_id = None
            _cancel_requested.discard(job_id)
        # Start next queued job (skips cancelled: they are no longer "queued")
        with _jobs_lock:
            for jid in _job_order:
                j = _jobs.get(jid)
                if j and j.get("status") == "queued":
                    threading.Thread(target=_run_generation, args=(jid,), daemon=True).start()
                    break


@bp.route("/lora_adapters", methods=["GET"])
def get_lora_adapters():
    """GET /api/generate/lora_adapters — list LoRA adapters (e.g. from Training or custom_lora)."""
    try:
        adapters = list_lora_adapters()
        return jsonify({"adapters": adapters})
    except Exception as e:
        logging.exception("[API generate] list_lora_adapters failed: %s", e)
        return jsonify({"adapters": []})


@bp.route("", methods=["POST"], strict_slashes=False)
@bp.route("/", methods=["POST"], strict_slashes=False)
def create_job():
    """POST /api/generate or /api/generate/ — enqueue generation job. Returns jobId, status, queuePosition."""
    global _generation_busy
    try:
        logging.info("[API generate] POST /api/generate received")
        raw = request.get_json(silent=True)
        # Ensure we always have a dict (get_json can return list or None; UI sends object)
        data = raw if isinstance(raw, dict) else {}
        logging.info("[API generate] Request body keys: %s", list(data.keys()) if data else [])

        if not data.get("customMode") and not data.get("songDescription"):
            return jsonify({"error": "Song description required for simple mode"}), 400
        # Custom mode: require at least one of style, lyrics, reference audio, or source audio
        if data.get("customMode"):
            style = (data.get("style") or "").strip()
            lyrics = (data.get("lyrics") or "").strip()
            ref_audio = (data.get("referenceAudioUrl") or data.get("reference_audio_path") or "").strip()
            src_audio = (data.get("sourceAudioUrl") or data.get("source_audio_path") or "").strip()
            if not style and not lyrics and not ref_audio and not src_audio:
                return jsonify({"error": "Style, lyrics, or reference/source audio required for custom mode"}), 400

        job_id = str(uuid.uuid4())
        # Store a copy so we don't keep a reference to the request body
        try:
            params_copy = dict(data)
        except (TypeError, ValueError):
            params_copy = {}
        config = load_config()
        dit_tag = config.get("ace_step_dit_model") or params_copy.get("aceStepDitModel") or "turbo"
        lm_tag = config.get("ace_step_lm") or params_copy.get("aceStepLm") or "1.7B"
        with _jobs_lock:
            _jobs[job_id] = {
                "status": "queued",
                "params": params_copy,
                "result": None,
                "error": None,
                "startTime": time.time(),
                "queuePosition": len(_job_order) + 1,
                "progressPercent": None,
                "progressSteps": None,
                "progressEta": None,
                "progressStage": None,
                "dit_model": dit_tag,
                "lm_model": lm_tag,
            }
            _job_order.append(job_id)
            pos = _jobs[job_id]["queuePosition"]

        if not _generation_busy:
            _generation_busy = True
            threading.Thread(target=_run_generation, args=(job_id,), daemon=True).start()

        logging.info("[API generate] Job %s (dit=%s, lm=%s) queued at position %s", job_id, dit_tag, lm_tag, pos)
        return jsonify({
            "jobId": job_id,
            "status": "queued",
            "queuePosition": pos,
        })
    except Exception as e:
        logging.exception("[API generate] create_job failed: %s", e)
        raise


@bp.route("/status/<job_id>", methods=["GET"])
def get_status(job_id: str):
    """GET /api/generate/status/:jobId — return job status and result when done."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    status = job.get("status", "unknown")
    progress_eta = job.get("progressEta")
    out = {
        "jobId": job_id,
        "status": status,
        "queuePosition": job.get("queuePosition"),
        "etaSeconds": int(progress_eta) if progress_eta is not None else None,
        "progressPercent": job.get("progressPercent"),
        "progressSteps": job.get("progressSteps"),
        "progressStage": job.get("progressStage"),
        "result": job.get("result"),
        "error": job.get("error"),
    }
    return jsonify(out)


@bp.route("/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id: str):
    """POST /api/generate/cancel/:jobId — cancel a queued or running generation job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        status = job.get("status", "unknown")
        if status == "queued":
            job["status"] = "cancelled"
            job["error"] = "Cancelled by user"
            return jsonify({"cancelled": True, "jobId": job_id, "message": "Job removed from queue."})
        if status == "running":
            _cancel_requested.add(job_id)
            return jsonify({"cancelled": True, "jobId": job_id, "message": "Cancel requested; generation will stop after the current step."})
        # already succeeded, failed, or cancelled
        return jsonify({"cancelled": False, "jobId": job_id, "message": f"Job already {status}."})


def _reference_tracks_meta_path() -> Path:
    """Path to reference_tracks.json (shared with api.reference_tracks)."""
    return get_user_data_dir() / "reference_tracks.json"


def _append_to_reference_library(ref_id: str, filename: str, audio_url: str, file_path: Path) -> None:
    """Add an entry to reference_tracks.json so the file appears in 'From library' and in the main player."""
    meta_path = _reference_tracks_meta_path()
    records = []
    if meta_path.is_file():
        try:
            with meta_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            records = data if isinstance(data, list) else []
        except Exception:
            pass
    records.append({
        "id": ref_id,
        "filename": filename,
        "storage_key": filename,
        "audio_url": audio_url,
        "duration": None,
        "file_size_bytes": file_path.stat().st_size if file_path.is_file() else None,
        "tags": ["uploaded"],
    })
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


@bp.route("/upload-audio", methods=["POST"])
def upload_audio():
    """POST /api/generate/upload-audio — multipart file; save to references dir and add to library."""
    if "audio" not in request.files:
        return jsonify({"error": "Audio file is required"}), 400
    f = request.files["audio"]
    if not f.filename:
        return jsonify({"error": "No filename"}), 400
    ext = Path(f.filename).suffix.lower() or ".audio"
    ref_id = str(uuid.uuid4())
    name = f"{ref_id}{ext}"
    path = _refs_dir() / name
    f.save(str(path))
    url = f"/audio/refs/{name}"
    _append_to_reference_library(ref_id, name, url, path)
    return jsonify({"url": url, "key": name})


@bp.route("/audio", methods=["GET"])
def get_audio():
    """GET /api/generate/audio?path=... — serve file from output or references."""
    path_arg = request.args.get("path")
    if not path_arg:
        return jsonify({"error": "Path required"}), 400
    path_arg = path_arg.strip()
    if ".." in path_arg or path_arg.startswith("/"):
        path_arg = path_arg.lstrip("/")
    if path_arg.startswith("refs/"):
        local = _refs_dir() / path_arg.replace("refs/", "", 1)
    else:
        local = Path(get_output_dir()) / path_arg
    if not local.is_file():
        return jsonify({"error": "File not found"}), 404
    return send_file(local, as_attachment=False, download_name=local.name)


@bp.route("/history", methods=["GET"])
def get_history():
    """GET /api/generate/history — last 50 jobs."""
    with _jobs_lock:
        order = _job_order[-50:]
        order.reverse()
        jobs = [{"id": jid, **_jobs.get(jid, {})} for jid in order if jid in _jobs]
    return jsonify({"jobs": jobs})


@bp.route("/endpoints", methods=["GET"])
def get_endpoints():
    """GET /api/generate/endpoints."""
    return jsonify({"endpoints": {"provider": "acestep-local", "endpoint": "local"}})


@bp.route("/health", methods=["GET"])
def get_health():
    """GET /api/generate/health."""
    return jsonify({"healthy": True})


@bp.route("/debug/<task_id>", methods=["GET"])
def get_debug(task_id: str):
    """GET /api/generate/debug/:taskId — raw job info."""
    with _jobs_lock:
        job = _jobs.get(task_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"rawResponse": job})


@bp.route("/format", methods=["POST"])
def format_input():
    """POST /api/generate/format — stub; return same payload."""
    data = request.get_json(silent=True) or {}
    return jsonify({
        "success": True,
        "caption": data.get("caption"),
        "lyrics": data.get("lyrics"),
        "bpm": data.get("bpm"),
        "duration": data.get("duration"),
        "key_scale": data.get("keyScale"),
        "time_signature": data.get("timeSignature"),
    })
