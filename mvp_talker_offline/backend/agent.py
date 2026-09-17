"""LiveKit Offline Voice AI Agent — English Grammar Master Coach & Simulator.
2026 Architectural Spec:
- STT: In-memory Faster-Whisper (zero HTTP socket serialization, CPU int8)
- VAD: Local Silero VAD
- Turn Detector: Local Audio Turn Detector (v1-mini on CPU)
- LLM: Local Ollama Qwen (qwen-buddy / qwen2.5:7b) via openai.LLM.with_ollama
- TTS: Local Audio Server via openai.TTS with calibrated Piper voice (length_scale=1.18)
- RAG: Hybrid Vector RAG (nomic-embed-text + SQLite FTS5)
- FastMCP: RAG search, DuckDuckGo search, dispute resolver, learner recasts
"""

import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"

import socket
import asyncio
import datetime
import subprocess
import json
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

from memory_mcp_server import memory_mcp
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

class InMemoryFasterWhisperSTT(stt.STT):
    def __init__(self, model_size: str = "tiny.en", device: str = "cpu", compute_type: str = "int8"):
        super().__init__(capabilities=stt.STTCapabilities(streaming=False))
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type, local_files_only=True)

    async def _recognize_impl(self, buffer: utils.AudioBuffer, *, language: str | None = None, conn_options=None) -> stt.SpeechEvent:
        resampled = buffer.resample(16000)
        audio_data = resampled.data
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)
        audio_float = audio_data.astype(np.float32) / 32768.0
        if audio_float.ndim > 1:
            audio_float = audio_float.mean(axis=1)

        segments, _ = await asyncio.to_thread(self._model.transcribe, audio_float, beam_size=1, language="en")
        text = " ".join([seg.text for seg in segments]).strip()
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=text, language="en")]
        )

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: AgentSession):
    await ensure_audio_server_async()

    stt_plugin = InMemoryFasterWhisperSTT(model_size="tiny.en")
    vad_plugin = silero.VAD.load()

    tts_plugin = openai.TTS(
        model="piper",
        voice="en_US-lessac-medium",
        base_url=AUDIO_SERVER_URL,
        api_key="offline"
    )

    llm_plugin = openai.LLM.with_ollama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL
    )

    greeting = tracker.get_startup_greeting()
    initial_ctx = ChatContext()
    initial_ctx.add_message(role="system", content=INSTRUCTIONS)

    agent = Agent(
        instructions=INSTRUCTIONS,
        chat_context=initial_ctx,
        tools=[mcp.MCPToolset(id="memory", mcp_server=memory_mcp)]
    )

    session = agents.VoiceSession(
        agent=agent,
        llm=llm_plugin,
        stt=stt_plugin,
        tts=tts_plugin,
        vad=vad_plugin,
        turn_handling=TurnHandlingOptions()
    )

    await session.start(ctx)
    await session.say(greeting, allow_interruptions=True)

if __name__ == "__main__":
    agents.cli.run_app(server)
