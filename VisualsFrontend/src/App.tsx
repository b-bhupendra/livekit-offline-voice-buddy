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
import { StreamingCard } from './components/StreamingCard';

export default function App() {
  useLiveKit();
  const { feed, fetchSyllabus } = useBuddyStore();
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
            feed.map((item) => {
              // ── Transcript Message (User or Assistant) ──
              if (item.type === 'transcript') {
                const isUser = item.speaker === 'user';
                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
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
                          <span>·</span>
                          <span>{item.ts}</span>
                        </>
                      ) : (
                        <>
                          <div
                            style={{
                              width: '14px',
                              height: '14px',
                              borderRadius: '50%',
                              background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: '#ffffff'
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

                    {/* Bubble */}
                    <div
                      style={{
                        padding: isUser ? '12px 18px' : '6px 0',
                        borderRadius: isUser ? '16px 16px 4px 16px' : '0px',
                        background: isUser ? 'var(--surface-2)' : 'transparent',
                        border: isUser ? '1px solid var(--border-subtle)' : 'none',
                        color: 'var(--text-primary)',
                        fontSize: '14.5px',
                        lineHeight: 1.65,
                        maxWidth: isUser ? '85%' : '100%'
                      }}
                    >
                      {isUser ? (
                        item.text
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
