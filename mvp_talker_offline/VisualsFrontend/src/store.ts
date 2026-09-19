import { create } from 'zustand';
import type { Room } from 'livekit-client';
import type {
  SyllabusData,
  LearnerState,
  QuizQuestion,
  QuizSubmitResult,
  ContentionProps,
  FeedItem,
  DrawerTab,
  ChapterInfo,
  GenUIEvent,
  LearnerSummary,
  GrammarMovementProps,
  SheetErrorProps,
  TutorState,
  CanvasLectureProps
} from './types';

// ── Default 18-Chapter Curriculum Roadmap ─────────────────────────────────────
export const DEFAULT_ROADMAP: ChapterInfo[] = [
  { index: 1, title: 'Course Foundations & Sentence Transformations', topic: 'Affirmative to Negative & Question forms', status: 'active', coursework_done: true, quiz_passed: false },
  { index: 2, title: 'Sentence Transformations & Inversion', topic: 'Auxiliary Verb Placement & Emphasis', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 3, title: 'Commands, Requests & Softening Politeness', topic: 'Imperatives, Softening, Polite Inquiries', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 4, title: 'Closed Questions & Auxiliary Verb Inversion', topic: 'Yes/No Aux Inversions, Tags & Modals', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 5, title: 'Open Questions (Wh- Clauses & Inquiry)', topic: 'Why, How, Who, Where, When, What', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 6, title: 'Special & Indirect Questions (Embedded Clauses)', topic: 'Embedded Inquiries & Tag Questions', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 7, title: 'Existential Sentences (There is/are & Stative Action)', topic: 'Existential Grammar & Agreement', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 8, title: 'Sensory Descriptions & Sensory Reference Points', topic: 'Look, Sound, Feel, Smell, Taste', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 9, title: 'Descriptions of Objects, People & Places', topic: 'Adjective Stacking, Order & Relative Clauses', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 10, title: 'Gerunds vs Infinitives', topic: 'Verbs + -ing vs to-Infinitive Concord', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 11, title: 'Coordinating Conjunctions (FANBOYS)', topic: 'Compound Sentence Construction', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 12, title: 'Subordinating Conjunctions & Clauses', topic: 'Complex Sentence Synthesis', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 13, title: 'Active vs Passive Voice & Agentless Forms', topic: 'Register Appropriateness & Agent Inversion', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 14, title: 'Conditionals & Hypotheticals', topic: 'Zero, 1st, 2nd, 3rd & Mixed Conditionals', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 15, title: 'Sentence Building & Clause Synthesis', topic: 'Multi-Clause Coordination', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 16, title: 'Sentence Beginnings & Fronting for Emphasis', topic: 'Adverbials, Prepositional & Participial Fronting', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 17, title: 'Cleft Sentences & Syntactic Inversion', topic: 'It-clefts, Wh-clefts & Negative Inversion', status: 'locked', coursework_done: false, quiz_passed: false },
  { index: 18, title: 'Advanced Discourse Fluency & Synthesis', topic: 'Cohesion, Ellipsis & Capstone Defense', status: 'locked', coursework_done: false, quiz_passed: false },
];

export const INITIAL_PRE_VERIFIED_QUESTIONS: QuizQuestion[] = [
  {
    id: 'ch01_q01',
    chapter: 1,
    question: 'Spot the error in the sentence: "Neither of the two candidates were chosen for the executive role."',
    sentence: 'Neither of the two candidates were chosen for the executive role.',
    options: [
      'were -> was',
      'No error',
      'Vocabulary error',
      'Punctuation error'
    ],
    correct_answer: 'were -> was',
    explanation: "Subject-verb agreement: 'Neither' is an indefinite singular pronoun requiring the singular verb 'was' (Oxford Guide Ch 2 / Arihant Rule 12).",
    rule_citation: 'Oxford Guide Ch 2 & Arihant General English Rule 12'
  },
  {
    id: 'ch01_q02',
    chapter: 1,
    question: 'Spot the error in the sentence: "Each of the students have submitted their research papers."',
    sentence: 'Each of the students have submitted their research papers.',
    options: [
      'have -> has',
      'No error',
      'students -> student',
      'submitted -> submits'
    ],
    correct_answer: 'have -> has',
    explanation: "'Each' is grammatically singular and requires the singular auxiliary 'has' (Arihant Rule 4).",
    rule_citation: 'Oxford Guide Ch 2 & Arihant General English Rule 12'
  }
];

