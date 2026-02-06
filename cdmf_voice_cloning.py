# cdmf_voice_cloning.py
# Voice cloning module using XTTS v2
#
# Mac Environment Setup Requirements:
# 1. Install Homebrew dependencies:
#    brew install ffmpeg mecab espeak-ng
# 2. Install PyTorch and TTS:
#    pip install torch torchaudio TTS
#
# Performance Notes:
# - First generation is slow (compiles execution graph), subsequent generations are faster
# - On M2/M3 chips, CPU can be surprisingly fast for this model
# - If MPS produces "muffled" audio or artifacts (rare bug on Ventura/Sonoma), use CPU instead
# - On macOS we use TTS 0.21.x + CPU-only (xtts2-ui style) to avoid TorchScript "can't get source" in frozen apps

from __future__ import annotations

import os
import platform
import tempfile
# Reduce TorchScript JIT use (helps in PyInstaller bundles where .py source may be inaccessible)
if "TORCH_JIT" not in os.environ:
    os.environ["TORCH_JIT"] = "0"
if "PYTORCH_JIT" not in os.environ:
    os.environ["PYTORCH_JIT"] = "0"

import torch
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Callable
import logging

logger = logging.getLogger(__name__)

# CRITICAL for Apple Silicon: This allows the M-series GPU to hand off 
# unsupported operations to the CPU instead of crashing.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")


