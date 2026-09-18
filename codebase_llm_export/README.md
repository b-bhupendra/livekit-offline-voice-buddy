# Codebase Context Export for LLMs

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
