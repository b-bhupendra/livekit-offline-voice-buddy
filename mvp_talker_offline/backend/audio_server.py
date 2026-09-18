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

os.environ["HF_HUB_OFFLINE"] = "1"

from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from structured_logger import tts_logger

app = FastAPI(title="Buddy Offline Piper TTS & Audio Server")

# Enable CORS for local dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Piper TTS setup ---
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
PIPER_VOICE_PATH = os.getenv(
    "PIPER_VOICE_PATH",
    str(MODELS_DIR / "en_US-lessac-medium.onnx"),
)
PIPER_LENGTH_SCALE = float(os.getenv("PIPER_LENGTH_SCALE", "1.18"))
PIPER_NOISE_SCALE = float(os.getenv("PIPER_NOISE_SCALE", "0.5"))
PIPER_NOISE_W_SCALE = float(os.getenv("PIPER_NOISE_W_SCALE", "0.8"))

piper_voice = None

try:
    from piper import PiperVoice
    if os.path.exists(PIPER_VOICE_PATH):
        piper_voice = PiperVoice.load(PIPER_VOICE_PATH)
        tts_logger.info(f"Piper TTS ready (voice: {PIPER_VOICE_PATH}, length_scale: {PIPER_LENGTH_SCALE}).")
except ImportError:
    pass

def clean_tts_text(text: str) -> str:
    cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    cleaned = re.sub(r'[^\w\s.,!?;:\'\"-]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def synthesize_wav_piper(text: str) -> bytes:
    from piper import SynthesisConfig
    text = clean_tts_text(text)
    if not text:
        text = "..."
    config = SynthesisConfig(
        length_scale=PIPER_LENGTH_SCALE,
        noise_scale=PIPER_NOISE_SCALE,
        noise_w_scale=PIPER_NOISE_W_SCALE
    )
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wav_file:
            piper_voice.synthesize_wav(text, wav_file, syn_config=config)
        return wav_io.getvalue()

# --- Focused Piper TTS Endpoint ---
@app.post("/v1/audio/speech")
@app.post("/synthesize")
async def speech(request: Request):
    """OpenAI-compatible audio speech synthesis endpoint powered by local Piper TTS."""
    data = await request.json()
    input_text = data.get("input", "") or data.get("text", "")
    if not input_text:
        return Response(content=b"", media_type="audio/wav")
    wav_bytes = synthesize_wav_piper(input_text)
    return Response(content=wav_bytes, media_type="audio/wav")

# --- LiveKit Token Minting Endpoint ---
@app.get("/api/token")
async def get_livekit_token(identity: str = "web-user", room_name: str = "buddy-room"):
    """
    Mints a LiveKit JWT access token allowing the browser to join as a full WebRTC participant.
    Grants room_join, audio publishing (mic), audio subscription (speaker), and data streams.
    """
    from livekit import api
    api_key = os.getenv("LIVEKIT_API_KEY", "devkey")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "secret")
    lk_url = os.getenv("LIVEKIT_URL", "ws://127.0.0.1:7880")

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
        .with_room_config(
            api.RoomConfiguration(
                agents=[api.RoomAgentDispatch(agent_name="offline-buddy")]
            )
        )
    )
    return {
        "token": token.to_jwt(),
        "url": lk_url,
        "room": room_name,
        "identity": identity
    }

if __name__ == "__main__":
    uvicorn.run("audio_server:app", host="0.0.0.0", port=8880, reload=False)
