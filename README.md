# LiveKit Offline Voice AI Agent ("Buddy")

An enterprise-grade, 100% offline, ultra-low-latency Voice AI Agent built using **LiveKit Agents (`>= 1.8.2`)**, **Ollama (`qwen2.5:7b` / custom `qwen-buddy`)**, **Faster-Whisper (`tiny.en`)**, and **Piper Neural TTS**.

Designed according to the **Master Voice AI Agents LiveKit Full Course** and the **2026 Offline Conversation Buddy Architecture Specification**.

---

## ⚡ Key Highlights & Architecture

- **Zero Cloud Dependencies**: 100% local STT, LLM, Turn Detection, and TTS.
- **In-Memory Streaming STT**: Uses an in-process `FasterWhisperSTT` directly on PCM16 audio buffers via LiveKit's `stt.StreamAdapter`, bypassing disk I/O and HTTP microservice socket overhead.
- **Hardware-Aware Turn Detection**: Single-instance `Silero VAD` + local `TurnDetector(v1-mini)` with pure VAD interruption (`interruption={"mode": "vad"}`).
- **Local LLM**: Local Ollama Qwen model with voice-first system prompt instructions (short natural sentences, no markdown symbols).
- **On-Device Neural TTS**: High-speed local Piper TTS synthesizing speech in ~0.12s.
- **First-Speaker Capability**: Buddy greets the user immediately upon room entry as demonstrated in Lesson 1 of the LiveKit course.

```
User Voice / Mic / WebRTC
          │
          ▼
    LiveKit Agent (`agent.py`)
    ├── VAD: Silero VAD (`silero.VAD.load()`)
    ├── Turn Detector: Local Audio Turn Detector (`v1-mini`) [VAD mode interruption]
    ├── STT: In-Memory Faster-Whisper (`tiny.en`) on CPU int8
    ├── LLM: Local Ollama Qwen (`qwen-buddy` / `qwen2.5:7b`) via `openai.LLM.with_ollama`
    └── TTS: Local Piper Neural TTS (`audio_server.py`) via `openai.TTS`
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+ (or [uv](https://docs.astral.sh/uv/))
- [Ollama](https://ollama.com/) running locally
- Pull or create the local Qwen model:
  ```bash
  ollama create qwen-buddy -f mvp_talker_offline/Modelfile
  ```

### 2. Installation

Clone and install dependencies:
```bash
git clone https://github.com/b-bhupendra/livekit-offline-voice-buddy.git
cd livekit-offline-voice-buddy
pip install -r mvp_talker_offline/requirements.txt
```
*(Or run with `uv`: `uv sync`)*

### 3. Run in Console Mode (Terminal Mic & Speaker)

Run directly from root:
```bash
python agent.py console
```
Or with `uv`:
```bash
uv run agent.py console
```

To run in text interactive mode:
```bash
python agent.py console --text
```

### 4. Run in Server Mode (LiveKit WebRTC Room)

1. Start LiveKit Server locally in one terminal:
   ```bash
   livekit-server --dev
   ```
2. Start the Voice Agent worker in another terminal:
   ```bash
   python agent.py dev
   ```

---

## 📁 Repository Structure

```
.
├── agent.py                                               # Root launcher delegating to mvp_talker_offline
├── pyproject.toml                                         # uv / PEP-621 project configuration
├── .env.example                                           # Environment variable template
├── mvp_talker_offline/
│   ├── agent.py                                           # Main LiveKit AgentServer, AgentSession & BuddyAgent
│   ├── audio_server.py                                    # Local OpenAI-compatible TTS/STT microservice
│   ├── Modelfile                                          # Voice-first Ollama configuration for Qwen
│   ├── requirements.txt                                   # Python dependencies
│   ├── models/                                            # Directory for Piper ONNX voices
│   └── README.md                                          # Subsystem documentation
├── lessons/                                               # Visual lecture slide decks from the LiveKit course
└── livekit_course_transcript.md                           # Full course video transcript and reference guide
```

---

## 📄 License

MIT License.
