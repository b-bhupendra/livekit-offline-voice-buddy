import React from 'react';
import { Sparkles, BookOpen, Layers, Zap } from 'lucide-react';
import { useBuddyStore, DEFAULT_ROADMAP } from '../store';

export const Header: React.FC = () => {
  const {
    sseConnected,
    livekitConnected,
    activeChapter,
    activeMode,
    tutorState,
    toggleTutorMode,
    triggerLLMQuiz,
    triggerRevision,
    toggleDrawer,
    syllabus
  } = useBuddyStore();

  const roadmap = syllabus?.roadmap || DEFAULT_ROADMAP;
  const currentChapterInfo = roadmap.find((c) => c.index === activeChapter) || roadmap[0];

  return (
    <header
      style={{
        height: '58px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        background: 'var(--surface-0)',
        zIndex: 20,
        flexShrink: 0
      }}
    >
      {/* ── Brand & Status Indicator ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: 'var(--radius-sm)',
              background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff'
            }}
          >
            <Sparkles size={16} />
          </div>
          <span style={{ fontWeight: 600, fontSize: '15.5px', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            Buddy
          </span>
        </div>

        {/* Live Audio & Engine Indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '12px',
            color: (sseConnected || livekitConnected) ? 'var(--text-secondary)' : 'var(--warning)',
            background: 'var(--surface-1)',
            padding: '3px 10px',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--border-subtle)'
          }}
        >
          <span
            style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              background: (sseConnected || livekitConnected) ? 'var(--success)' : 'var(--warning)',
              boxShadow: (sseConnected || livekitConnected) ? '0 0 8px rgba(16, 185, 129, 0.6)' : 'none'
            }}
            className={(sseConnected || livekitConnected) ? 'pulse-beacon' : ''}
          />
          <span>{(sseConnected || livekitConnected) ? 'Live WebRTC Voice' : 'Engine Ready'}</span>
        </div>

        {/* Mode Selector Pill: Buddy Mode vs Tutor Mode */}
        <button
          onClick={() => toggleTutorMode()}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '12px',
            fontWeight: 500,
            cursor: 'pointer',
            padding: '4px 12px',
            borderRadius: 'var(--radius-full)',
            background: activeMode === 'tutor' ? 'rgba(99, 102, 241, 0.15)' : 'var(--surface-1)',
            border: activeMode === 'tutor' ? '1px solid var(--accent)' : '1px solid var(--border-subtle)',
            color: activeMode === 'tutor' ? 'var(--accent)' : 'var(--text-secondary)',
            transition: 'all 0.15s ease'
          }}
          title={activeMode === 'tutor' ? 'Click to switch to casual Buddy Mode' : 'Click to activate grammar Tutor Mode'}
        >
          <Sparkles size={12} color={activeMode === 'tutor' ? 'var(--accent)' : 'var(--text-tertiary)'} />
          <span>{activeMode === 'tutor' ? '🎓 Tutor Mode (Active)' : '💬 Buddy Mode (Chat)'}</span>
        </button>
      </div>

      {/* ── Center Active Chapter / Tutor Topic Pill ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'var(--surface-1)',
          border: '1px solid var(--border-subtle)',
          padding: '4px 14px',
          borderRadius: 'var(--radius-full)',
          maxWidth: '420px'
        }}
      >
        <BookOpen size={13} color="var(--accent)" />
        <span
          style={{
            fontSize: '12.5px',
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}
        >
          {activeMode === 'tutor' ? (
            <>
              <strong style={{ color: 'var(--accent)', fontWeight: 600 }}>Tutor Track:</strong>{' '}
              {tutorState?.current_topic || 'Nouns & Sentence Foundations'}
              {tutorState?.pending_homework && (
                <span style={{ marginLeft: '6px', color: 'var(--warning)', fontWeight: 500 }}>· 📝 HW Pending</span>
              )}
            </>
          ) : (
            <>
              <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Ch. {activeChapter}:</strong>{' '}
              {currentChapterInfo.title}
            </>
          )}
        </span>
      </div>

      {/* ── Right Quick Actions ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={() => triggerLLMQuiz(activeChapter)}
          style={{
            background: 'var(--surface-2)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-subtle)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12.5px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.15s ease'
          }}
        >
          <Zap size={13} color="var(--accent)" />
          <span>Quick Quiz</span>
        </button>

        <button
          onClick={() => triggerRevision(activeChapter)}
          style={{
            background: 'var(--surface-2)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-subtle)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12.5px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.15s ease'
          }}
        >
          <BookOpen size={13} color="var(--text-secondary)" />
          <span>Notes</span>
        </button>

        <button
          onClick={() => toggleDrawer('syllabus')}
          style={{
            background: 'var(--surface-2)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-subtle)',
            padding: '6px 14px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12.5px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.15s ease'
          }}
        >
          <Layers size={13} color="var(--accent)" />
          <span>Syllabus & Stats</span>
        </button>
      </div>
    </header>
  );
};
