# AceForge User Guide

User Guide · v0.1-macos · macOS Edition

AceForge is a local AI music workstation powered by ACE-Step
and a custom UI designed to make generating, tweaking, and curating your music a smooth and cohesive experience.
This guide explains how to install AceForge on macOS, generate tracks, manage your library, and train LoRAs.

**Local-first · macOS · ACE-Step text → music · LoRA training · Stem separation · Dataset tools · Apple Metal (MPS) GPU acceleration**

## Contents

1. [Overview](#1-overview)
2. [System requirements](#2-system-requirements)
3. [Installation & first launch](#3-installation--first-launch)
4. [UI tour](#4-ui-tour)
5. [Generating music](#5-generating-music)
6. [Vocal / instrumental stem control](#6-vocal--instrumental-stem-control)
7. [Training LoRAs](#7-training-loras)
8. [Dataset mass-tagging tools](#8-dataset-mass-tagging-tools)
9. [MuFun-ACEStep analyzer (experimental)](#9-mufun-acestep-analyzer-experimental)
10. [Troubleshooting & FAQ](#10-troubleshooting--faq)

## 1. Overview

**AceForge** is a local AI music workstation for people
who actually like owning their tools. It runs on your macOS system, uses Apple Metal (MPS) GPU acceleration, and keeps
all audio and prompts on your hardware.

### What AceForge is built on

- **ACE-Step** – the diffusion engine that turns prompts + lyrics into audio.
- **PyTorch** – the deep learning runtime used by ACE-Step and related models, with native Apple Metal (MPS) support.
- **Qwen-like LLM backend** (via your configured model) – used for the
"Generate prompt / lyrics…" helper.
- **audio-separator** – used for post-process stem separation (vocals vs. instruments).
- **MuFun-ACEStep** (optional) – an analyzer that can auto-create
prompt/lyrics files for datasets.

### What makes AceForge more than "just a wrapper"

- **Sleek generation UI** with _Core_ and _Advanced_ sections, presets,
and clear tooltips so you don't have to memorize every ACE-Step knob.

- **Built-in music player + library view** – browse, sort, favorite, and categorize
every generated track.

- **Preset system** – save, load, and share your favorite generation settings.

- **LoRA training UI** – configure and kick off ACE-Step LoRA training runs
without hand-editing Python scripts.

- **Dataset helpers** – bulk create prompt/lyrics files or auto-generate them
with MuFun-ACEStep.

### Typical workflow

1. Launch AceForge → wait for first-time setup (venv + packages + ACE-Step models).
2. Use **Generate Track** to create songs from prompts (optionally with lyrics).
3. Browse, favorite, and categorize tracks in the **Music Player**.
4. (Optional) Use stem controls to tweak vocal vs. instrumental levels.
5. (Optional) Build datasets and use the **Training** tab to train custom LoRAs.

## 2. System requirements

### Minimum

- macOS 12.0 (Monterey) or later
- Apple Silicon (M1/M2/M3) or Intel Mac with AMD GPU
- 16 GB unified memory (for Apple Silicon) or 16 GB RAM
- ~10–12 GB VRAM/unified memory (more gives more headroom)
- SSD with tens of GB free (models + audio + datasets)
- Python 3.10 or later

### Recommended

- Apple Silicon M1 Pro/Max/Ultra, M2 Pro/Max/Ultra, or M3 Pro/Max
- 32 GB+ unified memory
- Fast SSD for models and datasets
- Comfortable with terminal and reading console logs

**Note:** The very first launch does a lot:
creates a virtual environment, installs Python packages, and downloads ACE-Step
and related models. This can take a while. All of that work is reused on later launches.

**Apple Metal (MPS) GPU acceleration** is automatically enabled on compatible systems, providing excellent performance on Apple Silicon.

## 3. Installation & first launch

### 3.1 Installing AceForge

#### Option 1: Pre-built Release (Recommended)

1. Download `AceForge-macOS.dmg` from the [Releases page](https://github.com/audiohacking/CDMF-Fork/releases).
2. Open the DMG file.
3. Drag `AceForge.app` to your Applications folder.
4. Right-click the app and select "Open" (first time only, to bypass Gatekeeper).
5. The application will start and open in your browser.

#### Option 2: From Source

1. Ensure you have Python 3.10 or later installed:
   ```bash
   # Check Python version
   python3 --version
   
   # If not installed, install via Homebrew
   brew install python@3.10
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/audiohacking/CDMF-Fork.git
   cd CDMF-Fork
   ```

3. Make the launcher script executable:
   ```bash
   chmod +x CDMF.sh
   ```

4. Run the launcher:
   ```bash
   ./CDMF.sh
   ```

### 3.2 First launch: what you'll see

1. Launch AceForge from Applications or by running `./CDMF.sh`.
2. A terminal window titled **"AceForge – Server Console"** will appear.
   This window _must stay open_ while AceForge runs.

3. AceForge immediately opens a **loading page** in your default browser
   while the backend is starting.

4. On first run, the console will:
   - Create `venv_ace` in the app folder.
   - Install packages from `requirements_ace_macos.txt`.
   - Install ACE-Step with PyTorch (including MPS support).
   - Set up other helpers like `audio-separator`.

5. When the server is ready, your browser will show the full AceForge UI.

**Important:** Don't close the terminal while it's working.
If you see Python / pip errors, read the last messages carefully.
Many issues (disk space, network connectivity) will show up here.

### 3.3 Subsequent launches

On later launches, AceForge will:

- Reuse the existing `venv_ace`.
- Skip package installs if everything is already in place.
- Skip large model downloads unless a feature needs a new one (e.g. MuFun).

## 4. UI tour

### 4.1 Title bar & tagline

At the top you'll see the **AceForge** titlebar:

- Logo on the left.
- App title and version (e.g. `v0.1-macos`) on the right.
- A short tagline:
_"Generate unlimited custom music with a simple prompt and style presets via ACE-Step."_

### 4.2 Music Player card

The first main card is **Music Player**. It's your library view for generated tracks.

- **Folder:** shows the current output directory.

- **Category filter chips:**
a row of colored chips lets you filter by category. These are driven
by category labels on your tracks.

- **Track header row:** sortable columns:
  - ★ (favorite)
  - Name
  - Length
  - Category
  - Created
  - Actions

Each track row shows:

- A **favorite button** (★) – click to toggle favorite state.
- The track name (based on the WAV filename).
- Metadata: length and category.
- A small **trash icon** to delete the file from disk.

**Tip:** You can use the header buttons to sort (e.g. by name or creation time), and use
the category filter chips above the list to quickly narrow down to "lofi", "battle",
"town", etc.

### 4.3 Player controls

Below the track list you'll find:

- **Time labels** – current time and total duration.
- **Seek bar** – click / drag to move around in the track.
- **Buttons:** Rewind, Play, Stop, Loop, Mute.
- **Volume slider** – global playback volume.

### 4.4 Mode tabs: Generate vs Training

Beneath the player is a small tab strip:

- **Generate** – the main text-to-music UI.
- **Training** – LoRA training and dataset tools.

Only one mode is visible at a time.

## 5. Generating music

### 5.1 Model status

At the top of the **Generate Track** card, you'll see:

- A **Generate** button.
- A loading bar that animates while a generation is in progress.
- A **model status notice** if ACE-Step isn't downloaded yet.
It will prompt you to click "Download Models" and warn that this is a large download.

### 5.2 Core vs Advanced tabs

The generation controls are split into:

- **Core** – most of what you need most of the time.
- **Advanced** – scheduler, CFG modes, repaint/extend, audio2audio, LoRA internals.

A good mental model: use the **Core** tab to get high-quality songs without
touching anything you don't understand. The **Advanced** tab is for
experiments and fine-tuning once you're comfortable.

### 5.3 Core controls

#### Base filename

**Base filename** (`basename`) is the prefix for your output WAV
files. AceForge will append numbers / timestamps as needed so they don't collide, but the base
name is what you'll see in the player.

#### Auto prompt / lyrics

The button **"Generate prompt / lyrics…"** opens a small modal where you can:

- Describe a **song concept** ("melancholic SNES overworld at night…").
- Choose to generate:
  - Prompt only
  - Lyrics only
  - Prompt + lyrics

AceForge uses an LLM backend to fill in the **Genre / Style Prompt** box
and/or the **Lyrics** box based on your selection.

When **Instrumental** is checked, the dialog will default to
_Prompt only_. When it's unchecked, it leans toward _Prompt + lyrics_.

#### Genre / Style Prompt

This is your main ACE-Step prompt. Use it to describe:

- Genre and instrument palette (e.g. "16-bit SNES snowfield, chiptune pads…").
- Tempo/mood ("slow, melancholic, wistful but hopeful").
- Context ("looping BGM for JRPG overworld").

#### Instrumental vs Vocal presets

Below the prompt field are two preset groups:

- **Instrumental preset buttons** shown when **Instrumental** is checked.
- **Vocal preset buttons** shown when **Instrumental** is unchecked.

Each preset sets a bundle of internal knobs (target seconds, steps, guidance, etc.) and may
tweak internal "seed vibes" for different sound families. The **Random** buttons
pick from a curated list to keep exploring without you having to think too hard.

#### Instrumental toggle & lyrics

- When **Instrumental** is checked:
  - Lyrics are not used for generation.
  - ACE-Step receives a special `[inst]` token so it focuses on backing tracks.
  - The **Lyrics** box is hidden to keep the UI clean.

- When **Instrumental** is unchecked:
  - The **Lyrics** panel appears.
  - You can paste or write lyrics with markers like `[verse]`, `[chorus]`, `[solo]`, etc.

There's also a **Clear** button inside the Lyrics row to quickly wipe
the lyrics field.

#### Target length & fades

- **Target length (seconds)** – slider + numeric box that tells ACE-Step
roughly how long the track should be.

- **Fade in / Fade out (seconds)** – small fades applied at the start/end
of the final audio.

**Tip:** 0.5–2.0 seconds is a good fade range for most BGM tracks.

#### Core ACE-Step knobs

- **Inference steps** – 50–125 is a good range.
Higher is slower and may not always increase quality.

- **Guidance scale** – how strongly ACE-Step follows your text.
Extreme values can introduce noise.

- **BPM (optional)** – if set, AceForge adds a hint like
`tempo 120 bpm` to the tags.

- **Seed** + **Random** checkbox:
  - When Random is checked, AceForge picks a random seed each time.
  - When unchecked, you can lock a specific seed to re-roll close variations.

#### Post-mix vocal / instrumental levels

At the end of the Core section you'll see:

- **Vocals level (dB)**
- **Instrumental level (dB)**

These are post-process gain adjustments created by running the track through
`audio-separator` and rebalancing stems.

**Important:** Using stem controls requires downloading a large stem
separation model on first use and adds a heavy post-process step. For fastest iteration:

1. Generate a track at neutral levels (0 dB / 0 dB).
2. Find a track you like.
3. Turn off Random Seed and keep other settings the same.
4. Re-generate with adjusted vocal / instrumental gains.

### 5.4 Advanced tab (high-level)

The **Advanced** tab exposes more ACE-Step internals:

- Scheduler type (Euler, Heun, ping-pong).
- CFG mode (APG, CFG, CFG★) and related parameters.
- ERG switches (tag, lyric, diffusion).
- Repaint / extend:
  - **Task**: text2music / retake / repaint / extend.
  - **Repaint start / end** in seconds.
  - **Retake variance** for variations.
- Audio2Audio:
  - **Ref strength**
  - **Ref audio file** upload
  - **Optional explicit source path**
- LoRA adapter fields:
  - Pick installed LoRAs from a dropdown.
  - Browse for a LoRA folder under `custom_lora`.
  - Set the LoRA weight (0–10).

If you're new to ACE-Step, you can ignore the Advanced tab entirely. The defaults were
chosen to be safe and high quality out of the box.

### 5.5 Saved presets

At the bottom of the Generate card is a **Saved presets** block:

- **My presets** dropdown – shows your saved presets after you create some.
- **Load** – apply the selected preset to the current form.
- **Save** – capture the current knobs as a new preset.
- **Delete** – remove a preset.

Presets record both text fields (prompt, lyrics, etc.) and numerical fields (steps, seeds,
gains, etc.), so you can quickly return to a particular "vibe kit" without screenshots or
manual notes.

### 5.6 Output directory

The **Output directory** field controls where WAVs are written. It defaults to
the path shown in the Music Player header. If you change this, remember that:

- The player will look at the directory you specify.
- If you point it somewhere else, you may want to restart AceForge or refresh so the player sees it.

## 6. Vocal / instrumental stem control

AceForge integrates **audio-separator** so you can rebalance vocals and
instrumentals after generation:

- **Vocals level (dB)** – boosts or reduces the vocal stem relative to the original mix.
- **Instrumental level (dB)** – boosts or reduces the backing track stem.

Both use decibel adjustments:

- `0 dB` – leave as-is.
- Negative values – make that stem quieter.
- Positive values – make that stem louder.

On first use, AceForge will need to download the stem-separation model.
This is large and adds a significant processing step. For quick sketching,
leave both gains at 0 dB and only use stems once you're close to a final track.

## 7. Training LoRAs

### 7.1 Training controls overview

Switch to the **Training** mode tab to see the LoRA controls:

- **Start Training** – submits the training form to the backend
and starts ACE-Step's trainer.

- **Pause / Resume / Cancel** – control an in-progress run.
These are wired up to backend endpoints that can pause, resume, or stop training.

- **Status indicator** – small banner and loading bar that
reflect the current state.

Pausing saves a checkpoint and allows resuming later. If you restart the server,
the paused state is preserved and you'll be prompted to Resume or Cancel before
starting a new run.

### 7.2 Dataset setup

The **Dataset Setup / Formatting** section describes how training datasets
should be structured:

- Your dataset folder must live under:
  ```
  <AceForge root>/training_datasets
  ```

- For each `foo.mp3` (or `foo.wav`) you should have:
  - `foo_lyrics.txt` – lyrics or `[inst]` for instrumentals.
  - `foo_prompt.txt` – ACE-Step tags for that track.

The UI provides:

- A **Dataset folder** text field.
- A **Browse…** button that uses a folder picker.

You can hand-create these files, use the **Dataset Mass Tagging** tool to
generate them from a base prompt, or use **MuFun-ACEStep** to auto-tag.

### 7.3 Core LoRA training parameters

- **Experiment / adapter name** – a short name like
`lofi_chiptunes_v1`. Used for the output folder under
`ace_training` and the final adapter under your
`custom_lora` hierarchy.

- **LoRA config (JSON)** – choose from JSON presets in the
`training_config` folder.

- **Max training steps** – upper bound on optimization steps.
Usually left high; you control real run length with epochs.

- **Max epochs** – number of full passes over the dataset
(e.g. 20).

- **Learning rate** – default `1e-4`,
with `1e-4`–`1e-5` being common LoRA values.

- **Max clip seconds** – max length per audio example.
Lowering this can reduce memory usage and speed up training.

- **SSL loss weight** – weight for MERT/mHuBERT self-supervised losses.
Set to 0 for pure instrumental / chiptune datasets.

- **Instrumental dataset** – checkbox telling the trainer to
freeze lyric/speaker-specific blocks and focus on music/texture layers.

- **Save LoRA every N steps** – periodic checkpoint saving,
with 0 disabling mid-run saves (but still writing a final adapter).

### 7.4 Advanced trainer settings

These map to PyTorch Lightning / ACE-Step trainer internals:

- **Precision** – 32-bit, 16-mixed, or bf16-mixed (note: MPS uses float32 by default).
- **Grad accumulation** – virtual batch size multiplier.
- **Gradient clip value + algorithm** – stability tuning.
- **DataLoader reload frequency** – how often to rebuild loaders.
- **Validation check interval** – how often validation runs.
- **Devices** – number of devices to use (typically 1 for MPS).

If you're not already used to debugging Lightning configs, leave these at their defaults.
You'll get more mileage from good datasets and reasonable learning rates.

### 7.5 LoRA config help

The LoRA config presets come in several families: light / medium / heavy, base_layers, extended_attn,
heavy transformer, full_stack, etc. As a rule of thumb:

- **Light / base_layers** – safest, smaller adapters, subtle style shaping.
- **Heavy / full_stack** – much stronger imprinting and higher overfit risk.

## 8. Dataset mass-tagging tools

Under Training mode you'll also see a card for
**Dataset Mass Tagging (Prompt / Lyrics Templates)**.
This is for quickly building simple prompt/lyrics files without ML tagging.

### 8.1 Choosing the dataset folder

- Use the **Dataset folder** field and **Browse…** button to point to a folder under:
  ```
  <AceForge root>/training_datasets
  ```

- Only `.mp3` and `.wav` files in that folder will be affected.

### 8.2 Base tags

The **Base tags** field is a short ACE-Step prompt snippet written into each
`_prompt.txt`. Example:

```
16-bit, 8-bit, SNES, retro RPG BGM, looping instrumental
```

### 8.3 Actions

- **Create prompt files** – creates or updates
`_prompt.txt` for each track using the base tags.

- **Create [inst] lyrics files** – creates or updates
`_lyrics.txt` files with just `[inst]`.

- **Overwrite existing files** – when checked, will overwrite
existing prompt/lyrics files instead of skipping them.

A small status text and loading bar show when the tool is busy.
Once complete, each track in the dataset should be ready to plug into the LoRA trainer.

## 9. MuFun-ACEStep analyzer (experimental)

The **"Experimental – Analyze Dataset with MuFun-ACEStep"** card lets you
run a large MuFun model over a folder of audio to auto-generate prompts and lyrics.

### 9.1 Installing the MuFun model

- Use the **Install / Check** button. AceForge will:
  - Check whether the model is already present.
  - Download it if needed into the AceForge models folder.

- The model is large (tens of GB). Make sure you have enough disk space.

### 9.2 Running analysis

- Select a dataset folder under `training_datasets`.
- Optionally provide a **Base tags** string.
- Optionally check **Instrumental** to force all lyrics to `[inst]`.
- Click **Analyze Folder**.

MuFun will:

- Create `_prompt.txt` and `_lyrics.txt` files next to each track.
- Include your base tags plus its own tags when writing prompts.
- Show progress and results in the **Results** text area.

MuFun is powerful but not perfect. For high-stakes datasets, skim a few outputs and
edit any bad tags or strange lyric outputs before training a LoRA.

## 10. Troubleshooting & FAQ

### 10.1 First launch is taking forever

- Check the terminal window for pip errors (network, disk, permissions).
- Ensure you have plenty of free disk space on your Mac.
- Slow networks will heavily impact model downloads.

### 10.2 "No .wav files found yet"

- Generate a track first from the **Generate** tab.
- Confirm that the **Output directory** field points to the correct folder.

### 10.3 MPS (Metal) backend errors

- Ensure you're running macOS 12.0+ for MPS support.
- Some operations may fall back to CPU if not yet supported on MPS.
- Try setting `ACE_PIPELINE_DTYPE=float32` environment variable if you encounter precision issues:
  ```bash
  export ACE_PIPELINE_DTYPE=float32
  ./CDMF.sh
  ```

### 10.4 Out-of-memory errors

- Reduce **Target length** for generation.
- Reduce **Max clip seconds** for training.
- Lower batch / grad accumulation values if you've changed them.
- On Apple Silicon, unified memory is shared between CPU and GPU, so closing other applications can help.

### 10.5 Python version issues

```bash
# Ensure you have Python 3.10 or later
python3 --version

# Install via Homebrew if needed
brew install python@3.10
```

### 10.6 Permission denied when running CDMF.sh

```bash
chmod +x CDMF.sh
```

### 10.7 Browser doesn't open automatically

- Manually navigate to `http://127.0.0.1:5056/` in your browser.
- Check if the terminal shows any error messages.

### 10.8 Virtual environment issues

```bash
# Remove existing venv and recreate
rm -rf venv_ace
./CDMF.sh
```

### 10.9 Uninstalling AceForge

**From pre-built app:**
- Drag `AceForge.app` from Applications to Trash.
- Remove the data folder: `~/Library/Application Support/AceForge` (if it exists).

**From source:**
- Delete the cloned repository folder.
- Remove `venv_ace` directory if it exists.

If you keep a lot of generated music, consider backing up your `.wav` files before uninstalling.

---

## Performance Tips for Apple Silicon

- **Unified memory management**: Apple Silicon Macs with unified memory can efficiently share memory between CPU and GPU.
- **Batch sizes**: Start with smaller batch sizes and gradually increase to find optimal performance.
- **Model precision**: The pipeline automatically selects appropriate precision for MPS (float32 instead of bfloat16).
- **Generation length**: Longer generation times may require more memory; start with shorter durations and scale up.

---

For more information and support, visit the [GitHub repository](https://github.com/audiohacking/CDMF-Fork).
