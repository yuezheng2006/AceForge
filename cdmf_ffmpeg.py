# cdmf_ffmpeg.py
# Ensure pydub can find ffprobe/ffmpeg when run from a .app or environment with minimal PATH.
# Prepends common macOS Homebrew paths so pydub.utils.which("ffprobe") and which("ffmpeg") succeed.

from __future__ import annotations

import os
from pathlib import Path

_ffmpeg_path_ensured = False

FFMPEG_INSTALL_HINT = (
    "ffprobe/ffmpeg not found. Voice cloning and audio conversion require ffmpeg. "
    "Install with: brew install ffmpeg"
)


def is_ffmpeg_not_found_error(e: BaseException) -> bool:
    """True if the exception indicates ffprobe/ffmpeg could not be found (e.g. [Errno 2] No such file or directory: 'ffprobe')."""
    msg = str(e)
    lower = msg.lower()
    if isinstance(e, (FileNotFoundError, OSError)) and getattr(e, "errno", None) == 2:
        return "ffprobe" in lower or "ffmpeg" in lower
    return ("ffprobe" in lower or "ffmpeg" in lower) and (
        "no such file" in lower or "errno 2" in lower or "[errno 2]" in lower
    )


def ensure_ffmpeg_in_path() -> None:
    """
    Prepend /opt/homebrew/bin and /usr/local/bin to PATH if they exist.
    pydub uses `which("ffprobe")` / `which("ffmpeg")` which only search PATH.
    When AceForge runs as a .app (or from a launcher with minimal PATH), ffprobe
    is not found even when installed via `brew install ffmpeg`. Idempotent.
    """
    global _ffmpeg_path_ensured
    if _ffmpeg_path_ensured:
        return
    to_prepend = [d for d in ("/opt/homebrew/bin", "/usr/local/bin") if Path(d).is_dir()]
    if to_prepend:
        os.environ["PATH"] = os.pathsep.join(to_prepend) + os.pathsep + os.environ.get("PATH", "")
    _ffmpeg_path_ensured = True
