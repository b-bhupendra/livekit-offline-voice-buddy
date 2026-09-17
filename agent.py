#!/usr/bin/env python3
"""Root-level launcher for LiveKit Voice Agent.
Allows running `python agent.py console` or `python agent.py dev` directly from workspace root.
"""
import os
import sys
from pathlib import Path

# Force offline mode for Hugging Face Hub to avoid IPv6 network timeouts
os.environ["HF_HUB_OFFLINE"] = "1"

# Add mvp_talker_offline to sys.path
AGENT_DIR = Path(__file__).resolve().parent / "mvp_talker_offline"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

os.chdir(str(AGENT_DIR))

# Import and run server
from agent import server
from livekit import agents

if __name__ == "__main__":
    agents.cli.run_app(server)
