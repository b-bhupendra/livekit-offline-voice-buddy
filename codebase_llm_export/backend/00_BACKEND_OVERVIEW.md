# Backend Architecture & Overview (mvp_talker_offline)

## 1. Executive Summary
**mvp_talker_offline** is a 100% locally-hosted, offline-capable Voice AI English Grammar Coach and simulator.
It combines LiveKit Agents SDK, Faster-Whisper (CPU int8 STT), Piper (neural TTS), Ollama (`qwen2.5:3b`), in-process LiveKit function tools, and hybrid BM25 + vector RAG across authoritative grammar textbooks (Oxford Guide, Arihant English, Espresso English).

## 2. Phase 1 Architecture: In-Process Function Tools
```
             ┌──────── LiveKit Voice Agent (agent.py) ────────┐
             │  • In-process function_tools:                  │
             │    - query_grammar_rag                         │
             │    - trigger_quiz                              │
             │    - dispute_answer                            │
             │    - get_learner_progress                      │
             │    - generate_revision_notes                   │
             │  • LiveKit text streams on room:               │
             │    - topic: 'transcript'                       │
             │    - topic: 'genui'                            │
             └───────┬───────────────────────────────┬────────┘
                     │ Direct python call            │ WebRTC Data
                     ▼                               ▼
       ┌───────────────────────────────┐     ┌───────────────────┐
       │ In-Process Pedagogical Layer  │     │ WebRTC Frontend   │
       │  - RAGStore (BM25 + vectors)  │     │ (VisualsFrontend) │
       │  - QuizEngine (Banks + Iso)   │     └───────────────────┘
       │  - SyllabusTracker (SQLite)   │
       │  - SimulationEngine           │
       └─────────────┬─────────────────┘
                     │ HTTP (Audio Only)
                     ▼
       ┌───────────────────────────────┐
       │ audio_server.py               │
       │  - /v1/audio/speech (Piper)   │
       │  - /v1/audio/transcriptions   │
       └───────────────────────────────┘
```

## 3. Key Subsystems
1. **LiveKit Voice Agent (`agent.py`)**:
   - Audio Pipeline: StreamAdapter wrapping in-memory Faster-Whisper `tiny.en`, Silero VAD, and local Audio Turn Detector `v1-mini`.
   - TTS: HTTP OpenAI-compatible endpoint provided by `audio_server.py` invoking Piper ONNX model (`en_US-lessac-medium`).
   - Hooks: Captures `user_input_transcribed` and `agent_speech_committed` and publishes directly via room text streams.
2. **Audio Server (`audio_server.py`)**:
   - Runs FastAPI on port 8880.
   - Dedicated audio processing: Piper TTS synthesis and Faster-Whisper transcription.
3. **Pedagogical Engines**:
   - **`quiz_engine.py`**: Linear chapter progression, error counting, isomorphic problem repetition with audit logging to SQLite (`isomorphic_mutation_audit`).
   - **`simulation_engine.py`**: Linguistic dispute resolution with offline local RAG fallback and dialect register analysis.
   - **`syllabus_tracker.py`**: SQLite database interface (`memory.db`) storing learner state and curriculum progress.
   - **`rag_store.py`**: BM25 + dense embedding vector index over textbook sections with explicit service outage logging.
