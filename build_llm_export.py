#!/usr/bin/env python3
"""
Generates high-fidelity, LLM-optimized codebase exports for both Frontend and Backend.
Provides:
- Directory trees & manifests
- Logically chunked text files (< 20K tokens each) for targeted LLM prompts
- Single full-codebase bundle text files for large-context models
- Delimiters and metadata headers formatted for zero-ambiguity parsing by any LLM
"""

import os
import sys
import json
import shutil
from pathlib import Path

BASE_DIR = Path("/home/bhupendra/Videos/livekit guides")
EXPORT_DIR = BASE_DIR / "codebase_llm_export"
FE_DIR = EXPORT_DIR / "frontend"
BE_DIR = EXPORT_DIR / "backend"

def read_file(rel_path: str) -> str:
    fp = BASE_DIR / rel_path
    if not fp.exists():
        return f"[File not found: {rel_path}]"
    try:
        return fp.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[Error reading {rel_path}: {e}]"

def format_file_block(rel_path: str, purpose: str, language: str) -> str:
    content = read_file(rel_path)
    lines = len(content.splitlines())
    header = (
        "=" * 80 + "\n"
        f"FILE: {rel_path}\n"
        f"LANGUAGE: {language}\n"
        f"LINES: {lines}\n"
        f"PURPOSE: {purpose}\n"
        + "=" * 80 + "\n"
    )
    return f"{header}\n{content}\n\n"

# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND DEFINITIONS (Conversational Generative UI — Gemini Live / Canvas)
# ─────────────────────────────────────────────────────────────────────────────

FE_CHUNKS = {
    "01_FE_CORE_AND_CONFIG.txt": [
        ("VisualsFrontend/package.json", "Project dependencies (React 19, Framer Motion, Lucide, Inter), scripts, build configuration", "json"),
        ("VisualsFrontend/vite.config.ts", "Vite build & dev server configuration with React plugin", "typescript"),
        ("VisualsFrontend/tsconfig.json", "Root TypeScript compiler options", "json"),
        ("VisualsFrontend/index.html", "HTML shell mounting root React container with Inter typography", "html"),
        ("VisualsFrontend/src/main.tsx", "React 19 entrypoint mounting App with @fontsource/inter", "typescript"),
        ("VisualsFrontend/src/index.css", "Design System: Dark surface tokens (--surface-0 to --surface-3), hairlines, and typography", "css"),
    ],
    "02_FE_STATE_AND_SERVICES.txt": [
        ("VisualsFrontend/src/types.ts", "Central TypeScript interfaces (FeedItem, QuizQuestion, ContentionProps, SyllabusData)", "typescript"),
        ("VisualsFrontend/src/store.ts", "Zustand state store managing sequential feed array, drawer state, and actions", "typescript"),
        ("VisualsFrontend/src/hooks/useSSE.ts", "Server-Sent Events hook subscribing to /api/stream (genui, genui_token, transcript)", "typescript"),
        ("VisualsFrontend/src/utils/bionic.ts", "Bionic reading text transformation algorithm bolding initial letters of words", "typescript"),
    ],
    "03_FE_CONVERSATIONAL_STAGE.txt": [
        ("VisualsFrontend/src/App.tsx", "Conversational Live Stage: Timeline feed, top status bar, bottom audio dock, and slide-over drawer", "typescript"),
        ("VisualsFrontend/src/components/Header.tsx", "Top navigation bar with engine status indicator, active chapter pill, and quick triggers", "typescript"),
        ("VisualsFrontend/src/components/AudioDock.tsx", "Floating voice visualizer dock with active waveform, composer textarea, and action chips", "typescript"),
        ("VisualsFrontend/src/components/SlideOverDrawer.tsx", "Collapsible slide-over drawer with 18-chapter roadmap, analytics, and remediation queue", "typescript"),
        ("VisualsFrontend/src/components/InlineQuizCard.tsx", "Inline generative quiz artifact card with feedback, rule citations, dispute handling, and isomorphic retry", "typescript"),
        ("VisualsFrontend/src/components/InlineDisputeCard.tsx", "Inline dispute ruling card comparing formal grammar vs colloquial usage with citations", "typescript"),
        ("VisualsFrontend/src/components/InlineNotesCard.tsx", "Inline revision notes artifact card with bionic reading toggle and common traps", "typescript"),
        ("VisualsFrontend/src/components/StreamingCard.tsx", "Live MCP/LLM token streaming card with typewriter animation and blinking cursor", "typescript"),
    ]
}

