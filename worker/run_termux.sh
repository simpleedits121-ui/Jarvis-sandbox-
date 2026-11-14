#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

# Worker outputs live in Downloads so Android apps can browse/import them.
export JARVIS_WORKSPACE="${JARVIS_WORKSPACE:-$HOME/storage/downloads/JARVIS_WORKSPACE}"
mkdir -p "$JARVIS_WORKSPACE"

# Keep the virtual environment in Termux's private home, not shared storage.
VENV_DIR="$HOME/.venvs/jarvis-sandbox"
mkdir -p "$(dirname "$VENV_DIR")"
python -m venv "$VENV_DIR" 2>/dev/null || true
source "$VENV_DIR/bin/activate"
pip install -r requirements.txt

export JARVIS_HOST=127.0.0.1
export JARVIS_PORT=8765
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo "JARVIS workspace: $JARVIS_WORKSPACE"
echo "JARVIS API: http://127.0.0.1:8765"
exec uvicorn jarvis_worker.main:app --host 127.0.0.1 --port 8765