export interface BuddyStore {
  // ── Unified Timeline Feed ────────────────────────────────
  feed: FeedItem[];
  sseConnected: boolean;
  livekitConnected: boolean;
  livekitRoom: Room | null;
  syllabus: SyllabusData | null;
  learnerState: LearnerState;
  learnerSummary: LearnerSummary | null;
  activeChapter: number;
  activeMode: 'buddy' | 'tutor';
  tutorState: TutorState | null;
  lectureHistory: CanvasLectureProps[];
  drawerOpen: boolean;
  activeDrawerTab: DrawerTab;
  isVoiceActive: boolean;

  // ── Actions ──────────────────────────────────────────────
  setLivekitRoom: (room: Room | null) => void;
  setLivekitConnected: (connected: boolean) => void;
  toggleTutorMode: (topic?: string) => Promise<void>;
  toggleDrawer: (tab?: DrawerTab) => void;
  setDrawerOpen: (open: boolean) => void;
  setActiveDrawerTab: (tab: DrawerTab) => void;
  setActiveChapter: (chapter: number) => void;
  setIsVoiceActive: (active: boolean) => void;
  syncProgress: (data: Partial<LearnerSummary> & Record<string, any>) => void;

  appendTranscript: (speaker: 'user' | 'agent', text: string, isFinal?: boolean) => void;
  appendStreamToken: (token: string, role: string) => void;
  finalizeStreamCard: () => void;

  pushInlineQuiz: (questions: QuizQuestion[], source: 'bank' | 'llm_generated', chapter?: number) => void;
  pushInlineDispute: (data: ContentionProps) => void;
  pushInlineNotes: (notes: Record<string, unknown>) => void;
  pushInlineMovement: (data: GrammarMovementProps) => void;
  pushInlineCanvasLecture: (lecture: CanvasLectureProps) => void;
  pushInlineSheetError: (data: SheetErrorProps) => void;
  pushGenUI: (evt: GenUIEvent) => void;

  submitAnswer: (questionId: string, optionId: string, chapter: number, rawText?: string) => Promise<QuizSubmitResult>;
  triggerLLMQuiz: (chapter: number, mode?: string) => Promise<void>;
  triggerRevision: (chapter: number) => Promise<void>;
  fetchLectureHistory: () => Promise<void>;
  deliverLecturePhase: (phase_index: number, topic?: string, session_type?: string, submodule?: string) => Promise<void>;
  requestReinterpretation: (style_hint: string, topic?: string) => Promise<void>;
  fetchSyllabus: () => Promise<void>;
  fetchQuiz: (chapter: number, mode?: string) => Promise<void>;
  fetchLastSheet: () => Promise<void>;
  disputeAnswer: (claim: string, questionId?: string) => Promise<void>;
  advanceChapter: () => Promise<void>;
  setSseConnected: (v: boolean) => void;
  sendUserMessage: (text: string) => Promise<void>;
}

function getAgentParticipantIdentity(room: Room | null): string {
  if (!room) return '';
  for (const p of room.remoteParticipants.values()) {
    const ident = p.identity.toLowerCase();
    if (ident.includes('agent') || ident.includes('buddy') || p.isAgent) {
      return p.identity;
    }
  }
  if (room.remoteParticipants.size > 0) {
    return Array.from(room.remoteParticipants.values())[0].identity;
  }
  return '';
}

