// ── Global Type Definitions for Buddy Live Voice & Conversational UI ─────────

export interface QuizOption {
  id: string;
  text: string;
}

export interface QuizQuestion {
  id: string;
  chapter?: number;
  stem?: string;
  question?: string; // used by pre-verified quiz banks
  sentence?: string;
  options: (string | QuizOption)[];
  correct_answer: string;
  explanation: string;
  rule_citation?: string;
  type?: string;
  isomorphic?: QuizQuestion;
  isomorphic_question?: QuizQuestion;
  is_isomorphic?: boolean;
  allow_dispute?: boolean;
}

export interface QuizSubmitResult {
  is_correct: boolean;
  feedback?: string;
  explanation?: string;
  rule_citation?: string;
  isomorphic_question?: QuizQuestion;
}

export interface WebSnippet {
  title: string;
  url: string;
  snippet: string;
}

export interface ContentionProps {
  user_claim: string;
  verdict: string;
  formal_rule: string;
  colloquial_usage: string;
  web_search_snippets?: WebSnippet[];
  recommended_recast?: string;
  question_id?: string;
}

export interface ChapterInfo {
  index: number; // 1-indexed (1 to 18)
  title: string;
  topic: string;
  status: 'locked' | 'active' | 'completed';
  coursework_done: boolean;
  quiz_passed: boolean;
}

export interface LearnerState {
  active_chapter: number;
  coursework_completed: boolean;
  milestone_quiz_passed: boolean;
  chapter_scores: Record<string, number>;
  total_errors: number;
  total_correct: number;
  session_start?: string;
  failed_questions_queue?: string[];
}

export interface SyllabusData {
  active_chapter: number;
  learner_state: LearnerState;
  roadmap: ChapterInfo[];
}

// SSE GenUI events
export type GenUIComponent =
  | 'QuizCard'
  | 'ContentionResolver'
  | 'InteractiveWorksheet'
  | 'BionicSketchNote'
  | 'SyllabusProgressTree';

export interface GenUIEvent {
  type: 'genui_render';
  component: GenUIComponent;
  props: Record<string, unknown>;
}

// Live AI Activity types
export interface TokenEvent {
  token: string;
  role: 'quiz' | 'revision' | string;
  chapter: number;
}

export interface TranscriptEntry {
  speaker: 'user' | 'agent';
  text: string;
  ts: string;
}

export interface EventLogEntry {
  id: string;
  type: 'quiz_result' | 'chapter_advance' | 'genui' | 'connection' | 'error';
  label: string;
  ok: boolean;
  ts: string;
}

export type FeedItem =
  | { id: string; type: 'transcript'; speaker: 'user' | 'agent'; text: string; ts: string }
  | { id: string; type: 'streaming_card'; role: string; content: string }
  | { id: string; type: 'quiz'; questions: QuizQuestion[]; source: 'bank' | 'llm_generated'; chapter?: number }
  | { id: string; type: 'dispute'; data: ContentionProps }
  | { id: string; type: 'notes'; notes: Record<string, unknown> };

export type DrawerTab = 'syllabus' | 'analytics' | 'remediation';
