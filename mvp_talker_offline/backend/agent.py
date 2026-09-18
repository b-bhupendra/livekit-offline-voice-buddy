"""LiveKit Offline Voice AI Agent — English Grammar Master Coach & Simulator.
2026 Architectural Spec:
- STT: In-memory Faster-Whisper (zero HTTP socket serialization, CPU int8) with StreamAdapter
- VAD: Local Silero VAD (shared instance)
- Turn Detector: Local Audio Turn Detector (v1-mini on CPU)
- LLM: Local Ollama Qwen (qwen-buddy) via openai.LLM.with_ollama
- TTS: Local Audio Server via openai.TTS with calibrated Piper voice (length_scale=1.18)
- In-Process Tools: Hybrid RAG, DuckDuckGo search, dispute resolver, linear syllabus progression
"""

import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"

import socket
import asyncio
import datetime
import subprocess
import json
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# Auto-reexec with local PortAudio library if needed
lib_dir = str(Path.home() / ".local/usr/lib/x86_64-linux-gnu")
if os.path.exists(lib_dir) and lib_dir not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception:
        pass

load_dotenv()

from faster_whisper import WhisperModel
from livekit import rtc
from livekit import agents
from livekit.agents import (
    Agent, AgentServer, AgentSession, ChatContext, ChatMessage,
    TurnHandlingOptions, inference, function_tool, RunContext, stt, utils
)
from livekit.plugins import openai, silero

from syllabus_tracker import SyllabusTracker
from simulation_engine import SimulationEngine
from quiz_engine import QuizEngine
from rag_store import RAGStore

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen-buddy")
AUDIO_SERVER_URL = os.getenv("AUDIO_SERVER_URL", "http://127.0.0.1:8880/v1")

tracker = SyllabusTracker()
rag = RAGStore()
simulation = SimulationEngine(rag_store=rag)
quizzer = QuizEngine(syllabus_tracker=tracker)

def is_audio_server_running(host: str = "127.0.0.1", port: int = 8880) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0

async def ensure_audio_server_async():
    if not is_audio_server_running():
        server_script = Path(__file__).resolve().parent / "audio_server.py"
        if server_script.exists():
            print("Starting background local audio server (port 8880)...")
            subprocess.Popen(
                [sys.executable, str(server_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            for _ in range(15):
                if is_audio_server_running():
                    print("Local audio server online.")
                    return
                await asyncio.sleep(0.2)

INSTRUCTIONS = """
You are Buddy, an authoritative yet encouraging English Grammar Master Coach, Story Simulator, and Conversational Companion.
You are coaching Bhupendra through a rigorous, linear English Grammar Mastery curriculum.

CORE PEDAGOGICAL PILLARS & ANTI-HALLUCINATION RULES:
1. STRICT ANTI-HALLUCINATION & RULE CITATION:
   - When explaining grammar, DO NOT invent non-existent rules.
   - Cite authoritative grammar rules: cite either the Oxford Guide to English Grammar or Arihant General English.
   - If unsure of a nuance, query your local RAG via `query_grammar_rag`.

2. LINEAR SYLLABUS DISCIPLINE:
   - Guide the student strictly through the 18 chapters from start to finish.
   - Today's session starts at Chapter 1 & 2: Course Foundations & Sentence Transformations.
   - Never skip ahead until the student has completed the coursework and passed the milestone quiz.

3. DUAL-TRACK FEEDBACK LOOP:
   - TRACK A (Grammar is Sound): Acknowledge correctness, then introduce a natural native colloquialism or idiom with gentle, light repetition.
   - TRACK B (Grammatical Mistake): Roleplay natural communicative friction/misunderstanding, explain the rule clearly, and immediately prompt an ISOMORPHIC SENTENCE with the same rule in a different context.

4. MULTI-TRIGGER QUIZZING & ISOMORPHIC MUTATION:
   - If the student says "Quiz me", "Test me on this", or "Give me a quiz", immediately invoke `trigger_quiz`.
   - If the student fails a question, explain why and reinforce with an isomorphic question.

5. CONTENTION RESOLUTION ("LLM IS WRONG"):
   - If the student challenges a correction saying "My answer is right" or "The LLM is wrong", DO NOT argue stubbornly.
   - Call `dispute_answer` to verify authoritative sources and provide an impartial ruling explaining register differences (formal vs. spoken).

6. VOICE & PACING:
   - Speak in clear, concise conversational turns (1-3 sentences per turn).
   - Keep speech articulate, warm, and easy to follow over voice.
"""

class FasterWhisperSTT(stt.STT):
    def __init__(self, model_size="tiny.en", device="cpu", compute_type="int8"):
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False))
        print(f"Initializing in-memory Faster-Whisper ({model_size}) on {device} [100% offline]...")
        try:
            self._model = WhisperModel(model_size, device=device, compute_type=compute_type, local_files_only=True)
        except Exception:
            self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print("In-memory STT ready.")

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
            if not resampled_frames:
                return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])
            frame = rtc.combine_audio_frames(resampled_frames)

        audio_np = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32) / 32768.0

        def run_inference():
            lang = language if isinstance(language, str) else "en"
            segments, info = self._model.transcribe(
                audio_np,
                beam_size=1,
                language=lang,
                condition_on_previous_text=False
            )
            text = " ".join(seg.text for seg in segments).strip()
            return text, info.language

        loop = asyncio.get_event_loop()
        text, detected_lang = await loop.run_in_executor(None, run_inference)

        if text:
            print(f"\n[Faster-Whisper STT]: \"{text}\"")

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=text, language=detected_lang)]
        )