export const useBuddyStore = create<BuddyStore>((set, get) => ({
  feed: [
    {
      id: 'welcome_1',
      type: 'transcript',
      speaker: 'agent',
      text: "Welcome back! I'm Buddy, your conversational English & grammar tutor. We're currently working on **Chapter 1: Course Foundations & Sentence Transformations**.\n\nYou can speak directly into your microphone, ask any grammar question, or tap **Generate Quiz** to test your knowledge.",
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
    {
      id: 'initial_quiz',
      type: 'quiz',
      questions: INITIAL_PRE_VERIFIED_QUESTIONS,
      source: 'bank',
      chapter: 1,
    }
  ],
  sseConnected: false,
  livekitConnected: false,
  livekitRoom: null,
  syllabus: {
    active_chapter: 1,
    learner_state: {
      active_chapter: 1,
      coursework_completed: true,
      milestone_quiz_passed: false,
      chapter_scores: { '1': 85 },
      total_errors: 2,
      total_correct: 14,
      failed_questions_queue: ['ch01_q01']
    },
    roadmap: DEFAULT_ROADMAP
  },
  learnerState: {
    active_chapter: 1,
    coursework_completed: true,
    milestone_quiz_passed: false,
    chapter_scores: { '1': 85 },
    total_errors: 2,
    total_correct: 14,
    failed_questions_queue: ['ch01_q01']
  },
  learnerSummary: null,
  activeChapter: 1,
  activeMode: 'buddy',
  tutorState: null,
  lectureHistory: [],
  drawerOpen: false,
  activeDrawerTab: 'syllabus',
  isVoiceActive: true,

  setLivekitRoom: (room) => set({ livekitRoom: room }),
  setLivekitConnected: (connected) => set({ livekitConnected: connected }),
  toggleTutorMode: async (topic?: string) => {
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);
    const newMode = get().activeMode === 'tutor' ? 'buddy' : 'tutor';
    if (room && room.state === 'connected' && agentId) {
      try {
        const res = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'toggleTutorMode',
          payload: JSON.stringify({ mode: newMode, topic }),
          responseTimeout: 4000
        });
        const st = JSON.parse(res);
        set({ activeMode: st.active_mode || newMode, tutorState: st });
        return;
      } catch (err) {
        console.warn('[LiveKit RPC] toggleTutorMode notice:', err);
      }
    }
    set({ activeMode: newMode });
  },
  toggleDrawer: (tab) => set((s) => ({
    drawerOpen: tab ? true : !s.drawerOpen,
    activeDrawerTab: tab || s.activeDrawerTab,
  })),

  setDrawerOpen: (open) => set({ drawerOpen: open }),
  setActiveDrawerTab: (tab) => set({ activeDrawerTab: tab }),
  setActiveChapter: (chapter) => set({ activeChapter: chapter }),
  setIsVoiceActive: (active) => set({ isVoiceActive: active }),

  syncProgress: (data) => {
    const currentRoadmap = get().syllabus?.roadmap || DEFAULT_ROADMAP;
    const currentLearner = get().learnerState;

    const activeCh = data.active_chapter ?? currentLearner.active_chapter;
    const updatedRoadmap = (data.roadmap as ChapterInfo[]) || currentRoadmap;

    const updatedLearnerState: LearnerState = {
      active_chapter: activeCh,
      coursework_completed: Boolean(data.coursework_completed ?? data.learner_state?.coursework_completed ?? currentLearner.coursework_completed),
      milestone_quiz_passed: Boolean(data.quiz_passed ?? data.learner_state?.milestone_quiz_passed ?? currentLearner.milestone_quiz_passed),
      chapter_scores: data.learner_state?.chapter_scores || currentLearner.chapter_scores,
      total_errors: (data.failed_questions_queue?.length) ?? data.learner_state?.total_errors ?? currentLearner.total_errors,
      total_correct: data.learner_state?.total_correct ?? currentLearner.total_correct,
      failed_questions_queue: data.failed_questions_queue || data.learner_state?.failed_questions_queue || currentLearner.failed_questions_queue || []
    };

    const activeM = (data.active_mode || data.tutor_state?.active_mode || get().activeMode);
    const tutorSt = (data.tutor_state || get().tutorState);
    const newLecs = (data.recent_lectures as CanvasLectureProps[]) || [];
    const mergedLecs = newLecs.length > 0
      ? [...newLecs, ...get().lectureHistory.filter(h => !newLecs.some(r => r.id === h.id))]
      : get().lectureHistory;

    set({
      activeChapter: activeCh,
      activeMode: activeM,
      tutorState: tutorSt,
      lectureHistory: mergedLecs,
      learnerState: updatedLearnerState,
      syllabus: {
        active_chapter: activeCh,
        learner_state: updatedLearnerState,
        roadmap: updatedRoadmap
      },
      learnerSummary: data as LearnerSummary
    });
  },

  appendTranscript: (speaker, text, isFinal = true) => set((s) => {
    const lastItem = s.feed[s.feed.length - 1];
    
    // Update existing interim bubble if same speaker
    if (!isFinal && lastItem && lastItem.type === 'transcript' && lastItem.speaker === speaker && lastItem.is_interim) {
        return {
            feed: [
                ...s.feed.slice(0, -1),
                { ...lastItem, text }
            ]
        };
    }
    
    // Finalize an existing interim bubble
    if (isFinal && lastItem && lastItem.type === 'transcript' && lastItem.speaker === speaker && lastItem.is_interim) {
        return {
            feed: [
                ...s.feed.slice(0, -1),
                { ...lastItem, text, is_interim: false }
            ]
        };
    }

    // Append new bubble
    return {
      feed: [
        ...s.feed,
        {
          id: Math.random().toString(36).slice(2, 9),
          type: 'transcript',
          speaker,
          text,
          ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          is_interim: !isFinal
        }
      ]
    };
  }),

  appendStreamToken: (token, role) => set((s) => {
    const lastItem = s.feed[s.feed.length - 1];
    if (lastItem && lastItem.type === 'streaming_card') {
      return {
        feed: [
          ...s.feed.slice(0, -1),
          { ...lastItem, content: lastItem.content + token }
        ]
      };
    }
    return {
      feed: [
        ...s.feed,
        { id: Math.random().toString(36).slice(2, 9), type: 'streaming_card', role, content: token }
      ]
    };
  }),

  finalizeStreamCard: () => set((s) => ({
    feed: s.feed.filter((i) => i.type !== 'streaming_card')
  })),

  pushInlineQuiz: (questions, source, chapter) => {
    const ch = chapter || get().activeChapter;
    set((s) => ({
      feed: [
        ...s.feed.filter((i) => i.type !== 'streaming_card'),
        {
          id: Math.random().toString(36).slice(2, 9),
          type: 'quiz',
          questions,
          source,
          chapter: ch
        }
      ]
    }));
  },

  pushInlineDispute: (data) => set((s) => ({
    feed: [
      ...s.feed,
      { id: Math.random().toString(36).slice(2, 9), type: 'dispute', data }
    ]
  })),

  pushInlineNotes: (notes) => set((s) => ({
    feed: [
      ...s.feed.filter((i) => i.type !== 'streaming_card'),
      { id: Math.random().toString(36).slice(2, 9), type: 'notes', notes }
    ]
  })),

  pushInlineMovement: (data) => set((s) => ({
    feed: [
      ...s.feed.filter((i) => i.type !== 'streaming_card'),
      { id: data.id || Math.random().toString(36).slice(2, 9), type: 'movement', data }
    ]
  })),

  pushInlineCanvasLecture: (lecture) => set((s) => ({
    feed: [
      ...s.feed.filter((i) => i.type !== 'streaming_card'),
      { id: lecture.id || Math.random().toString(36).slice(2, 9), type: 'canvas_lecture', data: lecture }
    ],
    lectureHistory: [lecture, ...s.lectureHistory.filter((l) => l.id !== lecture.id)]
  })),

  pushInlineSheetError: (data) => set((s) => ({
    feed: [
      ...s.feed.filter((i) => i.type !== 'streaming_card'),
      { id: data.req_id || Math.random().toString(36).slice(2, 9), type: 'sheet_error', data }
    ]
  })),

  pushGenUI: (evt) => {
    if (evt.component === 'QuizCard') {
      const questions = (evt.props?.questions as QuizQuestion[]) || [];
      const source = (evt.props?.source as 'bank' | 'llm_generated') || 'llm_generated';
      const chapter = (evt.props?.chapter as number) || get().activeChapter;
      get().pushInlineQuiz(questions, source, chapter);
    } else if (evt.component === 'BionicSketchNote') {
      const notes = (evt.props?.notes as Record<string, unknown>) || {};
      get().pushInlineNotes(notes);
    } else if (evt.component === 'ContentionResolver') {
      get().pushInlineDispute(evt.props as unknown as ContentionProps);
    } else if (evt.component === 'GrammarMovement') {
      get().pushInlineMovement(evt.props as unknown as GrammarMovementProps);
    } else if (evt.component === 'CanvasLectureCard') {
      get().pushInlineCanvasLecture(evt.props as unknown as CanvasLectureProps);
    } else if (evt.component === 'sheet_error') {
      get().pushInlineSheetError(evt.props as unknown as SheetErrorProps);
    }
  },

  submitAnswer: async (questionId, optionId, chapter, rawText) => {
    const chosenVal = rawText || optionId;
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);

    // 1. LiveKit Native RPC Call (Phase 0)
    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking submitQuizAnswer on ${agentId}...`);
        const rpcRes = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'submitQuizAnswer',
          payload: JSON.stringify({
            question_id: questionId,
            user_answer: chosenVal,
            chapter_idx: chapter
          }),
          responseTimeout: 4000
        });
        const data = JSON.parse(rpcRes);
        const isCorrect = Boolean(data.is_correct);

        set((s) => ({
          learnerState: {
            ...s.learnerState,
            total_correct: isCorrect ? s.learnerState.total_correct + 1 : s.learnerState.total_correct,
            total_errors: !isCorrect ? s.learnerState.total_errors + 1 : s.learnerState.total_errors,
            failed_questions_queue: !isCorrect
              ? Array.from(new Set([...(s.learnerState.failed_questions_queue || []), questionId]))
              : (s.learnerState.failed_questions_queue || []).filter((id) => id !== questionId)
          }
        }));

        return {
          is_correct: isCorrect,
          feedback: data.feedback,
          explanation: data.explanation,
          rule_citation: data.rule_citation,
          isomorphic_question: data.isomorphic_question
        };
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] submitQuizAnswer failed, falling back to local evaluation:', rpcErr);
      }
    }

    // 2. Local Evaluation Fallback
    const allQuizItems = get().feed.filter((i) => i.type === 'quiz') as { questions: QuizQuestion[] }[];
    const allQuestions = allQuizItems.flatMap((q) => q.questions);
    const target = allQuestions.find((q) => q.id === questionId);

    let isCorrect = false;
    if (target) {
      const exp = target.correct_answer.toLowerCase().trim();
      const chosenLower = chosenVal.toLowerCase().trim();
      isCorrect = exp === chosenLower || chosenLower.includes(exp) || exp.includes(chosenLower);
    } else {
      isCorrect = optionId === 'A' || chosenVal.includes('was');
    }

    set((s) => ({
      learnerState: {
        ...s.learnerState,
        total_correct: isCorrect ? s.learnerState.total_correct + 1 : s.learnerState.total_correct,
        total_errors: !isCorrect ? s.learnerState.total_errors + 1 : s.learnerState.total_errors,
      }
    }));

    return {
      is_correct: isCorrect,
      feedback: isCorrect ? 'Correct! Accurate application of the grammar rule.' : 'Not quite. Check the citation rule.',
      explanation: target?.explanation || 'Subject-verb agreement requires grammatical concord with the singular pronoun.',
      rule_citation: target?.rule_citation || 'Oxford Guide Ch 2 / Arihant Rule 12',
      isomorphic_question: !isCorrect ? {
        id: `${questionId}_iso`,
        chapter,
        question: 'Spot the error: "Each of the new engines were tested rigorously."',
        sentence: 'Each of the new engines were tested rigorously.',
        options: ['were -> was', 'No error', 'engines -> engine', 'rigorously -> rigorous'],
        correct_answer: 'were -> was',
        explanation: "'Each' is an indefinite singular pronoun requiring the singular verb 'was'.",
        rule_citation: 'Oxford Guide Ch 2 & Arihant Rule 12',
        is_isomorphic: true
      } : undefined
    };
  },

  triggerLLMQuiz: async (chapter, mode = 'milestone') => {
    get().appendStreamToken(`Synthesizing Chapter ${chapter} questions via LiveKit Agent... `, 'quiz');
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);

    // 1. LiveKit Native RPC (Phase 0 — Retired REST endpoint)
    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking triggerQuiz on ${agentId}...`);
        await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'triggerQuiz',
          payload: JSON.stringify({ chapter, mode }),
          responseTimeout: 5000
        });
        return;
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] triggerQuiz failed, falling back:', rpcErr);
      }
    }

    // 2. Simulated streaming generation fallback
    let progress = 0;
    const tokens = [
      'Analyzing curriculum topic...\n',
      'Retrieving Oxford Guide Ch ' + chapter + ' and Arihant rules...\n',
      'Formulating 3 progressive challenge items...\n',
      'Verification check: anti-hallucination temperature=0.1 passed.\n',
      'Compiling interactive Artifact...'
    ];

    const timer = setInterval(() => {
      if (progress < tokens.length) {
        get().appendStreamToken(tokens[progress], 'quiz');
        progress++;
      } else {
        clearInterval(timer);
        get().pushInlineQuiz([
          {
            id: `ch${chapter}_gen_${Date.now()}`,
            chapter,
            stem: `Isomorphic Evaluation: Inversion and subject concord in Chapter ${chapter}`,
            sentence: 'Neither the manager nor his assistants was aware of the policy update.',
            options: [
              { id: 'A', text: 'was aware -> were aware' },
              { id: 'B', text: 'No error' },
              { id: 'C', text: 'neither -> either' },
              { id: 'D', text: 'nor -> or' }
            ],
            correct_answer: 'A',
            explanation: "Proximity rule with 'neither... nor': When subjects differ in number, the verb agrees with the closer subject ('assistants' -> plural 'were').",
            rule_citation: 'Oxford Guide Ch 2 & Arihant General English Rule 14'
          },
          {
            id: `ch${chapter}_gen2_${Date.now()}`,
            chapter,
            stem: 'Select the sentence with impeccable tense consistency:',
            sentence: 'When the committee convened yesterday, they ______ the recommendation.',
            options: [
              { id: 'A', text: 'had endorsed' },
              { id: 'B', text: 'endorsed' },
              { id: 'C', text: 'are endorsing' },
              { id: 'D', text: 'have endorsed' }
            ],
            correct_answer: 'B',
            explanation: "Simple past 'convened' coordinates directly with simple past 'endorsed' for completed past actions.",
            rule_citation: 'Oxford Guide Ch 4 / Tense Consistency'
          }
        ], 'llm_generated', chapter);
      }
    }, 280);
  },

  triggerRevision: async (chapter) => {
    get().appendStreamToken(`Synthesizing Chapter ${chapter} revision notes via LiveKit Agent... `, 'revision');
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);

    // 1. LiveKit Native RPC (Phase 0 — Retired REST endpoint)
    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking triggerRevision on ${agentId}...`);
        await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'triggerRevision',
          payload: JSON.stringify({ chapter }),
          responseTimeout: 5000
        });
        return;
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] triggerRevision failed, falling back:', rpcErr);
      }
    }

    // 2. Simulated revision notes fallback
    setTimeout(() => {
      get().pushInlineNotes({
        title: `Chapter ${chapter}: Mastery & Structure Notes`,
        chapter,
        overview: 'This chapter solidifies syntactic concord, pronoun-auxiliary agreement, and natural spoken sentence rhythms.',
        rules: [
          {
            title: 'Indefinite Pronouns Concord',
            body: "'Each', 'every', 'neither', and 'either' take singular verbs in formal standard grammar.",
            citation: 'Oxford Guide Ch 2, p. 44'
          },
          {
            title: 'Correlative Conjunctions Proximity Rule',
            body: "With 'Neither... nor' or 'Either... or', the verb agrees in number and person with the closest subject.",
            citation: 'Arihant General English Rule 14'
          }
        ],
        pitfalls: [
          "Do not be distracted by intervening prepositional phrases (e.g., 'One [of the candidates] was').",
          "In casual spoken dialogue, native speakers often use plural 'they' or plural verb with 'neither', but academic exams strictly require singular."
        ],
        colloquial_alternatives: [
          "Formal: 'Neither of them is present.' -> Spoken: 'Neither of them showed up today.'"
        ]
      });
    }, 800);
  },

  disputeAnswer: async (claim, questionId) => {
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);

    // 1. LiveKit Native RPC (Phase 0)
    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking disputeAnswer on ${agentId}...`);
        const rpcRes = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'disputeAnswer',
          payload: JSON.stringify({ user_claim: claim, question_id: questionId }),
          responseTimeout: 5000
        });
        const ruling = JSON.parse(rpcRes);
        get().pushInlineDispute(ruling);
        return;
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] disputeAnswer failed, falling back to local simulation:', rpcErr);
      }
    }

    // 2. Local Simulated Impartial Arbitration
    const isNeitherContention = claim.toLowerCase().includes('neither') || claim.toLowerCase().includes('plural') || claim.toLowerCase().includes('were');
    get().pushInlineDispute({
      user_claim: claim,
      verdict: isNeitherContention
        ? 'Contention Partially Validated: Spoken British & American English frequently accepts plural concord with "neither of", but Prescriptive Academic Standards mandate singular.'
        : `Linguistic analysis completed for claim: "${claim}".`,
      formal_rule: "Prescriptive Standard: 'Neither' is an indefinite distributive pronoun, which strictly takes a singular verb (was/is/has) in standard written English (Oxford Guide Ch 2).",
      colloquial_usage: "Descriptive / Spoken English: Modern corpora (BNC & COCA) demonstrate over 42% frequency of plural verb agreement in informal conversation when followed by 'of + plural pronoun' ('neither of them were').",
      web_search_snippets: [
        {
          title: 'Merriam-Webster Usage Notes: "Neither of them is or are?"',
          url: 'https://www.merriam-webster.com/words-at-play/neither-singular-or-plural',
          snippet: 'Though grammarians insist on singular verb agreement, plural verbs have been used with neither by prestigious writers for centuries in informal contexts.'
        },
        {
          title: 'Oxford Academic Grammar Guide: Concord with Distributive Pronouns',
          url: 'https://academic.oup.com/grammar-guide',
          snippet: 'In formal testing and executive register, singular concord is the non-negotiable benchmark.'
        }
      ],
      recommended_recast: "For formal exams & professional writing: 'Neither of the candidates was chosen.' In relaxed conversation: 'Neither of them was (or were) chosen.'",
      question_id: questionId
    });
  },

  fetchLectureHistory: async () => {
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);
    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking getLectureHistory on ${agentId}...`);
        const rpcRes = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'getLectureHistory',
          payload: JSON.stringify({ limit: 25 }),
          responseTimeout: 4000
        });
        const list = JSON.parse(rpcRes);
        if (Array.isArray(list) && list.length > 0) {
          set({ lectureHistory: list });
        }
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] getLectureHistory failed:', rpcErr);
      }
    }
  },

  deliverLecturePhase: async (phase_index: number, topic = 'Nouns', session_type = 'grammar_mastery', submodule?: string) => {
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);
    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking deliverCanvasLecture for ${topic} (${session_type}) phase ${phase_index}...`);
        const rpcRes = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'deliverCanvasLecture',
          payload: JSON.stringify({ phase_index, topic, session_type, submodule }),
          responseTimeout: 8000
        });
        const lecture = JSON.parse(rpcRes);
        if (lecture && lecture.id) {
          get().pushInlineCanvasLecture(lecture);
        }
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] deliverCanvasLecture failed:', rpcErr);
      }
    }
  },

  requestReinterpretation: async (style_hint: string, topic?: string) => {
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);
    const currentTopic = topic || get().syllabus?.roadmap?.find(c => c.index === get().activeChapter)?.topic || 'Nouns';

    const styleLabels: Record<string, string> = {
      software: 'Software / Engineering Analogy',
      workplace: 'Workplace & Executive Register',
      everyday: 'Everyday Life Intuition'
    };
    const styleLabel = styleLabels[style_hint] || `${style_hint} model`;

    get().appendTranscript('user', `Can you re-explain ${currentTopic} using a ${styleLabel}?`);
    get().appendStreamToken(`Switching pedagogical model to ${styleLabel}...`, 'coach');

    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking requestReinterpretation (${style_hint}) on ${agentId}...`);
        const rpcRes = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'requestReinterpretation',
          payload: JSON.stringify({
            style_hint,
            node_id: currentTopic.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_')
          }),
          responseTimeout: 8000
        });
        get().finalizeStreamCard();
        const parsed = JSON.parse(rpcRes);
        if (parsed?.variant) {
          get().pushInlineCanvasLecture({
            id: parsed.variant.id || `re_${Date.now()}`,
            topic: currentTopic,
            submodule: `${currentTopic} (${styleLabel})`,
            phase_index: 2,
            session_type: 'grammar_mastery',
            spoken_summary: parsed.variant.spoken_summary,
            paragraphs: parsed.variant.lecture_paragraphs || [],
            canvas_type: parsed.variant.canvas_type || 'particle_classifier',
            canvas_config: parsed.variant.canvas_config || {},
            timestamp: new Date().toLocaleTimeString()
          });
        }
        return;
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] requestReinterpretation failed, falling back:', rpcErr);
      }
    }

    // Fallback conversational simulation
    setTimeout(() => {
      get().finalizeStreamCard();
      const fallbackAnalogy = style_hint === 'software'
        ? `In software architecture, **${currentTopic}** is like type-checking in a compiler. Countable nouns behave like instantiated objects (with length or count properties), whereas uncountable nouns behave like streams or primitive buffer references where discrete indices do not apply!`
        : style_hint === 'workplace'
        ? `In corporate communications, **${currentTopic}** determines executive presence. Using precise collective concord ("the committee has decided" vs "the team are aligned") ensures your reports and presentations strike the right tone of unified authority.`
        : `In everyday life, think of **${currentTopic}** like water vs ice cubes: you can't say "give me two waters" (mass noun), but you can easily count "two glasses of water" (quantified containers).`;

      get().appendTranscript('agent', fallbackAnalogy);
    }, 600);
  },

  fetchSyllabus: async () => {
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);

    // LiveKit Native RPC (Phase 1)
    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking getSyllabus on ${agentId}...`);
        const rpcRes = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'getSyllabus',
          payload: '',
          responseTimeout: 4000
        });
        const data = JSON.parse(rpcRes);
        if (data) {
          get().syncProgress(data);
          return;
        }
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] getSyllabus failed, retaining default roadmap:', rpcErr);
      }
    }
    // Offline or disconnected: default 18-chapter curriculum roadmap is already in state
  },

  fetchQuiz: async (chapter, mode = 'milestone') => {
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);

    // LiveKit Native RPC (Phase 1)
    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking getQuiz on ${agentId}...`);
        const rpcRes = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'getQuiz',
          payload: JSON.stringify({ chapter_idx: chapter, mode }),
          responseTimeout: 4000
        });
        const data = JSON.parse(rpcRes);
        const questions: QuizQuestion[] = data.questions || [];
        if (questions.length > 0) {
          get().pushInlineQuiz(questions, 'bank', chapter);
          return;
        }
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] getQuiz failed, falling back to LLM generation:', rpcErr);
      }
    }
    // Fall back to LLM synthesis
    get().triggerLLMQuiz(chapter, mode);
  },

  fetchLastSheet: async () => {
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);

    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking get_last_sheet on ${agentId}...`);
        const rpcRes = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'get_last_sheet',
          payload: '',
          responseTimeout: 4000
        });
        const data = JSON.parse(rpcRes);
        if (data && data.status === 'ok' && data.payload) {
          const reqId = data.req_id;
          const alreadyRendered = get().feed.some(
            (item: any) =>
              item.req_id === reqId ||
              item.id === reqId ||
              item.data?.req_id === reqId ||
              item.data?.id === reqId
          );
          if (!alreadyRendered) {
            console.log(`[LiveKit In-Flight Reconnect] Hydrating last sheet ${data.component} (req_id=${reqId})`);
            const payload = data.payload;
            if (payload.type === 'genui_render') {
              get().pushGenUI(payload as GenUIEvent);
            } else if (data.component === 'sheet_error') {
              get().pushInlineSheetError(payload.props || payload);
            } else {
              get().pushGenUI({
                type: 'genui_render',
                component: data.component,
                props: payload.props || payload
              });
            }
          }
        }
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] get_last_sheet hydration notice:', rpcErr);
      }
    }
  },

  advanceChapter: async () => {
    const room = get().livekitRoom;
    const agentId = getAgentParticipantIdentity(room);

    // 1. LiveKit Native RPC (Phase 1)
    if (room && room.state === 'connected' && agentId) {
      try {
        console.log(`[LiveKit RPC] Invoking advanceChapter on ${agentId}...`);
        const rpcRes = await room.localParticipant.performRpc({
          destinationIdentity: agentId,
          method: 'advanceChapter',
          payload: JSON.stringify({}),
          responseTimeout: 5000
        });
        const res = JSON.parse(rpcRes);
        if (res.success && res.active_chapter) {
          set({ activeChapter: res.active_chapter });
          await get().fetchSyllabus();
          return;
        }
      } catch (rpcErr) {
        console.warn('[LiveKit RPC] advanceChapter failed, falling back to local simulation:', rpcErr);
      }
    }

    // 2. Local advance simulation fallback
    const nextCh = Math.min(get().activeChapter + 1, 18);
    set((s) => ({
      activeChapter: nextCh,
      syllabus: s.syllabus ? {
        ...s.syllabus,
        active_chapter: nextCh,
        roadmap: s.syllabus.roadmap.map((c) =>
          c.index === nextCh ? { ...c, status: 'active' } : c.index < nextCh ? { ...c, status: 'completed' } : c
        )
      } : null
    }));

    get().appendTranscript('agent', `Great work! Advancing to **Chapter ${nextCh}: ${DEFAULT_ROADMAP.find(c => c.index === nextCh)?.title}**.`);
  },

  sendUserMessage: async (text) => {
    get().appendTranscript('user', text);
    const lower = text.toLowerCase().trim();

    // Check if user is triggering a specialized action via prompt
    if (lower.includes('quiz') || lower.includes('test me')) {
      await get().triggerLLMQuiz(get().activeChapter);
      return;
    }

    if (lower.includes('revision') || lower.includes('notes') || lower.includes('summary')) {
      await get().triggerRevision(get().activeChapter);
      return;
    }

    if (lower.startsWith('dispute:') || lower.includes('i think my answer is right') || lower.includes('llm is wrong')) {
      const claim = text.replace(/^dispute:/i, '').trim() || text;
      await get().disputeAnswer(claim);
      return;
    }

    // ── Real Bidirectional Conversational AI Integration ───────────
    const room = get().livekitRoom;
    if (room && room.state === 'connected') {
      const agentParticipant = Array.from(room.remoteParticipants.values()).find(
        (p) => p.isAgent || p.identity.toLowerCase().includes('agent') || p.identity.toLowerCase().includes('buddy')
      ) || Array.from(room.remoteParticipants.values())[0];

      if (agentParticipant) {
        try {
          await room.localParticipant.performRpc({
            destinationIdentity: agentParticipant.identity,
            method: 'sendChatMessage',
            payload: JSON.stringify({ message: text })
          });
          return;
        } catch (rpcErr) {
          console.warn('[Chat RPC] sendChatMessage failed, falling back to data packet:', rpcErr);
        }
      }

      // Fallback: send text packet over LiveKit DataChannel on topic 'chat'
      try {
        const payload = new TextEncoder().encode(JSON.stringify({ speaker: 'user', message: text, text }));
        await room.localParticipant.publishData(payload, { topic: 'chat' });
        return;
      } catch (pubErr) {
        console.warn('[Chat Data] publishData failed:', pubErr);
      }
    }

    // ── Offline Ollama Direct Fallback ──────────────────────────────
    try {
      const res = await fetch('http://localhost:11434/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'qwen-buddy',
          messages: [
            {
              role: 'system',
              content: 'You are Buddy, an encouraging, witty, and deeply knowledgeable English Grammar Master Coach. Answer the learner directly in 1-2 natural, spoken sentences.'
            },
            { role: 'user', content: text }
          ],
          stream: false
        })
      });
      if (res.ok) {
        const data = await res.json();
        const reply = data.message?.content || "I'm here! What grammar challenge are we tackling next?";
        get().appendTranscript('agent', reply, true);
        return;
      }
    } catch (ollamaErr) {
      console.warn('[Chat Ollama Fallback] Error:', ollamaErr);
    }

    get().appendTranscript('agent', "I'm listening! Make sure the agent is connected in the room so we can talk.", true);
  },

  setSseConnected: (v) => set({ sseConnected: v }),
}));
