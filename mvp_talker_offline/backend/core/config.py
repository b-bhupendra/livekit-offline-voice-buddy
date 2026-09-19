"""Centralized environment configuration for the Buddy Voice AI Agent.

Loads .env from the workspace root (mvp_talker_offline/.env) and exposes
all configuration values as module-level constants. Import this module
instead of scattering os.getenv() calls across files.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Locate workspace root (mvp_talker_offline/) ─────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent          # backend/
WORKSPACE_ROOT = BACKEND_DIR.parent                           # mvp_talker_offline/

# ── Load environment variables ───────────────────────────────────────────────
_env_path = WORKSPACE_ROOT / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

# ── LiveKit ──────────────────────────────────────────────────────────────────
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://127.0.0.1:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")
LIVEKIT_TRANSPORT_MODE = os.getenv("LIVEKIT_TRANSPORT_MODE", "webrtc")

# ── Ollama LLM ───────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen-buddy")

# ── Audio Server ─────────────────────────────────────────────────────────────
AUDIO_SERVER_PORT = int(os.getenv("AUDIO_SERVER_PORT", "8880"))
AUDIO_SERVER_URL = os.getenv("AUDIO_SERVER_URL", "http://127.0.0.1:8880/v1")

# ── TTS — Kokoro (Tier 1) ───────────────────────────────────────────────────
MODELS_DIR = WORKSPACE_ROOT / "models"
KOKORO_MODEL_PATH = os.getenv("KOKORO_MODEL_PATH", str(MODELS_DIR / "kokoro-v1.0.onnx"))
KOKORO_VOICES_PATH = os.getenv("KOKORO_VOICES_PATH", str(MODELS_DIR / "voices-v1.0.bin"))
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_heart")
KOKORO_SPEED = float(os.getenv("KOKORO_SPEED", "1.0"))

# ── TTS — Piper (Tier 2 fallback) ───────────────────────────────────────────
PIPER_VOICE_PATH = os.getenv(
    "PIPER_VOICE_PATH",
    str(MODELS_DIR / "en_US-lessac-medium.onnx"),
)
PIPER_LENGTH_SCALE = float(os.getenv("PIPER_LENGTH_SCALE", "1.05"))
PIPER_NOISE_SCALE = float(os.getenv("PIPER_NOISE_SCALE", "0.667"))
PIPER_NOISE_W_SCALE = float(os.getenv("PIPER_NOISE_W_SCALE", "0.8"))

# ── Data Paths ───────────────────────────────────────────────────────────────
DATA_DIR = WORKSPACE_ROOT / "data"
DB_PATH = DATA_DIR / "memory.db"
CURRICULUM_FILE = DATA_DIR / "curriculum.json"
CURRICULUM_DB_PATH = DATA_DIR / "curriculum.db"
BANKS_DIR = DATA_DIR / "quiz_banks"
STORIES_DIR = DATA_DIR / "stories"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"
CHECKPOINT_DB_PATH = DATA_DIR / "langgraph_checkpoints.db"
LECTURE_AUDIO_DIR = DATA_DIR / "lecture_audio"

# ── External Books ───────────────────────────────────────────────────────────
BOOKS_DIR = os.getenv("BOOKS_DIR", str(Path.home() / "buddy_reference_books"))
