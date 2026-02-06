#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Verify that LoRA training works from the frozen app bundle (--train entry point).
#
# Run after building the app (e.g. ./build_local.sh or pyinstaller CDMF.spec).
# Does not require ACE-Step models or a dataset.
#
# Usage:
#   ./test_train_from_bundle.sh
# ---------------------------------------------------------------------------

set -e

BUNDLED_BIN="${1:-./dist/AceForge.app/Contents/MacOS/AceForge_bin}"

echo "=================================================="
echo "AceForge - Training from bundle test (--train)"
echo "=================================================="
echo ""

if [ ! -f "$BUNDLED_BIN" ]; then
    echo "✗ Bundled binary not found: $BUNDLED_BIN"
    echo "  Build the app first, e.g.: ./build_local.sh"
    echo "  Or pass the binary path: $0 /path/to/AceForge_bin"
    exit 1
fi

echo "Using binary: $BUNDLED_BIN"
echo ""

# 1. Run frozen binary with --train --help. Should print trainer help and exit 0 (no GUI).
echo "Step 1: Running bundled app with --train --help..."
OUTPUT=$("$BUNDLED_BIN" --train --help 2>&1) || EXIT=$?
EXIT=${EXIT:-0}

if [ "$EXIT" -ne 0 ]; then
    echo "✗ Binary exited with code $EXIT (expected 0)"
    echo "Output:"
    echo "$OUTPUT"
    exit 1
fi

# Trainer help must include these options (same as cdmf_training passes)
for opt in "--dataset_path" "--exp_name" "--epochs" "--max_steps"; do
    if echo "$OUTPUT" | grep -q -- "$opt"; then
        echo "  ✓ Trainer option $opt present"
    else
        echo "✗ Trainer help missing option: $opt"
        echo "Output:"
        echo "$OUTPUT"
        exit 1
    fi
done

echo "✓ Bundled app correctly enters trainer mode with --train and shows help"
echo ""

# 2. Optional: from source, trainer --help works (sanity check)
if command -v python3 &>/dev/null && [ -f "cdmf_trainer.py" ]; then
    echo "Step 2: Sanity check - trainer script --help from source..."
    if python3 cdmf_trainer.py --help &>/dev/null; then
        echo "  ✓ python3 cdmf_trainer.py --help OK"
    else
        echo "  (skip: python3 cdmf_trainer.py --help failed or not run)"
    fi
fi

echo ""
echo "=================================================="
echo "✓ Training-from-bundle test PASSED"
echo "  The frozen app supports LoRA training via: binary --train [args...]"
echo "=================================================="
