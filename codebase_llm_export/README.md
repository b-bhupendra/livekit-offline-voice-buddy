# Codebase Context Export for LLMs

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
