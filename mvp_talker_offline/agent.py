"""LiveKit Offline Voice AI Agent.
2026 Architectural Spec:
- STT: In-memory Faster-Whisper (zero HTTP socket serialization, zero disk I/O, runs on CPU int8)
- VAD: Local Silero VAD (single instance reuse)
- Turn Detector: Local Audio Turn Detector (v1-mini on CPU)
- LLM: Local Ollama Qwen (qwen-buddy / qwen2.5:7b) via openai.LLM.with_ollama
- TTS: Local Audio Server via openai.TTS
- Compatible with:
    python agent.py console           (Interactive microphone/speaker console)
    python agent.py console --text    (Interactive text console)
    python agent.py dev               (LiveKit WebRTC server mode)
"""

import os
import sys

# Force offline mode for Hugging Face Hub to prevent broken IPv6 connection hangs
os.environ["HF_HUB_OFFLINE"] = "1"

import socket
import asyncio
import datetime
import subprocess
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
import memory_store

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen-buddy")
AUDIO_SERVER_URL = os.getenv("AUDIO_SERVER_URL", "http://127.0.0.1:8880/v1")

def is_audio_server_running(host: str = "127.0.0.1", port: int = 8880) -> bool:
    """Check if local audio TTS server is reachable."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0

async def ensure_audio_server_async():
    """Starts the local audio server daemon if not already running without blocking event loop."""
    if not is_audio_server_running():
        server_script = Path(__file__).resolve().parent / "audio_server.py"
        if server_script.exists():
            print("Starting background local audio server (port 8880) for TTS...")
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
You are Buddy, a friendly, supportive, and engaging English conversation buddy and speaking coach.
You are chatting with your friend and student, Bhupendra, in real time over voice.
Your mission is to help Bhupendra practice natural spoken English, build speaking confidence across everyday scenarios, and gently improve grammatical mistakes.

CORE TEACHING & CONVERSATIONAL RULES:
1. GENTLE CONVERSATIONAL RECASTING (NO PEDANTIC LECTURES):
   - When the user makes a grammatical slip, awkward phrasing, or wrong tense, DO NOT interrupt aggressively or lecture.
   - Gently recast and model the correct phrasing naturally in your reply.
     * Example: User says "Yesterday I have went to market." -> Buddy says: "Ah, you went to the market yesterday! What did you get while you were there?"
     * Example: User says "She don't know the answer." -> Buddy says: "Right, she doesn't know yet! How do you think she will find out?"
   - If a quick tip is helpful, give a simple one-sentence tip, then immediately keep the dialogue moving.
2. PRACTICE REAL-LIFE SCENARIOS & CASUAL TALK:
   - Guide the conversation through realistic scenarios: daily small talk, ordering at a cafe, job interviews, travel situations, discussing hobbies, technology, or weekend plans.
   - If the user seems stuck or gives very short replies, encourage them with two fun, easy options to choose from.
3. SPOKEN VOICE CONSTRAINTS (MANDATORY FOR AUDIO):
   - Keep answers short and natural: 1 to 3 spoken sentences per turn. Never dump long paragraphs.
   - Deliver one clear thought per breath.
   - NEVER emit markdown symbols: no asterisks (*), no bullet points (-), no numbered lists, no headers (#), no bold text.
   - Output only clean, plain conversational English suitable for text-to-speech.
4. CONTINUITY & ENGAGEMENT:
   - Always end your turn with an engaging follow-up question or conversational prompt to invite the user to speak next.
   - Use your memory tools and past session context to reference what you practiced earlier and pick up where you left off.
"""

class FasterWhisperSTT(stt.STT):
    """
    In-memory STT bypassing HTTP microservices and disk writes.
    Captures raw PCM16 frames, resamples to 16kHz mono, and runs Faster-Whisper on CPU.
    """
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

        # Whisper requires 16000Hz mono audio
        if frame.sample_rate != 16000 or frame.num_channels != 1:
            resampler = rtc.AudioResampler(input_rate=frame.sample_rate, output_rate=16000, num_channels=1)
            resampled_frames = resampler.push(frame)
            if not resampled_frames:
                return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])
            frame = rtc.combine_audio_frames(resampled_frames)

        # Convert PCM16 int16 to float32 normalized to [-1.0, 1.0]
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
    """English Practice Voice Assistant Agent implementation with Memory & RAG."""

    def __init__(self, session_id: str = "default-session"):
        super().__init__(instructions=INSTRUCTIONS)
        self.session_id = session_id

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        """
        Memory & RAG Hook: Records the user's turn and injects relevant past memory
        if the user asks about prior topics, mistakes, or learning progress.
        """
        content_items = getattr(new_message, "content", [])
        if isinstance(content_items, list):
            user_text = " ".join(str(c) for c in content_items if isinstance(c, str)).strip()
        else:
            user_text = str(content_items).strip()

        if user_text:
            # Check for memory recall queries
            query_lower = user_text.lower()
            recall_triggers = [
                "last time", "earlier", "remember", "yesterday", "previous",
                "mistake", "progress", "before", "what did we talk", "topics"
            ]
            if any(trigger in query_lower for trigger in recall_triggers):
                past_turns = memory_store.search_conversation_history(user_text, limit=3)
                if past_turns:
                    memory_lines = [f"- [{t['timestamp'][:16]}] {t['role']}: {t['content']}" for t in past_turns]
                    context_snippet = (
                        "RECALLED MEMORY FROM PREVIOUS SESSIONS:\n"
                        + "\n".join(memory_lines)
                        + "\nUse this context to accurately answer the user's question about what was discussed."
                    )
                    turn_ctx.add_message(role="system", content=context_snippet)

    @function_tool
    async def get_learning_history(self, context: RunContext) -> str:
        """Retrieves user's overall English learning progress, past practice topics, and recurring grammar areas."""
        prog = memory_store.get_learning_progress()
        recent = [t['topic'] for t in prog.get('recent_topics', []) if t.get('topic')]
        grammar = [g['grammar_point'] for g in prog.get('grammar_focus_areas', [])]
        recent_str = ", ".join(recent) if recent else "General English conversation"
        grammar_str = ", ".join(grammar) if grammar else "Conversational fluency and tense accuracy"
        return f"Past practice topics: {recent_str}. Active grammar focus areas: {grammar_str}."

    @function_tool
    async def save_practice_milestone(self, context: RunContext, topic: str, grammar_tip: str) -> str:
        """Saves a scenario milestone or grammar rule practiced during this session to persistent memory."""
        memory_store.update_session_summary(
            self.session_id,
            topic=topic,
            grammar_focus=grammar_tip,
            summary=f"Practiced {topic} with focus on {grammar_tip}."
        )
        return f"Saved milestone for topic '{topic}' with grammar focus '{grammar_tip}'."

    @function_tool
    async def get_current_time(self, context: RunContext) -> str:
        """Returns the current day, date, and local time."""
        now = datetime.datetime.now()
        return f"It is {now.strftime('%A, %B %d, %Y at %I:%M %p')}."

    @function_tool
    async def get_system_status(self, context: RunContext) -> str:
        """Checks local hardware, GPU acceleration, and model status."""
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True
            )
            gpu_info = res.stdout.strip() if res.returncode == 0 else "GPU status unavailable"
            return f"System is running offline locally. GPU status: {gpu_info}."
        except Exception:
            return "System is running offline locally in good condition."

