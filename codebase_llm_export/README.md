# Codebase Context Export for LLMs

This directory contains clean, structured, and chunked exports of the entire codebase for **Buddy — The Offline Voice AI English Grammar Coach**.

## Structure
```
codebase_llm_export/
├── README.md                      # This guide
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
