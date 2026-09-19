"""LiveKit Offline Voice AI Agent — English Grammar Master Coach & Simulator.
2026 Architectural Spec:
- STT: In-memory Faster-Whisper (zero HTTP socket serialization, CPU int8) with StreamAdapter
- VAD: Local Silero VAD (shared instance)
- Turn Detector: Local Audio Turn Detector (v1-mini on CPU)
- LLM: Local Ollama Qwen (qwen-buddy) via openai.LLM.with_ollama
- TTS: Kokoro-82M ONNX af_heart voice (warm, expressive, ~80-150ms) via local audio_server
- In-Process Tools: Hybrid ChromaDB RAG, DuckDuckGo search, dispute resolver, LangGraph tutor
"""

import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
import time
import asyncio
import datetime
import json
import sqlite3
import aiohttp
import contextlib
import subprocess
from typing import Optional, List, Dict, Any, Union
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

from core.structured_logger import (
    stt_logger, llm_logger, tts_logger, rag_logger, genui_logger, system_logger,
    next_turn, set_session_id, get_session_id, get_turn_id
)

# Configure dynamic library search path if local user libraries exist (safe environment setup without re-exec)
lib_dir = str(Path.home() / ".local/usr/lib/x86_64-linux-gnu")
if os.path.exists(lib_dir) and lib_dir not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from faster_whisper import WhisperModel
from livekit import rtc
from livekit import agents
from livekit.agents import (
    Agent, AgentServer, AgentSession, ChatContext, ChatMessage,
    TurnHandlingOptions, inference, function_tool, RunContext, stt, utils
)
from livekit.plugins import openai, silero

from engines.syllabus_tracker import SyllabusTracker
from engines.simulation_engine import SimulationEngine
from engines.quiz_engine import QuizEngine
from engines.rag_store import RAGStore
try:
    from tutor.langgraph_tutor_graph import langgraph_engine
except Exception:
    langgraph_engine = None

from core.gpu_arbiter import gpu_arbiter
from tutor.curriculum_notify import (
    register_active_session, flush_pending_announcements, push_ready_event, get_active_session
)
from tutor.curriculum_jobs import enqueue_reconsider, enqueue_build, enqueue_refine
from engines import curriculum_store

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen-buddy")
AUDIO_SERVER_URL = os.getenv("AUDIO_SERVER_URL", "http://127.0.0.1:8880/v1")
LIVEKIT_TRANSPORT_MODE = os.getenv("LIVEKIT_TRANSPORT_MODE", "webrtc")

_audio_server_proc: Optional[subprocess.Popen] = None

tracker = SyllabusTracker()
rag = RAGStore()
simulation = SimulationEngine(rag_store=rag)
quizzer = QuizEngine(syllabus_tracker=tracker)

async def ensure_audio_server_async():
    """
    Verify the local audio server is reachable via HTTP.
    Uses aiohttp (already imported) — no raw socket.connect() hacks.
    If not running, log a clear actionable message rather than spawning a subprocess.
    (Run audio_server.py as a separate process before starting the agent.)
    """
    url = f"{AUDIO_SERVER_URL.rstrip('/v1')}/v1/audio/speech"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                url,
                json={"input": "."},
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                if resp.status < 500:
                    tts_logger.info("Audio server (Kokoro TTS) is reachable.")
                    return
    except Exception:
        pass
    tts_logger.warning(
        "Audio server not reachable at port 8880. "
        "Start it with: python backend/audio_server.py"
    )

INSTRUCTIONS = """
You are Buddy, a warm, friendly conversational English companion who can seamlessly switch into Master English Tutor Mode.
You are chatting with your friend and learner, Bhupendra, in real time over voice.

MODES OF OPERATION:

1. BUDDY MODE (DEFAULT CASUAL CHAT & SOFT RECASTING):
   - You are a genuine human friend: warm, relaxed, lively, and conversational. Never say 'As an AI' or act robotic.
   - You remember Bhupendra's entire learning history, mastered patterns, and common grammar slips.
   - Soft Grammar Guidance: When Bhupendra makes a grammatical slip, NEVER lecture him or break the conversation. Softly and conversationally point it out in a friendly one-liner, then keep the chat moving.
     * Example: Bhupendra says 'I have many informations about the project.' -> Buddy: 'Nice! Quick friendly reminder: in English information is mass uncountable, so we say "a lot of information" — but tell me, what did you discover?'
   - Triggering Tutor Mode: If Bhupendra asks to study, learn a topic, or enter tutor mode ('Teach me about nouns', 'Tutor mode', 'Let's practice sentence repetition', 'Workplace English practice', 'Start lesson'), invoke `start_tutor_mode` or `deliver_canvas_lecture`.

2. MASTER TUTOR MODE (DYNAMIC CURRICULUM, CANVAS VISUALS & MULTI-TYPE PRACTICE):
   - When activated, you are an inspiring, authoritative English Master Coach powered by LangGraph and local reference books (Oxford Guide, Arihant, Teacher Luke's course).
   - FOUR PRACTICE SESSION TYPES SUPPORTED:
     * `grammar_mastery`: Deep syntactic rules, concord balance scale, countable vs uncountable particle sorting, compound head-noun pluralization, possessive genitives.
     * `sentence_repetition`: Spoken sentence shadowing of daily talk, rhythm & cadence, connected speech, contractions (wanna, gonna, could've, what're you).
     * `workplace_office`: Professional polite softening (transforming blunt imperatives into collaborative requests), meeting interjections, executive register.
     * `conversational_banter`: Natural daily talk, storytelling connectors, reactive dialogue.
   - STEP 1 (HOMEWORK CHECK): If the tool reports pending homework from the previous session, warmly ask about it first and invoke `complete_homework`.
   - STEP 2 (UNINTERRUPTED VOICE LECTURE + INTERACTIVE CANVAS):
     * Deliver the session by invoking `deliver_canvas_lecture`.
     * The tool renders 2 to 3 rich educational paragraphs and an interactive HTML5 Canvas visual (particle classifiers, concord balance scales, repetition cadence waves, or workplace matrices) to Bhupendra's screen, and persists it in SQLite for lifelong revision.
     * SPOKEN VOICE SCRIPT: During the lecture delivery, speak ONLY 2 to 3 clear, conversational sentences summarizing the core intuition, and announce the visual on screen.
   - STEP 3 (POST-LECTURE DISCUSSION & COUNTER-QUESTIONS):
     * Once the lecture is delivered, open the floor: invite Bhupendra to ask questions, debate grammar nuances, or ask you to re-narrate with different analogies (software engineering, business, or everyday life).
     * If Bhupendra asks to re-narrate or clarify, invoke `renarrate_lecture` or explain with fresh metaphors.
   - STEP 4 (ISOMORPHIC PATTERN QUIZZING & SHADOWING REPETITION):
     * Test the pattern directly with bite-sized challenges or invite him to shadow the practice sentences shown on screen.
     * When Bhupendra gets it right, celebrate and invoke `record_pattern_mastery`.
   - STEP 5 (ASSIGN HOMEWORK & RETURN TO BUDDY):
     * Assign a bite-sized spoken challenge and invoke `assign_homework`.
     * When Bhupendra wants to relax ('Let's just chat', 'Back to buddy mode', 'Exit tutor'), invoke `exit_tutor_mode` or `switch_to_buddy_mode`.

3. SPOKEN VOICE PERFECTION (MANDATORY):
   - You are a voice-first agent. Keep spoken replies concise: 1 to 3 clean sentences per turn.
   - NEVER emit raw markdown symbols: NO asterisks (*), NO bullet dashes (-), NO hashtags (###), NO bracketed status tags. Output natural, clean conversational English only.
   - Always end your turn with an engaging, friendly question or conversational prompt to invite him to speak.

4. VISUAL SYNTACTIC MOVEMENT (MANDATORY):
   - When explaining sentence transformations, negative inversions, questions, or passive voice shifts, invoke `demonstrate_grammar_movement` to animate tokens physically across the user's screen using Framer Motion.
"""

