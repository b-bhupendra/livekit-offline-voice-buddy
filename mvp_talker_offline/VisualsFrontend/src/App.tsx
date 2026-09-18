import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Sparkles } from 'lucide-react';
import { useBuddyStore } from './store';
import { useLiveKit } from './hooks/useLiveKit';
import { Header } from './components/Header';
import { AudioDock } from './components/AudioDock';
import { SlideOverDrawer } from './components/SlideOverDrawer';
import { InlineQuizCard } from './components/InlineQuizCard';
import { InlineDisputeCard } from './components/InlineDisputeCard';
import { InlineNotesCard } from './components/InlineNotesCard';
import { InlineGrammarMovementCard } from './components/InlineGrammarMovementCard';
import { InlineSheetErrorCard } from './components/InlineSheetErrorCard';
import { InlineCanvasLectureCard } from './components/InlineCanvasLectureCard';
import { StreamingCard } from './components/StreamingCard';

export default function App() {
  useLiveKit();
  const { feed, fetchSyllabus, activeMode, tutorState } = useBuddyStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchSyllabus();
  }, [fetchSyllabus]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [feed]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        width: '100vw',
        background: 'var(--surface-0)',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* ── Top Header ── */}
      <Header />

      {/* ── Main Conversational Canvas / Timeline Stream ── */}
      <main
        style={{
          flex: 1,
          overflowY: 'auto',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center'
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: '760px',
            padding: '36px 24px 140px',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          {/* ── Active Tutor Mode Live Banner ── */}
          {activeMode === 'tutor' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                marginBottom: '20px',
                padding: '12px 18px',
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.08) 100%)',
                border: '1px solid rgba(99, 102, 241, 0.35)',
                borderRadius: 'var(--radius-lg)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
                boxShadow: '0 4px 20px rgba(99, 102, 241, 0.12)',
                backdropFilter: 'blur(8px)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '16px',
                    boxShadow: '0 2px 8px rgba(99, 102, 241, 0.4)'
                  }}
                >
                  🎓
                </div>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>Tutor Mode: {tutorState?.current_topic || 'Nouns & Structure'}</span>
                    <span style={{ fontSize: '10px', background: 'rgba(99, 102, 241, 0.25)', color: '#818cf8', padding: '1px 7px', borderRadius: '10px', letterSpacing: '0.04em', fontWeight: 600 }}>
                      LIVE VOICE MASTERY
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    {tutorState?.pending_homework
                      ? `Pending Homework: "${tutorState.pending_homework}" (${tutorState.homework_status || 'assigned'})`
                      : 'Voice Lecture & Mastery Quiz Loop Active • 100% Conversational'}
                  </div>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent)' }}>
                  {tutorState?.mastered_patterns?.length || 0} Patterns
                </div>
                <div style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>Mastered</div>
              </div>
            </motion.div>
          )}

          {feed.length === 0 ? (
            <div
              style={{
                height: '60vh',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                color: 'var(--text-tertiary)'
              }}
            >
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--surface-1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '16px',
                  border: '1px solid var(--border-subtle)'
                }}
              >
                <Sparkles size={22} color="var(--accent)" />
              </div>
              <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                Buddy Conversational Grammar Engine
              </div>
              <div style={{ fontSize: '13.5px', maxWidth: '380px', lineHeight: 1.5 }}>
                Speak via microphone or use the prompt dock below to ask questions, challenge rules, or launch interactive quizzes.
              </div>
            </div>
          ) : (
            feed.map((item, idx) => {
              // ── Transcript Message (User or Assistant) ──
              if (item.type === 'transcript') {
                const isUser = item.speaker === 'user';
                const isLatest = idx === feed.length - 1;
                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: item.is_interim ? 0.85 : 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: isUser ? 'flex-end' : 'flex-start',
                      margin: '14px 0',
                      width: '100%'
                    }}
                  >
                    {/* Timestamp & Speaker Label */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '11px',
                        color: 'var(--text-tertiary)',
                        marginBottom: '4px',
                        padding: '0 6px'
                      }}
                    >
                      {isUser ? (
                        <>
                          <span>You</span>
                          {item.is_interim ? (
                            <span style={{ color: 'var(--accent)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)', display: 'inline-block', animation: 'pulse 1.2s infinite' }} />
                              speaking...
                            </span>
                          ) : (
                            <>
                              <span>·</span>
                              <span>{item.ts}</span>
                            </>
                          )}
                        </>
                      ) : (
                        <>
                          <div
                            style={{
                              width: '15px',
                              height: '15px',
                              borderRadius: '50%',
                              background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: '#ffffff',
                              boxShadow: isLatest ? '0 0 8px rgba(59, 130, 246, 0.5)' : 'none'
                            }}
                          >
                            <Sparkles size={9} />
                          </div>
                          <span style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>Buddy</span>
                          <span>·</span>
                          <span>{item.ts}</span>
                        </>
                      )}
                    </div>

                    {/* Bubble - Gemini Live / ChatGPT Live styling */}
                    <div
                      style={{
                        padding: isUser ? '12px 18px' : '6px 0',
                        borderRadius: isUser ? '16px 16px 4px 16px' : '0px',
                        background: isUser ? (item.is_interim ? 'rgba(99, 102, 241, 0.12)' : 'var(--surface-2)') : 'transparent',
                        border: isUser ? (item.is_interim ? '1px solid var(--accent)' : '1px solid var(--border-subtle)') : 'none',
                        boxShadow: isUser && item.is_interim ? '0 0 16px rgba(99, 102, 241, 0.25)' : 'none',
                        color: item.is_interim ? 'var(--text-primary)' : 'var(--text-primary)',
                        fontSize: '14.5px',
                        lineHeight: 1.65,
                        maxWidth: isUser ? '85%' : '100%',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      {isUser ? (
                        <>
                          {item.text}
                          {item.is_interim && (
                            <span
                              style={{
                                display: 'inline-block',
                                width: '6px',
                                height: '6px',
                                borderRadius: '50%',
                                background: 'var(--accent)',
                                marginLeft: '6px',
                                verticalAlign: 'middle'
                              }}
                            />
                          )}
                        </>
                      ) : (
                        <div className="markdown-content">
                          <Markdown remarkPlugins={[remarkGfm]}>{item.text}</Markdown>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              }

              // ── Streaming Card (Synthesizing Token Stream) ──
              if (item.type === 'streaming_card') {
                return <StreamingCard key={item.id} role={item.role} content={item.content} />;
              }

              // ── Inline Generative Quiz Card ──
              if (item.type === 'quiz') {
                return (
                  <InlineQuizCard
                    key={item.id}
                    questions={item.questions}
                    source={item.source}
                    chapter={item.chapter}
                  />
                );
              }

              // ── Inline Dispute Ruling Card ──
              if (item.type === 'dispute') {
                return <InlineDisputeCard key={item.id} data={item.data} />;
              }

              // ── Inline Revision Notes Card ──
              if (item.type === 'notes') {
                return <InlineNotesCard key={item.id} notes={item.notes} />;
              }

              // ── Inline Syntactic Grammar Movement Card ──
              if (item.type === 'movement') {
                return <InlineGrammarMovementCard key={item.id} data={item.data} />;
              }

              // ── Inline Canvas Visual Lecture Card ──
              if (item.type === 'canvas_lecture') {
                return <InlineCanvasLectureCard key={item.id} data={item.data} />;
              }

              // ── Inline Sheet Error Card ──
              if (item.type === 'sheet_error') {
                return <InlineSheetErrorCard key={item.id} data={item.data} />;
              }

              return null;
            })
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* ── Floating Conversational & Audio Dock ── */}
      <AudioDock />

      {/* ── Slide-Over Curriculum & Analytics Drawer ── */}
      <SlideOverDrawer />
    </div>
  );
}
