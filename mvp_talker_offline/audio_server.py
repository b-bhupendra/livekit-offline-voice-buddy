"""Local OpenAI-compatible Audio Microservice (STT & TTS).
Provides:
  POST /v1/audio/speech           -> TTS (Piper, fully on-device; pyttsx3/edge-tts fallback)
  POST /v1/audio/transcriptions   -> STT (faster-whisper)

TTS engine order, chosen once at startup:
  1. Piper (piper-tts)   - real offline neural TTS, no network call per request
  2. pyttsx3             - offline, lower quality, uses the OS speech engine
  3. edge-tts             - LAST RESORT ONLY. This calls Microsoft's cloud TTS
                            service over the network on every request, which
                            breaks the "fully offline" goal of this project.
                            It's kept only so the server never hard-fails if
                            you haven't downloaded a Piper voice yet.
"""

import io
import os
import re
import wave
import tempfile
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"

from fastapi import FastAPI, UploadFile, File, Form, Response, Request
from fastapi.responses import JSONResponse
import uvicorn
from faster_whisper import WhisperModel

app = FastAPI(title="Local Offline Audio Server")

whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        print("Initializing Faster-Whisper (tiny.en) [offline]...")
        whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8", local_files_only=True)
        print("Faster-Whisper ready!")
    return whisper_model

# --- TTS engine setup -------------------------------------------------------
# Piper voice files (.onnx + .onnx.json) are expected in ./models/. Download
# once with, e.g.:
#   python -m piper.download_voices en_US-lessac-medium --data-dir models
PIPER_VOICE_PATH = os.getenv(
    "PIPER_VOICE_PATH",
    str(Path(__file__).resolve().parent / "models" / "en_US-lessac-medium.onnx"),
)
# Voice pacing and clarity: length_scale > 1.0 makes speech slower and more articulate; noise_scale < 0.6 reduces jitter
PIPER_LENGTH_SCALE = float(os.getenv("PIPER_LENGTH_SCALE", "1.18"))
PIPER_NOISE_SCALE = float(os.getenv("PIPER_NOISE_SCALE", "0.5"))
PIPER_NOISE_W_SCALE = float(os.getenv("PIPER_NOISE_W_SCALE", "0.8"))

piper_voice = None
TTS_ENGINE = None

try:
    from piper import PiperVoice

    if os.path.exists(PIPER_VOICE_PATH):
        piper_voice = PiperVoice.load(PIPER_VOICE_PATH)
        TTS_ENGINE = "piper"
        print(f"Piper TTS ready (voice: {PIPER_VOICE_PATH}).")
    else:
        print(
            f"Piper is installed but no voice found at {PIPER_VOICE_PATH}. "
            "Run: python -m piper.download_voices en_US-lessac-medium --data-dir models"
        )
except ImportError:
    print("piper-tts not installed (pip install piper-tts).")

if TTS_ENGINE is None:
    try:
        import pyttsx3  # noqa: F401

        TTS_ENGINE = "pyttsx3"
        print("Falling back to pyttsx3 (offline, lower quality).")
    except ImportError:
        pass

if TTS_ENGINE is None:
    try:
        import edge_tts  # noqa: F401

        TTS_ENGINE = "edge_tts"
        print(
            "WARNING: falling back to edge-tts. This requires an internet "
            "connection and sends your text to Microsoft's cloud TTS service "
            "on every reply -- it is NOT offline. Install piper-tts and "
            "download a voice to fix this."
        )
    except ImportError:
        pass

if TTS_ENGINE is None:
    print("ERROR: no TTS engine available. /v1/audio/speech will return silence.")

def clean_text_for_speech(text: str) -> str:
    """Strip markdown symbols before speech synthesis."""
    text = re.sub(r"\[/?(PRIVATE KNOWLEDGE|MEMORY)[^\]]*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*#`_~>]", " ", text)
    text = re.sub(r"^\s*[-+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", text).strip()

@app.get("/health")
async def health():
    return {"status": "ok", "models": ["whisper-1", "tts-1"]}

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "whisper-1", "object": "model"},
            {"id": "tts-1", "object": "model"}
        ]
    }

@app.post("/v1/audio/speech")
async def create_speech(request: Request):
    """OpenAI-compatible TTS endpoint. Uses whichever engine was detected at startup."""
    body = await request.json()
    input_text = body.get("input", "")
    voice = body.get("voice", "default")
    clean_text = clean_text_for_speech(input_text)

    if not clean_text or TTS_ENGINE is None:
        return Response(content=b"", media_type="audio/mpeg")

    try:
        if TTS_ENGINE == "piper":
            from piper.config import SynthesisConfig

            syn_config = SynthesisConfig(
                length_scale=PIPER_LENGTH_SCALE,
                noise_scale=PIPER_NOISE_SCALE,
                noise_w_scale=PIPER_NOISE_W_SCALE,
            )
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav_file:
                piper_voice.synthesize_wav(clean_text, wav_file, syn_config=syn_config)
            return Response(content=buffer.getvalue(), media_type="audio/wav")

        elif TTS_ENGINE == "pyttsx3":
            import pyttsx3

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 155)  # Slightly slower and clearer (default 200)
                engine.save_to_file(clean_text, tmp_path)
                engine.runAndWait()
                with open(tmp_path, "rb") as audio_file:
                    audio_data = audio_file.read()
                return Response(content=audio_data, media_type="audio/wav")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        elif TTS_ENGINE == "edge_tts":
            import edge_tts

            if voice in ("alloy", "default"):
                voice = "en-US-GuyNeural"
            elif voice in ("nova", "shimmer"):
                voice = "en-US-JennyNeural"

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            try:
                # -12% rate for clear, well-paced spoken English
                communicate = edge_tts.Communicate(clean_text, voice, rate="-12%")
                await communicate.save(tmp_path)
                with open(tmp_path, "rb") as audio_file:
                    audio_data = audio_file.read()
                return Response(content=audio_data, media_type="audio/mpeg")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    except Exception as e:
        print(f"TTS error ({TTS_ENGINE}): {e}")
        return Response(content=b"", media_type="audio/mpeg")

@app.post("/v1/audio/transcriptions")
async def create_transcription(
    file: UploadFile = File(...),
    model: str = Form("whisper-1"),
    language: str = Form(None)
):
    """OpenAI-compatible STT transcription endpoint."""
    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        model_instance = get_whisper_model()
        segments, info = model_instance.transcribe(
            tmp_path,
            beam_size=1,
            language=language or "en",
            condition_on_previous_text=False
        )
        transcript = " ".join(seg.text for seg in segments).strip()
        return JSONResponse(content={"text": transcript})
    except Exception as e:
        print(f"Transcription error: {e}")
        return JSONResponse(content={"text": ""})
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8880, log_level="warning")