class FasterWhisperSTT(stt.STT):
    def __init__(self, model_size="tiny.en", device="cpu", compute_type="int8"):
        super().__init__(capabilities=stt.STTCapabilities(streaming=True, interim_results=True))
        stt_logger.info(f"Initializing in-memory Faster-Whisper ({model_size}) on {device} [100% offline]...")
        try:
            self._model = WhisperModel(model_size, device=device, compute_type=compute_type, local_files_only=True)
        except Exception:
            self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        stt_logger.info("In-memory STT ready.")

    def stream(
        self,
        *,
        language=None,
        conn_options=None,
    ) -> stt.RecognizeStream:
        from livekit.plugins import silero
        vad = silero.VAD.load()
        adapter = stt.StreamAdapter(stt=self, vad=vad)
        kwargs = {}
        if language is not None:
            kwargs["language"] = language
        if conn_options is not None:
            kwargs["conn_options"] = conn_options
        return adapter.stream(**kwargs)

    async def _recognize_impl(
        self, buffer: utils.AudioBuffer, *, language=None, conn_options=None
    ) -> stt.SpeechEvent:
        if isinstance(buffer, list):
            frame = rtc.combine_audio_frames(buffer)
        else:
            frame = buffer

        if not frame or frame.samples_per_channel == 0:
            return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])

        if frame.sample_rate != 16000 or frame.num_channels != 1:
            resampler = rtc.AudioResampler(input_rate=frame.sample_rate, output_rate=16000, num_channels=1)
            resampled_frames = resampler.push(frame)
            flushed = resampler.flush()
            if flushed:
                resampled_frames.extend(flushed)
            if not resampled_frames:
                return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])
            frame = rtc.combine_audio_frames(resampled_frames)

        audio_np = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32) / 32768.0

        HALLUCINATED_PHRASES = {
            "thank you.", "thank you", "thanks for watching.", "thanks for watching",
            "thank you for watching.", "subtitles by", "subtitles by the amara.org community",
            "bye.", "bye", "you", "so", "watching."
        }

        def run_inference():
            lang = language if isinstance(language, str) else "en"
            # Pedagogical STT configuration:
            # - condition_on_previous_text=False preserves raw acoustic output without auto-correcting ESL learner grammar errors.
            # - initial_prompt instructs Whisper's decoder to transcribe verbatim slips rather than 'fixing' them.
            segments, info = self._model.transcribe(
                audio_np,
                beam_size=1,
                language=lang,
                condition_on_previous_text=False,
                initial_prompt="Raw verbatim ESL English learner speech transcription. Transcribe grammatical errors, ungrammatical phrasing, and dropped words exactly as spoken without correcting.",
                temperature=0.0,
                no_speech_threshold=0.6,
            )
            text = " ".join(seg.text for seg in segments).strip()
            if text.lower().strip() in HALLUCINATED_PHRASES:
                text = ""
            return text, info.language

        loop = asyncio.get_event_loop()
        text, detected_lang = await loop.run_in_executor(None, run_inference)

        if text:
            stt_logger.info(f"Transcribed audio: \"{text}\" (lang={detected_lang})")
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(text=text, language=detected_lang)]
            )
        else:
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[]
            )

_whisper_singleton = None

def get_faster_whisper_stt(model_size="tiny.en") -> FasterWhisperSTT:
    global _whisper_singleton
    if _whisper_singleton is None:
        _whisper_singleton = FasterWhisperSTT(model_size=model_size)
    return _whisper_singleton

class StreamingFasterWhisperAdapter(stt.StreamAdapter):
    """
    Adapter enabling streaming STT compatibility while supporting both positional
    and keyword arguments, and explicitly exposing streaming=True and interim_results=True.
    """
    def __init__(self, stt_instance=None, vad_instance=None, **kwargs):
        target_stt = stt_instance if stt_instance is not None else kwargs.get("stt")
        target_vad = vad_instance if vad_instance is not None else kwargs.get("vad")
        super().__init__(stt=target_stt, vad=target_vad)
        self._capabilities = stt.STTCapabilities(
            streaming=True,
            interim_results=True,
            diarization=False,
            keyterms=getattr(target_stt.capabilities, "keyterms", False) if target_stt else False,
            chat_context=getattr(target_stt.capabilities, "chat_context", False) if target_stt else False,
        )

    @property
    def capabilities(self) -> stt.STTCapabilities:
        return self._capabilities

# ── PRIORITY MANAGER ──
OLLAMA_BG_URL = os.getenv("OLLAMA_BG_URL", "")

class VoiceTurnPriorityManager:
    def __init__(self):
        self.user_speaking = False
        self.agent_state = "listening"

    @property
    def is_voice_active(self) -> bool:
        return self.user_speaking or self.agent_state in ["thinking", "speaking"]

    async def wait_if_active(self):
        while self.is_voice_active:
            await asyncio.sleep(0.05)

    async def __aenter__(self):
        await self.wait_if_active()
        return self
        
    async def __aexit__(self, exc_type, exc, tb):
        pass

voice_priority_lock = VoiceTurnPriorityManager()

# ── IN-PROCESS NATIVE LIVEKIT FUNCTION TOOLS & TEXT STREAM BROADCASTS ────────

_active_room: Optional[rtc.Room] = None
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = WORKSPACE_ROOT / "data"
DB_PATH = DATA_DIR / "memory.db"

_db_initialized = False

def _init_db_schema(conn: sqlite3.Connection) -> None:
    global _db_initialized
    if not _db_initialized:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_message TEXT,
                    assistant_response TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learner_recasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    original_utterance TEXT,
                    polished_recast TEXT,
                    grammar_rule TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sheet_payloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    req_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    component TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    session_id TEXT
                )
            """)
        _db_initialized = True

@contextlib.contextmanager
def get_db_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_db_schema(conn)
    try:
        yield conn
    finally:
        conn.close()

def persist_sheet_payload(req_id: str, component: str, payload_data: Union[Dict[str, Any], str], session_id: Optional[str] = None) -> None:
    """Persist a GenUI sheet payload keyed by req_id in SQLite for in-flight reconnect hydration."""
    try:
        payload_str = json.dumps(payload_data) if isinstance(payload_data, dict) else str(payload_data)
        sid = session_id or get_session_id()
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO sheet_payloads (req_id, component, payload, session_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(req_id) DO UPDATE SET
                    component=excluded.component,
                    payload=excluded.payload,
                    session_id=excluded.session_id,
                    timestamp=CURRENT_TIMESTAMP
            """, (req_id, component, payload_str, sid))
            conn.commit()
        genui_logger.event("SHEET_PERSISTED", f"req_id={req_id}, component={component}", req_id=req_id, component=component)
    except Exception as e:
        genui_logger.error(f"Failed to persist sheet payload req_id={req_id}: {e}")

def get_last_sheet_payload() -> Optional[Dict[str, Any]]:
    """Retrieve the most recent sheet payload from SQLite."""
    try:
        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT req_id, component, payload, timestamp, session_id
                FROM sheet_payloads
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()
            if row:
                try:
                    parsed_payload = json.loads(row["payload"])
                except Exception:
                    parsed_payload = row["payload"]
                return {
                    "req_id": row["req_id"],
                    "component": row["component"],
                    "payload": parsed_payload,
                    "timestamp": row["timestamp"],
                    "session_id": row["session_id"],
                    "status": "ok"
                }
    except Exception as e:
        genui_logger.error(f"Failed to fetch last sheet payload from SQLite: {e}")
    return None

async def emit_sheet_error(
    context: Optional[RunContext],
    component_attempted: str,
    error_message: str,
    req_id: Optional[str] = None,
    details: Optional[str] = None,
    retryable: bool = True
) -> Dict[str, Any]:
    """Gracefully surfaces generation errors directly to the connected room as an inline GenUI card."""
    rid = req_id or f"req_err_{int(time.time() * 1000)}"
    error_payload = {
        "schema_version": "1.0",
        "type": "genui_render",
        "component": "sheet_error",
        "props": {
            "req_id": rid,
            "error_code": "GENUI_SYNTHESIS_ERROR",
            "title": f"Interactive {component_attempted} Unavailable",
            "message": error_message,
            "component_attempted": component_attempted,
            "retryable": retryable,
            "details": details or error_message
        }
    }
    genui_logger.error(f"Surfacing GenUI error: {error_message} for component {component_attempted}", req_id=rid)
    persist_sheet_payload(rid, "sheet_error", error_payload)
    await send_room_text(context, "genui", json.dumps(error_payload))
    return error_payload

async def send_room_text(context: Optional[RunContext], topic: str, payload_str: str):
    """
    Pushes real-time UI/artifact updates directly to the connected room
    via ctx.room.local_participant.send_text() with zero loopback overhead.
    """
    room = None
    if context and hasattr(context, "session"):
        try:
            room_io = getattr(context.session, "_room_io", None)
            if room_io:
                room = getattr(room_io, "room", None)
        except Exception:
            pass
    if not room:
        room = _active_room
    if room and room.isconnected():
        try:
            await room.local_participant.send_text(payload_str, topic=topic)
        except Exception as e:
            genui_logger.error(f"Failed to broadcast text on topic '{topic}': {e}")
    else:
        genui_logger.debug(f"send_room_text: room not connected or not present (topic={topic})")

async def broadcast_livekit_text(topic: str, payload_str: str):
    await send_room_text(None, topic, payload_str)

async def _ollama_stream(prompt: str, system: str = "", model: str = None):
    """
    Asynchronous generator that streams tokens from Ollama using aiohttp.
    Respects the VoiceTurnPriorityManager lock so background generations 
    don't starve the conversational audio pipeline.
    """
    model = model or OLLAMA_MODEL
    body = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": True,
        "options": {"temperature": 0.4, "num_predict": 800}
    }
    
    bg_url = OLLAMA_BG_URL if OLLAMA_BG_URL else OLLAMA_BASE_URL
    use_lock = not bool(OLLAMA_BG_URL)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{bg_url.rstrip('/')}/api/generate", json=body) as resp:
                async for line in resp.content:
                    line_str = line.decode('utf-8').strip()
                    if line_str:
                        if use_lock:
                            # Yield execution if voice is active
                            async with voice_priority_lock:
                                pass
                        try:
                            chunk = json.loads(line_str)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        llm_logger.error(f"Ollama streaming error: {e}")
        yield f"[Ollama error: {e}]"

