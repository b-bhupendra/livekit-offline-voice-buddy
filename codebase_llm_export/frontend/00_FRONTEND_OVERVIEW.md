# Frontend Architecture & Overview (mvp_talker_offline/VisualsFrontend)

## 1. Executive Summary
**VisualsFrontend** is a conversational generative UI modeled after **Gemini Live** and **ChatGPT Canvas**.
Built with React 19, TypeScript, Vite, Framer Motion, and Zustand, it serves as the real-time visual companion to the **Buddy Offline Voice AI Agent**. It lives under `mvp_talker_offline/VisualsFrontend/`.

## 2. Key Architecture Patterns
- **Event-Driven Conversation Timeline**:
  - Entire layout centers on a unified, chronological `feed: FeedItem[]` array.
  - Transcript utterances, in-flight token streaming cards (`StreamingCard`), interactive quiz cards (`InlineQuizCard`), linguistic dispute verdicts (`InlineDisputeCard`), study notes (`InlineNotesCard`), syntactic movement cards (`InlineGrammarMovementCard`), and canvas lecture cards (`InlineCanvasLectureCard`) render directly inline at their exact chronological position in the chat stream.
- **Design Token System (`index.css`)**:
  - Standardized dark-mode surface elevation tokens (`--surface-0` through `--surface-3`).
  - Specular hairline borders (`var(--border-specular)` / `rgba(255, 255, 255, 0.1)`).
  - Ambient radial mesh background (`.ambient-mesh-canvas`) and pulsing voice halo rings (`.voice-halo`).
- **Interactive Generative Primitives (`InlineCanvasLectureCard.tsx`)**:
  - 5 verified primitives: Syntactic Tree, Concord Balance, Cadence Flow, Workplace Matrix, Particle Classifier.
  - Direct Analogy Reinterpretation Toolbar (`⚡ Software Analogy`, `💼 Workplace Style`, `🌱 Everyday Intuition`).
- **Floating Voice & Audio Dock (`AudioDock.tsx`)**:
  - 9-bar reactive equalizer with cyan-to-violet gradient heights and glowing mic halo.
- **Slide-Over Syllabus & Mastery Drawer (`SlideOverDrawer.tsx`)**:
  - 18-chapter linear curriculum roadmap, mastery statistics, and isomorphic remediation queue.
- **Real-Time LiveKit Transport (`useLiveKit.ts`)**:
  - Native RPC caller for `getSyllabus`, `getQuiz`, `submitQuizAnswer`, `disputeAnswer`, `deliverCanvasLecture`, and `requestReinterpretation`.
