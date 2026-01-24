# cdmf_voice_cloning_bp.py
# Flask blueprint for voice cloning UI

from __future__ import annotations

import time
import traceback
import logging
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, request, render_template_string, jsonify
from werkzeug.utils import secure_filename

import cdmf_tracks
from cdmf_paths import DEFAULT_OUT_DIR, APP_VERSION
from cdmf_voice_cloning import get_voice_cloner

logger = logging.getLogger(__name__)


def create_voice_cloning_blueprint(html_template: str) -> Blueprint:
    """
    Create a blueprint for voice cloning routes.
    
    Routes:
      * "/voice_clone" -> Voice cloning endpoint
    """
    bp = Blueprint("cdmf_voice_cloning", __name__)
    
    # Default parameters
    DEFAULT_TEMPERATURE = 0.75
    DEFAULT_LENGTH_PENALTY = 1.0
    DEFAULT_REPETITION_PENALTY = 5.0
    DEFAULT_TOP_K = 50
    DEFAULT_TOP_P = 0.85
    DEFAULT_SPEED = 1.0
    DEFAULT_LANGUAGE = "en"
    DEFAULT_ENABLE_TEXT_SPLITTING = True
    
    @bp.route("/voice_clone", methods=["POST"])
    def voice_clone():
        """Handle voice cloning request."""
        try:
            # Get form data
            text = request.form.get("text", "").strip()
            if not text:
                return jsonify({
                    "error": True,
                    "message": "Text is required for voice cloning."
                }), 400
            
            # Get reference audio file
            if "speaker_wav" not in request.files:
                return jsonify({
                    "error": True,
                    "message": "Reference audio file is required."
                }), 400
            
            speaker_file = request.files["speaker_wav"]
            if speaker_file.filename == "":
                return jsonify({
                    "error": True,
                    "message": "No file selected."
                }), 400
            
            # Validate file extension
            filename = secure_filename(speaker_file.filename)
            if not filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac')):
                return jsonify({
                    "error": True,
                    "message": "Invalid file format. Please use MP3, WAV, M4A, or FLAC."
                }), 400
            
            # Get output filename (default MP3 256k for cloned voices)
            output_filename = request.form.get("output_filename", "").strip()
            if not output_filename:
                output_filename = "voice_clone_output"
            if not output_filename.lower().endswith((".wav", ".mp3")):
                output_filename += ".mp3"
            
            # Get output directory (same as music generation)
            out_dir = request.form.get("out_dir", DEFAULT_OUT_DIR)
            out_dir_path = Path(out_dir)
            out_dir_path.mkdir(parents=True, exist_ok=True)
            
            # Save uploaded reference audio temporarily
            temp_ref_path = out_dir_path / f"_temp_ref_{filename}"
            speaker_file.save(str(temp_ref_path))
            
            try:
                # Get parameters from form
                language = request.form.get("language", DEFAULT_LANGUAGE)
                device_preference = request.form.get("device_preference", "auto")  # "mps", "cpu", or "auto"
                temperature = float(request.form.get("temperature", DEFAULT_TEMPERATURE))
                length_penalty = float(request.form.get("length_penalty", DEFAULT_LENGTH_PENALTY))
                repetition_penalty = float(request.form.get("repetition_penalty", DEFAULT_REPETITION_PENALTY))
                top_k = int(request.form.get("top_k", DEFAULT_TOP_K))
                top_p = float(request.form.get("top_p", DEFAULT_TOP_P))
                speed = float(request.form.get("speed", DEFAULT_SPEED))
                enable_text_splitting = request.form.get("enable_text_splitting", "true").lower() == "true"
                
                # Generate output path
                output_path = out_dir_path / output_filename
                
                # Perform voice cloning
                logger.info(f"[Voice Cloning] Starting: text='{text[:50]}...', language={language}, output={output_path}")
                
                cloner = get_voice_cloner()
                result_path = cloner.clone_voice(
                    text=text,
                    speaker_wav=str(temp_ref_path),
                    language=language,
                    output_path=str(output_path),
                    device_preference=device_preference,
                    temperature=temperature,
                    length_penalty=length_penalty,
                    repetition_penalty=repetition_penalty,
                    top_k=top_k,
                    top_p=top_p,
                    speed=speed,
                    enable_text_splitting=enable_text_splitting,
                )
                
                # Clean up temporary reference file
                if temp_ref_path.exists():
                    temp_ref_path.unlink()

                # Save track metadata (seconds, generator, voice clone params) for Music Player
                # and "copy generation settings back to form"
                try:
                    from cdmf_ffmpeg import ensure_ffmpeg_in_path

                    ensure_ffmpeg_in_path()

                    from pydub import AudioSegment

                    final_name = Path(result_path).name
                    dur = len(AudioSegment.from_file(str(result_path))) / 1000.0
                    track_meta = cdmf_tracks.load_track_meta()
                    entry = track_meta.get(final_name, {})
                    if "favorite" not in entry:
                        entry["favorite"] = False
                    entry["seconds"] = dur
                    entry["created"] = time.time()
                    entry["generator"] = "voice_clone"
                    entry["basename"] = Path(final_name).stem
                    entry["text"] = text
                    entry["language"] = language
                    entry["temperature"] = temperature
                    entry["length_penalty"] = length_penalty
                    entry["repetition_penalty"] = repetition_penalty
                    entry["top_k"] = top_k
                    entry["top_p"] = top_p
                    entry["speed"] = speed
                    entry["enable_text_splitting"] = enable_text_splitting
                    entry["device_preference"] = device_preference
                    entry["out_dir"] = str(out_dir_path)
                    track_meta[final_name] = entry
                    cdmf_tracks.save_track_meta(track_meta)
                except Exception as e:
                    from cdmf_ffmpeg import FFMPEG_INSTALL_HINT, is_ffmpeg_not_found_error

                    if is_ffmpeg_not_found_error(e):
                        logger.warning("[Voice Cloning] Failed to save track metadata: %s", FFMPEG_INSTALL_HINT)
                    else:
                        logger.warning("[Voice Cloning] Failed to save track metadata: %s", e)

                # Get updated track list
                tracks = cdmf_tracks.list_music_files()

                logger.info(f"[Voice Cloning] Success: {result_path}")
                
                return jsonify({
                    "error": False,
                    "message": f"Voice cloning completed: {output_filename}",
                    "output_path": str(result_path),
                    "output_filename": output_filename,
                    "tracks": tracks,
                })
                
            except Exception as e:
                # Clean up temporary file on error
                if temp_ref_path.exists():
                    temp_ref_path.unlink()
                raise
                
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[Voice Cloning] Error: {e}\n{tb}")
            return jsonify({
                "error": True,
                "message": f"Voice cloning failed: {str(e)}",
                "details": tb,
            }), 500
    
    return bp
