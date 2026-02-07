"""
ACE-Step 1.5 Model Downloader (vendored from ACE-Step-1.5 for AceForge bundle).
Downloads models from HuggingFace Hub or ModelScope (ModelScope optional).
Source: https://github.com/ace-step/ACE-Step-1.5/blob/main/acestep/model_downloader.py

AceForge extensions: progress callback and cancel support for UI (tqdm_class + callbacks).
"""

import argparse
import os
import socket
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class DownloadCancelled(Exception):
    """Raised when the user cancels an in-progress model download."""
    pass


# =============================================================================
# Network & Download
# =============================================================================

def _can_access_google(timeout: float = 3.0) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(("www.google.com", 443))
        sock.close()
        return True
    except (socket.timeout, socket.error, OSError):
        return False

def _make_progress_tqdm(
    progress_callback: Optional[Callable[..., None]],
    cancel_check: Optional[Callable[[], bool]],
):
    """Build a tqdm subclass that reports progress and respects cancel_check."""
    try:
        from tqdm.auto import tqdm as base_tqdm
    except ImportError:
        base_tqdm = None

    if base_tqdm is None:
        return None

    progress_cb = progress_callback
    cancel_fn = cancel_check

    class ProgressTqdm(base_tqdm):
        def update(self, n: int = 1) -> Optional[bool]:
            if cancel_fn and cancel_fn():
                raise DownloadCancelled("Download cancelled by user")
            result = super().update(n)
            if progress_cb and self.total:
                try:
                    progress_cb(
                        file_index=int(self.n),
                        total_files=int(self.total),
                        current_file=str(self.desc) if self.desc else None,
                        fraction=self.n / self.total,
                    )
                except Exception:
                    pass
            return result

    return ProgressTqdm