_whisper_singleton = None

def get_faster_whisper_stt(model_size="tiny.en") -> FasterWhisperSTT:
    global _whisper_singleton
    if _whisper_singleton is None:
        _whisper_singleton = FasterWhisperSTT(model_size=model_size)
    return _whisper_singleton

# ── IN-PROCESS NATIVE LIVEKIT FUNCTION TOOLS & TEXT STREAM BROADCASTS ────────

_active_room: Optional[rtc.Room] = None

async def broadcast_livekit_text(topic: str, payload_str: str):
    global _active_room
    if _active_room and _active_room.isconnected():
        try:
            await _active_room.local_participant.send_text(payload_str, topic=topic)
        except Exception as e:
            print(f"[LiveKit Text Stream] send_text({topic}) failed: {e}")

@function_tool()
async def query_grammar_rag(context: RunContext, query: str) -> str:
    """Query verified Oxford Guide and Arihant General English grammar chunks for rules and citations."""
    active_ch = tracker.get_active_chapter()
    results = rag.hybrid_search(query, top_k=3, chapter_filter=active_ch)
    if not results:
        results = rag.hybrid_search(query, top_k=3)
    if not results:
        return "No direct grammar matches found in local reference."
    chunks = [
        f"[{r.get('source_title', 'Grammar Guide')} - Section: {r.get('section_title', '')}]\n{r['text']}"
        for r in results
    ]
    return "\n\n".join(chunks)

@function_tool()
async def trigger_quiz(context: RunContext, chapter: int, mode: str = "milestone") -> str:
    """Generate or retrieve a grammar quiz for the active chapter and render it on the student's interface."""
    qs = quizzer.get_milestone_quiz(chapter, count=5) if mode == "milestone" else quizzer.get_checkpoint_quiz(chapter, count=3)
    
    # Broadcast native LiveKit GenUI artifact to browser timeline
    payload = {
        "type": "genui_render",
        "component": "QuizCard",
        "props": {
            "questions": qs,
            "chapter": chapter,
            "mode": mode,
            "source": "llm_generated"
        }
    }
    await broadcast_livekit_text("genui", json.dumps(payload))
    
    return json.dumps({
        "status": "quiz_prepared",
        "chapter": chapter,
        "mode": mode,
        "questions_count": len(qs),
        "questions": qs
    }, indent=2)