class VoiceCloner:
    """
    Voice cloning using XTTS v2.
    On macOS: CPU only (xtts2-ui–style). Else: CUDA if available, else CPU.
    """
    
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        """
        Initialize the XTTS-v2 model.
        
        Args:
            model_name: TTS model identifier
        """
        self.model_name = model_name
        self.tts = None
        self.device = None
        self._initialized = False
        self._device_preference = None  # Will be set on first use
        
    def _initialize(self, device_preference: str = "auto"):
        """
        Lazy initialization of the TTS model.
        
        Args:
            device_preference: Device to use ("mps", "cpu", or "auto")
                - "mps": Force Apple Silicon GPU (MPS)
                - "cpu": Force CPU
                - "auto": Auto-detect (MPS if available, else CPU)
        """
        if self._initialized and self._device_preference == device_preference:
            return

        # Avoid "EOF when reading a line": in GUI/frozen app stdin is closed; input() in TTS
        # (TOS prompt in manage.ask_tos) or deps (nltk, datasets) raises EOFError.
        os.environ.setdefault("COQUI_TOS_AGREED", "1")  # skip TTS Coqui TOS interactive prompt
        import builtins
        _orig_input = builtins.input
        def _safe_input(prompt=""):
            try:
                return _orig_input(prompt)
            except EOFError:
                return "y"  # safe default for TOS or similar prompts
        builtins.input = _safe_input

        # get_source_lines_and_file is patched in aceforge_app (early) for frozen builds.
        # No-op torch.jit.script so @torch.jit.script in TTS (e.g. wavenet) stays plain Python.
        def _noop_jit_script(fn):
            return fn
        torch.jit.script = _noop_jit_script
        logger.info("[VoiceCloner] Patched torch.jit.script to no-op before TTS import.")

        # Second layer: patch torch._sources.get_source_lines_and_file to avoid
        # "could not get source code" when it catches OSError from inspect in frozen bundles.
        try:
            import torch._sources as _ts
            if hasattr(_ts, "get_source_lines_and_file"):
                _orig_gs = _ts.get_source_lines_and_file

                def _frozen_get_source_lines_and_file(obj, error_msg=None):
                    try:
                        return _orig_gs(obj, error_msg)
                    except Exception:
                        return (["def _frozen(*a,**k):\n", "    pass\n"], 1, "<frozen>")

                _ts.get_source_lines_and_file = _frozen_get_source_lines_and_file
                logger.info("[VoiceCloner] Patched torch._sources.get_source_lines_and_file for frozen.")
        except Exception as _e:
            logger.debug("[VoiceCloner] Could not patch torch._sources: %s", _e)

        try:
            from TTS.api import TTS
        except ImportError as e:
            raise ImportError(
                "TTS library not installed. Install with: pip install TTS. (Original: %s)" % e
            ) from e
        
        # On macOS, mirror xtts2-ui (https://github.com/BoltzmannEntropy/xtts2-ui): CPU only,
        # TTS(model_name=...).to(device) with no gpu= argument. That config is known to work
        # on macOS; 0.22 + MPS/gpu=False can trigger TorchScript "can't get source" in frozen apps.
        if platform.system() == "Darwin":
            self.device = torch.device("cpu")
            logger.info("Using CPU for voice cloning (macOS: xtts2-ui–style config).")
        else:
            # Non-Mac: keep explicit device selection
            if device_preference == "cpu":
                self.device = torch.device("cpu")
                logger.info("Using CPU for voice cloning (user selected).")
            elif device_preference == "mps":
                self.device = torch.device("cpu")
                logger.warning("MPS not used on this platform. Using CPU.")
            else:
                self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
                logger.info("Using %s for voice cloning.", self.device)
        
        logger.info(f"Loading model {self.model_name}...")
        
        # TTS (and its deps) imports matplotlib; silence font_manager logs (unrelated to TTS).
        os.environ.setdefault("MPLBACKEND", "Agg")
        logging.getLogger("matplotlib").setLevel(logging.ERROR)
        logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
        
        # Match xtts2-ui: TTS(model_name=...).to(device), no gpu= (on Mac TTS uses CPU by default).
        self.tts = TTS(self.model_name).to(self.device)
        
        self._initialized = True
        self._device_preference = device_preference
        logger.info("Voice cloning model loaded successfully.")

    def _ensure_wav(self, path: Path) -> Tuple[Path, bool]:
        """Convert to RIFF WAV if needed; TTS/XTTS requires WAV (\"file does not start with RIFF id\").
        Returns (path_to_use, is_temp) where is_temp=True means the caller must unlink the file."""
        ext = path.suffix.lower()
        if ext == ".wav":
            try:
                with open(path, "rb") as f:
                    if f.read(4) == b"RIFF":
                        return path, False
            except Exception:
                pass
        # Convert MP3/M4A/FLAC or mislabeled file to WAV via pydub
        from pydub import AudioSegment
        wav_path = Path(tempfile.mktemp(suffix=".wav"))
        seg = AudioSegment.from_file(str(path))
        seg.export(str(wav_path), format="wav")
        logger.debug("[VoiceCloner] Converted %s to WAV: %s", path.name, wav_path)
        return wav_path, True

    def clone_voice(
        self,
        text: str,
        speaker_wav: str,
        language: str = "en",
        output_path: str = "output.wav",
        device_preference: str = "auto",
        temperature: float = 0.75,
        length_penalty: float = 1.0,
        repetition_penalty: float = 5.0,
        top_k: int = 50,
        top_p: float = 0.85,
        speed: float = 1.0,
        enable_text_splitting: bool = True,
    ) -> str:
        """
        Clone voice from reference audio.
        
        Args:
            text: Text to synthesize
            speaker_wav: Path to reference audio file (mp3/wav)
            language: Language code (e.g., "en", "es", "fr")
            output_path: Output file path
            device_preference: Device to use ("mps", "cpu", or "auto")
            temperature: Sampling temperature (0.0-1.0)
            length_penalty: Length penalty (0.0-2.0)
            repetition_penalty: Repetition penalty (0.0-10.0)
            top_k: Top-k sampling
            top_p: Top-p (nucleus) sampling
            speed: Speech speed multiplier
            enable_text_splitting: Enable automatic text splitting
            
        Returns:
            Path to generated audio file
        """
        # Ensure pydub can find ffprobe/ffmpeg (e.g. when running from .app with minimal PATH)
        from cdmf_ffmpeg import ensure_ffmpeg_in_path

        ensure_ffmpeg_in_path()

        # Initialize with device preference (will reuse if same preference)
        self._initialize(device_preference)

        # Validate reference audio file exists
        speaker_path = Path(speaker_wav)
        if not speaker_path.exists():
            raise FileNotFoundError(f"Reference audio file not found: {speaker_wav}")

        # TTS/XTTS expects RIFF WAV; convert MP3/M4A/FLAC (or mislabeled .wav) to WAV
        ref_wav, is_temp = self._ensure_wav(speaker_path)

        logger.info(f"Synthesizing audio to: {output_path}...")

        try:
            out = Path(output_path)
            if out.suffix.lower() == ".mp3":
                # TTS only writes WAV; convert to MP3 256k for smaller files
                tmp_wav = Path(tempfile.mktemp(suffix=".wav"))
                try:
                    self.tts.tts_to_file(
                        text=text,
                        speaker_wav=str(ref_wav),
                        language=language,
                        file_path=str(tmp_wav),
                        temperature=temperature,
                        length_penalty=length_penalty,
                        repetition_penalty=repetition_penalty,
                        top_k=top_k,
                        top_p=top_p,
                        speed=speed,
                        enable_text_splitting=enable_text_splitting,
                    )
                    from pydub import AudioSegment
                    AudioSegment.from_wav(str(tmp_wav)).export(str(out), format="mp3", bitrate="256k")
                finally:
                    if tmp_wav.exists():
                        try:
                            tmp_wav.unlink()
                        except OSError:
                            pass
            else:
                self.tts.tts_to_file(
                    text=text,
                    speaker_wav=str(ref_wav),
                    language=language,
                    file_path=output_path,
                    temperature=temperature,
                    length_penalty=length_penalty,
                    repetition_penalty=repetition_penalty,
                    top_k=top_k,
                    top_p=top_p,
                    speed=speed,
                    enable_text_splitting=enable_text_splitting,
                )
            logger.info(f"Voice cloning completed: {output_path}")
            return output_path
        except Exception as e:
            from cdmf_ffmpeg import FFMPEG_INSTALL_HINT, is_ffmpeg_not_found_error

            if is_ffmpeg_not_found_error(e):
                raise RuntimeError(FFMPEG_INSTALL_HINT) from e
            logger.error(f"Voice cloning failed: {e}")
            raise
        finally:
            if is_temp and ref_wav.exists():
                try:
                    ref_wav.unlink()
                except OSError:
                    pass


# Global singleton instance
_voice_cloner: Optional[VoiceCloner] = None


def get_voice_cloner() -> VoiceCloner:
    """Get or create the global voice cloner instance."""
    global _voice_cloner
    if _voice_cloner is None:
        _voice_cloner = VoiceCloner()
    return _voice_cloner


def voice_clone_models_present() -> bool:
    """Return True if the TTS/XTTS model is already loaded (initialized)."""
    global _voice_cloner
    return _voice_cloner is not None and getattr(_voice_cloner, "_initialized", False)


def ensure_voice_clone_models(device_preference: str = "auto", progress_cb: Optional[Callable[[float], None]] = None) -> None:
    """
    Pre-download and load the TTS/XTTS model in the current process.
    progress_cb(fraction) is called with 0.0 at start and 1.0 when done (TTS does not expose download progress).
    """
    if progress_cb:
        try:
            progress_cb(0.0)
        except Exception:
            pass
    get_voice_cloner()._initialize(device_preference=device_preference)
    if progress_cb:
        try:
            progress_cb(1.0)
        except Exception:
            pass