server = AgentServer()

@server.rtc_session(agent_name="offline-buddy")
async def entrypoint(ctx: agents.JobContext):
    """Main LiveKit RTC Session entrypoint."""
    await ensure_audio_server_async()

    # 1. Local Ollama LLM provider
    llm_provider = openai.LLM.with_ollama(
        model=OLLAMA_MODEL,
        base_url=f"{OLLAMA_BASE_URL.rstrip('/')}/v1",
    )

    # 2. Local Silero VAD provider (Single instance loaded and shared)
    vad_provider = silero.VAD.load()

    # 3. Local Audio Turn Detector (v1-mini CPU local model) with local VAD interruption
    turn_handling = TurnHandlingOptions(
        turn_detection=inference.TurnDetector(version="v1-mini"),
        interruption={"mode": "vad"},
    )

    # 4. Local TTS (Synthesizes through local OpenAI-compatible endpoint)
    tts_provider = openai.TTS(
        model="tts-1",
        voice="alloy",
        base_url=AUDIO_SERVER_URL,
        api_key="local-only",
    )

    # 5. In-Memory Faster-Whisper STT with Silero StreamAdapter
    local_whisper = get_faster_whisper_stt(model_size="tiny.en")
    stt_provider = stt.StreamAdapter(
        stt=local_whisper,
        vad=vad_provider,
    )

    # 6. Configure MCP Memory Server via MCPToolset
    mcp_script = Path(__file__).resolve().parent / "memory_mcp_server.py"
    memory_mcp = mcp.MCPServerStdio(
        command=sys.executable,
        args=[str(mcp_script)],
    )
    memory_toolset = mcp.MCPToolset(id="memory", mcp_server=memory_mcp)

    # 7. Configure session with MCP Tools
    session = AgentSession(
        vad=vad_provider,
        turn_handling=turn_handling,
        llm=llm_provider,
        tts=tts_provider,
        stt=stt_provider,
        tools=[memory_toolset],
    )

    # Initialize persistent session tracking & previous context
    current_session_id = f"session-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    last_session = memory_store.get_last_session()

    # Real-time console diagnostics & memory persistence
    @session.on("conversation_item_added")
    def on_conversation_item(ev):
        item = getattr(ev, "item", None)
        if item:
            role = getattr(item, "role", None)
            content = getattr(item, "content", None)
            if role in ("user", "assistant") and content:
                if isinstance(content, list):
                    text = " ".join(str(c) for c in content if isinstance(c, str)).strip()
                else:
                    text = str(content).strip()
                if text:
                    memory_store.record_turn(current_session_id, role, text)

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

    @session.on("error")
    def on_error(ev):
        print(f"\n[Session Notice]: {ev.error}")

    buddy = BuddyAgent(session_id=current_session_id)
    await session.start(room=ctx.room, agent=buddy)

    # Context-aware first speech: Pick up from previous session or start fresh
    if last_session and last_session.get("topic") and last_session.get("topic") != "None":
        prev_topic = last_session.get("topic")
        prev_focus = last_session.get("grammar_focus") or "natural phrasing"
        memory_store.start_session(current_session_id, topic=prev_topic, grammar_focus=prev_focus)
        greeting = (
            f"Hello Bhupendra! Buddy here, ready for another English practice session. "
            f"Last time we practiced {prev_topic}. "
            f"Would you like to pick up where we left off, or practice a new scenario today?"
        )
    else:
        memory_store.start_session(
            current_session_id,
            topic="Daily Small Talk & Introduction",
            grammar_focus="Conversational Fluency & Tenses"
        )
        greeting = (
            "Hello Bhupendra! Buddy here, your English conversational buddy. "
            "I am excited to chat and practice with you today! "
            "How has your day been so far, or is there a particular scenario you want to try?"
        )

    print(f"\n[Agent]: Speaking initial greeting...")
    await session.say(greeting)

if __name__ == "__main__":
    agents.cli.run_app(server)
