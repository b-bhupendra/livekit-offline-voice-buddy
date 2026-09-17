"""LiveKit Offline Voice AI Agent — English Grammar Master Coach & Simulator.
2026 Architectural Spec:
- STT: In-memory Faster-Whisper (zero HTTP socket serialization, CPU int8) with StreamAdapter
- VAD: Local Silero VAD (shared instance)
- Turn Detector: Local Audio Turn Detector (v1-mini on CPU)
- LLM: Local Ollama Qwen (qwen-buddy) via openai.LLM.with_ollama
- TTS: Local Audio Server via openai.TTS with calibrated Piper voice (length_scale=1.18)
- FastMCP: Hybrid RAG, DuckDuckGo search, dispute resolver, learner recasts
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
    TurnHandlingOptions, inference, function_tool, RunContext, stt, utils, mcp
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
   - If unsure of a nuance, query your local RAG via `query_grammar_rag` or free DuckDuckGo search via `search_web_grammar`.

2. LINEAR SYLLABUS DISCIPLINE:
   - Guide the student strictly through the 18 chapters from start to finish.
   - Today's session starts at Chapter 1 & 2: Course Foundations & Sentence Transformations.
   - Never skip ahead until the student has completed the coursework and passed the milestone quiz.

3. DUAL-TRACK FEEDBACK LOOP:
   - TRACK A (Grammar is Sound): Acknowledge correctness, then introduce a natural native colloquialism or idiom with gentle, light repetition (e.g. "I'm swamped" instead of "I am very busy").
   - TRACK B (Grammatical Mistake): Roleplay natural communicative friction/misunderstanding, explain the rule clearly, and immediately prompt an ISOMORPHIC SENTENCE with the same rule in a different context.

4. MULTI-TRIGGER QUIZZING & ISOMORPHIC MUTATION:
   - If the student says "Quiz me", "Test me on this", or "Give me a quiz", immediately start quiz mode.
   - If the student fails a question, explain why and immediately issue a mutated isomorphic question.

5. CONTENTION RESOLUTION ("LLM IS WRONG"):
   - If the student challenges a correction saying "My answer is right" or "The LLM is wrong", DO NOT argue stubbornly.
   - Call `search_web_grammar` or `dispute_answer` to verify Cambridge, Oxford, and Merriam-Webster dictionaries, and provide an impartial ruling explaining register differences (formal vs. spoken).

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

class BuddyAgent(Agent):
    def __init__(self):
        super().__init__(instructions=INSTRUCTIONS)

server = AgentServer()

@server.rtc_session(agent_name="offline-buddy")
async def entrypoint(ctx: agents.JobContext):
    """Main LiveKit RTC Session entrypoint."""
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

    mcp_script = Path(__file__).resolve().parent / "memory_mcp_server.py"
    memory_mcp_stdio = mcp.MCPServerStdio(
        command=sys.executable,
        args=[str(mcp_script)],
    )
    memory_toolset = mcp.MCPToolset(id="memory", mcp_server=memory_mcp_stdio)

    session = AgentSession(
        vad=vad_provider,
        turn_handling=turn_handling,
        llm=llm_provider,
        tts=tts_provider,
        stt=stt_provider,
        tools=[memory_toolset],
    )

    @session.on("user_state_changed")
    def on_user_state(ev):
        if ev.new_state == "speaking":
            print("\n[Microphone: User is speaking...]")
        elif ev.new_state == "listening":
            print("\n[Microphone: Audio captured, processing utterance...]")

    @session.on("user_input_transcribed")
    def on_user_input(ev):
        if ev.transcript:
            print(f"\n[Transcribed Input]: \"{ev.transcript}\"")

    @session.on("agent_state_changed")
    def on_agent_state(ev):
        print(f"\n[Agent State]: {ev.new_state}")

    buddy = BuddyAgent()
    await session.start(agent=buddy, room=ctx.room)

    greeting = tracker.get_startup_greeting()
    print(f"\n[Agent]: Speaking initial greeting: \"{greeting}\"")
    await session.say(greeting, allow_interruptions=True)

if __name__ == "__main__":
    agents.cli.run_app(server)
