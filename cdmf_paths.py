# C:\AceForge\cdmf_paths.py

from __future__ import annotations

from pathlib import Path
import sys
import json
import os

# ---------------------------------------------------------------------------
# Core paths and directories (shared across modules)
# ---------------------------------------------------------------------------

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).parent.resolve()

# Configuration file for user settings
CONFIG_PATH = APP_DIR / "aceforge_config.json"

def load_config() -> dict:
    """Load configuration from aceforge_config.json or return defaults."""
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"[AceForge] Warning: Failed to load config: {e}", flush=True)
    return {}

def save_config(config: dict) -> None:
    """Save configuration to aceforge_config.json."""
    try:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[AceForge] Warning: Failed to save config: {e}", flush=True)

def get_models_folder() -> Path:
    """Get the configured models folder path, or default to APP_DIR / ace_models."""
    config = load_config()
    models_path = config.get("models_folder")
    if models_path:
        path = Path(models_path)
        # Validate that the path exists or can be created
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception as e:
            print(f"[AceForge] Warning: Cannot use configured models folder {models_path}: {e}", flush=True)
            print("[AceForge] Falling back to default models folder.", flush=True)
    
    # Default path
    default_path = APP_DIR / "ace_models"
    default_path.mkdir(parents=True, exist_ok=True)
    return default_path

def set_models_folder(path: str) -> bool:
    """Set the models folder path in configuration."""
    try:
        path_obj = Path(path).resolve()
        # Try to create the directory to validate the path
        path_obj.mkdir(parents=True, exist_ok=True)
        
        config = load_config()
        config["models_folder"] = str(path_obj)
        save_config(config)
        
        # Update environment variable for HF_HOME
        os.environ["HF_HOME"] = str(path_obj)
        
        return True
    except Exception as e:
        print(f"[AceForge] Error setting models folder: {e}", flush=True)
        return False

# Where finished tracks go
DEFAULT_OUT_DIR = str(APP_DIR / "generated")

# Presets / tracks metadata / user presets
PRESETS_PATH = APP_DIR / "presets.json"
TRACK_META_PATH = APP_DIR / "tracks_meta.json"
USER_PRESETS_PATH = APP_DIR / "user_presets.json"

# Shared location for ACE-Step base model weights used by the LoRA trainer.
ACE_TRAINER_MODEL_ROOT = APP_DIR / "ace_models"
ACE_TRAINER_MODEL_ROOT.mkdir(parents=True, exist_ok=True)

# Root for all ACE-Step training datasets (LoRA + MuFun).
TRAINING_DATA_ROOT = APP_DIR / "training_datasets"
TRAINING_DATA_ROOT.mkdir(parents=True, exist_ok=True)

# Training configs (JSON files for LoRA hyperparameters)
TRAINING_CONFIG_ROOT = APP_DIR / "training_config"
TRAINING_CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
DEFAULT_LORA_CONFIG = TRAINING_CONFIG_ROOT / "default_config.json"

# Where custom LoRA adapters live
CUSTOM_LORA_ROOT = APP_DIR / "custom_lora"
CUSTOM_LORA_ROOT.mkdir(parents=True, exist_ok=True)

# Seed vibes (these should match ACE_VIBE_TAGS in generate_ace.py)
SEED_VIBES = [
    ("any", "Any / Auto"),
    ("lofi_dreamy", "Lo-fi & Dreamy"),
    ("chiptunes_upbeat", "Chiptunes – Upbeat"),
    ("chiptunes_zelda", "Chiptunes – Legend of Zelda Fusion"),
    ("fantasy", "Fantasy / Orchestral"),
    ("cyberpunk", "Cyberpunk / Synthwave"),
    ("misc", "Misc / Other"),
]