@function_tool()
async def query_grammar_rag(context: RunContext, query: str) -> str:
    """Query verified Oxford Guide and Arihant General English grammar chunks for rules and citations."""
    rag_logger.info(f"Querying grammar RAG: \"{query}\"")
    active_info = tracker.get_active_chapter()
    active_ch = active_info.get("chapter_idx", 1)
    results = rag.hybrid_search(query, top_k=3, chapter_filter=active_ch)
    if not results:
        results = rag.hybrid_search(query, top_k=3)
    if not results:
        emb_status = rag.get_embedding_status()
        if not emb_status.get("is_available"):
            rag_logger.warning("Local embedding service unreachable during RAG query")
            return (
                f"[Embedding Service Offline]: Local embedding engine ({emb_status.get('model')}) is unreachable. "
                f"Sparse keyword search returned no direct matches in the local grammar reference. "
                f"Check local Ollama service at {emb_status.get('endpoint')}."
            )
        return "No direct grammar matches found in local reference."
    
    rag_logger.info(f"RAG search returned {len(results)} chunks")
    chunks = [
        f"[{r.get('source_title', 'Grammar Guide')} - Section: {r.get('section_title', '')}]\n{r['text']}"
        for r in results
    ]
    header = ""
    if not rag.is_embedding_available:
        header = "[Notice: Embedding service offline; results retrieved via verified keyword search]\n\n"
    return header + "\n\n".join(chunks)

@function_tool()
async def trigger_quiz(context: RunContext, chapter: int, mode: str = "milestone") -> str:
    """Generate or retrieve a grammar quiz for the active chapter and push UI updates directly via LiveKit text stream."""
    req_id = f"req_quiz_{int(time.time() * 1000)}"
    try:
        qs = quizzer.get_milestone_quiz(chapter, count=5) if mode == "milestone" else quizzer.get_checkpoint_quiz(chapter, count=3)
        if not qs:
            raise ValueError(f"No questions found for chapter {chapter}")
        
        # Broadcast native LiveKit GenUI artifact directly to browser timeline
        payload = {
            "schema_version": "1.0",
            "type": "genui_render",
            "component": "QuizCard",
            "props": {
                "req_id": req_id,
                "questions": qs,
                "chapter": chapter,
                "mode": mode,
                "source": "llm_generated"
            }
        }
        persist_sheet_payload(req_id, "QuizCard", payload)
        await send_room_text(context, "genui", json.dumps(payload))
        genui_logger.event("QUIZ_GENERATED", f"Chapter {chapter} ({mode})", req_id=req_id, count=len(qs))
        
        return json.dumps({
            "status": "quiz_prepared",
            "req_id": req_id,
            "chapter": chapter,
            "mode": mode,
            "questions_count": len(qs),
            "questions": qs
        }, indent=2)
    except Exception as e:
        await emit_sheet_error(
            context,
            component_attempted="QuizCard",
            error_message=f"Could not generate quiz for Chapter {chapter}: {e}",
            req_id=req_id,
            details=str(e)
        )
        return json.dumps({"status": "error", "error": str(e), "req_id": req_id})

@function_tool()
async def generate_quiz(context: RunContext, chapter: int, mode: str = "milestone") -> str:
    """In-process tool to generate or retrieve chapter quiz and render interactive QuizCard directly in the UI."""
    return await trigger_quiz(context, chapter, mode)

@function_tool()
async def dispute_answer(context: RunContext, user_claim: str) -> str:
    """Resolve a learner's dispute or contention regarding whether an answer is grammatically correct or acceptable."""
    req_id = f"req_dispute_{int(time.time() * 1000)}"
    try:
        ruling = simulation.handle_answer_contention(user_claim)
        ruling["req_id"] = req_id
        
        # Broadcast native LiveKit GenUI artifact directly to browser timeline
        payload = {
            "schema_version": "1.0",
            "type": "genui_render",
            "component": "ContentionResolver",
            "props": ruling
        }
        persist_sheet_payload(req_id, "ContentionResolver", payload)
        await send_room_text(context, "genui", json.dumps(payload))
        genui_logger.event("DISPUTE_RESOLVED", f"Claim: {user_claim[:40]}", req_id=req_id)
        
        return json.dumps(ruling, indent=2)
    except Exception as e:
        await emit_sheet_error(
            context,
            component_attempted="ContentionResolver",
            error_message=f"Failed to arbitrate contention: {e}",
            req_id=req_id,
            details=str(e)
        )
        return json.dumps({"status": "error", "error": str(e), "req_id": req_id})

@function_tool()
async def get_learner_progress(context: RunContext) -> str:
    """Get current learner state, accuracy, chapter scores, and failed question queue."""
    state = tracker.get_state()
    return json.dumps(state, indent=2)

@function_tool()
async def generate_revision_notes(context: RunContext, chapter: int) -> str:
    """Synthesize structured study notes and common pitfalls for the specified chapter and push to the UI."""
    req_id = f"req_notes_{int(time.time() * 1000)}"
    try:
        active_ch = tracker.get_active_chapter()
        rag_results = rag.hybrid_search(f"chapter {chapter} rules summary", top_k=4, chapter_filter=chapter)
        context_text = "\n\n".join([r["text"] for r in rag_results]) if rag_results else ""
        
        notes_payload = {
            "req_id": req_id,
            "title": f"Chapter {chapter}: Mastery & Structure Notes",
            "chapter": chapter,
            "overview": f"Synthesized revision summary for Chapter {chapter} based on Oxford Guide & Arihant references.",
            "rules": [
                {
                    "title": "Core Syntactic Concord",
                    "body": context_text[:350] if context_text else "Subject-verb agreement must be preserved across clauses.",
                    "citation": f"Oxford Guide Ch {chapter}"
                }
            ],
            "pitfalls": [
                "Avoid subject-verb discord across intervening prepositional phrases."
            ]
        }
        payload = {
            "schema_version": "1.0",
            "type": "genui_render",
            "component": "BionicSketchNote",
            "props": {"notes": notes_payload, "req_id": req_id}
        }
        persist_sheet_payload(req_id, "BionicSketchNote", payload)
        await send_room_text(context, "genui", json.dumps(payload))
        genui_logger.event("REVISION_NOTES_GENERATED", f"Chapter {chapter}", req_id=req_id)
        
        return json.dumps({
            "chapter": chapter,
            "req_id": req_id,
            "title": f"Chapter {chapter} Revision",
            "reference_excerpt": context_text[:800],
            "status": "ready"
        }, indent=2)
    except Exception as e:
        await emit_sheet_error(
            context,
            component_attempted="BionicSketchNote",
            error_message=f"Failed to generate revision notes for Chapter {chapter}: {e}",
            req_id=req_id,
            details=str(e)
        )
        return json.dumps({"status": "error", "error": str(e), "req_id": req_id})

@function_tool()
async def demonstrate_grammar_movement(
    context: RunContext,
    title: str = "Subject-Auxiliary Inversion",
    rule: str = "In questions and emphatic inversions, the auxiliary verb moves before the subject.",
    chapter: int = 2,
    initial_tokens: Optional[Union[str, List[Dict[str, Any]]]] = None,
    transformed_tokens: Optional[Union[str, List[Dict[str, Any]]]] = None,
    explanation: str = "Observe how the auxiliary verb shifts position across the subject boundary.",
    rule_citation: str = "Oxford Guide Ch 2 & Arihant Rule 14"
) -> str:
    """Demonstrate syntactic movement (e.g. subject-auxiliary inversion, cleft sentences, passive shifts) with animated GenUI cards."""
    req_id = f"req_movement_{int(time.time() * 1000)}"
    try:
        if isinstance(initial_tokens, str):
            try:
                initial_tokens = json.loads(initial_tokens)
            except Exception:
                initial_tokens = None
        if isinstance(transformed_tokens, str):
            try:
                transformed_tokens = json.loads(transformed_tokens)
            except Exception:
                transformed_tokens = None

        if not initial_tokens:
            initial_tokens = [
                {"id": "tok-1", "text": "She", "role": "subject"},
                {"id": "tok-2", "text": "is", "role": "aux"},
                {"id": "tok-3", "text": "reading", "role": "verb"},
                {"id": "tok-4", "text": "the book.", "role": "object"}
            ]
        if not transformed_tokens:
            transformed_tokens = [
                {"id": "tok-2", "text": "Is", "role": "aux"},
                {"id": "tok-1", "text": "she", "role": "subject"},
                {"id": "tok-3", "text": "reading", "role": "verb"},
                {"id": "tok-4", "text": "the book?", "role": "object"}
            ]

        movement_id = f"movement_{int(time.time() * 1000)}"
        props = {
            "id": movement_id,
            "req_id": req_id,
            "title": title,
            "rule": rule,
            "chapter": chapter,
            "initial_tokens": initial_tokens,
            "transformed_tokens": transformed_tokens,
            "explanation": explanation,
            "rule_citation": rule_citation
        }

        payload = {
            "schema_version": "1.0",
            "type": "genui_render",
            "component": "GrammarMovement",
            "props": props
        }
        persist_sheet_payload(req_id, "GrammarMovement", payload)
        await send_room_text(context, "genui", json.dumps(payload))
        genui_logger.event("GRAMMAR_MOVEMENT_DEMO", title, req_id=req_id, movement_id=movement_id)
        return json.dumps({
            "status": "demonstration_rendered",
            "req_id": req_id,
            "movement_id": movement_id,
            "title": title,
            "chapter": chapter
        }, indent=2)
    except Exception as e:
        await emit_sheet_error(
            context,
            component_attempted="GrammarMovement",
            error_message=f"Failed to generate grammar movement demonstration: {e}",
            req_id=req_id,
            details=str(e)
        )
        return json.dumps({"status": "error", "error": str(e), "req_id": req_id})

