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
    TurnHandlingOptions, inference, function_tool, RunContext, stt, utils
)
from livekit.plugins import openai, silero

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
You are Buddy, a friendly, concise, and upbeat voice AI assistant.
You are chatting with your friend Bhupendra in real-time over audio.

RULES:
1. Speak in short, natural sentences. Keep your response under three sentences.
2. Deliver one clear thought per breath.
3. NEVER output markdown symbols: no asterisks, no bullet points, no headers, no bold text.
4. Sound warm, supportive, and natural.
5. Ask a helpful follow-up question when it moves the conversation forward.
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
    """Voice Assistant Agent implementation."""

    def __init__(self):
        super().__init__(instructions=INSTRUCTIONS)

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        """
        2026 RAG & Memory Hook: Intercepts user utterance before the LLM speaks.
        """
        pass

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

    # 6. Configure session
    session = AgentSession(
        vad=vad_provider,
        turn_handling=turn_handling,
        llm=llm_provider,
        tts=tts_provider,
        stt=stt_provider,
    )

    # Real-time console diagnostics
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

    buddy = BuddyAgent()
    await session.start(room=ctx.room, agent=buddy)

    # Speak first as demonstrated in Lesson 1 [11:26]
    print("\n[Agent]: Speaking initial greeting...")
    await session.say("Hello Bhupendra! Buddy here, ready to chat. How can I help you today?")

if __name__ == "__main__":
    agents.cli.run_app(server)
