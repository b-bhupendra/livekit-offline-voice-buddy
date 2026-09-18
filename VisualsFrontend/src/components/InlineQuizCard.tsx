import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  CheckCircle2,
  XCircle,
  Scale,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Send,
  BookOpen,
  Award
} from 'lucide-react';
import { useBuddyStore } from '../store';
import type { QuizQuestion, QuizSubmitResult } from '../types';

interface InlineQuizCardProps {
  questions: QuizQuestion[];
  source: 'bank' | 'llm_generated' | string;
  chapter?: number;
}

export const InlineQuizCard: React.FC<InlineQuizCardProps> = ({
  questions: initialQuestions,
  source,
  chapter: cardChapter
}) => {
  const [questions, setQuestions] = useState<QuizQuestion[]>(initialQuestions);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [evalResult, setEvalResult] = useState<QuizSubmitResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDispute, setShowDispute] = useState(false);
  const [disputeClaim, setDisputeClaim] = useState('');
  const [isDisputeSubmitted, setIsDisputeSubmitted] = useState(false);

  const activeChapter = useBuddyStore((s) => s.activeChapter);
  const submitAnswer = useBuddyStore((s) => s.submitAnswer);
  const disputeAnswer = useBuddyStore((s) => s.disputeAnswer);

  const q = questions[currentIndex];
  if (!q) {
    return (
      <div
        style={{
          margin: '16px 0',
          background: 'var(--surface-2)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          maxWidth: '680px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}
      >
        <Award size={20} color="var(--success)" />
        <span style={{ fontSize: '14px', fontWeight: 500 }}>
          Quiz session completed! Check Syllabus & Stats for your updated mastery level.
        </span>
      </div>
    );
  }

  // ── Normalize Question Attributes ──────────────────────────────────────────
  const stem = q.stem || q.question || 'Select the grammatically accurate option:';
  const effectiveChapter = q.chapter || cardChapter || activeChapter || 1;

  // Normalize options: handles both string[] and {id, text}[]
  const rawOptions = q.options || [];
  const normalizedOptions = rawOptions.map((opt, i) => {
    const letter = String.fromCharCode(65 + i); // 'A', 'B', 'C', 'D'
    if (typeof opt === 'string') {
      return { id: letter, text: opt, raw: opt };
    }
    return {
      id: opt.id || letter,
      text: opt.text || String(opt),
      raw: opt.text || opt.id
    };
  });

  const handleSelect = async (optId: string, rawText: string) => {
    if (selectedId !== null || isSubmitting) return;
    setSelectedId(optId);
    setIsSubmitting(true);

    try {
      const result = await submitAnswer(q.id, optId, effectiveChapter, rawText);
      setEvalResult(result);
    } catch {
      setEvalResult({
        is_correct: false,
        explanation: q.explanation || 'Verification error'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNext = () => {
    setSelectedId(null);
    setEvalResult(null);
    setShowDispute(false);
    setDisputeClaim('');
    setIsDisputeSubmitted(false);
    setCurrentIndex((prev) => prev + 1);
  };

  const handleLoadIsomorphic = (iso: QuizQuestion) => {
    // Insert isomorphic question immediately after current question
    const updated = [...questions];
    updated.splice(currentIndex + 1, 0, iso);
    setQuestions(updated);
    handleNext();
  };

  const handleSubmitDispute = async () => {
    if (!disputeClaim.trim()) return;
    await disputeAnswer(disputeClaim.trim(), q.id);
    setIsDisputeSubmitted(true);
    setShowDispute(false);
  };

  const isAnswered = selectedId !== null;
  const isCorrect = evalResult?.is_correct ?? null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      style={{
        margin: '20px 0',
        background: 'var(--surface-2)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: '22px 24px',
        maxWidth: '700px',
        width: '100%',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.25)'
      }}
    >
      {/* ── Header Bar ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {source === 'llm_generated' ? (
            <Sparkles size={14} color="var(--accent)" />
          ) : (
            <BookOpen size={14} color="var(--text-secondary)" />
          )}
          <span
            style={{
              fontSize: '11px',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-tertiary)',
              fontWeight: 600
            }}
          >
            Artifact · Question {currentIndex + 1} of {questions.length}
          </span>
          <span
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              background: source === 'llm_generated' ? 'var(--accent-soft)' : 'var(--surface-3)',
              borderRadius: 'var(--radius-full)',
              color: source === 'llm_generated' ? 'var(--accent)' : 'var(--text-secondary)',
              fontWeight: 500
            }}
          >
            {source === 'llm_generated' ? 'MCP / LLM Orchestrated' : 'Verified Bank'}
          </span>
        </div>

        {q.rule_citation && (
          <span
            style={{
              fontSize: '11.5px',
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              background: 'var(--surface-1)',
              padding: '2px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)'
            }}
          >
            {q.rule_citation}
          </span>
        )}
      </div>

      {/* ── Question Stem ── */}
      <div
        style={{
          fontSize: '15px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '12px',
          lineHeight: 1.5
        }}
      >
        {stem}
      </div>

      {/* ── Context Sentence Block ── */}
      {q.sentence && (
        <div
          style={{
            padding: '12px 16px',
            background: 'var(--surface-1)',
            borderLeft: '3px solid var(--accent)',
            borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
            marginBottom: '18px',
            fontSize: '14px',
            color: 'var(--text-secondary)',
            fontStyle: 'italic',
            lineHeight: 1.6
          }}
        >
          "{q.sentence}"
        </div>
      )}

      {/* ── Options List ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {normalizedOptions.map((opt) => {
          const isCurrentSelected = selectedId === opt.id;
          let borderColor = 'var(--border-subtle)';
          let bg = 'var(--surface-1)';
          let textColor = 'var(--text-primary)';
          let icon = null;

          if (isAnswered) {
            if (isCurrentSelected) {
              if (isCorrect) {
                borderColor = 'var(--success)';
                bg = 'var(--success-soft)';
                icon = <CheckCircle2 size={16} color="var(--success)" />;
              } else {
                borderColor = 'var(--danger)';
                bg = 'var(--danger-soft)';
                icon = <XCircle size={16} color="var(--danger)" />;
              }
            } else {
              // Check if this option is the correct answer
              const isTargetCorrect =
                q.correct_answer.toLowerCase().trim() === opt.raw.toLowerCase().trim() ||
                q.correct_answer.toUpperCase().trim() === opt.id.toUpperCase().trim();
              if (isTargetCorrect && !isCorrect) {
                borderColor = 'rgba(16, 185, 129, 0.4)';
                bg = 'rgba(16, 185, 129, 0.05)';
              }
            }
          }

          return (
            <button
              key={opt.id}
              onClick={() => handleSelect(opt.id, opt.raw)}
              disabled={isAnswered || isSubmitting}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '12px 16px',
                background: bg,
                border: `1px solid ${borderColor}`,
                borderRadius: 'var(--radius-md)',
                color: textColor,
                fontSize: '14px',
                cursor: isAnswered ? 'default' : 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s ease',
                position: 'relative'
              }}
            >
              <span
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: 'var(--radius-sm)',
                  background: isCurrentSelected ? 'var(--surface-3)' : 'var(--surface-2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: 600,
                  marginRight: '14px',
                  color: isCurrentSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)'
                }}
              >
                {opt.id}
              </span>

              <span style={{ flex: 1, lineHeight: 1.4 }}>{opt.text}</span>

              {icon && <div style={{ marginLeft: '12px' }}>{icon}</div>}
            </button>
          );
        })}
      </div>

      {/* ── Explanation & Remediation ── */}
      <AnimatePresence>
        {isAnswered && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              marginTop: '18px',
              borderTop: '1px solid var(--border-subtle)',
              paddingTop: '16px'
            }}
          >
            {/* Explanation box */}
            <div
              style={{
                fontSize: '13.5px',
                color: 'var(--text-secondary)',
                marginBottom: '16px',
                lineHeight: 1.6,
                background: 'var(--surface-1)',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)'
              }}
            >
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                {isCorrect ? 'Accurate' : 'Linguistic Explanation'}
              </div>
              <div className="markdown-content">
                <Markdown remarkPlugins={[remarkGfm]}>
                  {evalResult?.explanation || q.explanation}
                </Markdown>
              </div>
            </div>

            {/* Actions Bar */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '10px'
              }}
            >
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                {!isCorrect && !showDispute && !isDisputeSubmitted && (
                  <button
                    onClick={() => setShowDispute(true)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      fontSize: '13px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 8px',
                      borderRadius: 'var(--radius-sm)'
                    }}
                  >
                    <Scale size={14} />
                    <span>Dispute result</span>
                  </button>
                )}

                {isDisputeSubmitted && (
                  <span style={{ fontSize: '12.5px', color: 'var(--accent)', fontStyle: 'italic' }}>
                    Dispute submitted to impartial arbitrator...
                  </span>
                )}

                {evalResult?.isomorphic_question && (
                  <button
                    onClick={() => handleLoadIsomorphic(evalResult.isomorphic_question!)}
                    style={{
                      background: 'var(--accent-soft)',
                      color: 'var(--accent)',
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                      padding: '6px 12px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '12.5px',
                      fontWeight: 500,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <RefreshCw size={13} />
                    <span>Try Isomorphic Practice</span>
                  </button>
                )}
              </div>

              {currentIndex + 1 < questions.length ? (
                <button
                  onClick={handleNext}
                  style={{
                    background: 'var(--text-primary)',
                    color: 'var(--surface-0)',
                    padding: '8px 18px',
                    borderRadius: 'var(--radius-full)',
                    border: 'none',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <span>Continue</span>
                  <ArrowRight size={14} />
                </button>
              ) : (
                <span
                  style={{
                    fontSize: '13px',
                    color: 'var(--success)',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <CheckCircle2 size={16} />
                  <span>Quiz Completed</span>
                </span>
              )}
            </div>

            {/* ── Dispute Claim Drawer ── */}
            {showDispute && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  marginTop: '14px',
                  background: 'var(--surface-1)',
                  border: '1px solid var(--border-strong)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px'
                }}
              >
                <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                  Contend Answer with Linguistic Evidence
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '8px' }}>
                  Provide colloquial context, regional usage (e.g. British vs American), or specific grammar rules:
                </div>
                <textarea
                  placeholder="e.g. In British spoken English, 'neither of them were' is widely used according to BNC..."
                  value={disputeClaim}
                  onChange={(e) => setDisputeClaim(e.target.value)}
                  rows={3}
                  style={{
                    width: '100%',
                    background: 'var(--surface-2)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    padding: '8px 12px',
                    fontSize: '13px',
                    fontFamily: 'inherit',
                    outline: 'none',
                    resize: 'none',
                    marginBottom: '10px'
                  }}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                  <button
                    onClick={() => setShowDispute(false)}
                    style={{
                      background: 'transparent',
                      color: 'var(--text-secondary)',
                      border: 'none',
                      fontSize: '12.5px',
                      cursor: 'pointer',
                      padding: '6px 12px'
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmitDispute}
                    disabled={!disputeClaim.trim()}
                    style={{
                      background: 'var(--accent)',
                      color: '#ffffff',
                      border: 'none',
                      padding: '6px 14px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '12.5px',
                      fontWeight: 500,
                      cursor: disputeClaim.trim() ? 'pointer' : 'default',
                      opacity: disputeClaim.trim() ? 1 : 0.5,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <Send size={12} />
                    <span>Submit Dispute</span>
                  </button>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
