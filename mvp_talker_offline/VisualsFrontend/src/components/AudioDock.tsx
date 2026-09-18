import React, { useState } from 'react';
import { motion } from 'framer-motion';
import TextareaAutosize from 'react-textarea-autosize';
import { Mic, MicOff, Send, Sparkles, BookOpen, Scale, GraduationCap } from 'lucide-react';
import { useBuddyStore } from '../store';

export const AudioDock: React.FC = () => {
  const [inputVal, setInputVal] = useState('');
  const {
    isVoiceActive,
    setIsVoiceActive,
    sseConnected,
    livekitConnected,
    activeChapter,
    activeMode,
    toggleTutorMode,
    deliverLecturePhase,
    triggerLLMQuiz,
    triggerRevision,
    disputeAnswer,
    sendUserMessage
  } = useBuddyStore();

  const handleSend = () => {
    if (!inputVal.trim()) return;
    sendUserMessage(inputVal.trim());
    setInputVal('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '24px',
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(720px, calc(100% - 32px))',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '10px',
        zIndex: 30
      }}
    >
      {/* ── Quick Action Suggestion Chips ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          overflowX: 'auto',
          maxWidth: '100%',
          paddingBottom: '2px'
        }}
      >
        <button
          onClick={() => toggleTutorMode()}
          style={{
            background: activeMode === 'tutor' ? 'rgba(99, 102, 241, 0.2)' : 'var(--surface-1)',
            border: activeMode === 'tutor' ? '1px solid var(--accent)' : '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 14px',
            fontSize: '12px',
            fontWeight: 500,
            color: activeMode === 'tutor' ? 'var(--accent)' : 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            whiteSpace: 'nowrap',
            transition: 'all 0.15s ease'
          }}
        >
          <Sparkles size={12} color="var(--accent)" />
          <span>{activeMode === 'tutor' ? '🎓 Exit Tutor Mode (Chat)' : '🎓 Start Tutor Mode: Nouns'}</span>
        </button>

        <button
          onClick={() => deliverLecturePhase(2)}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 12px',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            whiteSpace: 'nowrap',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--accent)';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          <GraduationCap size={12} color="var(--accent)" />
          <span>Canvas Lecture: Nouns</span>
        </button>

        <button
          onClick={() => triggerLLMQuiz(activeChapter)}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 12px',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            whiteSpace: 'nowrap',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--accent)';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          <Sparkles size={12} color="var(--accent)" />
          <span>Generate Ch. {activeChapter} Quiz</span>
        </button>

        <button
          onClick={() => triggerRevision(activeChapter)}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 12px',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            whiteSpace: 'nowrap',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--accent)';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          <BookOpen size={12} color="var(--text-secondary)" />
          <span>Revision Notes</span>
        </button>

        <button
          onClick={() => disputeAnswer('In modern English, plural verb agreement with neither is common.')}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 12px',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            whiteSpace: 'nowrap',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--accent)';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          <Scale size={12} color="var(--text-tertiary)" />
          <span>Test Dispute Ruling</span>
        </button>
      </div>

      {/* ── Floating Primary Audio & Prompt Dock ── */}
      <div
        style={{
          width: '100%',
          background: 'var(--surface-1)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-xl)',
          padding: '8px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          boxShadow: '0 12px 36px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(16px)'
        }}
      >
        {/* Audio Wave Visualizer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            padding: '0 4px',
            height: '24px'
          }}
        >
          {[8, 14, 22, 12, 7].map((height, i) => (
            <motion.span
              key={i}
              animate={{
                height: isVoiceActive && (sseConnected || livekitConnected) ? [height, height * 0.35, height] : 4
              }}
              transition={{
                repeat: Infinity,
                duration: 0.9,
                delay: i * 0.12,
                ease: 'easeInOut'
              }}
              style={{
                width: '3px',
                background: isVoiceActive && (sseConnected || livekitConnected) ? 'var(--accent)' : 'var(--surface-3)',
                borderRadius: '2px',
                height: isVoiceActive ? `${height}px` : '4px'
              }}
            />
          ))}
        </div>

        {/* Mic Toggle Button */}
        <button
          onClick={() => setIsVoiceActive(!isVoiceActive)}
          style={{
            width: '34px',
            height: '34px',
            borderRadius: 'var(--radius-full)',
            background: isVoiceActive ? 'var(--accent-soft)' : 'var(--surface-2)',
            border: `1px solid ${isVoiceActive ? 'rgba(59, 130, 246, 0.3)' : 'var(--border-subtle)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: isVoiceActive ? 'var(--accent)' : 'var(--text-tertiary)',
            transition: 'all 0.15s ease'
          }}
          title={isVoiceActive ? 'Mute Live Voice Input' : 'Enable Live Voice Input'}
        >
          {isVoiceActive ? <Mic size={16} /> : <MicOff size={16} />}
        </button>

        {/* Text Area Composer */}
        <TextareaAutosize
          maxRows={4}
          placeholder="Talk with Buddy or ask a grammar question..."
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={handleKeyDown}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontSize: '14px',
            lineHeight: 1.5,
            resize: 'none',
            padding: '4px 0'
          }}
        />

        {/* Send Button */}
        <button
          onClick={handleSend}
          disabled={!inputVal.trim()}
          style={{
            width: '34px',
            height: '34px',
            borderRadius: 'var(--radius-full)',
            background: inputVal.trim() ? 'var(--accent)' : 'var(--surface-2)',
            border: 'none',
            color: inputVal.trim() ? '#ffffff' : 'var(--text-tertiary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: inputVal.trim() ? 'pointer' : 'default',
            transition: 'all 0.15s ease'
          }}
          title="Send message (Enter)"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  );
};
