#!/usr/bin/env python3
"""Launcher for LiveKit Voice Agent inside mvp_talker_offline."""
import os
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.chdir(str(BACKEND_DIR))

from agent import server
from livekit import agents

if __name__ == "__main__":
    agents.cli.run_app(server)