@function_tool()
async def advance_chapter(context: RunContext) -> str:
    """Attempts to advance the learner to the next chapter in the linear syllabus if requirements are met."""
    if not tracker.can_advance():
        return "Cannot advance: both coursework and milestone quiz must be completed."
    new_ch = tracker.advance_to_next_chapter()
    await send_room_text(context, "genui", json.dumps({
        "type": "genui_render",
        "component": "SyllabusProgressTree",
        "props": {"new_chapter": new_ch}
    }))
    return f"Successfully advanced to Chapter {new_ch}."

@function_tool()
async def log_learner_recast(context: RunContext, original_utterance: str, polished_recast: str, grammar_rule: str) -> str:
    """Logs a grammatical correction or colloquial refinement for the student's study notes."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO learner_recasts (original_utterance, polished_recast, grammar_rule) VALUES (?, ?, ?)",
                (original_utterance, polished_recast, grammar_rule)
            )
            conn.commit()
    except Exception as e:
        system_logger.error(f"[log_learner_recast] DB error: {e}")
    return f"Logged recast: '{original_utterance}' -> '{polished_recast}' ({grammar_rule})"

@function_tool()
async def save_conversation_turn(context: RunContext, user_message: str, assistant_response: str) -> str:
    """Saves a conversation turn to SQLite memory store."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_history (user_message, assistant_response) VALUES (?, ?)",
                (user_message, assistant_response)
            )
            conn.commit()
    except Exception as e:
        system_logger.error(f"[save_conversation_turn] DB error: {e}")
    return "Saved turn successfully."

@function_tool()
async def search_web_grammar(context: RunContext, query: str) -> str:
    """Free web search fallback using DuckDuckGo for language disputes."""
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().text(f"grammar rule English {query[:80]}", max_results=3))
        if not results:
            return f"No authoritative web results found for: {query}"
        snippets = [f"- {r.get('title')}: {r.get('body')[:200]} ({r.get('href')})" for r in results]
        return "\n".join(snippets)
    except Exception as e:
        return f"Web search notice: {e}"

@function_tool()
async def start_tutor_mode(context: RunContext, topic: Optional[str] = None) -> str:
    """Activates focused Tutor Mode for English grammar mastery.
    Retrieves syllabus state, active topic (e.g. Nouns), and any pending homework from last session.
    """
    tutor_state = tracker.activate_tutor_mode(topic=topic)
    summary = tracker.get_learner_summary()
    await send_room_text(context, "progress", json.dumps(summary))
    
    pending_hw = tutor_state.get("pending_homework")
    active_top = tutor_state.get("current_topic", "Nouns: Concrete, Abstract & Countable")
    mastered = tutor_state.get("mastered_patterns", [])
    
    genui_logger.info(f"Tutor mode activated. Topic: {active_top}, Pending HW: {bool(pending_hw)}")
    
    if pending_hw:
        return (
            f"[TUTOR MODE ACTIVATED] You are now in Tutor Mode. "
            f"PENDING HOMEWORK FROM LAST SESSION: '{pending_hw}'. "
            f"MANDATORY: Ask Bhupendra how he did with this homework challenge first before starting the new lecture. "
            f"Upcoming topic after homework: '{active_top}'."
        )
    else:
        return (
            f"[TUTOR MODE ACTIVATED] You are now in Tutor Mode. No pending homework. "
            f"Current topic: '{active_top}'. Mastered patterns so far: {mastered}. "
            f"Deliver a short, interactive voice-first lecture in 2-3 sentences with one clear example, then check comprehension."
        )

@function_tool()
async def complete_homework(context: RunContext, student_response: str, evaluation: str) -> str:
    """Marks pending homework as completed and logs the student's response."""
    tracker.complete_homework(evaluation=evaluation)
    summary = tracker.get_learner_summary()
    await send_room_text(context, "progress", json.dumps(summary))
    genui_logger.info(f"Homework completed. Evaluation: {evaluation[:50]}")
    return "Homework marked as completed! You may now proceed with the lesson or pattern quiz."

@function_tool()
async def assign_homework(context: RunContext, homework_task: str) -> str:
    """Assigns a real-world, bite-sized spoken homework challenge for the next tutor session."""
    tracker.assign_homework(task=homework_task)
    summary = tracker.get_learner_summary()
    await send_room_text(context, "progress", json.dumps(summary))
    genui_logger.info(f"Assigned homework: {homework_task}")
    return f"Homework challenge successfully recorded: '{homework_task}'. It will be checked next time Tutor Mode starts."

@function_tool()
async def record_pattern_mastery(context: RunContext, pattern_name: str, passed: bool) -> str:
    """Records whether the learner successfully demonstrated mastery of a specific grammar pattern."""
    mastered = tracker.record_pattern_mastery(pattern=pattern_name, passed=passed)
    summary = tracker.get_learner_summary()
    await send_room_text(context, "progress", json.dumps(summary))
    genui_logger.info(f"Pattern mastery recorded: {pattern_name} (passed={passed})")
    if passed:
        return f"Pattern '{pattern_name}' mastered! Total mastered patterns: {mastered}. You can now give homework and conclude or practice the next pattern."
    else:
        return f"Pattern '{pattern_name}' not yet mastered. Offer another isomorphic practice question."

@function_tool()
async def deliver_canvas_lecture(
    context: RunContext,
    phase_index: int = 1,
    topic: str = "Nouns",
    submodule: Optional[str] = None,
    session_type: str = "grammar_mastery",
    custom_spoken_summary: Optional[str] = None,
    custom_paragraphs: Optional[Union[str, List[str]]] = None,
    canvas_type: Optional[str] = None,
    canvas_config: Optional[Union[str, Dict[str, Any]]] = None,
    repetition_items: Optional[Union[str, List[Dict[str, Any]]]] = None
) -> str:
    """Delivers a structured visual lecture across any grammar or fluency domain (grammar mastery,
    daily sentence repetition, workplace office English, or conversational banter).
    Renders 2-3 educational paragraphs and an interactive HTML5 Canvas visual, saves the session
    in SQLite for lifelong student revision, and prepares for post-lecture Q&A / counter-questions.
    """
    req_id = f"req_lecture_{int(time.time() * 1000)}"
    try:
        # Dynamically synthesize session from curriculum & RAG
        dyn_session = tracker.get_dynamic_course_session(
            topic=topic,
            submodule=submodule,
            session_type=session_type,
            phase_index=phase_index
        )
        
        submod = submodule or dyn_session["submodule"]
        spoken = custom_spoken_summary or dyn_session["spoken_summary"]
        
        if custom_paragraphs:
            if isinstance(custom_paragraphs, str):
                try:
                    paras = json.loads(custom_paragraphs)
                except Exception:
                    paras = [p.strip() for p in custom_paragraphs.split("\n\n") if p.strip()]
            else:
                paras = custom_paragraphs
        else:
            paras = dyn_session["paragraphs"]

        c_type = canvas_type or dyn_session.get("canvas_type", "particle_classifier")
        
        if canvas_config:
            if isinstance(canvas_config, str):
                try:
                    cfg = json.loads(canvas_config)
                except Exception:
                    cfg = dyn_session.get("canvas_config", {})
            else:
                cfg = canvas_config
        else:
            cfg = dyn_session.get("canvas_config", {})

        if repetition_items:
            if isinstance(repetition_items, str):
                try:
                    reps = json.loads(repetition_items)
                except Exception:
                    reps = dyn_session.get("repetition_items", [])
            else:
                reps = repetition_items
        else:
            reps = dyn_session.get("repetition_items", [])

        # Adapt content to learner preferences
        prefs = tracker.get_learner_preferences()
        analogy_style = prefs.get("analogy_style", "everyday")
        if analogy_style == "software_engineering" and "laptop" not in paras[0].lower():
            paras = [p + " (Analogy: like immutable vs mutable data structures)" for p in paras]

        saved = tracker.save_lecture_session(
            topic=topic,
            submodule=submod,
            phase_index=phase_index,
            session_type=session_type,
            spoken_summary=spoken,
            paragraphs=paras,
            canvas_type=c_type,
            canvas_config=cfg,
            repetition_items=reps,
            key_takeaways=dyn_session.get("key_takeaways", [])
        )

        # Update LangGraph state to post-lecture Q&A
        if langgraph_engine:
            langgraph_engine.update_state({
                "active_mode": "tutor_qa",
                "current_topic": topic,
                "submodule": submod,
                "phase_index": phase_index,
                "session_type": session_type,
                "is_delivering_lecture": False,
                "lecture_data": saved
            })

        payload = {
            "schema_version": "1.0",
            "type": "genui_render",
            "component": "CanvasLectureCard",
            "props": {
                "id": saved["id"],
                "req_id": req_id,
                "topic": topic,
                "submodule": submod,
                "phase_index": phase_index,
                "session_type": session_type,
                "spoken_summary": spoken,
                "paragraphs": paras,
                "key_takeaways": dyn_session.get("key_takeaways", []),
                "canvas_type": c_type,
                "canvas_config": cfg,
                "canvas_html": dyn_session.get("canvas_html", ""),
                "repetition_items": reps,
                "timestamp": saved["timestamp"]
            }
        }
        persist_sheet_payload(req_id, "CanvasLectureCard", payload)
        await send_room_text(context, "genui", json.dumps(payload))
        summary = tracker.get_learner_summary()
        await send_room_text(context, "progress", json.dumps(summary))
        genui_logger.event("CANVAS_LECTURE_DELIVERED", submod, req_id=req_id, phase=phase_index, session_type=session_type)

        return (
            f"[LECTURE RENDERED ON CANVAS] Delivered visual session '{submod}' ({session_type}, Phase {phase_index}). "
            f"SPOKEN VOICE SCRIPT: '{spoken}'. Speak this naturally to Bhupendra in 2-3 clean sentences, "
            f"then open the floor: tell him he can ask counter-questions, ask you to re-narrate, or practice the shadowing drills!"
        )
    except Exception as e:
        await emit_sheet_error(
            context,
            component_attempted="CanvasLectureCard",
            error_message=f"Failed to deliver canvas lecture: {e}",
            req_id=req_id,
            details=str(e)
        )
        return json.dumps({"status": "error", "error": str(e), "req_id": req_id})

