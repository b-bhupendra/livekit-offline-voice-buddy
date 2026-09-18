# Codebase Context Export for LLMs

This directory contains clean, structured, and chunked exports of the entire codebase for **Buddy — The Offline Voice AI English Grammar Coach**.

The project is organized under the monorepo folder **`mvp_talker_offline/`**:
- **`mvp_talker_offline/backend/`**: Python LiveKit Voice Agent, pedagogical engines, and audio microservice.
- **`mvp_talker_offline/VisualsFrontend/`**: React 19 / TypeScript / Vite / Zustand conversational UI.
- **`mvp_talker_offline/data/`**: Curriculum schema, quiz banks, and narrative practice stories.
- **`mvp_talker_offline/models/`**: Offline neural Piper TTS voice model.

## Available Export Modes

1. **Combined Full Project Bundle (Frontend + Backend Together)**:
   - **`FULL_PROJECT_CODEBASE.txt`**: The entire codebase (Backend + Frontend) concatenated in a single file for large-context models (Claude 3.5 Sonnet, GPT-4o, Gemini 1.5/2.0 Pro).

2. **Separated Full Stacks**:
   - **`frontend/FULL_FRONTEND_CODEBASE.txt`**: All frontend files bundled together.
   - **`backend/FULL_BACKEND_CODEBASE.txt`**: All backend files bundled together.

3. **Separated Logical Chunks (< 20K tokens each)**:
   - For smaller context windows or targeted tasks (editing UI, tuning prompts, adjusting STT/TTS).

## Structure
```
codebase_llm_export/
├── README.md                      # This guide
├── FULL_PROJECT_CODEBASE.txt      # Combined Backend & Frontend in a single master bundle
├── frontend/                      # VisualsFrontend (React 19, TypeScript, Zustand, Vite)
│   ├── 00_FRONTEND_OVERVIEW.md    # Architecture overview, component tree, state diagram
│   ├── 01_FE_CORE_AND_CONFIG.txt  # package.json, vite.config.ts, tsconfig.json, index.html, main.tsx, index.css
│   ├── 02_FE_STATE_AND_SERVICES.txt # types.ts, store.ts, useLiveKit.ts, bionic.ts
│   ├── 03_FE_CONVERSATIONAL_STAGE.txt # App.tsx, Header, AudioDock, Drawer, and inline artifact cards
│   └── FULL_FRONTEND_CODEBASE.txt # Single bundle of all frontend source files
└── backend/                       # mvp_talker_offline (Python, LiveKit, FastAPI, SQLite)
    ├── 00_BACKEND_OVERVIEW.md     # Architecture overview, voice pipeline, and in-process tools
    ├── 01_BE_CORE_PIPELINE.txt    # agent.py, audio_server.py, Modelfile, requirements
    ├── 02_BE_ENGINES.txt          # simulation, quiz, syllabus, rag_store
    ├── 03_BE_INGESTION_AND_DATA.txt # knowledge_ingestor.py, curriculum.json, sample quiz banks
    └── FULL_BACKEND_CODEBASE.txt  # Single bundle of all backend source files
```

## How to Feed this to an LLM
1. **For End-to-End Architectural Tasks**:
   - Load **`FULL_PROJECT_CODEBASE.txt`**.
2. **For Frontend-Specific Tasks**:
   - Load **`frontend/FULL_FRONTEND_CODEBASE.txt`** (or specific chunks `01` to `03`).
3. **For Backend-Specific Tasks**:
   - Load **`backend/FULL_BACKEND_CODEBASE.txt`** (or specific chunks `01` to `03`).
