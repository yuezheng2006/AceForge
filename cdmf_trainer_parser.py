# Parser-only module for the LoRA trainer CLI.
# Used by aceforge_app for --train --help so we can show help without importing
# heavy deps (diffusers, pytorch_lightning, etc.) in the frozen app.
from __future__ import annotations

import argparse


def _make_parser() -> argparse.ArgumentParser:
    """Build the trainer ArgumentParser (used by cdmf_trainer and by aceforge_app for --train --help)."""
    p = argparse.ArgumentParser()
    p.add_argument("--num_nodes", type=int, default=1)
    p.add_argument("--shift", type=float, default=3.0)
    p.add_argument("--learning_rate", type=float, default=1e-4)
    p.add_argument("--num_workers", type=int, default=8)
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--max_steps", type=int, default=-1)
    p.add_argument("--every_n_train_steps", type=int, default=50)
    p.add_argument("--dataset_path", type=str, default="./zh_lora_dataset")
    p.add_argument("--exp_name", type=str, default="chinese_rap_lora")
    p.add_argument("--precision", type=str, default="32")
    p.add_argument("--accumulate_grad_batches", type=int, default=1)
    p.add_argument("--devices", type=int, default=1)
    p.add_argument("--logger_dir", type=str, default="./exps/logs/")
    p.add_argument("--ckpt_path", type=str, default=None)
    p.add_argument("--checkpoint_dir", type=str, default=None)
    p.add_argument("--gradient_clip_val", type=float, default=0.5)
    p.add_argument("--gradient_clip_algorithm", type=str, default="norm")
    p.add_argument("--reload_dataloaders_every_n_epochs", type=int, default=1)
    p.add_argument("--every_plot_step", type=int, default=2000)
    p.add_argument("--val_check_interval", type=int, default=None)
    p.add_argument("--lora_config_path", type=str, default="config/zh_rap_lora_config.json")
    p.add_argument("--ssl_coeff", type=float, default=1.0)
    p.add_argument("--max_audio_seconds", type=float, default=60.0)
    p.add_argument(
        "--instrumental_only",
        action="store_true",
        help=(
            "Treat dataset as instrumental / no vocals. "
            "LoRA layers attached to lyric and speaker-specific blocks will be frozen."
        ),
    )
    return p
