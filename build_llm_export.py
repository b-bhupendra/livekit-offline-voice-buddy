#!/usr/bin/env python3
"""
Generates high-fidelity, LLM-optimized codebase exports for both Frontend and Backend.
Provides:
- All 3 full codebase bundles at root level:
    1. FULL_PROJECT_CODEBASE.txt (Combined BE + FE, 32 files)
    2. FULL_FRONTEND_CODEBASE.txt (All FE, 18 files)
    3. FULL_BACKEND_CODEBASE.txt (All BE, 14 files)
- Single consolidated 'chunks/' directory containing all 6 logical chunks (< 20K tokens each)
- Separated 'frontend/' and 'backend/' directories with architectural overviews and dedicated chunks
- Delimiters and metadata headers formatted for zero-ambiguity parsing by any LLM
"""

import os
import sys
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "codebase_llm_export"
CHUNKS_DIR = EXPORT_DIR / "chunks"
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
# FRONTEND DEFINITIONS (mvp_talker_offline/VisualsFrontend)
# ─────────────────────────────────────────────────────────────────────────────

FE_CHUNKS = {
    "01_FE_CORE_AND_CONFIG.txt": [
        ("mvp_talker_offline/VisualsFrontend/package.json", "Project dependencies (React 19, Framer Motion, Lucide, Inter, LiveKit Client), scripts, build configuration", "json"),
        ("mvp_talker_offline/VisualsFrontend/vite.config.ts", "Vite build & dev server configuration with React plugin", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/tsconfig.json", "Root TypeScript compiler options", "json"),
        ("mvp_talker_offline/VisualsFrontend/index.html", "HTML shell mounting root React container with Inter typography", "html"),
        ("mvp_talker_offline/VisualsFrontend/src/main.tsx", "React 19 entrypoint mounting App with @fontsource/inter", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/index.css", "Design System: Dark surface tokens (--surface-0 to --surface-3), hairlines, and typography", "css"),
    ],
    "02_FE_STATE_AND_SERVICES.txt": [
        ("mvp_talker_offline/VisualsFrontend/src/types.ts", "Central TypeScript interfaces (FeedItem, QuizQuestion, ContentionProps, SyllabusData)", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/store.ts", "Zustand state store managing sequential feed array, LiveKit room instance, drawer state, and LiveKit RPC actions", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/hooks/useLiveKit.ts", "LiveKit WebRTC transport hook: room joining (/api/token), speaker audio track playback, text stream handling, and client RPC", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/utils/bionic.ts", "Bionic reading text transformation algorithm bolding initial letters of words", "typescript"),
    ],
    "03_FE_CONVERSATIONAL_STAGE.txt": [
        ("mvp_talker_offline/VisualsFrontend/src/App.tsx", "Conversational Live Stage: Timeline feed, top status bar, bottom audio dock, and slide-over drawer", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/Header.tsx", "Top navigation bar with engine status indicator, active chapter pill, and quick triggers", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/AudioDock.tsx", "Floating voice visualizer dock with active waveform, composer textarea, and action chips", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/SlideOverDrawer.tsx", "Collapsible slide-over drawer with 18-chapter roadmap, analytics, and remediation queue", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/SyllabusSection.tsx", "Modular syllabus section displaying active chapter hero, stage badges, coursework gating, 18-chapter roadmap, and drift audit metrics", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/InlineQuizCard.tsx", "Inline generative quiz artifact card with feedback, rule citations, dispute handling, and isomorphic retry", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/InlineDisputeCard.tsx", "Inline dispute ruling card comparing formal grammar vs colloquial usage with citations", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/InlineNotesCard.tsx", "Inline revision notes artifact card with bionic reading toggle and common traps", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/InlineGrammarMovementCard.tsx", "Inline syntactic movement animation card with Framer Motion layoutId spring physics and role capsules", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/StreamingCard.tsx", "Live LLM token synthesis card with typewriter animation and blinking cursor", "typescript"),
    ]
}

FE_OVERVIEW_MD = """# Frontend Architecture & Overview (mvp_talker_offline/VisualsFrontend)

## 1. Executive Summary
**VisualsFrontend** is a conversational generative UI modeled after **Gemini Live** and **ChatGPT Canvas**.
Built with React 19, TypeScript, Vite, Framer Motion, and Zustand, it serves as the real-time visual companion to the **Buddy Offline Voice AI Agent**. It lives under `mvp_talker_offline/VisualsFrontend/`.

## 2. Key Architecture Patterns
- **Event-Driven Conversation Timeline**:
  - Entire layout centers on a unified, chronological `feed: FeedItem[]` array.
  - Transcript utterances, in-flight token streaming cards (`StreamingCard`), interactive quiz cards (`InlineQuizCard`), linguistic dispute verdicts (`InlineDisputeCard`), study notes (`InlineNotesCard`), and syntactic movement cards (`InlineGrammarMovementCard`) render directly inline at their exact chronological position in the chat stream.
- **Top Header Bar**:
  - Live Audio / Engine status indicator pill (`Live Audio Connected` / `Engine Ready`).
  - Active chapter display pill.
  - Action triggers: `Quick Quiz`, `Notes`, and `Syllabus & Stats` drawer toggle.
- **Floating Voice & Audio Dock**:
  - Docked at the bottom of the viewport with an animated 5-bar active audio wave visualizer, auto-expanding composer, and quick prompt action chips.
- **Slide-Over Syllabus & Mastery Drawer**:
  - On-demand slide-over panel on the right side displaying current chapter details, mastery statistics (Accuracy Rate, Correct Answers, Errors Detected), 18-chapter linear curriculum roadmap, and isomorphic remediation queue.
- **Real-Time LiveKit Transport** (`useLiveKit.ts`):
  - Connects to LiveKit room via WebRTC data channels and text streams (`transcript`, `genui`, `genui_token`).
  - Native RPC caller for `getSyllabus`, `getQuiz`, `submitQuizAnswer`, `disputeAnswer`, and `advanceChapter`.

## 3. Directory Tree
```
mvp_talker_offline/
└── VisualsFrontend/
    ├── package.json               # React 19, Vite, Zustand, Framer-Motion, Lucide, LiveKit Client
    ├── vite.config.ts            # Vite config
    ├── tsconfig.json             # TypeScript config
    ├── index.html                # HTML entrypoint
    └── src/
        ├── main.tsx              # React DOM render with Inter font
        ├── index.css             # Minimalist surface tokens & typography
        ├── types.ts              # FeedItem, QuizQuestion, ContentionProps, GrammarMovementProps
        ├── store.ts              # Unified timeline Zustand store with LiveKit RPC
        ├── App.tsx               # Conversational Live Stage
        ├── hooks/
        │   └── useLiveKit.ts     # LiveKit WebRTC transport & RPC hook
        ├── utils/
        │   └── bionic.ts         # Bionic reading algorithm
        └── components/
            ├── Header.tsx        # Top status bar & chapter display
            ├── AudioDock.tsx     # Floating voice dock & waveform
            ├── SlideOverDrawer.tsx # 18-chapter roadmap & analytics drawer
            ├── InlineQuizCard.tsx# Inline interactive quiz card artifact
            ├── InlineDisputeCard.tsx # Inline linguistic dispute ruling artifact
            ├── InlineNotesCard.tsx # Inline study notes with Bionic reading
            ├── InlineGrammarMovementCard.tsx # Inline syntactic movement card with Framer Motion layoutId
            └── StreamingCard.tsx # Live LLM token synthesis typewriter
```

## 4. Chunk Guide for LLMs
- **`01_FE_CORE_AND_CONFIG.txt`**: Core package config, HTML entrypoint, main.tsx, and design system CSS.
- **`02_FE_STATE_AND_SERVICES.txt`**: TypeScript interfaces, Zustand store, and LiveKit WebRTC hook.
- **`03_FE_CONVERSATIONAL_STAGE.txt`**: Conversational Live Stage component (`App.tsx`), components (`Header`, `AudioDock`, `SlideOverDrawer`, `InlineQuizCard`, `InlineDisputeCard`, `InlineNotesCard`, `InlineGrammarMovementCard`, `StreamingCard`).
- **`FULL_FRONTEND_CODEBASE.txt`**: Complete bundle of all frontend source files in one continuous document.
"""

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND DEFINITIONS (mvp_talker_offline/backend)
# ─────────────────────────────────────────────────────────────────────────────

BE_CHUNKS = {
    "01_BE_CORE_PIPELINE.txt": [
        ("mvp_talker_offline/backend/agent.py", "LiveKit voice AI agent entrypoint: Faster-Whisper STT, Silero VAD, Piper TTS, Ollama LLM, in-process function tools (with RunContext UI streaming), and LiveKit RPC handlers", "python"),
        ("mvp_talker_offline/backend/audio_server.py", "Isolated FastAPI microservice serving local Piper neural TTS (/v1/audio/speech) and LiveKit JWT token minting (/api/token)", "python"),
        ("mvp_talker_offline/Modelfile", "Custom Ollama Modelfile configuring qwen2.5:3b with pedagogical teacher persona and grammar guidelines", "dockerfile"),
        ("mvp_talker_offline/requirements.txt", "Python backend requirements (livekit, faster-whisper, fastapi, uvicorn, rank-bm25, duckduckgo-search)", "text"),
        ("mvp_talker_offline/.env.example", "Environment variable documentation (LiveKit keys, Ollama URL, Piper voice model path)", "ini"),
    ],
    "02_BE_ENGINES.txt": [
        ("mvp_talker_offline/backend/simulation_engine.py", "Pedagogical simulation engine handling error detection, dispute resolution via local RAG & DuckDuckGo, and colloquial recasts", "python"),
        ("mvp_talker_offline/backend/quiz_engine.py", "Quiz state machine managing chapter banks, answer verification, error tracking, and isomorphic repeat questions with SQLite audit logging", "python"),
        ("mvp_talker_offline/backend/syllabus_tracker.py", "18-chapter linear progression tracker backed by SQLite database (memory.db) tracking coursework, mastery, and isomorphic audits", "python"),
        ("mvp_talker_offline/backend/rag_store.py", "Hybrid retrieval store combining BM25 keyword matching and dense embeddings over textbook chunks with distinct outage logging", "python"),
    ],
    "03_BE_INGESTION_AND_DATA.txt": [
        ("mvp_talker_offline/backend/knowledge_ingestor.py", "Textbook & PDF ingestion pipeline indexing Oxford Guide, Arihant Grammar, Espresso English, and narrative stories into SQLite & RAG", "python"),
        ("mvp_talker_offline/backend/verify_phase1.py", "Automated test suite verifying RAG search, syllabus progression, quiz evaluation, and dispute handling", "python"),
        ("mvp_talker_offline/backend/verify_phase2.py", "Automated test suite verifying embedding outage fallback, offline dispute, SQLite isomorphic audits, and learner state sync", "python"),
        ("mvp_talker_offline/backend/verify_phase3.py", "Automated test suite verifying streaming STT capabilities, StreamingFasterWhisperAdapter, and VoiceTurnPriorityManager", "python"),
        ("mvp_talker_offline/backend/verify_phase4.py", "Automated test suite verifying versioned GenUI schema ('1.0'), demonstrate_grammar_movement tool, and frontend motion integration", "python"),
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
             │    - advance_chapter                           │
             │  • LiveKit text streams on room:               │
             │    - topic: 'transcript'                       │
             │    - topic: 'genui'                            │
             │  • Native RPC Handlers:                        │
             │    - getSyllabus, getQuiz, submitQuizAnswer,   │
             │      disputeAnswer, advanceChapter             │
             └───────┬───────────────────────────────┬────────┘
                     │ Direct python call            │ WebRTC Data / Streams
                     ▼                               ▼
       ┌───────────────────────────────┐     ┌───────────────────────────────┐
       │ In-Process Pedagogical Layer  │     │ WebRTC Frontend               │
       │  - RAGStore (BM25 + vectors)  │     │ (mvp_talker_offline/          │
       │  - QuizEngine (Banks + Iso)   │     │  VisualsFrontend)             │
       │  - SyllabusTracker (SQLite)   │     └───────────────────────────────┘
       │  - SimulationEngine           │
       └─────────────┬─────────────────┘
                     │ HTTP (Audio Only)
                     ▼
       ┌───────────────────────────────┐
       │ audio_server.py (port 8880)   │
       │  - /v1/audio/speech (Piper)   │
       │  - /api/token (JWT minting)   │
       └───────────────────────────────┘
```

## 3. Key Subsystems
1. **LiveKit Voice Agent (`backend/agent.py`)**:
   - Audio Pipeline: StreamAdapter wrapping Faster-Whisper `tiny.en`, Silero VAD, and local Audio Turn Detector `v1-mini`.
   - TTS: HTTP OpenAI-compatible endpoint provided by `audio_server.py` invoking Piper ONNX model (`en_US-lessac-medium`).
   - In-Process Tools: Tools receive `RunContext` and push interactive GenUI cards (`QuizCard`, `BionicSketchNote`, `ContentionResolver`) directly to the WebRTC room via `send_room_text`.
2. **Audio Server (`backend/audio_server.py`)**:
   - Runs FastAPI on port 8880.
   - Dedicated microservice: Piper TTS synthesis and LiveKit JWT access token minting.
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

The project is organized under the monorepo folder **`mvp_talker_offline/`**:
- **`mvp_talker_offline/backend/`**: Python LiveKit Voice Agent, pedagogical engines, and audio microservice.
- **`mvp_talker_offline/VisualsFrontend/`**: React 19 / TypeScript / Vite / Zustand conversational UI.
- **`mvp_talker_offline/data/`**: Curriculum schema, quiz banks, and narrative practice stories.
- **`mvp_talker_offline/models/`**: Offline neural Piper TTS voice model.

---

## 1. ALL 3 FULL CODEBASE BUNDLES (Root Level)

For zero-navigation feeding into large-context LLMs (Claude 3.5 Sonnet, GPT-4o, Gemini 1.5/2.0 Pro):

| Bundle File | Scope | Description |
|---|---|---|
| **`FULL_PROJECT_CODEBASE.txt`** | **Complete Project (BE + FE)** | All 32 source files across the entire backend and frontend in one file |
| **`FULL_FRONTEND_CODEBASE.txt`** | **Full Frontend Stack** | All 18 frontend files (React 19, Zustand, LiveKit WebRTC, components) |
| **`FULL_BACKEND_CODEBASE.txt`** | **Full Backend Stack** | All 14 backend files (LiveKit Agent, FastAPI audio, engines, data) |

---

## 2. ALL CHUNKS IN A SINGLE FOLDER (`chunks/`)

For smaller context models (8k – 32k tokens) or targeted subagent prompts, all 6 chunks are unified in one directory:

```
codebase_llm_export/chunks/
├── 01_BE_CORE_PIPELINE.txt          # agent.py, audio_server.py, Modelfile, requirements
├── 02_BE_ENGINES.txt                # simulation_engine, quiz_engine, syllabus_tracker, rag_store
├── 03_BE_INGESTION_AND_DATA.txt     # knowledge_ingestor, curriculum.json, chapter_01_bank
├── 04_FE_CORE_AND_CONFIG.txt        # package.json, vite.config, tsconfig, index.html, index.css
├── 05_FE_STATE_AND_SERVICES.txt     # types.ts, store.ts, useLiveKit.ts, bionic.ts
└── 06_FE_CONVERSATIONAL_STAGE.txt   # App.tsx, Header, AudioDock, SlideOverDrawer, cards
```

---

## 3. SEPARATED STACK DIRECTORIES (`frontend/` and `backend/`)

For domain-specific development and targeted reviews:

```
codebase_llm_export/
├── frontend/
│   ├── 00_FRONTEND_OVERVIEW.md      # UI architecture, state model, component tree
│   ├── 01_FE_CORE_AND_CONFIG.txt
│   ├── 02_FE_STATE_AND_SERVICES.txt
│   ├── 03_FE_CONVERSATIONAL_STAGE.txt
│   └── FULL_FRONTEND_CODEBASE.txt
└── backend/
    ├── 00_BACKEND_OVERVIEW.md       # Agent pipeline, in-process tools, audio microservice
    ├── 01_BE_CORE_PIPELINE.txt
    ├── 02_BE_ENGINES.txt
    ├── 03_BE_INGESTION_AND_DATA.txt
    └── FULL_BACKEND_CODEBASE.txt
```

---

## How to Feed this to an LLM
1. **End-to-End Tasks**: Load **`FULL_PROJECT_CODEBASE.txt`**.
2. **Frontend Tasks**: Load **`FULL_FRONTEND_CODEBASE.txt`** (or chunks `04`, `05`, `06` in `chunks/`).
3. **Backend Tasks**: Load **`FULL_BACKEND_CODEBASE.txt`** (or chunks `01`, `02`, `03` in `chunks/`).
"""

def generate_exports():
    print(f"Generating LLM export at: {EXPORT_DIR}")
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    FE_DIR.mkdir(parents=True, exist_ok=True)
    BE_DIR.mkdir(parents=True, exist_ok=True)

    # Master README
    (EXPORT_DIR / "README.md").write_text(MASTER_README_MD.strip() + "\n", encoding="utf-8")

    # Frontend Overview
    (FE_DIR / "00_FRONTEND_OVERVIEW.md").write_text(FE_OVERVIEW_MD.strip() + "\n", encoding="utf-8")

    # Frontend Chunks
    full_fe_content = []
    fe_chunk_contents = {}
    for chunk_filename, file_list in FE_CHUNKS.items():
        chunk_content = []
        for rel_path, purpose, lang in file_list:
            block = format_file_block(rel_path, purpose, lang)
            chunk_content.append(block)
            full_fe_content.append(block)
        text = "".join(chunk_content)
        fe_chunk_contents[chunk_filename] = text
        (FE_DIR / chunk_filename).write_text(text, encoding="utf-8")
        print(f"  [FE Chunk] Wrote {chunk_filename} ({len(file_list)} files)")

    full_fe_str = "".join(full_fe_content)
    (FE_DIR / "FULL_FRONTEND_CODEBASE.txt").write_text(full_fe_str, encoding="utf-8")
    (EXPORT_DIR / "FULL_FRONTEND_CODEBASE.txt").write_text(full_fe_str, encoding="utf-8")
    print(f"  [FE Bundle] Wrote FULL_FRONTEND_CODEBASE.txt ({len(full_fe_content)} files total)")

    # Backend Overview
    (BE_DIR / "00_BACKEND_OVERVIEW.md").write_text(BE_OVERVIEW_MD.strip() + "\n", encoding="utf-8")

    # Backend Chunks
    full_be_content = []
    be_chunk_contents = {}
    for chunk_filename, file_list in BE_CHUNKS.items():
        chunk_content = []
        for rel_path, purpose, lang in file_list:
            block = format_file_block(rel_path, purpose, lang)
            chunk_content.append(block)
            full_be_content.append(block)
        text = "".join(chunk_content)
        be_chunk_contents[chunk_filename] = text
        (BE_DIR / chunk_filename).write_text(text, encoding="utf-8")
        print(f"  [BE Chunk] Wrote {chunk_filename} ({len(file_list)} files)")

    full_be_str = "".join(full_be_content)
    (BE_DIR / "FULL_BACKEND_CODEBASE.txt").write_text(full_be_str, encoding="utf-8")
    (EXPORT_DIR / "FULL_BACKEND_CODEBASE.txt").write_text(full_be_str, encoding="utf-8")
    print(f"  [BE Bundle] Wrote FULL_BACKEND_CODEBASE.txt ({len(full_be_content)} files total)")

    # Combined Master Bundle (BE + FE Together)
    combined_project_header = (
        "=" * 80 + "\n"
        "BUDDY CONVERSATIONAL VOICE AI & GENERATIVE UI — COMPLETE PROJECT EXPORT\n"
        "INCLUDES: BACKEND (LiveKit Agent, Engines, Pipeline) & FRONTEND (React 19 Canvas UI)\n"
        "=" * 80 + "\n\n"
    )
    combined_project_content = combined_project_header + full_be_str + full_fe_str
    (EXPORT_DIR / "FULL_PROJECT_CODEBASE.txt").write_text(combined_project_content, encoding="utf-8")
    print(f"  [Combined Project Bundle] Wrote FULL_PROJECT_CODEBASE.txt ({len(full_be_content) + len(full_fe_content)} files total)")

    # Consolidated Single 'chunks/' Directory with all 6 chunks sequentially ordered
    all_chunks_map = {
        "01_BE_CORE_PIPELINE.txt": be_chunk_contents["01_BE_CORE_PIPELINE.txt"],
        "02_BE_ENGINES.txt": be_chunk_contents["02_BE_ENGINES.txt"],
        "03_BE_INGESTION_AND_DATA.txt": be_chunk_contents["03_BE_INGESTION_AND_DATA.txt"],
        "04_FE_CORE_AND_CONFIG.txt": fe_chunk_contents["01_FE_CORE_AND_CONFIG.txt"],
        "05_FE_STATE_AND_SERVICES.txt": fe_chunk_contents["02_FE_STATE_AND_SERVICES.txt"],
        "06_FE_CONVERSATIONAL_STAGE.txt": fe_chunk_contents["03_FE_CONVERSATIONAL_STAGE.txt"],
    }
    for chunk_name, chunk_text in all_chunks_map.items():
        (CHUNKS_DIR / chunk_name).write_text(chunk_text, encoding="utf-8")
        print(f"  [Consolidated Chunk] Wrote chunks/{chunk_name}")

    print(f"\nExport complete! Files written to:\n  {EXPORT_DIR}")

if __name__ == "__main__":
    generate_exports()