FE_OVERVIEW_MD = """# Frontend Architecture & Overview (VisualsFrontend)

## 1. Executive Summary
**VisualsFrontend** is a conversational generative UI modeled after **Gemini Live** and **ChatGPT Canvas**.
Built with React 19, TypeScript, Vite, Framer Motion, and Zustand, it serves as the real-time visual companion to the **Buddy Offline Voice AI Agent**.

## 2. Key Architecture Patterns
- **Event-Driven Conversation Timeline**:
  - Entire layout centers on a unified, chronological `feed: FeedItem[]` array.
  - Transcript utterances, in-flight token streaming cards (`StreamingCard`), interactive quiz cards (`InlineQuizCard`), linguistic dispute verdicts (`InlineDisputeCard`), and study notes (`InlineNotesCard`) render directly inline at their exact chronological position in the chat stream.
- **Top Header Bar**:
  - Live Audio / Engine status indicator pill (`Live Audio Connected` / `Engine Ready`).
  - Active chapter display pill.
  - Action triggers: `Quick Quiz`, `Notes`, and `Syllabus & Stats` drawer toggle.
- **Floating Voice & Audio Dock**:
  - Docked at the bottom of the viewport with an animated 5-bar active audio wave visualizer, auto-expanding composer, and quick prompt action chips.
- **Slide-Over Syllabus & Mastery Drawer**:
  - On-demand slide-over panel on the right side displaying current chapter details, mastery statistics (Accuracy Rate, Correct Answers, Errors Detected), 18-chapter linear curriculum roadmap, and isomorphic remediation queue.
- **Real-Time Stream Subscriber** (`useSSE.ts`):
  - Subscribes to backend event stream with automatic reconnect and exponential backoff.
  - Interleaves voice transcripts, live streaming LLM tokens, and generative UI component cards dynamically into the timeline.

## 3. Directory Tree
```
VisualsFrontend/
├── package.json               # React 19, Vite, Zustand, Framer-Motion, Lucide
├── vite.config.ts            # Vite config
├── tsconfig.json             # TypeScript config
├── index.html                # HTML entrypoint
└── src/
    ├── main.tsx              # React DOM render with Inter font
    ├── index.css             # Minimalist surface tokens & typography
    ├── types.ts              # FeedItem, QuizQuestion, ContentionProps
    ├── store.ts              # Unified timeline Zustand store
    ├── App.tsx               # Conversational Live Stage
    ├── hooks/
    │   └── useSSE.ts         # SSE event subscriber hook
    ├── utils/
    │   └── bionic.ts         # Bionic reading algorithm
    └── components/
        ├── Header.tsx        # Top status bar & chapter display
        ├── AudioDock.tsx     # Floating voice dock & waveform
        ├── SlideOverDrawer.tsx # 18-chapter roadmap & analytics drawer
        ├── InlineQuizCard.tsx# Inline interactive quiz card artifact
        ├── InlineDisputeCard.tsx # Inline linguistic dispute ruling artifact
        ├── InlineNotesCard.tsx # Inline study notes with Bionic reading
        └── StreamingCard.tsx # Live LLM token synthesis typewriter
```

## 4. Chunk Guide for LLMs
- **`01_FE_CORE_AND_CONFIG.txt`**: Core package config, HTML entrypoint, main.tsx, and design system CSS.
- **`02_FE_STATE_AND_SERVICES.txt`**: TypeScript interfaces, Zustand store, and SSE subscriber hook.
- **`03_FE_CONVERSATIONAL_STAGE.txt`**: Conversational Live Stage component (`App.tsx`), components (`Header`, `AudioDock`, `SlideOverDrawer`, `InlineQuizCard`, `InlineDisputeCard`, `InlineNotesCard`, `StreamingCard`).
- **`FULL_FRONTEND_CODEBASE.txt`**: Complete bundle of all frontend source files in one continuous document.
"""

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

