# Frontend Architecture & Overview (VisualsFrontend)

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
- **Real-Time LiveKit Transport** (`useLiveKit.ts`):
  - Connects to LiveKit room via WebRTC data channels and text streams (`transcript`, `genui`, `genui_token`).
  - Native RPC caller for `getSyllabus`, `getQuiz`, `submitQuizAnswer`, `disputeAnswer`, and `advanceChapter`.

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
        └── StreamingCard.tsx # Live LLM token synthesis typewriter
```

## 4. Chunk Guide for LLMs
- **`01_FE_CORE_AND_CONFIG.txt`**: Core package config, HTML entrypoint, main.tsx, and design system CSS.
- **`02_FE_STATE_AND_SERVICES.txt`**: TypeScript interfaces, Zustand store, and LiveKit WebRTC hook.
- **`03_FE_CONVERSATIONAL_STAGE.txt`**: Conversational Live Stage component (`App.tsx`), components (`Header`, `AudioDock`, `SlideOverDrawer`, `InlineQuizCard`, `InlineDisputeCard`, `InlineNotesCard`, `StreamingCard`).
- **`FULL_FRONTEND_CODEBASE.txt`**: Complete bundle of all frontend source files in one continuous document.
