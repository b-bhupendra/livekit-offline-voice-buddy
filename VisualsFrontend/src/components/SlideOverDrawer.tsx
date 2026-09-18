import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  BookOpen,
  BarChart3,
  RefreshCw,
  CheckCircle2,
  Lock,
  ArrowRight,
  Sparkles,
  AlertCircle
} from 'lucide-react';
import { useBuddyStore, DEFAULT_ROADMAP } from '../store';
import type { DrawerTab } from '../types';

export const SlideOverDrawer: React.FC = () => {
  const {
    drawerOpen,
    toggleDrawer,
    activeDrawerTab,
    setActiveDrawerTab,
    activeChapter,
    setActiveChapter,
    syllabus,
    learnerState,
    advanceChapter,
    triggerLLMQuiz
  } = useBuddyStore();

  const roadmap = syllabus?.roadmap || DEFAULT_ROADMAP;
  const currentChapterInfo = roadmap.find((c) => c.index === activeChapter) || roadmap[0];

  const totalCorrect = learnerState.total_correct || 0;
  const totalErrors = learnerState.total_errors || 0;
  const totalAnswers = totalCorrect + totalErrors;
  const accuracyRate = totalAnswers > 0 ? Math.round((totalCorrect / totalAnswers) * 100) : 100;
  const failedQueue = learnerState.failed_questions_queue || [];

  return (
    <AnimatePresence>
      {drawerOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => toggleDrawer()}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(4px)',
              zIndex: 40
            }}
          />

          {/* Slide-Over Panel */}
          <motion.aside
            initial={{ x: 420 }}
            animate={{ x: 0 }}
            exit={{ x: 420 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            style={{
              position: 'fixed',
              top: 0,
              right: 0,
              width: 'min(440px, 100vw)',
              height: '100%',
              background: 'var(--surface-1)',
              borderLeft: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              zIndex: 50,
              boxShadow: '-10px 0 40px rgba(0, 0, 0, 0.6)'
            }}
          >
            {/* Header */}
            <div
              style={{
                height: '58px',
                padding: '0 20px',
                borderBottom: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexShrink: 0
              }}
            >
              <span style={{ fontSize: '14.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                Curriculum & Mastery Analytics
              </span>
              <button
                onClick={() => toggleDrawer()}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Sub-navigation Tabs */}
            <div
              style={{
                display: 'flex',
                borderBottom: '1px solid var(--border-subtle)',
                padding: '0 12px',
                background: 'var(--surface-0)',
                flexShrink: 0
              }}
            >
              {[
                { id: 'syllabus', label: 'Roadmap', icon: BookOpen },
                { id: 'analytics', label: 'Analytics', icon: BarChart3 },
                { id: 'remediation', label: `Remediation (${failedQueue.length})`, icon: RefreshCw }
              ].map((tab) => {
                const isActive = activeDrawerTab === tab.id;
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveDrawerTab(tab.id as DrawerTab)}
                    style={{
                      flex: 1,
                      padding: '10px 6px',
                      background: 'none',
                      border: 'none',
                      borderBottom: `2px solid ${isActive ? 'var(--accent)' : 'transparent'}`,
                      color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                      fontSize: '12.5px',
                      fontWeight: isActive ? 600 : 500,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <Icon size={14} color={isActive ? 'var(--accent)' : 'var(--text-secondary)'} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Content Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
              {/* ── TAB 1: ROADMAP ── */}
              {activeDrawerTab === 'syllabus' && (
                <div>
                  {/* Current Chapter Hero Card */}
                  <div
                    style={{
                      background: 'var(--surface-2)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-md)',
                      padding: '16px',
                      marginBottom: '20px'
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '6px'
                      }}
                    >
                      <span
                        style={{
                          fontSize: '11px',
                          textTransform: 'uppercase',
                          color: 'var(--accent)',
                          fontWeight: 600,
                          letterSpacing: '0.06em'
                        }}
                      >
                        Active Chapter
                      </span>
                      <span
                        style={{
                          fontSize: '11.5px',
                          color: 'var(--success)',
                          background: 'var(--success-soft)',
                          padding: '2px 8px',
                          borderRadius: 'var(--radius-full)',
                          fontWeight: 500
                        }}
                      >
                        Coursework Ready
                      </span>
                    </div>

                    <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                      Chapter {activeChapter}: {currentChapterInfo.title}
                    </div>

                    <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                      Focus: {currentChapterInfo.topic}
                    </div>

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
                          padding: '7px 12px',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '12px',
                          fontWeight: 500,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '6px'
                        }}
                      >
                        <Sparkles size={12} color="var(--accent)" />
                        <span>Launch Quiz</span>
                      </button>

                      <button
                        onClick={() => advanceChapter()}
                        style={{
                          flex: 1,
                          background: 'var(--accent)',
                          border: 'none',
                          color: '#ffffff',
                          padding: '7px 12px',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '12px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '6px'
                        }}
                      >
                        <span>Advance</span>
                        <ArrowRight size={13} />
                      </button>
                    </div>
                  </div>

                  {/* 18-Chapter Curriculum List */}
                  <div
                    style={{
                      fontSize: '11.5px',
                      textTransform: 'uppercase',
                      color: 'var(--text-tertiary)',
                      letterSpacing: '0.06em',
                      marginBottom: '10px'
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
              )}

              {/* ── TAB 2: ANALYTICS ── */}
              {activeDrawerTab === 'analytics' && (
                <div>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '12px',
                      marginBottom: '20px'
                    }}
                  >
                    <div
                      style={{
                        background: 'var(--surface-2)',
                        padding: '16px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-subtle)'
                      }}
                    >
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
                        Accuracy Rate
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--accent)' }}>
                        {accuracyRate}%
                      </div>
                      <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        {totalAnswers} questions answered
                      </div>
                    </div>

                    <div
                      style={{
                        background: 'var(--surface-2)',
                        padding: '16px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-subtle)'
                      }}
                    >
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
                        Curriculum Progress
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {activeChapter} / 18
                      </div>
                      <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        Chapters unlocked
                      </div>
                    </div>

                    <div
                      style={{
                        background: 'var(--surface-2)',
                        padding: '16px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-subtle)'
                      }}
                    >
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
                        Verified Correct
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--success)' }}>
                        {totalCorrect}
                      </div>
                    </div>

                    <div
                      style={{
                        background: 'var(--surface-2)',
                        padding: '16px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-subtle)'
                      }}
                    >
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
                        Errors Logged
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: 700, color: totalErrors > 0 ? 'var(--danger)' : 'var(--text-secondary)' }}>
                        {totalErrors}
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      background: 'var(--surface-2)',
                      padding: '16px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-subtle)',
                      marginBottom: '16px'
                    }}
                  >
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                      RAG Anti-Hallucination Engine
                    </div>
                    <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      The audio engine strictly references Oxford Guide and Arihant General English at temperature=0.1. Any linguistic contention triggers an automatic impartial RAG + web search arbitration.
                    </div>
                  </div>
                </div>
              )}

              {/* ── TAB 3: REMEDIATION ── */}
              {activeDrawerTab === 'remediation' && (
                <div>
                  <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
                    When questions are missed, our Isomorphic Mutation Engine generates parallel practice items targeting the exact same syntactic obstacle.
                  </div>

                  {failedQueue.length === 0 ? (
                    <div
                      style={{
                        padding: '30px 20px',
                        textAlign: 'center',
                        background: 'var(--surface-2)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-subtle)'
                      }}
                    >
                      <CheckCircle2 size={28} color="var(--success)" style={{ margin: '0 auto 10px' }} />
                      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        Queue Clear!
                      </div>
                      <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                        No unresolved grammatical errors in current queue.
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {failedQueue.map((item, idx) => (
                        <div
                          key={idx}
                          style={{
                            padding: '12px 14px',
                            background: 'var(--surface-2)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--border-subtle)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <AlertCircle size={15} color="var(--warning)" />
                            <span style={{ fontSize: '12.5px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                              {item}
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              triggerLLMQuiz(activeChapter);
                              toggleDrawer();
                            }}
                            style={{
                              background: 'var(--surface-3)',
                              border: '1px solid var(--border-subtle)',
                              color: 'var(--text-primary)',
                              fontSize: '11.5px',
                              padding: '4px 10px',
                              borderRadius: 'var(--radius-sm)',
                              cursor: 'pointer'
                            }}
                          >
                            Retry Isomorphic
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};
