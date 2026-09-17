#!/usr/bin/env python3
"""Root-level launcher for LiveKit Voice Agent.
Runs the backend voice agent from workspace root.
"""
import os
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"

BACKEND_DIR = Path(__file__).resolve().parent / "mvp_talker_offline" / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.chdir(str(BACKEND_DIR))

from agent import server
from livekit import agents

if __name__ == "__main__":
    agents.cli.run_app(server)