@function_tool()
async def dispute_answer(context: RunContext, user_claim: str) -> str:
    """Resolve a learner's dispute or contention regarding whether an answer is grammatically correct or acceptable."""
    ruling = simulation.handle_answer_contention(user_claim)
    
    # Broadcast native LiveKit GenUI artifact to browser timeline
    payload = {
        "type": "genui_render",
        "component": "ContentionResolver",
        "props": ruling
    }
    await broadcast_livekit_text("genui", json.dumps(payload))
    
    return json.dumps(ruling, indent=2)

@function_tool()
async def get_learner_progress(context: RunContext) -> str:
    """Get current learner state, accuracy, chapter scores, and failed question queue."""
    state = tracker.get_state()
    return json.dumps(state, indent=2)

@function_tool()
async def generate_revision_notes(context: RunContext, chapter: int) -> str:
    """Synthesize structured study notes and common pitfalls for the specified chapter."""
    active_ch = tracker.get_active_chapter()
    rag_results = rag.hybrid_search(f"chapter {chapter} rules summary", top_k=4, chapter_filter=chapter)
    context_text = "\n\n".join([r["text"] for r in rag_results]) if rag_results else ""
    
    notes_payload = {
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
        "type": "genui_render",
        "component": "BionicSketchNote",
        "props": {"notes": notes_payload}
    }
    await broadcast_livekit_text("genui", json.dumps(payload))
    
    return json.dumps({
        "chapter": chapter,
        "title": f"Chapter {chapter} Revision",
        "reference_excerpt": context_text[:800],
        "status": "ready"
    }, indent=2)

class BuddyAgent(Agent):
    def __init__(self):
        super().__init__(instructions=INSTRUCTIONS)

server = AgentServer()

