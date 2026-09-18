import React from 'react';
import {
  Sparkles,
  CheckCircle2,
  Lock,
  ArrowRight,
  ShieldCheck,
  Award,
  AlertTriangle,
  RotateCcw
} from 'lucide-react';
import { useBuddyStore, DEFAULT_ROADMAP } from '../store';

export const SyllabusSection: React.FC = () => {
  const {
    activeChapter,
    setActiveChapter,
    syllabus,
    learnerState,
    learnerSummary,
    advanceChapter,
    triggerLLMQuiz,
    toggleDrawer
  } = useBuddyStore();

  const roadmap = syllabus?.roadmap || DEFAULT_ROADMAP;
  const currentChapterInfo = roadmap.find((c) => c.index === activeChapter) || roadmap[0];

  const stage = learnerSummary?.stage || 'EXPLANATION';
  const courseworkDone = learnerState.coursework_completed || currentChapterInfo.coursework_done;
  const quizPassed = learnerState.milestone_quiz_passed || currentChapterInfo.quiz_passed;
  const failedQueue = learnerState.failed_questions_queue || [];
  const driftAudit = learnerSummary?.drift_audit;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Active Chapter Hero Card ── */}
      <div
        style={{
          background: 'linear-gradient(145deg, var(--surface-2) 0%, var(--surface-1) 100%)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '16px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                fontSize: '10.5px',
                textTransform: 'uppercase',
                color: 'var(--accent)',
                fontWeight: 700,
                letterSpacing: '0.08em',
                background: 'rgba(99, 102, 241, 0.12)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-full)'
              }}
            >
              Chapter {activeChapter}
            </span>
            <span
              style={{
                fontSize: '10.5px',
                textTransform: 'uppercase',
                color: 'var(--text-tertiary)',
                fontWeight: 600,
                letterSpacing: '0.06em'
              }}
            >
              Stage: {stage}
            </span>
          </div>

          <span
            style={{
              fontSize: '11px',
              color: courseworkDone ? 'var(--success)' : 'var(--text-secondary)',
              background: courseworkDone ? 'var(--success-soft)' : 'var(--surface-3)',
              padding: '2px 8px',
              borderRadius: 'var(--radius-full)',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            {courseworkDone ? (
              <>
                <CheckCircle2 size={11} /> Coursework Complete
              </>
            ) : (
              'Coursework In Progress'
            )}
          </span>
        </div>

        <div style={{ fontSize: '15.5px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
          {currentChapterInfo.title}
        </div>

        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: 1.4 }}>
          Focus: {currentChapterInfo.topic}
        </div>

        {/* Status Pills */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', flexWrap: 'wrap' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              fontSize: '11.5px',
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              background: quizPassed ? 'var(--success-soft)' : 'rgba(234, 179, 8, 0.1)',
              color: quizPassed ? 'var(--success)' : '#eab308',
              border: `1px solid ${quizPassed ? 'rgba(34,197,94,0.2)' : 'rgba(234,179,8,0.2)'}`
            }}
          >
            <Award size={12} />
            <span>{quizPassed ? 'Milestone Passed' : 'Quiz Gated (Pass Required to Advance)'}</span>
          </div>
        </div>

        {/* Quick Actions */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => {
              triggerLLMQuiz(activeChapter);
              toggleDrawer();
            }}
            style={{
              flex: 1,
              background: 'var(--surface-3)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-primary)',
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'background 0.15s ease'
            }}
          >
            <Sparkles size={13} color="var(--accent)" />
            <span>Launch Quiz</span>
          </button>

          <button
            onClick={() => advanceChapter()}
            style={{
              flex: 1,
              background: courseworkDone ? 'var(--accent)' : 'var(--surface-3)',
              border: 'none',
              color: courseworkDone ? '#ffffff' : 'var(--text-secondary)',
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'opacity 0.15s ease'
            }}
          >
            <span>Advance</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>

      {/* ── Isomorphic Drift & Engine Auditing ── */}
      {driftAudit && driftAudit.total_mutations > 0 && (
        <div
          style={{
            background: 'var(--surface-2)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 14px'
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '8px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={14} color="var(--success)" />
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                Isomorphic Drift Audit
              </span>
            </div>
            <span
              style={{
                fontSize: '10.5px',
                color: 'var(--success)',
                background: 'var(--success-soft)',
                padding: '2px 6px',
                borderRadius: 'var(--radius-full)',
                fontWeight: 600
              }}
            >
              {driftAudit.status.toUpperCase()}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', textAlign: 'center' }}>
            <div style={{ background: 'var(--surface-1)', padding: '6px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {driftAudit.total_mutations}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>Variants</div>
            </div>
            <div style={{ background: 'var(--surface-1)', padding: '6px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--success)' }}>
                {driftAudit.pass_rate}%
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>Pass Rate</div>
            </div>
            <div style={{ background: 'var(--surface-1)', padding: '6px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {driftAudit.fail_count}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>Remediations</div>
            </div>
          </div>
        </div>
      )}

      {/* ── Remediation Alert (If Any) ── */}
      {failedQueue.length > 0 && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={15} color="#ef4444" />
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#fca5a5' }}>
                {failedQueue.length} Remediation Questions Pending
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                Isomorphic variations queued for concept retention
              </div>
            </div>
          </div>
          <button
            onClick={() => {
              triggerLLMQuiz(activeChapter, 'remediation');
              toggleDrawer();
            }}
            style={{
              background: '#ef4444',
              color: '#ffffff',
              border: 'none',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <RotateCcw size={11} />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* ── 18-Chapter Progressive Roadmap ── */}
      <div>
        <div
          style={{
            fontSize: '11.5px',
            textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
            letterSpacing: '0.06em',
            marginBottom: '10px',
            fontWeight: 600
          }}
        >
          18-Chapter Progressive Roadmap
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {roadmap.map((ch) => {
            const isCurrent = ch.index === activeChapter;
            const isCompleted = ch.index < activeChapter || ch.status === 'completed';

            return (
              <button
                key={ch.index}
                onClick={() => setActiveChapter(ch.index)}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: isCurrent ? 'var(--surface-2)' : 'transparent',
                  border: isCurrent ? '1px solid var(--accent)' : '1px solid transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ marginTop: '2px' }}>
                  {isCompleted ? (
                    <CheckCircle2 size={16} color="var(--success)" />
                  ) : isCurrent ? (
                    <Sparkles size={16} color="var(--accent)" />
                  ) : (
                    <Lock size={15} color="var(--text-tertiary)" />
                  )}
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        color: isCurrent ? 'var(--accent)' : 'var(--text-tertiary)'
                      }}
                    >
                      {String(ch.index).padStart(2, '0')}
                    </span>
                    <span
                      style={{
                        fontSize: '13px',
                        fontWeight: isCurrent ? 600 : 500,
                        color: isCurrent ? 'var(--text-primary)' : isCompleted ? 'var(--text-secondary)' : 'var(--text-tertiary)'
                      }}
                    >
                      {ch.title}
                    </span>
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-tertiary)' }}>
                    {ch.topic}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
