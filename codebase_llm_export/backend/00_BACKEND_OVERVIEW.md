# Backend Architecture & Overview (mvp_talker_offline)

## 1. Executive Summary
**mvp_talker_offline** is a 100% locally-hosted, offline-capable Voice AI English Grammar Coach and simulator.
It combines LiveKit Agents SDK, Faster-Whisper (CPU int8 STT), Piper/Kokoro (neural TTS), Ollama (`qwen2.5:7b`), in-process LiveKit function tools, and hybrid BM25 + vector RAG across authoritative grammar textbooks (Oxford Guide, Arihant English, Espresso English).

## 2. Phase 1 Architecture: In-Process Function Tools
```
             ┌──────── LiveKit Voice Agent (agent.py) ────────┐
              • In-process function_tools:
                - query_grammar_rag
                - trigger_quiz
                - dispute_answer
                - get_learner_progress
                - generate_revision_notes
                - advance_chapter
                - deliver_canvas_lecture
                - request_reinterpretation
              • LiveKit text streams on room:
                - topic: 'transcript'
                - topic: 'genui'
              • Native RPC Handlers:
                - getSyllabus, getQuiz, submitQuizAnswer,
                  disputeAnswer, advanceChapter,
                  deliverCanvasLecture, requestReinterpretation
             └───────┬───────────────────────────────┬────────┘
                     │ Direct python call            │ WebRTC Data / Streams
                     ▼                               ▼
       ┌───────────────────────────────┐     ┌───────────────────────────────┐
       │ In-Process Pedagogical Layer  │     │ WebRTC Frontend               │
       │  - RAGStore (BM25 + vectors)  │     │ (mvp_talker_offline/          │
       │  - QuizEngine (Banks + Iso)   │     │  VisualsFrontend)             │
       │  - SyllabusTracker (SQLite)   │     └───────────────────────────────┘
       │  - SimulationEngine           │
       │  - CurriculumStore (5 tables) │
       │  - LangGraph Tutor (8 nodes)  │
       └─────────────┬─────────────────┘
                     │ HTTP (Audio Only)
                     ▼
       ┌───────────────────────────────┐
       │ audio_server.py (port 8880)   │
       │  - /v1/audio/speech (Kokoro)  │
       │  - /api/token (JWT minting)   │
       └───────────────────────────────┘
```