BE_CHUNKS = {
    "01_BE_CORE_PIPELINE.txt": [
        ("mvp_talker_offline/backend/agent.py", "LiveKit voice AI agent entrypoint: Faster-Whisper STT, Silero VAD, Piper TTS, Ollama LLM, in-process function tools, and LiveKit text streams", "python"),
        ("mvp_talker_offline/backend/audio_server.py", "FastAPI server running Piper TTS audio synthesis (/v1/audio/speech), Faster-Whisper STT fallback, and curriculum/quiz REST endpoints", "python"),
        ("mvp_talker_offline/Modelfile", "Custom Ollama Modelfile configuring qwen2.5:3b with pedagogical teacher persona and grammar guidelines", "dockerfile"),
        ("mvp_talker_offline/requirements.txt", "Python backend requirements (livekit, faster-whisper, mcp, fastapi, uvicorn, rank-bm25, duckduckgo-search)", "text"),
        ("mvp_talker_offline/.env.example", "Environment variable documentation (LiveKit keys, Ollama URL, Piper voice model path)", "ini"),
    ],
    "02_BE_MCP_AND_ENGINES.txt": [
        ("mvp_talker_offline/backend/memory_mcp_server.py", "FastMCP server exposing tools: query_grammar_rag, get_learner_progress, advance_chapter, search_web_grammar, dispute_answer, log_learner_recast, generate_quiz, generate_revision_notes", "python"),
        ("mvp_talker_offline/backend/simulation_engine.py", "Pedagogical simulation engine handling error detection, dispute resolution via local RAG & DuckDuckGo, and colloquial recasts", "python"),
        ("mvp_talker_offline/backend/quiz_engine.py", "Quiz state machine managing chapter banks, answer verification, error tracking, and isomorphic repeat questions with SQLite audit logging", "python"),
        ("mvp_talker_offline/backend/syllabus_tracker.py", "18-chapter linear progression tracker backed by SQLite database (memory.db) tracking coursework, mastery, and isomorphic audits", "python"),
        ("mvp_talker_offline/backend/rag_store.py", "Hybrid retrieval store combining BM25 keyword matching and dense embeddings over textbook chunks with distinct outage logging", "python"),
    ],
    "03_BE_INGESTION_AND_DATA.txt": [
        ("mvp_talker_offline/backend/knowledge_ingestor.py", "Textbook & PDF ingestion pipeline indexing Oxford Guide, Arihant Grammar, Espresso English, and narrative stories into SQLite & RAG", "python"),
        ("mvp_talker_offline/backend/verify_phase1.py", "Automated test suite verifying RAG search, syllabus progression, quiz evaluation, and dispute handling", "python"),
        ("mvp_talker_offline/data/curriculum.json", "Official 18-chapter English grammar curriculum definition with title, topics, rules, and coursework requirements", "json"),
        ("mvp_talker_offline/data/quiz_banks/chapter_01_bank.json", "Pre-verified milestone quiz bank schema for Chapter 1 (Present Simple & Continuous) with citations and explanations", "json"),
        ("mvp_talker_offline/data/stories/aesop_dilemmas.txt", "Sample narrative conversation scenario used by agent for conversational grammar practice", "text"),
    ]
}

BE_OVERVIEW_MD = """# Backend Architecture & Overview (mvp_talker_offline)

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
"""

# ─────────────────────────────────────────────────────────────────────────────
# MASTER README
# ─────────────────────────────────────────────────────────────────────────────

