#!/usr/bin/env bash
# Boot the P&ID Copilot brain + review pane. (On the GB10, run inside the OpenShell
# sandbox; OpenClaw/NemoClaw provide the agent face + Telegram separately.)
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PIDCOPILOT_PORT:-8000}"

# 1) (optional) ensure the local model is served — NemoClaw/Ollama owns this on the box
#    ollama serve &  ;  ollama run nemotron-3-nano

# 2) start the brain (FastAPI + websocket + Python watcher heartbeat)
echo "Starting P&ID Copilot on http://127.0.0.1:${PORT}  (pane at /)"
exec uvicorn pidcopilot.server:app --host 127.0.0.1 --port "${PORT}"
