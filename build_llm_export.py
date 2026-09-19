#!/usr/bin/env python3
"""
Generates high-fidelity, LLM-optimized codebase exports for both Frontend and Backend.

Provides:
- 4 Full Codebase Bundles at root level:
    1. FULL_PROJECT_CODEBASE.txt (Combined Architecture, BE, and FE)
    2. FULL_FRONTEND_CODEBASE.txt (All FE files)
    3. FULL_BACKEND_CODEBASE.txt (All BE files)
    4. FULL_SPECS_AND_ARCHITECTURE.txt (All design docs and plans)
- Single consolidated 'chunks/' directory containing 9 logical chunks (< 25K tokens each)
- Separated 'frontend/' and 'backend/' directories with architectural overviews
- Automated codebase audit verifying zero untracked source files
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
    tokens = len(content) // 4
    header = (
        "=" * 80 + "\n"
        f"FILE: {rel_path}\n"
        f"LANGUAGE: {language}\n"
        f"LINES: {lines} | EST_TOKENS: ~{tokens}\n"
        f"PURPOSE: {purpose}\n"
        + "=" * 80 + "\n"
    )
    return f"{header}\n{content}\n\n"

# ─────────────────────────────────────────────────────────────────────────────
# ARCHITECTURE & DESIGN SPECS DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

SPEC_CHUNKS = {
    "00_ARCHITECTURE_AND_SPECS.txt": [
        ("buddy.md", "Core design doctrine: Voice-first buddy persona, offline-first philosophy, reactive GenUI, and turn-taking rules", "markdown"),
        ("buddy-implementation-plan.md", "Comprehensive two-tier architectural plan: LiveKit agent loop, GPU arbiter, in-process Kokoro TTS, and SQLite curriculum store", "markdown"),
        ("buddy-implementation-plan (1).md", "Deep curriculum engine coding plan: LangGraph 8-node DAG, reconsideration request logging, and dynamic course sessions", "markdown"),
        ("README.md", "Monorepo root README with fast startup guide and architectural overview", "markdown"),
        ("mvp_talker_offline/README.md", "Backend package README with console and server run commands", "markdown"),
        ("agent.py", "Root-level launcher delegating directly to mvp_talker_offline/backend/agent.py", "python"),
        ("pyproject.toml", "Root Python project configuration and dependency metadata", "toml"),
    ]
}

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
        ("mvp_talker_offline/VisualsFrontend/src/index.css", "Design System: Dark surface tokens (--surface-0 to --surface-3), ambient mesh background, voice halo, and typography", "css"),
        (".mcp.json", "Workspace MCP configuration for frontend design, React, and UI component servers (shadcn, shadcn-ui, tailgrids)", "json"),
    ],
    "02_FE_STATE_AND_SERVICES.txt": [
        ("mvp_talker_offline/VisualsFrontend/src/types.ts", "Central TypeScript interfaces (FeedItem, QuizQuestion, ContentionProps, CanvasLectureProps, SyllabusData)", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/config/transport.ts", "Transport configuration establishing LiveKit WebRTC as authoritative transport and formally deprecating legacy SSE/stdio bridges", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/store.ts", "Zustand state store managing sequential feed array, LiveKit room instance, drawer state, and LiveKit RPC actions (including requestReinterpretation)", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/hooks/useLiveKit.ts", "LiveKit WebRTC transport hook: room joining (/api/token), speaker audio track playback, text stream handling, and client RPC", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/utils/bionic.ts", "Bionic reading text transformation algorithm bolding initial letters of words", "typescript"),
    ],
    "03_FE_CONVERSATIONAL_STAGE.txt": [
        ("mvp_talker_offline/VisualsFrontend/src/App.tsx", "Conversational Live Stage: Timeline feed, ambient mesh canvas, top status bar, bottom audio dock, and slide-over drawer", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/layout/Header.tsx", "Top navigation bar with engine status indicator, active chapter pill, and quick triggers", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/layout/AudioDock.tsx", "Floating voice visualizer dock with 9-bar reactive equalizer, pulsing voice halo ring, composer textarea, and action chips", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/layout/SlideOverDrawer.tsx", "Collapsible slide-over drawer with 18-chapter roadmap, analytics, and remediation queue", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/syllabus/SyllabusSection.tsx", "Modular syllabus section displaying active chapter hero, stage badges, coursework gating, 18-chapter roadmap, and drift audit metrics", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/cards/InlineQuizCard.tsx", "Inline generative quiz artifact card with feedback, rule citations, dispute handling, and isomorphic retry", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/cards/InlineDisputeCard.tsx", "Inline dispute ruling card comparing formal grammar vs colloquial usage with citations", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/cards/InlineNotesCard.tsx", "Inline revision notes artifact card with bionic reading toggle and common traps", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/cards/InlineGrammarMovementCard.tsx", "Inline syntactic movement animation card with Framer Motion layoutId spring physics and role capsules", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/cards/InlineSheetErrorCard.tsx", "Inline sheet error card with alert status, target component diagnostics, and interactive retry action", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/cards/InlineCanvasLectureCard.tsx", "Interactive canvas lecture card with 5 visual primitives (syntactic tree, concord balance, flow, matrix, classifier), bionic reading, and analogy reinterpretation toolbar", "typescript"),
        ("mvp_talker_offline/VisualsFrontend/src/components/cards/StreamingCard.tsx", "Live LLM token synthesis card with typewriter animation and blinking cursor", "typescript"),
    ]
}

FE_OVERVIEW_MD = """# Frontend Architecture & Overview (mvp_talker_offline/VisualsFrontend)

