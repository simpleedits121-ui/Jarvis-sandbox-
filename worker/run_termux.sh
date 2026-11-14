#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements.txt
export JARVIS_HOST=127.0.0.1
exec uvicorn jarvis_worker.main:app --host 127.0.0.1 --port 8765