@server.rtc_session(agent_name="offline-buddy")
async def entrypoint(ctx: agents.JobContext):
    """Main LiveKit RTC Session entrypoint."""
    global _active_room
    await ensure_audio_server_async()

    llm_provider = openai.LLM.with_ollama(
        model=OLLAMA_MODEL,
        base_url=f"{OLLAMA_BASE_URL.rstrip('/')}/v1",
    )

    vad_provider = silero.VAD.load()

    turn_handling = TurnHandlingOptions(
        turn_detection=inference.TurnDetector(version="v1-mini"),
        interruption={"mode": "vad"},
    )

    tts_provider = openai.TTS(
        model="tts-1",
        voice="en_US-lessac-medium",
        base_url=AUDIO_SERVER_URL,
        api_key="offline",
    )

    local_whisper = get_faster_whisper_stt(model_size="tiny.en")
    stt_provider = stt.StreamAdapter(
        stt=local_whisper,
        vad=vad_provider,
    )

    # In-process function tools replacing external stdio MCP loopback
    in_process_tools = [
        query_grammar_rag,
        trigger_quiz,
        dispute_answer,
        get_learner_progress,
        generate_revision_notes
    ]

    session = AgentSession(
        vad=vad_provider,
        turn_handling=turn_handling,
        llm=llm_provider,
        tts=tts_provider,
        stt=stt_provider,
        tools=in_process_tools,
    )

    @session.on("user_state_changed")
    def on_user_state(ev):
        if ev.new_state == "speaking":
            print("\n[Microphone: User is speaking...]")
        elif ev.new_state == "listening":
            print("\n[Microphone: Audio captured, processing utterance...]")

    @session.on("user_input_transcribed")
    async def on_user_input(ev):
        if ev.transcript:
            print(f"\n[Transcribed Input]: \"{ev.transcript}\"")
            # LiveKit-native text stream (no loopback HTTP)
            if ctx.room and ctx.room.isconnected():
                try:
                    await ctx.room.local_participant.send_text(
                        json.dumps({"speaker": "user", "text": ev.transcript}),
                        topic="transcript"
                    )
                except Exception:
                    pass

    @session.on("agent_state_changed")
    def on_agent_state(ev):
        print(f"\n[Agent State]: {ev.new_state}")

    @session.on("agent_speech_committed")
    async def on_agent_speech(ev):
        text = getattr(ev, "text", None) or getattr(ev, "transcript", None) or ""
        if text:
            # LiveKit-native text stream (no loopback HTTP)
            if ctx.room and ctx.room.isconnected():
                try:
                    await ctx.room.local_participant.send_text(
                        json.dumps({"speaker": "agent", "text": text}),
                        topic="transcript"
                    )
                except Exception:
                    pass

    buddy = BuddyAgent()
    await session.start(agent=buddy, room=ctx.room)
    _active_room = ctx.room

    # ── LiveKit RPC Method Registrations on Agent Local Participant ──
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
            return json.dumps(eval_result)
        except Exception as e:
            return json.dumps({"error": str(e), "is_correct": False})

    @ctx.room.local_participant.register_rpc_method("disputeAnswer")
    async def rpc_dispute_answer(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload)
            user_claim = params.get("user_claim", "")
            ruling = simulation.handle_answer_contention(user_claim)
            await broadcast_livekit_text("genui", json.dumps({
                "type": "genui_render",
                "component": "ContentionResolver",
                "props": ruling
            }))
            return json.dumps(ruling)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("triggerQuiz")
    async def rpc_trigger_quiz(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload) if data.payload else {}
            chapter = int(params.get("chapter", tracker.get_active_chapter()))
            mode = params.get("mode", "milestone")
            qs = quizzer.get_milestone_quiz(chapter, count=5) if mode == "milestone" else quizzer.get_checkpoint_quiz(chapter, count=3)
            await broadcast_livekit_text("genui", json.dumps({
                "type": "genui_render",
                "component": "QuizCard",
                "props": {"questions": qs, "chapter": chapter, "mode": mode, "source": "bank"}
            }))
            return json.dumps({"status": "ok", "questions": qs})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("triggerRevision")
    async def rpc_trigger_revision(data: rtc.RpcInvocationData) -> str:
        try:
            params = json.loads(data.payload) if data.payload else {}
            chapter = int(params.get("chapter", tracker.get_active_chapter()))
            rag_results = rag.hybrid_search(f"chapter {chapter} rules summary", top_k=4, chapter_filter=chapter)
            context_text = "\n\n".join([r["text"] for r in rag_results]) if rag_results else ""
            notes_payload = {
                "title": f"Chapter {chapter}: Mastery & Structure Notes",
                "chapter": chapter,
                "overview": f"Synthesized revision summary for Chapter {chapter}.",
                "rules": [
                    {"title": "Core Syntactic Concord", "body": context_text[:350] if context_text else "Subject-verb concord must be preserved.", "citation": f"Oxford Guide Ch {chapter}"}
                ],
                "pitfalls": ["Avoid subject-verb discord across intervening clauses."]
            }
            await broadcast_livekit_text("genui", json.dumps({
                "type": "genui_render",
                "component": "BionicSketchNote",
                "props": {"notes": notes_payload}
            }))
            return json.dumps({"status": "ok", "notes": notes_payload})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @ctx.room.local_participant.register_rpc_method("advanceChapter")
    async def rpc_advance_chapter(data: rtc.RpcInvocationData) -> str:
        can = tracker.can_advance()
        if not can:
            return json.dumps({"success": False, "message": "Cannot advance: coursework and milestone quiz must be completed."})
        advanced = tracker.advance_to_next_chapter()
        new_ch = tracker.get_active_chapter()
        await broadcast_livekit_text("genui", json.dumps({
            "type": "genui_render",
            "component": "SyllabusProgressTree",
            "props": {"new_chapter": new_ch}
        }))
        return json.dumps({"success": True, "active_chapter": new_ch})

    greeting = tracker.get_startup_greeting()
    print(f"\n[Agent]: Speaking initial greeting: \"{greeting}\"")
    await session.say(greeting, allow_interruptions=True)

if __name__ == "__main__":
    agents.cli.run_app(server)
