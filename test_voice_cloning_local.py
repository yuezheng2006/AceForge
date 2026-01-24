#!/usr/bin/env python3
"""
Local test for voice cloning path. Run with:
  venv_build/bin/python test_voice_cloning_local.py

Reproduces the frozen-app flow to catch errors (e.g. EOF when reading a line)
before rebuilding. Simulates GUI: stdin from /dev/null so input() gets EOF.
"""
import os
import sys

# Simulate frozen app env
os.environ.setdefault("TORCH_JIT", "0")
os.environ.setdefault("PYTORCH_JIT", "0")
# Skip TTS Coqui TOS prompt (uses input() -> EOF in GUI)
os.environ["COQUI_TOS_AGREED"] = "1"

# Simulate GUI: no stdin (EOF when reading a line)
devnull = os.open(os.devnull, os.O_RDONLY)
os.dup2(devnull, 0)
os.close(devnull)

def main():
    print("[test] 1. Importing cdmf_voice_cloning...")
    from cdmf_voice_cloning import get_voice_cloner

    print("[test] 2. get_voice_cloner()...")
    cloner = get_voice_cloner()

    # Need a real wav for speaker_wav. XTTS needs non-silence (Max/min != 0) and sufficient length.
    import tempfile
    import wave
    import struct
    from pathlib import Path

    # 1s 16kHz mono 16-bit WAV with tone (XTTS rejects silence)
    sr, duration = 16000, 1.0
    n = int(sr * duration)
    wav_path = tempfile.mktemp(suffix=".wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        for i in range(n):
            v = int(8000 * (0.3 * (i / sr) % 1.0))  # simple tone, not silence
            w.writeframes(struct.pack("<h", max(-32768, min(32767, v))))
    speaker_wav = wav_path

    out = Path(tempfile.gettempdir()) / "test_voice_clone_out.wav"
    try:
        print("[test] 3. clone_voice(text=..., speaker_wav=..., output_path=...)...")
        p = cloner.clone_voice(
            text="Hello.",
            speaker_wav=speaker_wav,
            language="en",
            output_path=str(out),
            device_preference="cpu",
        )
        print("[test] OK:", p)
    except Exception as e:
        import traceback
        print("[test] FAIL:", e)
        traceback.print_exc()
        sys.exit(1)
    finally:
        os.unlink(speaker_wav)

if __name__ == "__main__":
    main()