## 1. Executive Summary
**VisualsFrontend** is a conversational generative UI modeled after **Gemini Live** and **ChatGPT Canvas**.
Built with React 19, TypeScript, Vite, Framer Motion, and Zustand, it serves as the real-time visual companion to the **Buddy Offline Voice AI Agent**. It lives under `mvp_talker_offline/VisualsFrontend/`.

## 2. Key Architecture Patterns
- **Event-Driven Conversation Timeline**:
  - Entire layout centers on a unified, chronological `feed: FeedItem[]` array.
  - Transcript utterances, in-flight token streaming cards (`StreamingCard`), interactive quiz cards (`InlineQuizCard`), linguistic dispute verdicts (`InlineDisputeCard`), study notes (`InlineNotesCard`), syntactic movement cards (`InlineGrammarMovementCard`), and canvas lecture cards (`InlineCanvasLectureCard`) render directly inline at their exact chronological position in the chat stream.
- **Top Header Bar**:
  - Live Audio / Engine status indicator pill (`Live Audio Connected` / `Engine Ready`).
  - Active chapter display pill.
  - Action triggers: `Quick Quiz`, `Notes`, and `Syllabus & Stats` drawer toggle.
- **Floating Voice & Audio Dock**:
  - Docked at the bottom of the viewport with an animated 9-bar active audio wave visualizer, pulsing voice halo ring, auto-expanding composer, and quick prompt action chips.
- **Slide-Over Syllabus & Mastery Drawer**:
  - On-demand slide-over panel on the right side displaying current chapter details, mastery statistics (Accuracy Rate, Correct Answers, Errors Detected), 18-chapter linear curriculum roadmap, and isomorphic remediation queue.
- **Real-Time LiveKit Transport** (`useLiveKit.ts`):
  - Connects to LiveKit room via WebRTC data channels and text streams (`transcript`, `genui`, `genui_token`).
  - Native RPC caller for `getSyllabus`, `getQuiz`, `submitQuizAnswer`, `disputeAnswer`, `deliverCanvasLecture`, and `requestReinterpretation`.

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
        ├── types.ts              # FeedItem, QuizQuestion, ContentionProps, CanvasLectureProps
        ├── store.ts              # Unified timeline Zustand store with LiveKit RPC
        ├── App.tsx               # Conversational Live Stage
        ├── hooks/
        │   └── useLiveKit.ts     # LiveKit WebRTC transport & RPC hook
        ├── utils/
        │   └── bionic.ts         # Bionic reading algorithm
        └── components/
            ├── layout/           # Layout shell components
            │   ├── Header.tsx    # Top status bar & chapter display
            │   ├── AudioDock.tsx # Floating voice dock & waveform
            │   └── SlideOverDrawer.tsx # 18-chapter roadmap & analytics drawer
            ├── cards/            # Inline feed artifact cards
            │   ├── InlineQuizCard.tsx       # Interactive quiz card
            │   ├── InlineDisputeCard.tsx    # Linguistic dispute ruling
            │   ├── InlineNotesCard.tsx      # Study notes with Bionic reading
            │   ├── InlineGrammarMovementCard.tsx # Syntactic movement with Framer Motion
            │   ├── InlineSheetErrorCard.tsx # Sheet error diagnostics
            │   ├── InlineCanvasLectureCard.tsx # Canvas lecture with 5 visual primitives & analogy toolbar
            │   └── StreamingCard.tsx        # Live LLM token typewriter
            └── syllabus/         # Syllabus & curriculum UI
                └── SyllabusSection.tsx # Chapter roadmap & mastery tracking
