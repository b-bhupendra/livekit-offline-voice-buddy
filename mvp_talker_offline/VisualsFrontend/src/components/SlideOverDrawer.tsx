import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  BookOpen,
  BarChart3,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  GraduationCap,
  Play,
  Sparkles,
  Clock,
  Repeat,
  Briefcase,
  MessageSquare
} from 'lucide-react';
import { useBuddyStore } from '../store';
import type { DrawerTab } from '../types';
import { SyllabusSection } from './SyllabusSection';

export const SlideOverDrawer: React.FC = () => {
  const [lectureFilter, setLectureFilter] = useState<string>('all');
  const {
    drawerOpen,
    toggleDrawer,
    activeDrawerTab,
    setActiveDrawerTab,
    activeChapter,
    learnerState,
    lectureHistory,
    pushInlineCanvasLecture,
    deliverLecturePhase,
    triggerLLMQuiz
  } = useBuddyStore();

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
                { id: 'lectures', label: `Lectures (${lectureHistory.length})`, icon: GraduationCap },
                { id: 'analytics', label: 'Analytics', icon: BarChart3 },
                { id: 'remediation', label: `Errors (${failedQueue.length})`, icon: RefreshCw }
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
              {/* ── TAB 1: ROADMAP / SYLLABUS SECTION ── */}
              {activeDrawerTab === 'syllabus' && <SyllabusSection />}

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

              {/* ── TAB 4: LECTURES & REVISION SESSIONS ── */}
              {activeDrawerTab === 'lectures' && (
                <div>
                  {/* Practice Category Selection Filter Pills */}
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 600, letterSpacing: '0.06em', marginBottom: '8px' }}>
                      Practice Session Categories
                    </div>
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {[
                        { id: 'all', label: 'All Sessions', icon: Sparkles },
                        { id: 'grammar_mastery', label: 'Grammar', icon: GraduationCap },
                        { id: 'sentence_repetition', label: 'Repetition', icon: Repeat },
                        { id: 'workplace_office', label: 'Workplace', icon: Briefcase },
                        { id: 'conversational_banter', label: 'Banter', icon: MessageSquare }
                      ].map((tab) => {
                        const Icon = tab.icon;
                        const isSel = lectureFilter === tab.id;
                        return (
                          <button
                            key={tab.id}
                            onClick={() => setLectureFilter(tab.id)}
                            style={{
                              padding: '5px 10px',
                              borderRadius: 'var(--radius-full)',
                              fontSize: '11px',
                              fontWeight: 500,
                              background: isSel ? 'var(--accent)' : 'var(--surface-2)',
                              color: isSel ? '#ffffff' : 'var(--text-secondary)',
                              border: `1px solid ${isSel ? 'var(--accent)' : 'var(--border-subtle)'}`,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '5px',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <Icon size={12} />
                            <span>{tab.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Practice Launchers */}
                  <div style={{ marginBottom: '20px' }}>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 600, letterSpacing: '0.06em', marginBottom: '8px' }}>
                      Interactive Practice Launchers
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {[
                        { phase: 1, topic: 'Nouns', session_type: 'grammar_mastery', title: 'Nouns 1: Concrete vs Abstract', desc: 'Sensory perception vs Cognitive concepts' },
                        { phase: 2, topic: 'Nouns', session_type: 'grammar_mastery', title: 'Nouns 2: Countable vs Uncountable', desc: 'Mass nouns (much/many, fewer/less)' },
                        { phase: 3, topic: 'Nouns', session_type: 'grammar_mastery', title: 'Nouns 3: Collective Concord', desc: 'Unitary whole vs Individual members' },
                        { phase: 4, topic: 'Nouns', session_type: 'grammar_mastery', title: 'Nouns 4: Compound Head Nouns', desc: 'Head noun pluralization (mothers-in-law)' },
                        { phase: 5, topic: 'Nouns', session_type: 'grammar_mastery', title: 'Nouns 5: Possessive Genitives', desc: "Tom and Mary's vs Tom's and Mary's" },
                        { phase: 1, topic: 'Conversational Fluency', session_type: 'sentence_repetition', title: '🗣️ Daily Repetition: Spoken Contractions', desc: 'Cadence & rhythm of gonna, wanna, could\'ve' },
                        { phase: 1, topic: 'Workplace Communication', session_type: 'workplace_office', title: '💼 Workplace: Polite Softening & Requests', desc: 'Transforming blunt commands into diplomatic requests' }
                      ].filter(item => lectureFilter === 'all' || item.session_type === lectureFilter).map((item, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            deliverLecturePhase(item.phase, item.topic, item.session_type);
                            toggleDrawer();
                          }}
                          style={{
                            padding: '10px 12px',
                            background: 'var(--surface-2)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-md)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            cursor: 'pointer',
                            textAlign: 'left',
                            transition: 'all 0.15s ease'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = 'var(--accent)';
                            e.currentTarget.style.background = 'var(--surface-3)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = 'var(--border-subtle)';
                            e.currentTarget.style.background = 'var(--surface-2)';
                          }}
                        >
                          <div>
                            <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                              {item.title}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                              {item.desc}
                            </div>
                          </div>
                          <Play size={13} color="var(--accent)" />
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Previous Generated Lectures List */}
                  <div>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 600, letterSpacing: '0.06em', marginBottom: '8px' }}>
                      Previous Saved Sessions ({lectureHistory.filter(l => lectureFilter === 'all' || (l.session_type || 'grammar_mastery') === lectureFilter).length})
                    </div>
                    {lectureHistory.filter(l => lectureFilter === 'all' || (l.session_type || 'grammar_mastery') === lectureFilter).length === 0 ? (
                      <div
                        style={{
                          padding: '24px 16px',
                          textAlign: 'center',
                          background: 'var(--surface-0)',
                          borderRadius: 'var(--radius-md)',
                          border: '1px dashed var(--border-subtle)',
                          color: 'var(--text-tertiary)'
                        }}
                      >
                        <Sparkles size={20} color="var(--accent)" style={{ margin: '0 auto 8px', display: 'block' }} />
                        <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)' }}>
                          No Saved Sessions in This Category
                        </div>
                        <div style={{ fontSize: '11.5px', marginTop: '4px' }}>
                          Launch a practice session above or ask Buddy in voice: "Teach me about nouns" or "Let's do sentence repetition"!
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {lectureHistory
                          .filter(l => lectureFilter === 'all' || (l.session_type || 'grammar_mastery') === lectureFilter)
                          .map((lec) => (
                          <div
                            key={lec.id}
                            style={{
                              padding: '12px 14px',
                              background: 'var(--surface-2)',
                              borderRadius: 'var(--radius-md)',
                              border: '1px solid var(--border-subtle)',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '6px'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                                  {lec.submodule}
                                </span>
                                <span
                                  style={{
                                    fontSize: '9.5px',
                                    padding: '1px 6px',
                                    borderRadius: '8px',
                                    background: 'rgba(99, 102, 241, 0.15)',
                                    color: '#818cf8',
                                    fontWeight: 600,
                                    textTransform: 'uppercase'
                                  }}
                                >
                                  {lec.session_type || 'grammar'}
                                </span>
                              </div>
                              <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: '3px' }}>
                                <Clock size={10} />
                                {lec.timestamp ? lec.timestamp.slice(11, 16) : 'Recent'}
                              </span>
                            </div>

                            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontStyle: 'italic', lineHeight: 1.4 }}>
                              "{lec.spoken_summary ? lec.spoken_summary.slice(0, 110) + '...' : 'Interactive visual lecture'}"
                            </div>

                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                              <button
                                onClick={() => {
                                  pushInlineCanvasLecture(lec);
                                  toggleDrawer();
                                }}
                                style={{
                                  background: 'rgba(99, 102, 241, 0.15)',
                                  border: '1px solid var(--accent)',
                                  color: 'var(--accent)',
                                  fontSize: '11px',
                                  fontWeight: 500,
                                  padding: '4px 10px',
                                  borderRadius: 'var(--radius-sm)',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '4px'
                                }}
                              >
                                <Sparkles size={11} />
                                <span>Re-open / Revise</span>
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};