def _download_from_huggingface(
    repo_id: str,
    local_dir: Path,
    token: Optional[str] = None,
    progress_callback: Optional[Callable[..., None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> None:
    from huggingface_hub import snapshot_download
    logger.info(f"[Model Download] Downloading from HuggingFace: {repo_id} -> {local_dir}")
    tqdm_class = _make_progress_tqdm(progress_callback, cancel_check)
    kwargs = dict(
        repo_id=repo_id,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        token=token,
        max_workers=4,
    )
    if tqdm_class is not None:
        kwargs["tqdm_class"] = tqdm_class
    snapshot_download(**kwargs)

def _download_from_modelscope(repo_id: str, local_dir: Path) -> None:
    try:
        from modelscope import snapshot_download
    except ImportError:
        raise RuntimeError("ModelScope not installed. Install with: pip install modelscope")
    logger.info(f"[Model Download] Downloading from ModelScope: {repo_id} -> {local_dir}")
    snapshot_download(model_id=repo_id, local_dir=str(local_dir))

def _smart_download(
    repo_id: str,
    local_dir: Path,
    token: Optional[str] = None,
    prefer_source: Optional[str] = None,
    progress_callback: Optional[Callable[..., None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, str]:
    local_dir.mkdir(parents=True, exist_ok=True)
    use_hf_first = prefer_source != "modelscope" if prefer_source else _can_access_google()
    hf_kw = {"progress_callback": progress_callback, "cancel_check": cancel_check}
    if use_hf_first:
        try:
            _download_from_huggingface(repo_id, local_dir, token, **hf_kw)
            return True, f"Successfully downloaded from HuggingFace: {repo_id}"
        except DownloadCancelled:
            raise
        except Exception as e:
            logger.warning(f"[Model Download] HuggingFace failed: {e}")
            try:
                _download_from_modelscope(repo_id, local_dir)
                return True, f"Successfully downloaded from ModelScope: {repo_id}"
            except Exception as e2:
                return False, f"Both sources failed. HF: {e}, MS: {e2}"
    else:
        try:
            _download_from_modelscope(repo_id, local_dir)
            return True, f"Successfully downloaded from ModelScope: {repo_id}"
        except Exception as e:
            logger.warning(f"[Model Download] ModelScope failed: {e}")
            try:
                _download_from_huggingface(repo_id, local_dir, token, **hf_kw)
                return True, f"Successfully downloaded from HuggingFace: {repo_id}"
            except DownloadCancelled:
                raise
            except Exception as e2:
                return False, f"Both sources failed. MS: {e}, HF: {e2}"

# =============================================================================
# Model Registry (ACE-Step 1.5)
# =============================================================================
MAIN_MODEL_REPO = "ACE-Step/Ace-Step1.5"
SUBMODEL_REGISTRY: Dict[str, str] = {
    "acestep-5Hz-lm-0.6B": "ACE-Step/acestep-5Hz-lm-0.6B",
    "acestep-5Hz-lm-4B": "ACE-Step/acestep-5Hz-lm-4B",
    "acestep-v15-turbo-shift3": "ACE-Step/acestep-v15-turbo-shift3",
    "acestep-v15-sft": "ACE-Step/acestep-v15-sft",
    "acestep-v15-base": "ACE-Step/acestep-v15-base",
    "acestep-v15-turbo-shift1": "ACE-Step/acestep-v15-turbo-shift1",
    "acestep-v15-turbo-continuous": "ACE-Step/acestep-v15-turbo-continuous",
}
MAIN_MODEL_COMPONENTS = [
    "acestep-v15-turbo",
    "vae",
    "Qwen3-Embedding-0.6B",
    "acestep-5Hz-lm-1.7B",
]
DEFAULT_LM_MODEL = "acestep-5Hz-lm-1.7B"

def get_checkpoints_dir(custom_dir: Optional[str] = None) -> Path:
    if custom_dir:
        return Path(custom_dir).resolve()
    return Path.cwd() / "checkpoints"

def check_main_model_exists(checkpoints_dir: Optional[Path] = None) -> bool:
    if checkpoints_dir is None:
        checkpoints_dir = get_checkpoints_dir()
    for component in MAIN_MODEL_COMPONENTS:
        if not (checkpoints_dir / component).exists():
            return False
    return True

def check_model_exists(model_name: str, checkpoints_dir: Optional[Path] = None) -> bool:
    if checkpoints_dir is None:
        checkpoints_dir = get_checkpoints_dir()
    return (checkpoints_dir / model_name).exists()

def download_main_model(
    checkpoints_dir: Optional[Path] = None,
    force: bool = False,
    token: Optional[str] = None,
    prefer_source: Optional[str] = None,
    progress_callback: Optional[Callable[..., None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, str]:
    if checkpoints_dir is None:
        checkpoints_dir = get_checkpoints_dir()
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    if not force and check_main_model_exists(checkpoints_dir):
        return True, f"Main model already exists at {checkpoints_dir}"
    return _smart_download(
        MAIN_MODEL_REPO, checkpoints_dir, token, prefer_source,
        progress_callback=progress_callback, cancel_check=cancel_check,
    )

def download_submodel(
    model_name: str,
    checkpoints_dir: Optional[Path] = None,
    force: bool = False,
    token: Optional[str] = None,
    prefer_source: Optional[str] = None,
    progress_callback: Optional[Callable[..., None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, str]:
    if model_name not in SUBMODEL_REGISTRY:
        return False, f"Unknown model '{model_name}'. Available: {', '.join(SUBMODEL_REGISTRY.keys())}"
    if checkpoints_dir is None:
        checkpoints_dir = get_checkpoints_dir()
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    model_path = checkpoints_dir / model_name
    if not force and model_path.exists():
        return True, f"Model '{model_name}' already exists at {model_path}"
    repo_id = SUBMODEL_REGISTRY[model_name]
    return _smart_download(
        repo_id, model_path, token, prefer_source,
        progress_callback=progress_callback, cancel_check=cancel_check,
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Download ACE-Step 1.5 models (HuggingFace / ModelScope)")
    parser.add_argument("--model", "-m", type=str, help="Model to download (use --list to see available)")
    parser.add_argument("--all", "-a", action="store_true", help="Download all models")
    parser.add_argument("--list", "-l", action="store_true", help="List available models")
    parser.add_argument("--dir", "-d", type=str, default=None, help="Checkpoints directory (required when run from AceForge)")
    parser.add_argument("--force", "-f", action="store_true", help="Force re-download")
    parser.add_argument("--token", "-t", type=str, default=None, help="HuggingFace token")
    parser.add_argument("--skip-main", action="store_true", help="Skip main model when downloading a sub-model")
    args = parser.parse_args()

    if args.list:
        print("\nAvailable models:")
        print("  main ->", MAIN_MODEL_REPO, "(vae, turbo DiT, 1.7B LM)")
        for name, repo in SUBMODEL_REGISTRY.items():
            print(f"  {name} -> {repo}")
        return 0

    checkpoints_dir = get_checkpoints_dir(args.dir)
    if not args.dir:
        print(f"Checkpoints directory: {checkpoints_dir} (use --dir to override)")
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        success, msg = download_main_model(checkpoints_dir, args.force, args.token)
        print(msg)
        if not success:
            return 1
        for name in SUBMODEL_REGISTRY:
            ok, m = download_submodel(name, checkpoints_dir, args.force, args.token)
            print(m)
            if not ok:
                success = False
        return 0 if success else 1

    if args.model:
        if args.model == "main":
            success, msg = download_main_model(checkpoints_dir, args.force, args.token)
        elif args.model in SUBMODEL_REGISTRY:
            if not args.skip_main and not check_main_model_exists(checkpoints_dir):
                print("Main model not found. Downloading main model first...")
                ok, m = download_main_model(checkpoints_dir, args.force, args.token)
                print(m)
                if not ok:
                    return 1
            success, msg = download_submodel(args.model, checkpoints_dir, args.force, args.token)
        else:
            print(f"Unknown model: {args.model}. Use --list to see available models.")
            return 1
        print(msg)
        return 0 if success else 1

    # Default: main model
    print("Downloading main model (vae, turbo DiT, 1.7B LM)...")
    success, msg = download_main_model(checkpoints_dir, args.force, args.token)
    print(msg)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
