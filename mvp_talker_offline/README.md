# MVP Offline LiveKit Voice Agent

A clean, self-contained, offline LiveKit Voice Agent built according to the **LiveKit Voice AI Course tutorial** and the **2026 Offline Conversation Buddy Architecture Guide**.

---

## Architecture

```
User Voice / Mic / WebRTC
          │
          ▼
    LiveKit Agent (`agent.py`)
    ├── VAD: Silero VAD (`silero.VAD.load()`)
    ├── Turn Detector: Local Audio Turn Detector (`v1-mini`)
    ├── LLM: Ollama Qwen (`qwen-buddy` / `qwen2.5:3b`) via `openai.LLM.with_ollama`
    ├── STT: Local Faster-Whisper via `stt.StreamAdapter`
    └── TTS: Local Audio Synthesizer via `openai.TTS`
```

---

## How to Run

### 1. Run in LiveKit Console Mode (Terminal Mic & Speaker)
This matches the exact command demonstrated in Lesson 1 & Lesson 2 of the course:
```bash
cd mvp_talker_offline
python agent.py console
```
To list your machine's input/output audio devices:
```bash
python agent.py console --list-devices
```
To run in interactive text console mode:
```bash
python agent.py console --text
```

---

### 2. Run in LiveKit Server Mode (WebRTC Room)
1. Start LiveKit Server locally in one terminal:
   ```bash
   livekit-server --dev
   ```

2. Start the Voice Agent worker in another terminal:
   ```bash
   cd mvp_talker_offline
   python agent.py dev
   ```

---

## Files

- `agent.py`: The main LiveKit Agent script (`AgentServer` + `AgentSession` + `BuddyAgent`).
- `audio_server.py`: Local OpenAI-compatible STT/TTS microservice (Faster-Whisper + Edge-TTS). Auto-launched by `agent.py`.
- `Modelfile`: Ollama model configuration for `qwen-buddy`.
- `.env`: Environment variables for LiveKit and Ollama.