@function_tool()
async def switch_to_buddy_mode(context: RunContext) -> str:
    """Switches from Tutor mode back to friendly conversational Buddy mode while preserving all learning memory."""
    tracker.exit_tutor_mode()
    if langgraph_engine:
        langgraph_engine.update_state({"active_mode": "buddy"})
    summary = tracker.get_learner_summary()
    await send_room_text(context, "progress", json.dumps(summary))
    genui_logger.info("Switched to buddy mode.")
    return "[BUDDY MODE ACTIVATED] Switched back to friendly casual conversation mode. Chat warmly and softly point out grammar slips."

@function_tool()
async def switch_to_tutor_mode(context: RunContext, topic: str = "Nouns", session_type: str = "grammar_mastery") -> str:
    """Switches into Master Tutor Mode to deliver an educational lecture, interactive visual canvas, and practice drills."""
    tracker.enter_tutor_mode(topic=topic)
    if langgraph_engine:
        langgraph_engine.update_state({"active_mode": "tutor_lecture", "current_topic": topic, "session_type": session_type})
    summary = tracker.get_learner_summary()
    await send_room_text(context, "progress", json.dumps(summary))
    genui_logger.info(f"Switched to tutor mode for {topic} ({session_type}).")
    return f"[TUTOR MODE ACTIVATED] Master Tutor active for '{topic}' ({session_type}). Ready to deliver lecture via deliver_canvas_lecture!"

@function_tool()
async def request_reinterpretation(
    context: RunContext,
    node_id: Optional[str] = None,
    style_hint: str = "everyday",
    learner_complaint: str = ""
) -> str:
    """Requests an alternative pedagogical explanation or analogy for a grammar/fluency concept node (e.g., everyday life, software engineering, workplace office, or sports).
    If a pre-compiled visual variant exists in SQLite, it loads immediately onto the user's screen.
    Otherwise, an async background authoring task is enqueued without blocking conversation.
    """
    if not node_id or node_id in ("current", "none", ""):
        state = tracker.get_state()
        curr_topic = state.get("current_topic", "Nouns")
        node_id = curr_topic.lower().replace(" ", "_").replace("-", "_")

    req_id = curriculum_store.log_reconsideration_request(
        node_id=node_id,
        style_hint=style_hint,
        complaint=learner_complaint
    )

    # Check if an alternative variant already exists in curriculum_store
    existing = curriculum_store.get_variant(node_id, style_hint)
    if existing:
        curriculum_store.resolve_reconsideration_request(req_id, existing.get("id"))
        draft_payload = {
            "title": f"{node_id.replace('_', ' ').title()} ({style_hint.title()})",
            "core_concept": existing.get("spoken_summary", ""),
            "canvas_type": existing.get("canvas_type", "classifier"),
            "canvas_config": existing.get("canvas_config", {}),
            "lecture_paragraphs": existing.get("lecture_paragraphs", []),
            "citations": existing.get("citations", []),
        }
        fake_state = {
            "node_id": node_id,
            "job_type": "reconsider",
            "result_id": existing.get("id"),
            "draft": draft_payload
        }
        await push_ready_event(fake_state)
        return (
            f"[RE-INTERPRETATION LOADED] Delivered pre-compiled {style_hint} visual for '{node_id}'. "
            f"Intuition: {existing.get('spoken_summary', '')}. "
            f"Explain this concept to Bhupendra in 2 spoken sentences using the {style_hint} analogy."
        )

    # If not yet generated, launch background job via arbiter and return immediate spoken response instructions
    enqueue_reconsider(node_id=node_id, style_hint=style_hint, complaint=learner_complaint, request_id=req_id)
    return (
        f"[RE-INTERPRETATION REQUESTED] Scheduled background authoring of a tailored {style_hint} visual for '{node_id}'. "
        f"Right now in voice, explain this concept directly to Bhupendra using a relatable {style_hint} analogy in 2-3 warm, conversational sentences."
    )

@function_tool()
async def renarrate_lecture(context: RunContext, analogy_style: Optional[str] = "everyday") -> str:
    """Re-narrates the current topic using alternative analogies (software engineering, business, or everyday life)."""
    return await request_reinterpretation(context=context, node_id="current", style_hint=analogy_style or "everyday")

@function_tool()
async def exit_tutor_mode(context: RunContext) -> str:
    """Exits Tutor Mode and returns to friendly conversational Buddy Mode."""
    tracker.exit_tutor_mode()
    if langgraph_engine:
        langgraph_engine.update_state({"active_mode": "buddy"})
    summary = tracker.get_learner_summary()
    await send_room_text(context, "progress", json.dumps(summary))
    if _active_session:
        unmount_tools_to_fastpath(_active_session)
    genui_logger.info("Exited tutor mode to buddy mode.")
    return "[BUDDY MODE ACTIVATED] Switched back to friendly casual conversation mode."

# Native LiveKit in-process function tools with RunContext
IN_PROCESS_TOOLS = [
    start_tutor_mode,
    switch_to_tutor_mode,
    switch_to_buddy_mode,
    deliver_canvas_lecture,
    request_reinterpretation,
    renarrate_lecture,
    complete_homework,
    assign_homework,
    record_pattern_mastery,
    exit_tutor_mode,
    query_grammar_rag,
    trigger_quiz,
    generate_quiz,
    dispute_answer,
    get_learner_progress,
    generate_revision_notes,
    demonstrate_grammar_movement,
    advance_chapter,
    log_learner_recast,
    save_conversation_turn,
    search_web_grammar
]
in_process_tools = IN_PROCESS_TOOLS
BUDDY_FAST_PATH_TOOLS = []
TUTOR_MODE_TOOLS = IN_PROCESS_TOOLS


def mount_tutor_tools(sess: AgentSession) -> None:
    """Dynamically mount the 21 tutor tools into the live session when study mode is requested."""
    try:
        sess._tools = list(TUTOR_MODE_TOOLS)
        if hasattr(sess, "update_agent"):
            sess.update_agent(Agent(instructions=INSTRUCTIONS, tools=TUTOR_MODE_TOOLS))
        llm_logger.info("[FastPath] Dynamically MOUNTED 21 tutor tools into AgentSession.")
    except Exception as e:
        llm_logger.error(f"[FastPath] Error mounting tutor tools: {e}")


def unmount_tools_to_fastpath(sess: AgentSession) -> None:
    """Revert to Zero-Tool Fast Path for sub-300ms conversational turn-taking."""
    try:
        sess._tools = []
        if hasattr(sess, "update_agent"):
            sess.update_agent(Agent(instructions=INSTRUCTIONS, tools=[]))
        llm_logger.info("[FastPath] REVERTED to Zero-Tool Fast Path (0 tools) for maximum voice fluidness.")
    except Exception as e:
        llm_logger.error(f"[FastPath] Error unmounting tools: {e}")


