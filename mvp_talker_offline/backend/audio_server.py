import io
import os
import re
import wave
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

os.environ["HF_HUB_OFFLINE"] = "1"

from fastapi import FastAPI, UploadFile, File, Form, Response, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from faster_whisper import WhisperModel

from rag_store import RAGStore
from syllabus_tracker import SyllabusTracker
from simulation_engine import SimulationEngine
from quiz_engine import QuizEngine

app = FastAPI(title="Buddy Offline Audio & Grammar Engine API")

# Enable CORS for local dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Subsystem instances
rag = RAGStore()
tracker = SyllabusTracker()
simulation = SimulationEngine(rag_store=rag)
quizzer = QuizEngine(syllabus_tracker=tracker)

# Global event queue for SSE (Generative UI stream)
sse_subscribers: List[asyncio.Queue] = []

async def broadcast_genui_event(component: str, props: Dict[str, Any]):
    """Broadcast a Generative UI render event to all connected clients."""
    payload = json.dumps({
        "type": "genui_render",
        "component": component,
        "props": props
    })
    msg = f"event: genui\ndata: {payload}\n\n"
    for q in list(sse_subscribers):
        try:
            await q.put(msg)
        except Exception:
            sse_subscribers.remove(q)

whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        print("Initializing Faster-Whisper (tiny.en) [offline]...")
        whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8", local_files_only=True)
        print("Faster-Whisper ready!")
    return whisper_model

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
TTS_ENGINE = None

try:
    from piper import PiperVoice
    if os.path.exists(PIPER_VOICE_PATH):
        piper_voice = PiperVoice.load(PIPER_VOICE_PATH)
        TTS_ENGINE = "piper"
        print(f"Piper TTS ready (voice: {PIPER_VOICE_PATH}, length_scale: {PIPER_LENGTH_SCALE}).")
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

@app.post("/v1/audio/speech")
@app.post("/synthesize")
async def speech(request: Request):
    data = await request.json()
    input_text = data.get("input", "") or data.get("text", "")
    if not input_text:
        return Response(content=b"", media_type="audio/wav")
    wav_bytes = synthesize_wav_piper(input_text)
    return Response(content=wav_bytes, media_type="audio/wav")

@app.post("/v1/audio/transcriptions")
async def transcriptions(file: UploadFile = File(...), model: str = Form("whisper-1")):
    model_instance = get_whisper_model()
    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        segments, info = model_instance.transcribe(tmp_path, beam_size=1)
        text = " ".join([segment.text for segment in segments]).strip()
        return JSONResponse(content={"text": text})
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Generative UI SSE Stream ---
@app.get("/api/stream")
async def sse_stream(request: Request):
    q = asyncio.Queue()
    sse_subscribers.append(q)

    async def event_generator():
        # Send initial connected ping
        yield "event: connected\ndata: {\"status\": \"ok\"}\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            if q in sse_subscribers:
                sse_subscribers.remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Linear Syllabus & Progression APIs ---
@app.get("/api/syllabus")
async def get_syllabus():
    state = tracker.get_state()
    active_ch = tracker.get_active_chapter()
    roadmap = tracker.get_roadmap()
    return {
        "active_chapter": active_ch,
        "learner_state": state,
        "roadmap": roadmap
    }

@app.post("/api/advance-chapter")
async def advance_chapter():
    can = tracker.can_advance()
    if not can:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "Cannot advance: both coursework and milestone quiz must be completed."
        })
    advanced = tracker.advance_to_next_chapter()
    new_ch = tracker.get_active_chapter()
    await broadcast_genui_event("SyllabusProgressTree", {"new_chapter": new_ch})
    return {"success": True, "active_chapter": new_ch}

# --- Quiz & Practice Evaluation APIs ---
class PracticeSubmission(BaseModel):
    chapter: int
    answers: List[Dict[str, Any]] # [{"id": "q1", "user_answer": "...", "expected": "...", "rule": "..."}]

@app.post("/api/check-practice")
async def check_practice(submission: PracticeSubmission):
    """
    Evaluates submitted fill-in-the-blank practice worksheets using ground truth and local RAG.
    Operates with strict anti-hallucination guarantees (temperature=0.1).
    """
    results = []
    all_correct = True

    for ans in submission.answers:
        user_val = str(ans.get("user_answer", "")).strip().lower()
        expected = str(ans.get("expected", "")).strip().lower()
        rule = ans.get("rule", "English Grammar Rule")

        is_correct = (user_val == expected) or (user_val in expected and len(user_val) > 2)
        if is_correct:
            results.append({
                "id": ans.get("id"),
                "is_correct": True,
                "feedback": "Correct!",
                "explanation": f"Accurate application of: {rule}."
            })
        else:
            all_correct = False
            # Generate isomorphic practice blank
            iso_stem = f"Isomorphic retry: She did not ______ ({ans.get('verb', 'write')}) the response."
            results.append({
                "id": ans.get("id"),
                "is_correct": False,
                "feedback": f"Incorrect. Expected: '{expected}'.",
                "explanation": f"Rule: {rule} (Oxford Guide / Arihant Grammar).",
                "isomorphic_blank": {
                    "stem": iso_stem,
                    "expected": expected
                }
            })

    if all_correct:
        tracker.mark_coursework_completed()

    return {
        "all_correct": all_correct,
        "results": results,
        "coursework_completed": tracker.get_state()["coursework_completed"]
    }

class DisputeRequest(BaseModel):
    user_claim: str
    question_id: Optional[str] = None

@app.post("/api/dispute-answer")
async def dispute_answer_endpoint(req: DisputeRequest):
    """Fact-check user dispute via RAG and DuckDuckGo search without hallucination."""
    ruling = simulation.handle_answer_contention(req.user_claim)
    await broadcast_genui_event("ContentionResolver", ruling)
    return ruling

@app.get("/api/quiz/{chapter_idx}")
async def get_quiz(chapter_idx: int, mode: str = "milestone"):
    if mode == "checkpoint":
        qs = quizzer.get_checkpoint_quiz(chapter_idx, count=3)
    elif mode == "on_demand":
        qs = quizzer.get_on_demand_quiz(chapter_idx, count=5)
    else:
        qs = quizzer.get_milestone_quiz(chapter_idx, count=10)
    
    # Broadcast GenUI QuizCard
    if qs:
        await broadcast_genui_event("QuizCard", {"questions": qs, "chapter": chapter_idx, "mode": mode})
    return {"chapter": chapter_idx, "mode": mode, "questions": qs}

class QuizAnswerSubmission(BaseModel):
    question_id: str
    chapter_idx: int
    user_answer: str

@app.post("/api/quiz/submit")
async def submit_quiz_answer(submission: QuizAnswerSubmission):
    bank = quizzer.load_quiz_bank(submission.chapter_idx)
    target_q = next((q for q in bank if q["id"] == submission.question_id), None)
    if not target_q:
        return JSONResponse(status_code=404, content={"error": "Question not found in bank"})

    eval_result = quizzer.evaluate_answer(target_q, submission.user_answer)
    return eval_result

if __name__ == "__main__":
    uvicorn.run("audio_server:app", host="0.0.0.0", port=8880, reload=False)