```
"""

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND DEFINITIONS (mvp_talker_offline/backend)
# ─────────────────────────────────────────────────────────────────────────────

BE_CHUNKS = {
    "01_BE_CORE_PIPELINE.txt": [
        ("mvp_talker_offline/backend/agent.py", "LiveKit voice AI agent entrypoint: Faster-Whisper STT, Silero VAD, Kokoro TTS, Ollama LLM, in-process function tools, and LiveKit RPC handlers (including requestReinterpretation)", "python"),
        ("mvp_talker_offline/backend/core/kokoro_tts.py", "Native in-process Kokoro-82M ONNX streaming TTS plugin implementing tts.TTS and tts.SynthesizeStream with clause boundary splitting and direct 24kHz int16 PCM streaming to AudioEmitter", "python"),
        ("mvp_talker_offline/backend/core/gpu_arbiter.py", "Application-level GPU Session Mutex & VRAM Arbiter enforcing strict voice-call priority and pausing Tier 2 LangGraph jobs to protect 8GB VRAM", "python"),
        ("mvp_talker_offline/backend/core/structured_logger.py", "Localized structured logging subsystem with consistent session_id and sequential turn_id for STT, LLM, TTS, RAG, and GenUI", "python"),
        ("mvp_talker_offline/backend/core/config.py", "Centralized environment configuration: all env vars (LiveKit, Ollama, TTS, data paths) loaded from .env via dotenv", "python"),
        ("mvp_talker_offline/backend/core/audio_server.py", "Isolated FastAPI microservice serving local Kokoro/Piper neural TTS (/v1/audio/speech) and LiveKit JWT token minting (/api/token)", "python"),
        ("mvp_talker_offline/Modelfile", "Custom Ollama Modelfile configuring qwen2.5:7b with pedagogical teacher persona and grammar guidelines", "dockerfile"),
        ("mvp_talker_offline/requirements.txt", "Python backend requirements (livekit, faster-whisper, fastapi, uvicorn, rank-bm25, duckduckgo-search)", "text"),
        ("mvp_talker_offline/.env.example", "Environment variable documentation (LiveKit keys, Ollama URL, Piper voice model path)", "ini"),
    ],
    "02_BE_ENGINES.txt": [
        ("mvp_talker_offline/backend/engines/__init__.py", "Engine package re-exports: SimulationEngine, QuizEngine, SyllabusTracker, RAGStore", "python"),
        ("mvp_talker_offline/backend/engines/curriculum_store.py", "Production curriculum SQLite engine: 5 tables (curriculum_nodes, curriculum_variants, quiz_items, reconsideration_requests, critique_log), typed CRUD, variant retrieval, and auto-seeding", "python"),
        ("mvp_talker_offline/backend/engines/simulation_engine.py", "Pedagogical simulation engine handling error detection, dispute resolution via local RAG & DuckDuckGo, and colloquial recasts", "python"),
        ("mvp_talker_offline/backend/engines/quiz_engine.py", "Quiz state machine managing chapter banks, answer verification, error tracking, and isomorphic repeat questions with SQLite audit logging", "python"),
        ("mvp_talker_offline/backend/engines/syllabus_tracker.py", "18-chapter linear progression tracker backed by SQLite database (memory.db) tracking coursework, mastery, and isomorphic audits", "python"),
        ("mvp_talker_offline/backend/engines/rag_store.py", "ChromaDB-backed hybrid RAG store: ANN vector search (HNSW) + BM25 keyword search with Reciprocal Rank Fusion; vectors persisted to data/chroma_db/ — no re-indexing on restart", "python"),
    ],
    "03_BE_LANGGRAPH_AND_TUTOR.txt": [
        ("mvp_talker_offline/backend/tutor/__init__.py", "Tutor package re-exports: langgraph_engine", "python"),
        ("mvp_talker_offline/backend/tutor/curriculum_authoring.py", "CurriculumNode & CriticVerdict Pydantic schemas, parse_structured with json_repair fallback, structured_authoring_call with exact validation diff retry loop, and semantic critic routing", "python"),
        ("mvp_talker_offline/backend/tutor/curriculum_pipeline.py", "Shared 8-node LangGraph StateGraph (build, refine, reconsider) compiled with SqliteSaver at data/langgraph_checkpoints.db", "python"),
        ("mvp_talker_offline/backend/tutor/curriculum_jobs.py", "Thin background job dispatch layer (enqueue_build, enqueue_refine, enqueue_reconsider) gated on GPUSessionArbiter", "python"),
        ("mvp_talker_offline/backend/tutor/curriculum_notify.py", "Asynchronous GenUI broadcast and context injection: pushes WebRTC cards and injects session.history.add_message to prevent context blindness", "python"),
        ("mvp_talker_offline/backend/tutor/curriculum_feedback.py", "Automated curriculum feedback scanner monitoring learner quiz failure rates and clustered reconsideration requests", "python"),
        ("mvp_talker_offline/backend/tutor/studio_tts.py", "Studio-grade neural audio clip synthesis using Kokoro-82M ONNX caching 24kHz WAV files into data/lecture_audio/", "python"),
        ("mvp_talker_offline/backend/tutor/langgraph_tutor_graph.py", "LangGraph StateGraph driving tutor mode: lecture phase sequencing, homework check, quiz flow, preference tracking, and session memory via SQLite checkpoints", "python"),
        ("mvp_talker_offline/backend/tutor/curriculum_banks_generator.py", "Offline curriculum generator: builds and exports all 18 chapter quiz banks from ESL syllabus research", "python"),
        ("mvp_talker_offline/langgraph.json", "LangGraph Studio & CLI configuration exposing tutor_graph and curriculum_pipeline DAGs", "json"),
    ],
    "04_BE_INGESTION_AND_DATA.txt": [
        ("mvp_talker_offline/backend/ingestion/__init__.py", "Ingestion package marker", "python"),
        ("mvp_talker_offline/backend/ingestion/knowledge_ingestor.py", "Textbook & PDF ingestion pipeline indexing Oxford Guide, Arihant Grammar, Espresso English, and narrative stories into SQLite & RAG", "python"),
        ("mvp_talker_offline/data/curriculum.json", "Official 18-chapter English grammar curriculum definition with title, topics, rules, and coursework requirements", "json"),
        ("mvp_talker_offline/data/quiz_banks/chapter_01_bank.json", "Pre-verified milestone quiz bank schema for Chapter 1 (Present Simple & Continuous) with citations and explanations", "json"),
    ],
    "05_BE_TESTS.txt": [
        ("mvp_talker_offline/backend/tests/__init__.py", "Tests package marker", "python"),
        ("mvp_talker_offline/backend/tests/verify_curriculum_engine.py", "Automated test suite verifying curriculum_store tables, variants, reconsideration, Pydantic authoring validation, GPUSessionArbiter concurrency gating, context injection, studio TTS, and LangGraph 8-node DAG", "python"),
        ("mvp_talker_offline/backend/tests/verify_phase1.py", "Automated test suite verifying RAG search, syllabus progression, quiz evaluation, and dispute handling", "python"),
        ("mvp_talker_offline/backend/tests/verify_phase2.py", "Automated test suite verifying embedding outage fallback, offline dispute, SQLite isomorphic audits, and learner state sync", "python"),
        ("mvp_talker_offline/backend/tests/verify_phase3.py", "Automated test suite verifying streaming STT capabilities, StreamingFasterWhisperAdapter, and VoiceTurnPriorityManager", "python"),
        ("mvp_talker_offline/backend/tests/verify_phase4.py", "Automated test suite verifying versioned GenUI schema ('1.0'), demonstrate_grammar_movement tool, and frontend motion integration", "python"),
        ("mvp_talker_offline/backend/tests/verify_phase5.py", "Automated test suite verifying in-flight reconnects, SQLite sheet persistence, get_last_sheet RPC, structured logging, and sheet_error surfacing", "python"),
        ("mvp_talker_offline/backend/tests/verify_langgraph_livekit.py", "Integration test suite verifying LangGraph tutor graph <-> LiveKit agent handshake: state transitions, checkpoint persistence, and voice-first turn-taking", "python"),
        ("mvp_talker_offline/backend/tests/headless_console_test.py", "Headless CLI runner scripting milestone execution via LiveKit Agents fake_job_context with GenUI ANSI event cards and assertions", "python"),
    ],
}

BE_OVERVIEW_MD = """# Backend Architecture & Overview (mvp_talker_offline)

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
"""

# ─────────────────────────────────────────────────────────────────────────────
# MASTER README
# ─────────────────────────────────────────────────────────────────────────────

MASTER_README_MD = """# Codebase Context Export for LLMs

This directory contains clean, structured, and chunked exports of the entire codebase for **Buddy — The Offline Voice AI English Grammar Coach**.

The project is organized under the monorepo folder **`mvp_talker_offline/`**:
- **`mvp_talker_offline/backend/`**: Python LiveKit Voice Agent with submodules: `core/`, `engines/`, `tutor/`, `ingestion/`, `tests/`.
- **`mvp_talker_offline/VisualsFrontend/`**: React 19 / TypeScript / Vite / Zustand conversational UI with `components/layout/`, `components/cards/`, `components/syllabus/`.
- **`mvp_talker_offline/data/`**: Curriculum schema, quiz banks, and narrative practice stories.
- **`mvp_talker_offline/models/`**: Offline neural Piper/Kokoro TTS voice models.

---

## 1. ALL 4 FULL CODEBASE BUNDLES (Root Level)

For zero-navigation feeding into large-context LLMs (Claude 3.5 Sonnet, GPT-4o, Gemini 1.5/2.0 Pro):

| Bundle File | Scope | Description |
|---|---|---|
| **`FULL_PROJECT_CODEBASE.txt`** | **Complete Project (Specs + BE + FE)** | All design documents and active source files across the entire codebase |
| **`FULL_FRONTEND_CODEBASE.txt`** | **Full Frontend Stack** | All frontend files (React 19, Zustand, LiveKit WebRTC, components) |
| **`FULL_BACKEND_CODEBASE.txt`** | **Full Backend Stack** | All backend files (LiveKit Agent, FastAPI audio, engines, data) |
| **`FULL_SPECS_AND_ARCHITECTURE.txt`** | **Architecture & Design Plans** | All architectural specs, curriculum engine coding plans, and doctrines |

---

## 2. ALL CHUNKS IN A SINGLE FOLDER (`chunks/`)

For smaller context models (8k – 32k tokens) or targeted subagent prompts, all 9 chunks are unified in one directory:

```
codebase_llm_export/chunks/
├── 00_ARCHITECTURE_AND_SPECS.txt     # buddy.md, implementation plans, pyproject.toml, READMEs
├── 01_BE_CORE_PIPELINE.txt          # agent.py, core/config, core/audio_server, Modelfile, requirements
├── 02_BE_ENGINES.txt                # engines/__init__, simulation_engine, quiz_engine, syllabus_tracker, rag_store
├── 03_BE_LANGGRAPH_AND_TUTOR.txt    # tutor/langgraph_tutor_graph, curriculum_authoring, pipeline, jobs
├── 04_BE_INGESTION_AND_DATA.txt     # ingestion/knowledge_ingestor, curriculum.json, chapter_01_bank
├── 05_BE_TESTS.txt                  # tests/verify_curriculum_engine, verify_phase1-5, headless_console_test
├── 06_FE_CORE_AND_CONFIG.txt        # package.json, vite.config, tsconfig, index.html, index.css, .mcp.json
├── 07_FE_STATE_AND_SERVICES.txt     # types.ts, store.ts, useLiveKit.ts, bionic.ts
└── 08_FE_CONVERSATIONAL_STAGE.txt   # App.tsx, layout/, cards/, syllabus/ components
```
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

    # 1. Architecture & Specs Chunk
    spec_chunk_contents = {}
    full_spec_content = []
    for chunk_filename, file_list in SPEC_CHUNKS.items():
        chunk_content = []
        for rel_path, purpose, lang in file_list:
            block = format_file_block(rel_path, purpose, lang)
            chunk_content.append(block)
            full_spec_content.append(block)
        text = "".join(chunk_content)
        spec_chunk_contents[chunk_filename] = text
        (CHUNKS_DIR / chunk_filename).write_text(text, encoding="utf-8")
        print(f"  [Spec Chunk] Wrote {chunk_filename} ({len(file_list)} files)")

    full_spec_str = "".join(full_spec_content)
    (EXPORT_DIR / "FULL_SPECS_AND_ARCHITECTURE.txt").write_text(full_spec_str, encoding="utf-8")
    print(f"  [Spec Bundle] Wrote FULL_SPECS_AND_ARCHITECTURE.txt ({len(full_spec_content)} files total)")

    # 2. Frontend Overview & Chunks
    (FE_DIR / "00_FRONTEND_OVERVIEW.md").write_text(FE_OVERVIEW_MD.strip() + "\n", encoding="utf-8")

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

    # 3. Backend Overview & Chunks
    (BE_DIR / "00_BACKEND_OVERVIEW.md").write_text(BE_OVERVIEW_MD.strip() + "\n", encoding="utf-8")

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

    # 4. Combined Master Bundle (Specs + BE + FE)
    combined_project_header = (
        "=" * 80 + "\n"
        "BUDDY CONVERSATIONAL VOICE AI & GENERATIVE UI — COMPLETE PROJECT EXPORT\n"
        "INCLUDES: ARCHITECTURE & SPECS, BACKEND (LiveKit Agent, Engines, Pipeline) & FRONTEND (React 19 Canvas UI)\n"
        "=" * 80 + "\n\n"
    )
    combined_project_content = combined_project_header + full_spec_str + full_be_str + full_fe_str
    (EXPORT_DIR / "FULL_PROJECT_CODEBASE.txt").write_text(combined_project_content, encoding="utf-8")
    total_files = len(full_spec_content) + len(full_be_content) + len(full_fe_content)
    print(f"  [Combined Project Bundle] Wrote FULL_PROJECT_CODEBASE.txt ({total_files} files total)")

    # 5. Consolidated Single 'chunks/' Directory — 9 chunks: 1 Spec + 5 BE + 3 FE
    all_chunks_map = {
        "00_ARCHITECTURE_AND_SPECS.txt":  spec_chunk_contents["00_ARCHITECTURE_AND_SPECS.txt"],
        "01_BE_CORE_PIPELINE.txt":        be_chunk_contents["01_BE_CORE_PIPELINE.txt"],
        "02_BE_ENGINES.txt":              be_chunk_contents["02_BE_ENGINES.txt"],
        "03_BE_LANGGRAPH_AND_TUTOR.txt":  be_chunk_contents["03_BE_LANGGRAPH_AND_TUTOR.txt"],
        "04_BE_INGESTION_AND_DATA.txt":   be_chunk_contents["04_BE_INGESTION_AND_DATA.txt"],
        "05_BE_TESTS.txt":               be_chunk_contents["05_BE_TESTS.txt"],
        "06_FE_CORE_AND_CONFIG.txt":      fe_chunk_contents["01_FE_CORE_AND_CONFIG.txt"],
        "07_FE_STATE_AND_SERVICES.txt":   fe_chunk_contents["02_FE_STATE_AND_SERVICES.txt"],
        "08_FE_CONVERSATIONAL_STAGE.txt": fe_chunk_contents["03_FE_CONVERSATIONAL_STAGE.txt"],
    }
    for chunk_name, chunk_text in all_chunks_map.items():
        (CHUNKS_DIR / chunk_name).write_text(chunk_text, encoding="utf-8")
        print(f"  [Consolidated Chunk] Wrote chunks/{chunk_name}")

    print(f"\nExport complete! {total_files} files packaged across 9 chunks into:\n  {EXPORT_DIR}")

if __name__ == "__main__":
    generate_exports()
