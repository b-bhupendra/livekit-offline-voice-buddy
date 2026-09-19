# Frontend Architecture & Overview (mvp_talker_offline/VisualsFrontend)

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
