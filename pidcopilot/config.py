"""Central config — ports, paths, model names, sandbox dirs. Override via env."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Service
HOST = os.getenv("PIDCOPILOT_HOST", "127.0.0.1")
PORT = int(os.getenv("PIDCOPILOT_PORT", "8000"))

# Watched folder: where "saved revisions" land (draw.io Ctrl+S / scripted drops).
# In the sandbox this is /sandbox/revisions; locally it defaults under the repo.
WATCH_DIR = Path(os.getenv("PIDCOPILOT_WATCH_DIR", str(ROOT / "fixtures" / "revisions")))
WATCH_POLL_SECONDS = float(os.getenv("PIDCOPILOT_WATCH_POLL", "1.0"))

# Local inference (via NemoClaw/Ollama). Reasoning/narration model.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nemotron-3-nano")
VL_MODEL = os.getenv("NEMOTRON_VL_MODEL", "nemotron-nano-12b-vl")

# Telegram (terse notifications only; diagram content NEVER leaves the box).
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

FIXTURES = ROOT / "fixtures"
WEB_DIR = ROOT / "web"
