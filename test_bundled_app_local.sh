#!/bin/bash
# Local test script to build and test the bundled app
# This replicates what CI does but runs locally

set -e

echo "=========================================="
echo "Local Bundled App Test"
echo "=========================================="
echo ""

# Check Python version
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    if [[ "$PYTHON_VERSION" == "3.1"* ]] || [[ "$PYTHON_VERSION" == "3.11" ]]; then
        PYTHON_CMD=python3
    else
        echo "⚠ WARNING: python3 is version $PYTHON_VERSION, but 3.11 is recommended"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        PYTHON_CMD=python3
    fi
else
    echo "✗ Python 3.11 not found. Please install Python 3.11."
    exit 1
fi

echo "Using Python: $PYTHON_CMD"
$PYTHON_CMD --version
echo ""

# Check if PyInstaller is installed
if ! $PYTHON_CMD -c "import PyInstaller" 2>/dev/null; then
    echo "⚠ PyInstaller not found. Please install it:"
    echo "  $PYTHON_CMD -m pip install pyinstaller"
    exit 1
fi

echo "✓ PyInstaller found"
echo ""

# Clean previous builds (PyInstaller outputs only).
# NEVER delete build/macos/ — it contains AceForge.icns (app icon), codesign.sh, pyinstaller hooks.
echo "Cleaning previous builds..."
rm -rf dist/AceForge.app dist/CDMF build/AceForge
echo "✓ Cleaned"
echo ""

if [ ! -f "build/macos/AceForge.icns" ]; then
    echo "✗ ERROR: build/macos/AceForge.icns not found. build/macos/ must never be deleted."
    echo "  Restore from main: git checkout main -- build/macos/"
    exit 1
fi

# Build the app
echo "Building bundled app with PyInstaller..."
echo "This may take several minutes..."
$PYTHON_CMD -m PyInstaller CDMF.spec --clean --noconfirm

if [ ! -f "dist/AceForge.app/Contents/MacOS/AceForge_bin" ]; then
    echo "✗ Build failed - bundled binary not found"
    exit 1
fi

echo "✓ Build completed"
echo ""

# Check if models exist
echo "Checking for ACE-Step models..."
if ! $PYTHON_CMD -c "from ace_model_setup import get_ace_checkpoint_root, ACE_LOCAL_DIRNAME; from pathlib import Path; root = get_ace_checkpoint_root(); repo = root / ACE_LOCAL_DIRNAME; exit(0 if repo.exists() else 1)" 2>/dev/null; then
    echo "⚠ Models not found. Please download them first:"
    echo "  $PYTHON_CMD ace_model_setup.py"
    echo ""
    echo "Skipping generation test, but checking imports..."
    MODELS_EXIST=false
else
    echo "✓ Models found"
    MODELS_EXIST=true
fi
echo ""

# Test imports
echo "Testing bundled app imports..."
BUNDLED_BIN="./dist/AceForge.app/Contents/MacOS/AceForge_bin"

$BUNDLED_BIN -c "
import sys
print('Python version:', sys.version)
print('Frozen:', getattr(sys, 'frozen', False))
print('Executable:', sys.executable)
print('')

errors = []

# Test lzma
try:
    import lzma
    import _lzma
    print('✓ lzma imported')
except Exception as e:
    print(f'✗ lzma failed: {e}')
    errors.append(('lzma', str(e)))

# Test py3langid data file location
try:
    import py3langid
    from pathlib import Path
    pkg_file = py3langid.__file__
    pkg_dir = Path(pkg_file).parent
    data_file = pkg_dir / 'data' / 'model.plzma'
    print(f'py3langid.__file__: {pkg_file}')
    print(f'Looking for data at: {data_file}')
    if data_file.exists():
        print(f'✓ py3langid data/model.plzma found at {data_file}')
    else:
        print(f'✗ py3langid data/model.plzma NOT FOUND at {data_file}')
        errors.append(('py3langid data', f'File not found: {data_file}'))
except Exception as e:
    print(f'✗ py3langid check failed: {e}')
    errors.append(('py3langid', str(e)))

# Test VoiceBpeTokenizer
try:
    from acestep.models.lyrics_utils.lyric_tokenizer import VoiceBpeTokenizer
    print('✓ VoiceBpeTokenizer imported')
except Exception as e:
    print(f'✗ VoiceBpeTokenizer import failed: {e}')
    errors.append(('VoiceBpeTokenizer', str(e)))

# Test ACEStepPipeline
try:
    from cdmf_pipeline_ace_step import ACEStepPipeline
    print('✓ ACEStepPipeline imported')
except Exception as e:
    print(f'✗ ACEStepPipeline import failed: {e}')
    errors.append(('ACEStepPipeline', str(e)))

if errors:
    print('')
    print('✗ Import/data file errors:')
    for module, error in errors:
        print(f'  - {module}: {error}')
    sys.exit(1)

print('')
print('✓ All imports and data files OK')
" || {
    echo ""
    echo "✗ Import test failed"
    exit 1
}

echo ""

if [ "$MODELS_EXIST" = true ]; then
    echo "Testing generation with bundled app..."
    echo "This will catch runtime bundling issues..."
    echo ""
    
    $BUNDLED_BIN -c "
import sys
import os
from pathlib import Path

os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'

print('=' * 60)
print('Bundled App Generation Test')
print('=' * 60)
print(f'Python executable: {sys.executable}')
print(f'Frozen: {getattr(sys, \"frozen\", False)}')
print('=' * 60)
print('')

try:
    from generate_ace import generate_track_ace
    print('✓ generate_track_ace imported')
except Exception as e:
    print(f'✗ Failed to import generate_track_ace: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print('Starting generation test (10 seconds, 5 steps)...')
print('')

try:
    result = generate_track_ace(
        genre_prompt='upbeat electronic music, synthwave',
        instrumental=True,
        target_seconds=10,
        steps=5,
        guidance_scale=4.0,
        seed=42,
        out_dir=Path('test_output_bundled'),
        basename='local_test_bundled_track'
    )
    
    print('')
    print('✓ Generation completed successfully')
    
    output_dir = Path('test_output_bundled')
    wav_files = list(output_dir.glob('*.wav'))
    if not wav_files:
        print(f'✗ No WAV files found in {output_dir}')
        sys.exit(1)
    
    for wav_file in wav_files:
        size = wav_file.stat().st_size
        print(f'✓ Generated file: {wav_file.name} ({size:,} bytes)')
        if size == 0:
            print(f'✗ File is empty')
            sys.exit(1)
    
    print('')
    print('=' * 60)
    print('✓ ALL TESTS PASSED')
    print('=' * 60)
        
except Exception as e:
    print('')
    print('=' * 60)
    print('✗ Generation failed')
    print('=' * 60)
    print(f'Error: {e}')
    print('')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" || {
    echo ""
    echo "✗ Generation test failed"
    echo "This indicates a runtime bundling issue."
    exit 1
}
else
    echo "⚠ Generation test skipped (models not available)"
fi

echo ""
echo "=========================================="
echo "✓ Local test completed"
echo "=========================================="
echo ""
echo "Bundled app location: dist/AceForge.app"
