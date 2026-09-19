import React, { useState } from 'react';
import { motion } from 'framer-motion';
import TextareaAutosize from 'react-textarea-autosize';
import { Mic, MicOff, Send, Sparkles, BookOpen, Scale, GraduationCap, Code2 } from 'lucide-react';
import { useBuddyStore } from '../../store';

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
    requestReinterpretation,
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

  const waveBars = [6, 12, 18, 24, 15, 22, 16, 11, 7];

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '24px',
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(740px, calc(100% - 32px))',
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
          paddingBottom: '3px',
          scrollbarWidth: 'none'
        }}
      >
        <button
          onClick={() => toggleTutorMode()}
          style={{
            background: activeMode === 'tutor' ? 'rgba(99, 102, 241, 0.22)' : 'var(--surface-1)',
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
            boxShadow: activeMode === 'tutor' ? '0 0 12px rgba(99, 102, 241, 0.3)' : 'none',
            transition: 'all 0.15s ease'
          }}
        >
          <Sparkles size={13} color="var(--accent)" />
          <span>{activeMode === 'tutor' ? '🎓 Exit Tutor Mode' : '🎓 Tutor Mode: Nouns'}</span>
        </button>

        <button
          onClick={() => deliverLecturePhase(2)}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 13px',
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
          <GraduationCap size={13} color="var(--accent)" />
          <span>Canvas Lecture</span>
        </button>

        <button
          onClick={() => requestReinterpretation('software')}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 13px',
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
            e.currentTarget.style.borderColor = '#38bdf8';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          <Code2 size={13} color="#38bdf8" />
          <span>⚡ Software Analogy</span>
        </button>

        <button
          onClick={() => triggerLLMQuiz(activeChapter)}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 13px',
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
          <Sparkles size={13} color="var(--accent)" />
          <span>Generate Quiz</span>
        </button>

        <button
          onClick={() => triggerRevision(activeChapter)}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 13px',
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
          <BookOpen size={13} color="var(--text-secondary)" />
          <span>Revision Notes</span>
        </button>

        <button
          onClick={() => disputeAnswer('In modern English, plural verb agreement with neither is widely accepted.')}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-full)',
            padding: '5px 13px',
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
          <Scale size={13} color="var(--text-tertiary)" />
          <span>Test Dispute Ruling</span>
        </button>
      </div>

      {/* ── Floating Primary Audio & Prompt Dock ── */}
      <div
        style={{
          width: '100%',
          background: 'rgba(15, 20, 31, 0.88)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: 'var(--radius-xl)',
          padding: '8px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          boxShadow: '0 16px 42px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.04)',
          backdropFilter: 'blur(20px)'
        }}
      >
        {/* 9-Bar Reactive Equalizer Wave Visualizer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '2.5px',
            padding: '0 4px',
            height: '26px'
          }}
          title={isVoiceActive ? 'Real-time Audio Spectrum Active' : 'Microphone Muted'}
        >
          {waveBars.map((height, i) => (
            <motion.span
              key={i}
              animate={{
                height: isVoiceActive && (sseConnected || livekitConnected) ? [height, height * 0.3, height] : 4
              }}
              transition={{
                repeat: Infinity,
                duration: 0.85,
                delay: i * 0.09,
                ease: 'easeInOut'
              }}
              style={{
                width: '3px',
                background: isVoiceActive
                  ? 'linear-gradient(to top, #6366f1, #06b6d4)'
                  : 'var(--surface-3)',
                borderRadius: '2px',
                height: isVoiceActive ? `${height}px` : '4px'
              }}
            />
          ))}
        </div>

        {/* Mic Toggle Button with Pulsing Voice Halo */}
        <div style={{ position: 'relative' }}>
          {isVoiceActive && (
            <div
              style={{
                position: 'absolute',
                top: '-4px',
                left: '-4px',
                right: '-4px',
                bottom: '-4px',
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(99, 102, 241, 0.35) 0%, rgba(6, 182, 212, 0) 70%)',
                animation: 'pulse 1.8s infinite ease-in-out',
                pointerEvents: 'none'
              }}
            />
          )}
          <button
            onClick={() => setIsVoiceActive(!isVoiceActive)}
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-full)',
              background: isVoiceActive ? 'linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%)' : 'var(--surface-2)',
              border: `1px solid ${isVoiceActive ? 'rgba(99, 102, 241, 0.5)' : 'var(--border-subtle)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: isVoiceActive ? '#ffffff' : 'var(--text-tertiary)',
              boxShadow: isVoiceActive ? '0 0 16px rgba(99, 102, 241, 0.5)' : 'none',
              transition: 'all 0.15s ease',
              position: 'relative',
              zIndex: 2
            }}
            title={isVoiceActive ? 'Mute Live Voice Input' : 'Enable Live Voice Input'}
          >
            {isVoiceActive ? <Mic size={17} /> : <MicOff size={17} />}
          </button>
        </div>

        {/* Text Area Composer */}
        <TextareaAutosize
          maxRows={4}
          placeholder="Talk with Buddy, dispute a rule, or request an analogy..."
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
            width: '36px',
            height: '36px',
            borderRadius: 'var(--radius-full)',
            background: inputVal.trim()
              ? 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)'
              : 'var(--surface-2)',
            border: 'none',
            color: inputVal.trim() ? '#ffffff' : 'var(--text-tertiary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: inputVal.trim() ? 'pointer' : 'default',
            boxShadow: inputVal.trim() ? '0 2px 10px rgba(99, 102, 241, 0.4)' : 'none',
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
