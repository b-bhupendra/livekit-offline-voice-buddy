"""
audio_server.py — Local TTS microservice + LiveKit JWT token minting.

TTS synthesis tiers (in priority order):
  Tier 1: Kokoro-82M ONNX  — warm, expressive, ~80-150ms first chunk  (af_heart voice)
  Tier 2: Piper ONNX       — fallback if Kokoro model files missing
  Tier 3: pyttsx3          — system TTS, always available offline
  Tier 4: Silence WAV      — 100ms silent buffer; ensures client never crashes

LiveKit official Kokoro pattern:
  openai.TTS(model="kokoro", voice="af_heart", base_url=AUDIO_SERVER_URL)
  → hits /v1/audio/speech here → Kokoro synthesis → WAV bytes back to agent
"""

import io
import os
import re
import wave
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

import sys
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

os.environ["HF_HUB_OFFLINE"] = "1"

from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from core.structured_logger import tts_logger

app = FastAPI(title="Buddy Offline Kokoro TTS & Audio Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from core.config import (
    KOKORO_MODEL_PATH,
    KOKORO_VOICES_PATH,
    KOKORO_VOICE,
    KOKORO_SPEED,
    PIPER_VOICE_PATH,
    PIPER_LENGTH_SCALE,
    PIPER_NOISE_SCALE,
    PIPER_NOISE_W_SCALE,
)

# ─────────────────────────────────────────────────────────────────────────────
# Kokoro-82M ONNX — Tier 1 (warm, expressive, ~80-150ms)
# ─────────────────────────────────────────────────────────────────────────────
kokoro_tts = None

try:
    from kokoro_onnx import Kokoro as KokoroOnnx
    import soundfile as sf

    if os.path.exists(KOKORO_MODEL_PATH) and os.path.exists(KOKORO_VOICES_PATH):
        kokoro_tts = KokoroOnnx(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        tts_logger.info(
            f"Kokoro-82M TTS ready | voice={KOKORO_VOICE} | speed={KOKORO_SPEED} | "
            f"model={KOKORO_MODEL_PATH}"
        )
    else:
        tts_logger.warning(
            f"Kokoro model files not found — Tier 1 unavailable.\n"
            f"  Expected: {KOKORO_MODEL_PATH}\n"
            f"  Expected: {KOKORO_VOICES_PATH}\n"
        )
except ImportError:
    tts_logger.warning("kokoro-onnx not installed. Run: pip install kokoro-onnx soundfile")

# ─────────────────────────────────────────────────────────────────────────────
# Piper ONNX — Tier 2 (fallback)
# ─────────────────────────────────────────────────────────────────────────────
piper_voice = None
if kokoro_tts is None:   # only load Piper when Kokoro is unavailable
    try:
        from piper import PiperVoice
        if os.path.exists(PIPER_VOICE_PATH):
            piper_voice = PiperVoice.load(PIPER_VOICE_PATH)
            tts_logger.info(f"Piper TTS ready (Tier 2 fallback) | voice={PIPER_VOICE_PATH}")
    except ImportError:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# Text cleaning
# ─────────────────────────────────────────────────────────────────────────────

def clean_tts_text(text: str) -> str:
    """Strip emoji / non-ASCII decoration; normalise whitespace."""
    cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    cleaned = re.sub(r'[^\w\s.,!?;:\'\"-]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

# ─────────────────────────────────────────────────────────────────────────────
# Synthesis tiers
# ─────────────────────────────────────────────────────────────────────────────

def _silence_wav(duration_ms: int = 100) -> bytes:
    """Return a valid PCM WAV buffer of silence (never crashes the OpenAI TTS client)."""
    frames = int(24000 * duration_ms / 1000)
    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"\x00\x00" * frames)
        return buf.getvalue()


def synthesize_wav(text: str, voice: str | None = None) -> bytes:
    """
    Four-tier TTS synthesis with graceful degradation.

    voice param is passed through from the /v1/audio/speech request
    (e.g. "af_heart", "af_bella") and overrides the env default for Kokoro.
    """
    text = clean_tts_text(text) or "..."
    kokoro_voice = voice or KOKORO_VOICE

    # ── Tier 1: Kokoro-82M ONNX ──────────────────────────────────────────────
    if kokoro_tts is not None:
        try:
            import soundfile as sf
            samples, sample_rate = kokoro_tts.create(
                text,
                voice=kokoro_voice,
                speed=KOKORO_SPEED,
                lang="en-us",
            )
            with io.BytesIO() as buf:
                sf.write(buf, samples, sample_rate, format="WAV")
                data = buf.getvalue()
            tts_logger.debug(f"Kokoro synthesis ok | voice={kokoro_voice} | chars={len(text)}")
            return data
        except Exception as exc:
            tts_logger.error(f"Kokoro Tier 1 failed ({exc}), trying Piper fallback")

    # ── Tier 2: Piper ONNX ───────────────────────────────────────────────────
    if piper_voice is not None:
        try:
            from piper import SynthesisConfig
            config = SynthesisConfig(
                length_scale=PIPER_LENGTH_SCALE,
                noise_scale=PIPER_NOISE_SCALE,
                noise_w_scale=PIPER_NOISE_W_SCALE,
            )
            with io.BytesIO() as buf:
                with wave.open(buf, "wb") as wf:
                    piper_voice.synthesize_wav(text, wf, syn_config=config)
                data = buf.getvalue()
            tts_logger.warning("Piper Tier 2 used (Kokoro unavailable)")
            return data
        except Exception as exc:
            tts_logger.error(f"Piper Tier 2 failed ({exc}), trying pyttsx3 fallback")

    # ── Tier 3: pyttsx3 system TTS ───────────────────────────────────────────
    try:
        import pyttsx3
        import tempfile
        engine = pyttsx3.init()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            tmp_path = tf.name
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as f:
            data = f.read()
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        if data:
            tts_logger.warning("pyttsx3 Tier 3 used")
            return data
    except Exception as exc:
        tts_logger.warning(f"pyttsx3 Tier 3 failed ({exc}), returning silence")

    # ── Tier 4: Silence WAV (guaranteed non-crash) ────────────────────────────
    tts_logger.error("All TTS tiers exhausted — returning silence buffer")
    return _silence_wav(100)


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI-compatible speech endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/v1/audio/speech")
@app.post("/synthesize")
async def speech(request: Request):
    """
    OpenAI-compatible /v1/audio/speech endpoint.
    Accepts: { "input": "...", "voice": "af_heart", "model": "kokoro" }
    Returns: audio/wav
    """
    data = await request.json()
    input_text = data.get("input", "") or data.get("text", "")
    voice      = data.get("voice")   # e.g. "af_heart", "af_bella", "am_adam"
    if not input_text:
        return Response(content=_silence_wav(50), media_type="audio/wav")
    wav_bytes = synthesize_wav(input_text, voice=voice)
    return Response(content=wav_bytes, media_type="audio/wav")


# ─────────────────────────────────────────────────────────────────────────────
# LiveKit JWT token minting
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/token")
async def get_livekit_token(identity: str = "web-user", room_name: str = "buddy-room"):
    """
    Mint a LiveKit JWT access token for the browser participant.
    Uses the official LiveKit Python SDK api.AccessToken — no hand-rolled JWT hacks.
    """
    from livekit import api
    api_key    = os.getenv("LIVEKIT_API_KEY",    "devkey")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "secret")
    lk_url     = os.getenv("LIVEKIT_URL",         "ws://127.0.0.1:7880")

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
    )
    return {
        "token":    token.to_jwt(),
        "url":      lk_url,
        "room":     room_name,
        "identity": identity,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8880)