class BuddyAgent(Agent):
    def __init__(self):
        super().__init__(instructions=INSTRUCTIONS)

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    """Main LiveKit RTC Session entrypoint."""
    global _active_room
    await ensure_audio_server_async()

    async def cleanup_audio_server():
        global _audio_server_proc
        if _audio_server_proc and _audio_server_proc.poll() is None:
            tts_logger.info("Stopping spawned background audio server...")
            try:
                _audio_server_proc.terminate()
                _audio_server_proc.wait(timeout=2)
            except Exception:
                try:
                    _audio_server_proc.kill()
                except Exception:
                    pass

    ctx.add_shutdown_callback(cleanup_audio_server)

    llm_provider = openai.LLM.with_ollama(
        model=OLLAMA_MODEL,
        base_url=f"{OLLAMA_BASE_URL.rstrip('/')}/v1",
    )

    vad_provider = silero.VAD.load()

    turn_handling = TurnHandlingOptions(
        turn_detection=inference.TurnDetector(version="v1-mini"),
        interruption={"mode": "vad"},
    )

    # Native in-process Kokoro-82M ONNX streaming TTS plugin:
    # Sub-300ms latency, clause-boundary streaming directly to AudioEmitter
    from core.kokoro_tts import KokoroTTS
    tts_provider = KokoroTTS()

    local_whisper = get_faster_whisper_stt(model_size="tiny.en")
    stt_provider = stt.StreamAdapter(
        stt=local_whisper,
        vad=vad_provider,
    )

    session = AgentSession(
        vad=vad_provider,
        turn_handling=turn_handling,
        llm=llm_provider,
        tts=tts_provider,
        stt=stt_provider,
        tools=BUDDY_FAST_PATH_TOOLS,  # START FAST & TOOL-LESS (sub-300ms conversational TTFT)
    )

    register_active_session(session, None)

    set_session_id(ctx.room.name if ctx.room else f"session_{int(time.time())}")
    system_logger.info(f"RTC session initialized for room: {get_session_id()}")
    system_logger.info(f"Active transport mode: {LIVEKIT_TRANSPORT_MODE} (LiveKit WebRTC active, legacy SSE bridge retired)")

    @session.on("user_state_changed")
    def on_user_state(ev):
        if ev.new_state == "speaking":
            voice_priority_lock.user_speaking = True
            gpu_arbiter.set_voice_active(True)
            stt_logger.info("User started speaking")
        elif ev.new_state == "listening":
            voice_priority_lock.user_speaking = False
            if voice_priority_lock.agent_state == "listening":
                gpu_arbiter.set_voice_active(False)
            stt_logger.info("User stopped speaking, processing utterance...")

    @session.on("agent_state_changed")
    def on_agent_state(ev):
        new_state_str = str(ev.new_state).split('.')[-1].lower()
        voice_priority_lock.agent_state = new_state_str
        llm_logger.info(f"Agent state changed to: {ev.new_state}")
        if new_state_str in ("speaking", "thinking"):
            gpu_arbiter.set_voice_active(True)
        elif new_state_str == "listening":
            if not voice_priority_lock.user_speaking:
                gpu_arbiter.set_voice_active(False)
            pending = flush_pending_announcements()
            if pending and hasattr(session, "generate_reply"):
                stt_logger.info(f"Delivering pending curriculum announcement: {pending.get('title')}")
                try:
                    session.generate_reply()
                except Exception as e:
                    llm_logger.error(f"Error delivering announcement reply: {e}")

    @session.on("user_input_transcribed")
    def on_user_input(ev):
        async def _send_transcript():
            transcript = getattr(ev, "transcript", "")
            is_final = getattr(ev, "is_final", True)
            if not transcript and hasattr(ev, "alternatives") and ev.alternatives:
                transcript = ev.alternatives[0].text
            
            if transcript:
                if is_final:
                    turn = next_turn()
                    stt_logger.info(f"Final user transcript: \"{transcript}\" (turn={turn})")

                    # Dynamic mode-switching triggers to mount/unmount tools
                    lower = transcript.lower()
                    tutor_triggers = (
                        "teach me", "tutor mode", "start lesson", "start lecture",
                        "learn grammar", "practice grammar", "workplace practice",
                        "scenario mode", "study mode", "let's learn", "teach about"
                    )
                    exit_triggers = (
                        "back to buddy", "let's just chat", "exit tutor",
                        "stop lesson", "casual chat", "buddy mode", "just talk"
                    )

                    current_tools_count = len(getattr(session, "tools", []))
                    if any(trig in lower for trig in tutor_triggers):
                        if current_tools_count == 0:
                            mount_tutor_tools(session)
                    elif any(trig in lower for trig in exit_triggers):
                        if current_tools_count > 0:
                            unmount_tools_to_fastpath(session)
                else:
                    stt_logger.debug(f"Interim user transcript: \"{transcript}\"")
                    
                if ctx.room and ctx.room.isconnected():
                    try:
                        await ctx.room.local_participant.send_text(
                            json.dumps({
                                "speaker": "user", 
                                "text": transcript,
                                "is_final": is_final
                            }),
                            topic="transcript"
                        )
                    except Exception as e:
                        stt_logger.error(f"Failed to send transcript to room: {e}")
        asyncio.create_task(_send_transcript())

    @session.on("conversation_item_added")
    def on_conversation_item(ev):
        item = getattr(ev, "item", None)
        if not item:
            return
        role = getattr(item, "role", None)
        content = getattr(item, "content", None)
        if isinstance(content, list):
            text = " ".join(str(c) for c in content if isinstance(c, str)).strip()
        else:
            text = str(content).strip() if content else ""
        if not text:
            return

        if role == "assistant":
            tts_logger.info(f"Agent speech committed: \"{text[:100]}...\"")
            async def _send_speech():
                if ctx.room and ctx.room.isconnected():
                    try:
                        await ctx.room.local_participant.send_text(
                            json.dumps({
                                "speaker": "agent", 
                                "text": text,
                                "is_final": True
                            }),
                            topic="transcript"
                        )
                    except Exception as e:
                        tts_logger.error(f"Failed to send agent speech to room: {e}")
            asyncio.create_task(_send_speech())

    @session.on("error")
    def on_session_error(ev):
        source = getattr(ev, "source", "unknown")
        err = getattr(ev, "error", ev)
        system_logger.error(f"LiveKit agent session error from {source}: {err}")

    @session.on("metrics_collected")
    def on_metrics_collected(ev):
        metrics = getattr(ev, "metrics", ev)
        system_logger.debug(f"Metrics collected: {metrics}")

    from livekit.agents.voice.room_io import RoomInputOptions
    buddy = BuddyAgent()
    await session.start(
        agent=buddy,
        room=ctx.room,
        room_input_options=RoomInputOptions(close_on_disconnect=False)
    )
    _active_room = ctx.room

    # ── LiveKit RPC Method Registrations on Agent Local Participant ──
    @ctx.room.local_participant.register_rpc_method("sendChatMessage")
    async def rpc_send_chat_message(data: rtc.RpcInvocationData) -> str:
        """Handle incoming typed text chat message from user client."""
        try:
            params = json.loads(data.payload) if data.payload else {}
            user_msg = str(params.get("message", "") or params.get("text", "")).strip()
            if not user_msg:
                return json.dumps({"error": "Empty message"})
            
            turn = next_turn()
            stt_logger.info(f"User chat message received via RPC: \"{user_msg}\" (turn={turn})")

            # Check dynamic tool triggers for fastpath
            lower = user_msg.lower()
            tutor_triggers = (
                "teach me", "tutor mode", "start lesson", "start lecture",
                "learn grammar", "practice grammar", "workplace practice",
                "scenario mode", "study mode", "let's learn", "teach about"
            )
            exit_triggers = (
                "back to buddy", "let's just chat", "exit tutor",
                "stop lesson", "casual chat", "buddy mode", "just talk"
            )
            current_tools_count = len(getattr(session, "tools", []))
            if any(trig in lower for trig in tutor_triggers) and current_tools_count == 0:
                mount_tutor_tools(session)
            elif any(trig in lower for trig in exit_triggers) and current_tools_count > 0:
                unmount_tools_to_fastpath(session)

            # Echo transcript back so all participants share consistent chat history
            if ctx.room and ctx.room.isconnected():
                try:
                    await ctx.room.local_participant.send_text(
                        json.dumps({"speaker": "user", "text": user_msg, "is_final": True}),
                        topic="transcript"
                    )
                except Exception as e:
                    stt_logger.debug(f"Failed to echo user chat transcript: {e}")

            # Generate conversational reply via Ollama LLM + Kokoro TTS
            try:
                session.generate_reply(user_input=user_msg, allow_interruptions=True)
            except Exception as gen_err:
                llm_logger.error(f"Error calling session.generate_reply: {gen_err}")
            return json.dumps({"status": "ok", "message": user_msg})
        except Exception as e:
            system_logger.error(f"rpc_send_chat_message error: {e}")
            return json.dumps({"error": str(e)})

    @ctx.room.on("data_received")
    def on_room_data_received(dp: rtc.DataPacket):
        """Fallback listener for user chat messages delivered over DataChannel."""
        if dp.topic == "chat":
            try:
                raw = dp.data.decode("utf-8")
                parsed = json.loads(raw) if raw.startswith("{") else {"message": raw}
                user_msg = str(parsed.get("message", "") or parsed.get("text", "")).strip()
                if user_msg:
                    turn = next_turn()
                    stt_logger.info(f"User chat message received via DataPacket: \"{user_msg}\" (turn={turn})")
                    lower = user_msg.lower()
                    tutor_triggers = (
                        "teach me", "tutor mode", "start lesson", "start lecture",
                        "learn grammar", "practice grammar", "workplace practice",
                        "scenario mode", "study mode", "let's learn", "teach about"
                    )
                    exit_triggers = (
                        "back to buddy", "let's just chat", "exit tutor",
                        "stop lesson", "casual chat", "buddy mode", "just talk"
                    )
                    current_tools_count = len(getattr(session, "tools", []))
                    if any(trig in lower for trig in tutor_triggers) and current_tools_count == 0:
                        mount_tutor_tools(session)
                    elif any(trig in lower for trig in exit_triggers) and current_tools_count > 0:
                        unmount_tools_to_fastpath(session)
                    try:
                        session.generate_reply(user_input=user_msg, allow_interruptions=True)
                    except Exception as gen_err:
                        llm_logger.error(f"Error calling session.generate_reply from DataPacket: {gen_err}")
            except Exception as e:
                system_logger.error(f"on_room_data_received error: {e}")

    @ctx.room.local_participant.register_rpc_method("get_last_sheet")
    async def rpc_get_last_sheet(data: rtc.RpcInvocationData) -> str:
        genui_logger.info("Client invoked get_last_sheet RPC on mount/reconnect")
        sheet = get_last_sheet_payload()
        if sheet:
            genui_logger.event("LAST_SHEET_RETURNED", f"req_id={sheet.get('req_id')}, component={sheet.get('component')}")
            return json.dumps(sheet)
        genui_logger.info("No previous interactive sheet found in SQLite")
        return json.dumps({"status": "empty", "message": "No previous interactive sheet found."})

    @ctx.room.local_participant.register_rpc_method("getLastSheet")
    async def rpc_get_last_sheet_alias(data: rtc.RpcInvocationData) -> str:
        return await rpc_get_last_sheet(data)

    @ctx.room.local_participant.register_rpc_method("getTutorState")
    async def rpc_get_tutor_state(data: rtc.RpcInvocationData) -> str:
        try:
            return json.dumps(tracker.get_tutor_state())
        except Exception as e:
            genui_logger.error(f"rpc_get_tutor_state error: {e}")
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("toggleTutorMode")
    async def rpc_toggle_tutor_mode(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload) if data.payload else {}
            target = params.get("mode")
            topic = params.get("topic")
            current = tracker.get_state().get("active_mode", "buddy")
            if target == "tutor" or current != "tutor":
                st = tracker.activate_tutor_mode(topic=topic)
            else:
                st = tracker.exit_tutor_mode()
            summary = tracker.get_learner_summary()
            await send_room_text(None, "progress", json.dumps(summary))
            genui_logger.event("TUTOR_MODE_TOGGLED", f"Active mode: {st.get('active_mode')}, Topic: {st.get('current_topic')}")
            return json.dumps(st)
        except Exception as e:
            genui_logger.error(f"rpc_toggle_tutor_mode error: {e}")
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("submitQuizAnswer")
    async def rpc_submit_quiz_answer(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload)
            chapter_idx = int(params.get("chapter_idx", tracker.get_active_chapter()))
            q_id = params.get("question_id")
            user_ans = str(params.get("user_answer", ""))
            
            bank = quizzer.load_quiz_bank(chapter_idx)
            target_q = next((q for q in bank if q.get("id") == q_id), None)
            if not target_q and "question" in params:
                target_q = params["question"]
            
            if not target_q:
                target_q = {
                    "id": q_id,
                    "stem": params.get("stem", "Grammar Question"),
                    "options": params.get("options", []),
                    "correct_answer": params.get("correct_answer", "A"),
                    "explanation": "Evaluated against Oxford Guide rules.",
                    "rule_citation": "Oxford Guide"
                }
            
            eval_result = quizzer.evaluate_answer(target_q, user_ans)
            genui_logger.event("QUIZ_ANSWER_EVALUATED", f"q_id={q_id}, is_correct={eval_result.get('is_correct')}")
            # Push authoritative progress update immediately over WebRTC
            try:
                await send_room_text(None, "progress", json.dumps(tracker.get_learner_summary()))
            except Exception as e:
                genui_logger.error(f"Failed to broadcast progress after answer: {e}")
            return json.dumps(eval_result)
        except Exception as e:
            genui_logger.error(f"rpc_submit_quiz_answer error: {e}")
            return json.dumps({"error": str(e), "is_correct": False})

    @ctx.room.local_participant.register_rpc_method("disputeAnswer")
    async def rpc_dispute_answer(data: rtc.RpcInvocationData) -> str:
        req_id = f"req_dispute_{int(time.time() * 1000)}"
        try:
            params = json.loads(data.payload)
            user_claim = params.get("user_claim", "")
            ruling = simulation.handle_answer_contention(user_claim)
            ruling["req_id"] = req_id
            payload = {
                "schema_version": "1.0",
                "type": "genui_render",
                "component": "ContentionResolver",
                "props": ruling
            }
            persist_sheet_payload(req_id, "ContentionResolver", payload)
            await send_room_text(None, "genui", json.dumps(payload))
            genui_logger.event("RPC_DISPUTE_ANSWER", f"Claim: {user_claim[:30]}", req_id=req_id)
            return json.dumps(ruling)
        except Exception as e:
            genui_logger.error(f"rpc_dispute_answer error: {e}")
            await emit_sheet_error(None, component_attempted="ContentionResolver", error_message=str(e), req_id=req_id)
            return json.dumps({"error": str(e), "req_id": req_id})

    @ctx.room.local_participant.register_rpc_method("triggerQuiz")
    async def rpc_trigger_quiz(data: rtc.RpcInvocationData) -> str:
        req_id = f"req_quiz_{int(time.time() * 1000)}"
        try:
            params = json.loads(data.payload) if data.payload else {}
            chapter = int(params.get("chapter", tracker.get_active_chapter()))
            mode = params.get("mode", "milestone")
            qs = quizzer.get_milestone_quiz(chapter, count=5) if mode == "milestone" else quizzer.get_checkpoint_quiz(chapter, count=3)
            payload = {
                "schema_version": "1.0",
                "type": "genui_render",
                "component": "QuizCard",
                "props": {"req_id": req_id, "questions": qs, "chapter": chapter, "mode": mode, "source": "bank"}
            }
            persist_sheet_payload(req_id, "QuizCard", payload)
            await send_room_text(None, "genui", json.dumps(payload))
            genui_logger.event("RPC_QUIZ_TRIGGERED", f"Chapter {chapter}", req_id=req_id)
            return json.dumps({"status": "ok", "req_id": req_id, "questions": qs})
        except Exception as e:
            genui_logger.error(f"rpc_trigger_quiz error: {e}")
            await emit_sheet_error(None, component_attempted="QuizCard", error_message=str(e), req_id=req_id)
            return json.dumps({"error": str(e), "req_id": req_id})

    @ctx.room.local_participant.register_rpc_method("triggerRevision")
    async def rpc_trigger_revision(data: rtc.RpcInvocationData) -> str:
        req_id = f"req_notes_{int(time.time() * 1000)}"
        try:
            params = json.loads(data.payload) if data.payload else {}
            chapter = int(params.get("chapter", tracker.get_active_chapter()))
            rag_results = rag.hybrid_search(f"chapter {chapter} rules summary", top_k=4, chapter_filter=chapter)
            context_text = "\n\n".join([r["text"] for r in rag_results]) if rag_results else ""
            notes_payload = {
                "req_id": req_id,
                "title": f"Chapter {chapter}: Mastery & Structure Notes",
                "chapter": chapter,
                "overview": f"Synthesized revision summary for Chapter {chapter}.",
                "rules": [
                    {"title": "Core Syntactic Concord", "body": context_text[:350] if context_text else "Subject-verb concord must be preserved.", "citation": f"Oxford Guide Ch {chapter}"}
                ],
                "pitfalls": ["Avoid subject-verb discord across intervening clauses."]
            }
            payload = {
                "schema_version": "1.0",
                "type": "genui_render",
                "component": "BionicSketchNote",
                "props": {"notes": notes_payload, "req_id": req_id}
            }
            persist_sheet_payload(req_id, "BionicSketchNote", payload)
            await send_room_text(None, "genui", json.dumps(payload))
            genui_logger.event("RPC_REVISION_TRIGGERED", f"Chapter {chapter}", req_id=req_id)
            return json.dumps({"status": "ok", "req_id": req_id, "notes": notes_payload})
        except Exception as e:
            genui_logger.error(f"rpc_trigger_revision error: {e}")
            await emit_sheet_error(None, component_attempted="BionicSketchNote", error_message=str(e), req_id=req_id)
            return json.dumps({"error": str(e), "req_id": req_id})

    @ctx.room.local_participant.register_rpc_method("advanceChapter")
    async def rpc_advance_chapter(data: rtc.RpcInvocationData) -> str:
        can = tracker.can_advance()
        if not can:
            return json.dumps({"success": False, "message": "Cannot advance: coursework and milestone quiz must be completed."})
        advanced = tracker.advance_to_next_chapter()
        active_info = tracker.get_active_chapter()
        new_ch = active_info.get("chapter_idx", 1)
        summary = tracker.get_learner_summary()
        await send_room_text(None, "progress", json.dumps(summary))
        await send_room_text(None, "genui", json.dumps({
            "type": "genui_render",
            "component": "SyllabusProgressTree",
            "props": {"new_chapter": new_ch}
        }))
        genui_logger.event("CHAPTER_ADVANCED", f"Advanced to Chapter {new_ch}")
        return json.dumps({"success": True, "active_chapter": new_ch})

    @ctx.room.local_participant.register_rpc_method("getSyllabus")
    async def rpc_get_syllabus(data: rtc.RpcInvocationData) -> str:
        try:
            summary = tracker.get_learner_summary()
            return json.dumps(summary)
        except Exception as e:
            genui_logger.error(f"rpc_get_syllabus error: {e}")
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("getQuiz")
    async def rpc_get_quiz(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload) if data.payload else {}
            active_info = tracker.get_active_chapter()
            chapter_idx = int(params.get("chapter_idx", active_info.get("chapter_idx", 1)))
            mode = params.get("mode", "milestone")
            if mode == "checkpoint":
                qs = quizzer.get_checkpoint_quiz(chapter_idx, count=3)
            elif mode == "on_demand":
                qs = quizzer.get_on_demand_quiz(chapter_idx, count=5)
            else:
                qs = quizzer.get_milestone_quiz(chapter_idx, count=10)
            return json.dumps({"chapter": chapter_idx, "mode": mode, "questions": qs})
        except Exception as e:
            genui_logger.error(f"rpc_get_quiz error: {e}")
            return json.dumps({"error": str(e), "questions": []})

    @ctx.room.local_participant.register_rpc_method("demonstrateGrammarMovement")
    async def rpc_demonstrate_grammar_movement(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload) if data.payload else {}
            title = params.get("title", "Subject-Auxiliary Inversion")
            rule = params.get("rule", "In questions and emphatic inversions, the auxiliary verb moves before the subject.")
            active_info = tracker.get_active_chapter()
            chapter = int(params.get("chapter", active_info.get("chapter_idx", 2)))
            initial_tokens = params.get("initial_tokens")
            transformed_tokens = params.get("transformed_tokens")
            explanation = params.get("explanation", "Observe how the auxiliary verb shifts position across the subject boundary.")
            rule_citation = params.get("rule_citation", "Oxford Guide Ch 2 & Arihant Rule 14")
            res = await demonstrate_grammar_movement(
                None,
                title=title,
                rule=rule,
                chapter=chapter,
                initial_tokens=initial_tokens,
                transformed_tokens=transformed_tokens,
                explanation=explanation,
                rule_citation=rule_citation
            )
            return res
        except Exception as e:
            genui_logger.error(f"rpc_demonstrate_grammar_movement error: {e}")
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("getCurriculumCatalog")
    async def rpc_get_curriculum_catalog(data: rtc.RpcInvocationData) -> str:
        try:
            return json.dumps(tracker.get_curriculum_catalog())
        except Exception as e:
            genui_logger.error(f"rpc_get_curriculum_catalog error: {e}")
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("getLectureHistory")
    async def rpc_get_lecture_history(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload) if data.payload else {}
            st = params.get("session_type")
            limit = int(params.get("limit", 30))
            return json.dumps(tracker.get_lecture_history(limit=limit, session_type=st))
        except Exception as e:
            genui_logger.error(f"rpc_get_lecture_history error: {e}")
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("updateLearnerPreferences")
    async def rpc_update_learner_preferences(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload) if data.payload else {}
            res = tracker.update_learner_preferences(params)
            summary = tracker.get_learner_summary()
            await send_room_text(None, "progress", json.dumps(summary))
            return json.dumps(res)
        except Exception as e:
            genui_logger.error(f"rpc_update_learner_preferences error: {e}")
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("deliverCanvasLecture")
    async def rpc_deliver_canvas_lecture(data: rtc.RpcInvocationData) -> str:
        req_id = f"req_lec_{int(time.time() * 1000)}"
        try:
            params = json.loads(data.payload) if data.payload else {}
            phase = int(params.get("phase_index", 1))
            topic = params.get("topic", "Nouns")
            submod = params.get("submodule")
            st = params.get("session_type", "grammar_mastery")
            session = tracker.get_dynamic_course_session(
                topic=topic,
                submodule=submod,
                session_type=st,
                phase_index=phase
            )
            saved = tracker.save_lecture_session(
                topic=session["topic"],
                submodule=session["submodule"],
                phase_index=session["phase_index"],
                session_type=session["session_type"],
                spoken_summary=session["spoken_summary"],
                paragraphs=session["paragraphs"],
                canvas_type=session["canvas_type"],
                canvas_config=session["canvas_config"],
                repetition_items=session.get("repetition_items", []),
                key_takeaways=session.get("key_takeaways", [])
            )
            if langgraph_engine:
                langgraph_engine.update_state({
                    "active_mode": "tutor_qa",
                    "current_topic": session["topic"],
                    "submodule": session["submodule"],
                    "phase_index": phase,
                    "session_type": session["session_type"],
                    "is_delivering_lecture": False,
                    "lecture_data": saved
                })
            payload = {
                "schema_version": "1.0",
                "type": "genui_render",
                "component": "CanvasLectureCard",
                "props": {
                    "id": saved["id"],
                    "req_id": req_id,
                    "topic": saved["topic"],
                    "submodule": saved["submodule"],
                    "phase_index": saved["phase_index"],
                    "session_type": saved["session_type"],
                    "spoken_summary": saved["spoken_summary"],
                    "paragraphs": saved["paragraphs"],
                    "key_takeaways": saved["key_takeaways"],
                    "canvas_type": saved["canvas_type"],
                    "canvas_config": saved["canvas_config"],
                    "repetition_items": saved.get("repetition_items", []),
                    "timestamp": saved["timestamp"]
                }
            }
            persist_sheet_payload(req_id, "CanvasLectureCard", payload)
            await send_room_text(None, "genui", json.dumps(payload))
            summary = tracker.get_learner_summary()
            await send_room_text(None, "progress", json.dumps(summary))
            genui_logger.event("RPC_CANVAS_LECTURE_DELIVERED", session["submodule"], phase=phase, session_type=st)
            return json.dumps(saved)
        except Exception as e:
            genui_logger.error(f"rpc_deliver_canvas_lecture error: {e}")
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("requestReinterpretation")
    async def rpc_request_reinterpretation(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload) if data.payload else {}
            style_hint = params.get("style_hint", "everyday")
            node_id = params.get("node_id", "current")
            complaint = params.get("complaint", "")
            if not node_id or node_id in ("current", "none", ""):
                state = tracker.get_state()
                curr_topic = state.get("current_topic", "Nouns")
                node_id = curr_topic.lower().replace(" ", "_").replace("-", "_")

            req_id = curriculum_store.log_reconsideration_request(
                node_id=node_id,
                style_hint=style_hint,
                complaint=complaint
            )

            existing = curriculum_store.get_variant(node_id, style_hint)
            if existing:
                curriculum_store.resolve_reconsideration_request(req_id, existing.get("id"))
                draft_payload = {
                    "title": f"{node_id.replace('_', ' ').title()} ({style_hint.title()})",
                    "core_concept": existing.get("spoken_summary", ""),
                    "canvas_type": existing.get("canvas_type", "classifier"),
                    "canvas_config": existing.get("canvas_config", {}),
                    "lecture_paragraphs": existing.get("lecture_paragraphs", []),
                    "citations": existing.get("citations", []),
                }
                fake_state = {
                    "node_id": node_id,
                    "job_type": "reconsider",
                    "result_id": existing.get("id"),
                    "draft": draft_payload
                }
                await push_ready_event(fake_state)
                spoken = existing.get("spoken_summary", "")
                if spoken and session:
                    try:
                        session.say(f"Here is how to think about this in a {style_hint} context: {spoken}", allow_interruptions=True)
                    except Exception as say_err:
                        tts_logger.error(f"session.say error: {say_err}")
                return json.dumps({"status": "loaded", "variant": existing})
            else:
                enqueue_reconsider(node_id=node_id, style_hint=style_hint, complaint=complaint, request_id=req_id)
                voice_msg = f"Got it! I am switching to a {style_hint} analogy for {node_id.replace('_', ' ')}."
                if session:
                    try:
                        session.say(voice_msg, allow_interruptions=True)
                    except Exception as say_err:
                        tts_logger.error(f"session.say error: {say_err}")
                return json.dumps({"status": "enqueued", "style_hint": style_hint, "node_id": node_id})
        except Exception as e:
            genui_logger.error(f"rpc_request_reinterpretation error: {e}")
            return json.dumps({"error": str(e)})

    # ── Periodic Authoritative Learner State Sync Loop ───────────────
    async def push_periodic_progress():
        """Periodically pushes authoritative learner summary to room on topic 'progress'."""
        while True:
            try:
                await asyncio.sleep(10)
                summary = tracker.get_learner_summary()
                await send_room_text(None, "progress", json.dumps(summary))
            except asyncio.CancelledError:
                break
            except Exception as e:
                genui_logger.debug(f"Periodic progress broadcast notice: {e}")

    progress_task = asyncio.create_task(push_periodic_progress())
    async def _cancel_progress():
        progress_task.cancel()
    ctx.add_shutdown_callback(_cancel_progress)

    # Broadcast initial state immediately to room
    try:
        await send_room_text(None, "progress", json.dumps(tracker.get_learner_summary()))
    except Exception as e:
        genui_logger.debug(f"Initial progress broadcast notice: {e}")

    greeting = tracker.get_startup_greeting()
    tts_logger.info(f"Agent initial greeting: \"{greeting}\"")
    await session.say(greeting, allow_interruptions=True)

if __name__ == "__main__":
    agents.cli.run_app(server)