MASTER_README_MD = """# Codebase Context Export for LLMs

This directory contains clean, structured, and chunked exports of the entire codebase for **Buddy — The Offline Voice AI English Grammar Coach**.

## Structure
```
codebase_llm_export/
├── README.md                      # This guide
├── frontend/                      # VisualsFrontend (React 19, TypeScript, Zustand, Vite)
│   ├── 00_FRONTEND_OVERVIEW.md    # Architecture overview, component tree, state diagram
│   ├── 01_FE_CORE_AND_CONFIG.txt  # package.json, vite.config.ts, tsconfig.json, index.html, main.tsx, index.css
│   ├── 02_FE_STATE_AND_SERVICES.txt # types.ts, store.ts, useSSE.ts, bionic.ts
│   ├── 03_FE_CONVERSATIONAL_STAGE.txt # App.tsx, Header, AudioDock, Drawer, and inline artifact cards
│   └── FULL_FRONTEND_CODEBASE.txt # Single bundle of all frontend source files
└── backend/                       # mvp_talker_offline (Python, LiveKit, FastAPI, FastMCP, SQLite)
    ├── 00_BACKEND_OVERVIEW.md     # Architecture overview, voice pipeline, and in-process tools
    ├── 01_BE_CORE_PIPELINE.txt    # agent.py, audio_server.py, Modelfile, requirements
    ├── 02_BE_MCP_AND_ENGINES.txt  # memory_mcp_server.py, simulation, quiz, syllabus, rag_store
    ├── 03_BE_INGESTION_AND_DATA.txt # knowledge_ingestor.py, curriculum.json, sample quiz banks
    └── FULL_BACKEND_CODEBASE.txt  # Single bundle of all backend source files
```

## How to Feed this to an LLM
1. **For Large-Context Models (Claude 3.5 Sonnet, GPT-4o, Gemini 1.5/2.0)**:
   - Provide `frontend/FULL_FRONTEND_CODEBASE.txt` for frontend tasks or refactoring.
   - Provide `backend/FULL_BACKEND_CODEBASE.txt` for backend tasks or agent logic.
2. **For Smaller-Context or Local Models (8k – 32k tokens)**:
   - Start by reading `00_FRONTEND_OVERVIEW.md` or `00_BACKEND_OVERVIEW.md`.
   - Select only the relevant chunk:
     - To edit state: Load `02_FE_STATE_AND_SERVICES.txt`.
     - To edit UI components: Load `03_FE_CONVERSATIONAL_STAGE.txt`.
     - To modify core configs: Load `01_FE_CORE_AND_CONFIG.txt`.
     - To modify LiveKit audio: Load `01_BE_CORE_PIPELINE.txt`.
"""

def generate_exports():
    print(f"Generating LLM export at: {EXPORT_DIR}")
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    FE_DIR.mkdir(parents=True, exist_ok=True)
    BE_DIR.mkdir(parents=True, exist_ok=True)

    # Master README
    (EXPORT_DIR / "README.md").write_text(MASTER_README_MD.strip() + "\n", encoding="utf-8")

    # Frontend Overview
    (FE_DIR / "00_FRONTEND_OVERVIEW.md").write_text(FE_OVERVIEW_MD.strip() + "\n", encoding="utf-8")

    # Frontend Chunks
    full_fe_content = []
    for chunk_filename, file_list in FE_CHUNKS.items():
        chunk_content = []
        for rel_path, purpose, lang in file_list:
            block = format_file_block(rel_path, purpose, lang)
            chunk_content.append(block)
            full_fe_content.append(block)
        (FE_DIR / chunk_filename).write_text("".join(chunk_content), encoding="utf-8")
        print(f"  [FE Chunk] Wrote {chunk_filename} ({len(file_list)} files)")

    (FE_DIR / "FULL_FRONTEND_CODEBASE.txt").write_text("".join(full_fe_content), encoding="utf-8")
    print(f"  [FE Bundle] Wrote FULL_FRONTEND_CODEBASE.txt ({len(full_fe_content)} files total)")

    # Backend Overview
    (BE_DIR / "00_BACKEND_OVERVIEW.md").write_text(BE_OVERVIEW_MD.strip() + "\n", encoding="utf-8")

    # Backend Chunks
    full_be_content = []
    for chunk_filename, file_list in BE_CHUNKS.items():
        chunk_content = []
        for rel_path, purpose, lang in file_list:
            block = format_file_block(rel_path, purpose, lang)
            chunk_content.append(block)
            full_be_content.append(block)
        (BE_DIR / chunk_filename).write_text("".join(chunk_content), encoding="utf-8")
        print(f"  [BE Chunk] Wrote {chunk_filename} ({len(file_list)} files)")

    (BE_DIR / "FULL_BACKEND_CODEBASE.txt").write_text("".join(full_be_content), encoding="utf-8")
    print(f"  [BE Bundle] Wrote FULL_BACKEND_CODEBASE.txt ({len(full_be_content)} files total)")

    print(f"\nExport complete! Files written to:\n  {EXPORT_DIR}")

if __name__ == "__main__":
    generate_exports()
