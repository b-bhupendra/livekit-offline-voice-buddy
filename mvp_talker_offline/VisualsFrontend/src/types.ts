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

export interface DriftAuditData {
  total_mutations: number;
  pass_count: number;
  fail_count: number;
  pass_rate: number;
  status: string;
}

export interface TutorState {
  active_mode: 'buddy' | 'tutor';
  current_topic: string;
  pending_homework?: string | null;
  homework_status: 'none' | 'pending' | 'completed';
  mastered_patterns: string[];
  current_chapter_idx: number;
  current_chapter_title?: string;
  stage: string;
}

export interface LearnerSummary {
  user_id: string;
  active_chapter: number;
  active_chapter_title: string;
  stage: string;
  active_mode?: 'buddy' | 'tutor';
  current_topic?: string;
  pending_homework?: string | null;
  homework_status?: 'none' | 'pending' | 'completed';
  mastered_patterns?: string[];
  tutor_state?: TutorState;
  learner_preferences?: Record<string, unknown>;
  recent_lectures?: CanvasLectureProps[];
  coursework_completed: boolean;
  quiz_passed: boolean;
  cumulative_accuracy: number;
  failed_questions_queue: string[];
  completed_chapters: number[];
  roadmap: Array<{
    chapter_idx?: number;
    index?: number;
    title: string;
    topic?: string;
    status: 'locked' | 'active' | 'completed';
    is_current?: boolean;
    coursework_done?: boolean;
    quiz_passed?: boolean;
  }>;
  learner_state?: LearnerState & {
    active_mode?: 'buddy' | 'tutor';
    current_topic?: string;
    pending_homework?: string | null;
  };
  drift_audit?: DriftAuditData;
}

export interface SyllabusData {
  active_chapter: number;
  learner_state: LearnerState;
  roadmap: ChapterInfo[];
}

export interface CanvasLectureProps {
  id: string;
  req_id?: string;
  topic: string;
  submodule: string;
  phase_index: number;
  session_type?: 'grammar_mastery' | 'sentence_repetition' | 'workplace_office' | 'conversational_banter' | string;
  spoken_summary: string;
  paragraphs: string[];
  key_takeaways?: string[];
  canvas_type: 'particle_classifier' | 'concord_balance' | 'noun_hierarchy' | 'compound_builder' | 'repetition_flow' | 'workplace_matrix' | string;
  canvas_config?: Record<string, unknown>;
  style_hint?: string;
  citations?: Array<string | { text: string; source: string; rule?: string }>;
  repetition_items?: Array<{
    prompt?: string;
    target: string;
    drill_type?: string;
    audio_cue?: string;
    notes?: string;
  }>;
  timestamp: string;
}

// SSE GenUI events
export type GenUIComponent =
  | 'QuizCard'
  | 'ContentionResolver'
  | 'InteractiveWorksheet'
  | 'BionicSketchNote'
  | 'SyllabusProgressTree'
  | 'GrammarMovement'
  | 'CanvasLectureCard'
  | 'sheet_error';

export interface SheetErrorProps {
  req_id?: string;
  error_code?: string;
  title?: string;
  message: string;
  component_attempted?: string;
  retryable?: boolean;
  details?: string;
}

export interface GenUIEvent {
  schema_version?: '1.0' | string;
  type: 'genui_render';
  component: GenUIComponent;
  props: Record<string, unknown>;
}

export type GrammarRole = 'subject' | 'aux' | 'verb' | 'object' | 'particle' | 'rest';

export interface GrammarMovementToken {
  id: string;
  text: string;
  role: GrammarRole;
  original_index?: number;
}

export interface GrammarMovementProps {
  id: string;
  title: string;
  rule: string;
  chapter: number;
  initial_tokens: GrammarMovementToken[];
  transformed_tokens: GrammarMovementToken[];
  explanation: string;
  rule_citation?: string;
}

export interface VersionedGenUIEvent<T = Record<string, unknown>> {
  schema_version: '1.0';
  type: 'genui_render';
  component: GenUIComponent;
  props: T;
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
  | { id: string; type: 'transcript'; speaker: 'user' | 'agent'; text: string; ts: string; is_interim?: boolean }
  | { id: string; type: 'streaming_card'; role: string; content: string }
  | { id: string; type: 'quiz'; questions: QuizQuestion[]; source: 'bank' | 'llm_generated'; chapter?: number; req_id?: string }
  | { id: string; type: 'dispute'; data: ContentionProps; req_id?: string }
  | { id: string; type: 'notes'; notes: Record<string, unknown>; req_id?: string }
  | { id: string; type: 'movement'; data: GrammarMovementProps; req_id?: string }
  | { id: string; type: 'canvas_lecture'; data: CanvasLectureProps }
  | { id: string; type: 'sheet_error'; data: SheetErrorProps };

export type DrawerTab = 'syllabus' | 'analytics' | 'remediation' | 'lectures';

