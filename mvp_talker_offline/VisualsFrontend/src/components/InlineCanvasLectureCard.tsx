import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { GraduationCap, Eye, Sparkles, CheckCircle2, Volume2, Repeat, Briefcase, MessageSquare, Mic, Volume1 } from 'lucide-react';
import type { CanvasLectureProps } from '../types';
import { bionicHtml } from '../utils/bionic';

interface InlineCanvasLectureCardProps {
  data: CanvasLectureProps;
}

export const InlineCanvasLectureCard: React.FC<InlineCanvasLectureCardProps> = ({ data }) => {
  const [bionicEnabled, setBionicEnabled] = useState(false);
  const [activeInteractiveMode, setActiveInteractiveMode] = useState<'unitary' | 'divided'>('unitary');
  const [activeWorkplaceIdx, setActiveWorkplaceIdx] = useState<number>(0);
  const [practicingIdx, setPracticingIdx] = useState<number | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const canvasType = data.canvas_type || 'particle_classifier';
  const cfg = (data.canvas_config || {}) as Record<string, any>;
  const sessionType = data.session_type || 'grammar_mastery';

  // ── Session Type Meta ──
  const sessionMeta = {
    grammar_mastery: {
      label: 'Grammar Mastery',
      icon: GraduationCap,
      color: '#6366f1',
      bg: 'rgba(99, 102, 241, 0.15)',
      border: 'rgba(99, 102, 241, 0.3)'
    },
    sentence_repetition: {
      label: 'Sentence Repetition',
      icon: Repeat,
      color: '#06b6d4',
      bg: 'rgba(6, 182, 212, 0.15)',
      border: 'rgba(6, 182, 212, 0.3)'
    },
    workplace_office: {
      label: 'Workplace & Office',
      icon: Briefcase,
      color: '#10b981',
      bg: 'rgba(16, 185, 129, 0.15)',
      border: 'rgba(16, 185, 129, 0.3)'
    },
    conversational_banter: {
      label: 'Conversational Banter',
      icon: MessageSquare,
      color: '#f59e0b',
      bg: 'rgba(245, 158, 11, 0.15)',
      border: 'rgba(245, 158, 11, 0.3)'
    }
  }[sessionType as string] || {
    label: 'Interactive Lecture',
    icon: GraduationCap,
    color: '#6366f1',
    bg: 'rgba(99, 102, 241, 0.15)',
    border: 'rgba(99, 102, 241, 0.3)'
  };

  const SessionIcon = sessionMeta.icon;

  // ── Speech Synthesis for Shadowing Practice ──
  const handleListenPractice = (text: string, idx: number) => {
    setPracticingIdx(idx);
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = 0.92;
      utter.pitch = 1.0;
      utter.onend = () => setPracticingIdx(null);
      utter.onerror = () => setPracticingIdx(null);
      window.speechSynthesis.speak(utter);
    } else {
      setTimeout(() => setPracticingIdx(null), 2000);
    }
  };

  // ── HTML5 Interactive Canvas Animation Engine ──
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 640);
    let height = (canvas.height = 220);

    // Particle Classifier state
    const items = (cfg.items as Array<{ name: string; category: string; type: string }>) || [
      { name: 'Apples', category: 'Countable', type: 'countable' },
      { name: 'Water', category: 'Uncountable', type: 'uncountable' },
      { name: 'Advice', category: 'Uncountable', type: 'uncountable' },
      { name: 'Laptops', category: 'Countable', type: 'countable' },
      { name: 'Information', category: 'Uncountable', type: 'uncountable' },
      { name: 'Furniture', category: 'Uncountable', type: 'uncountable' }
    ];

    const particles = items.map((it, idx) => ({
      ...it,
      x: 80 + (idx % 3) * ((width - 160) / 2) + Math.random() * 40,
      y: 35 + Math.floor(idx / 3) * 60,
      vx: (Math.random() - 0.5) * 0.8,
      vy: (Math.random() - 0.5) * 0.8,
      radius: 28
    }));

    let scaleAngle = activeInteractiveMode === 'unitary' ? -0.12 : 0.12;
    let waveOffset = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      if (canvasType === 'concord_balance') {
        // ── Concord Balance Scale Visualizer ──
        const centerX = width / 2;
        const centerY = 120;
        const beamLength = Math.min(width * 0.7, 340);

        const targetAngle = activeInteractiveMode === 'unitary' ? -0.14 : 0.14;
        scaleAngle += (targetAngle - scaleAngle) * 0.08;

        // Base Stand
        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - 20);
        ctx.lineTo(centerX, centerY + 65);
        ctx.moveTo(centerX - 40, centerY + 65);
        ctx.lineTo(centerX + 40, centerY + 65);
        ctx.stroke();

        // Fulcrum Triangle
        ctx.fillStyle = '#3b82f6';
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - 20);
        ctx.lineTo(centerX - 14, centerY + 5);
        ctx.lineTo(centerX + 14, centerY + 5);
        ctx.closePath();
        ctx.fill();

        // Rotating Beam
        ctx.save();
        ctx.translate(centerX, centerY - 20);
        ctx.rotate(scaleAngle);

        ctx.strokeStyle = '#94a3b8';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(-beamLength / 2, 0);
        ctx.lineTo(beamLength / 2, 0);
        ctx.stroke();

        // Left Pan: Unitary (Singular)
        ctx.fillStyle = activeInteractiveMode === 'unitary' ? '#3b82f6' : '#475569';
        ctx.fillRect(-beamLength / 2 - 35, 15, 70, 26);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('IS / HAS', -beamLength / 2, 32);

        // Right Pan: Divided (Plural)
        ctx.fillStyle = activeInteractiveMode === 'divided' ? '#10b981' : '#475569';
        ctx.fillRect(beamLength / 2 - 35, 15, 70, 26);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('ARE / HAVE', beamLength / 2, 32);

        ctx.restore();

        // Top Status Bubble
        ctx.fillStyle = activeInteractiveMode === 'unitary' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(16, 185, 129, 0.15)';
        ctx.strokeStyle = activeInteractiveMode === 'unitary' ? '#3b82f6' : '#10b981';
        ctx.lineWidth = 1.5;
        ctx.roundRect(width / 2 - 170, 15, 340, 36, [8]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#f8fafc';
        ctx.font = '12.5px Inter, sans-serif';
        ctx.textAlign = 'center';
        const statusText =
          activeInteractiveMode === 'unitary'
            ? 'Unified Whole: "The committee has reached its decision."'
            : 'Individual Members: "The committee are divided in opinions."';
        ctx.fillText(statusText, width / 2, 38);

      } else if (canvasType === 'repetition_flow') {
        // ── Repetition Cadence & Rhythm Waveform Visualizer ──
        waveOffset += 0.05;
        const centerY = height / 2 + 10;
        const barCount = 36;
        const barWidth = (width - 60) / barCount;

        ctx.fillStyle = 'rgba(6, 182, 212, 0.05)';
        ctx.fillRect(10, 10, width - 20, height - 20);

        // Draw animated soundwave bars
        for (let i = 0; i < barCount; i++) {
          const x = 30 + i * barWidth;
          const sine = Math.sin(i * 0.35 + waveOffset);
          const barHeight = Math.max(8, Math.abs(sine) * 65 + 10);
          
          // Gradient from cyan to indigo
          ctx.fillStyle = i % 4 === 0 ? '#38bdf8' : i % 2 === 0 ? '#818cf8' : '#475569';
          ctx.roundRect(x, centerY - barHeight / 2, barWidth - 4, barHeight, [3]);
          ctx.fill();
        }

        // Top Label Pill
        ctx.fillStyle = 'rgba(6, 182, 212, 0.2)';
        ctx.strokeStyle = '#06b6d4';
        ctx.lineWidth = 1;
        ctx.roundRect(width / 2 - 160, 14, 320, 28, [6]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 11.5px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('STRESS-TIMED CADENCE: STRESS CONTENT WORDS', width / 2, 32);

        // Bottom guide
        ctx.fillStyle = '#94a3b8';
        ctx.font = '11px Inter, sans-serif';
        ctx.fillText('Listen to the sentence cadence below and shadow each beat.', width / 2, height - 14);

      } else if (canvasType === 'workplace_matrix') {
        // ── Workplace Softening Matrix Visualizer ──
        const pairs = (cfg.pairs as Array<{ direct: string; softened: string; tone: string }>) || [
          { direct: 'Send me the file now.', softened: 'Could you possibly send the file over when you get a chance?', tone: 'Polite Request' },
          { direct: 'You are wrong.', softened: 'I see it a bit differently; could we review this together?', tone: 'Diplomatic Feedback' }
        ];
        const activePair = pairs[activeWorkplaceIdx % pairs.length];
        const colW = (width - 40) / 2;

        // Direct side
        ctx.fillStyle = 'rgba(239, 68, 68, 0.08)';
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.roundRect(14, 20, colW - 10, height - 40, [8]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#f87171';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('DIRECT (MAY SOUND BLUNT)', 26, 44);

        ctx.fillStyle = '#ffffff';
        ctx.font = '12px Inter, sans-serif';
        ctx.fillText(`"${activePair.direct}"`, 26, 75);

        // Softened side
        ctx.fillStyle = 'rgba(16, 185, 129, 0.08)';
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.roundRect(colW + 14, 20, colW - 10, height - 40, [8]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#34d399';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.fillText(`SOFTENED (${activePair.tone.toUpperCase()})`, colW + 26, 44);

        ctx.fillStyle = '#ffffff';
        ctx.font = '12px Inter, sans-serif';
        ctx.fillText(`"${activePair.softened.slice(0, 42)}..."`, colW + 26, 75);

        // Bottom indicator
        ctx.fillStyle = '#94a3b8';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Tap selector buttons above to toggle workplace phrasing examples', width / 2, height - 12);

      } else {
        // ── Particle Classifier Visualizer (Countable vs Uncountable / Concrete vs Abstract) ──
        const colWidth = (width - 40) / 2;

        ctx.fillStyle = 'rgba(59, 130, 246, 0.08)';
        ctx.strokeStyle = 'rgba(59, 130, 246, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.roundRect(14, 18, colWidth - 10, height - 36, [10]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#60a5fa';
        ctx.font = 'bold 12px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('COUNTABLE / SENSORY [Many • Fewer • Units]', 26, 42);

        ctx.fillStyle = 'rgba(168, 85, 247, 0.08)';
        ctx.strokeStyle = 'rgba(168, 85, 247, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.roundRect(colWidth + 14, 18, colWidth - 10, height - 36, [10]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#c084fc';
        ctx.font = 'bold 12px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('UNCOUNTABLE / MASS [Much • Less • Continuous]', colWidth + 26, 42);

        particles.forEach((p) => {
          p.x += p.vx;
          p.y += p.vy;

          const isCountable = p.type === 'countable' || p.type === 'concrete';
          const minX = isCountable ? 26 : colWidth + 26;
          const maxX = isCountable ? colWidth - 26 : width - 26;

          if (p.x < minX || p.x > maxX) p.vx *= -1;
          if (p.y < 65 || p.y > height - 35) p.vy *= -1;

          const pillW = 90;
          const pillH = 26;
          const px = p.x - pillW / 2;
          const py = p.y - pillH / 2;

          ctx.fillStyle = isCountable ? 'rgba(30, 58, 138, 0.85)' : 'rgba(88, 28, 135, 0.85)';
          ctx.strokeStyle = isCountable ? '#38bdf8' : '#e879f9';
          ctx.lineWidth = 1;
          ctx.roundRect(px, py, pillW, pillH, [13]);
          ctx.fill();
          ctx.stroke();

          ctx.fillStyle = '#ffffff';
          ctx.font = '500 11.5px Inter, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(p.name, p.x, p.y + 4);
        });
      }

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [canvasType, activeInteractiveMode, activeWorkplaceIdx, cfg]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      style={{
        margin: '20px 0',
        background: 'var(--surface-1)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-xl)',
        padding: '22px 24px',
        maxWidth: '720px',
        width: '100%',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.35)',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* ── Top Header Badge Bar ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '30px',
              height: '30px',
              borderRadius: '50%',
              background: sessionMeta.bg,
              border: `1px solid ${sessionMeta.border}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: sessionMeta.color,
              boxShadow: `0 2px 10px ${sessionMeta.bg}`
            }}
          >
            <SessionIcon size={16} />
          </div>
          <div>
            <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Phase {data.phase_index || 1}: {data.submodule}</span>
              <span
                style={{
                  fontSize: '10px',
                  background: sessionMeta.bg,
                  color: sessionMeta.color,
                  border: `1px solid ${sessionMeta.border}`,
                  padding: '2px 8px',
                  borderRadius: '10px',
                  fontWeight: 600,
                  textTransform: 'uppercase'
                }}
              >
                {sessionMeta.label}
              </span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
              Curriculum Topic: {data.topic} • Generated at {data.timestamp}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setBionicEnabled(!bionicEnabled)}
            style={{
              background: bionicEnabled ? 'rgba(99, 102, 241, 0.2)' : 'var(--surface-2)',
              border: `1px solid ${bionicEnabled ? 'var(--accent)' : 'var(--border-subtle)'}`,
              borderRadius: 'var(--radius-full)',
              padding: '4px 10px',
              fontSize: '11px',
              color: bionicEnabled ? 'var(--accent)' : 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px'
            }}
            title="Toggle Bionic Rapid Reading"
          >
            <Eye size={12} />
            <span>Bionic</span>
          </button>
        </div>
      </div>

      {/* ── Spoken Voice Script Pill ── */}
      {data.spoken_summary && (
        <div
          style={{
            marginBottom: '16px',
            padding: '10px 14px',
            background: 'rgba(59, 130, 246, 0.08)',
            border: '1px solid rgba(59, 130, 246, 0.25)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px'
          }}
        >
          <Volume2 size={16} color="var(--accent)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '13px', lineHeight: 1.55, color: 'var(--text-primary)', fontStyle: 'italic' }}>
            "{data.spoken_summary}"
          </div>
        </div>
      )}

      {/* ── Educational Lecture Paragraphs (2 to 3 structured paragraphs) ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
        {data.paragraphs.map((para, idx) => (
          <div
            key={idx}
            style={{
              fontSize: '13.5px',
              lineHeight: 1.7,
              color: 'var(--text-secondary)',
              background: 'var(--surface-0)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)'
            }}
          >
            {bionicEnabled ? (
              <span dangerouslySetInnerHTML={{ __html: bionicHtml(para, true) }} />
            ) : (
              <span>{para}</span>
            )}
          </div>
        ))}
      </div>

      {/* ── Interactive HTML5 Canvas Section ── */}
      <div
        style={{
          background: '#090d16',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          padding: '14px',
          marginBottom: '16px',
          position: 'relative'
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
            <Sparkles size={13} color="var(--accent)" />
            <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--accent)', fontWeight: 600 }}>
              Interactive Visual Canvas
            </span>
          </div>

          {canvasType === 'concord_balance' && (
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                onClick={() => setActiveInteractiveMode('unitary')}
                style={{
                  background: activeInteractiveMode === 'unitary' ? 'var(--accent)' : 'var(--surface-2)',
                  border: 'none',
                  borderRadius: 'var(--radius-full)',
                  padding: '3px 10px',
                  fontSize: '11px',
                  color: '#ffffff',
                  cursor: 'pointer'
                }}
              >
                Unitary Whole
              </button>
              <button
                onClick={() => setActiveInteractiveMode('divided')}
                style={{
                  background: activeInteractiveMode === 'divided' ? '#10b981' : 'var(--surface-2)',
                  border: 'none',
                  borderRadius: 'var(--radius-full)',
                  padding: '3px 10px',
                  fontSize: '11px',
                  color: '#ffffff',
                  cursor: 'pointer'
                }}
              >
                Individual Concord
              </button>
            </div>
          )}

          {canvasType === 'workplace_matrix' && (
            <div style={{ display: 'flex', gap: '6px' }}>
              {((cfg.pairs as Array<any>) || [1, 2]).map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveWorkplaceIdx(idx)}
                  style={{
                    background: activeWorkplaceIdx === idx ? '#10b981' : 'var(--surface-2)',
                    border: 'none',
                    borderRadius: 'var(--radius-full)',
                    padding: '3px 10px',
                    fontSize: '11px',
                    color: '#ffffff',
                    cursor: 'pointer'
                  }}
                >
                  Example {idx + 1}
                </button>
              ))}
            </div>
          )}
        </div>

        <canvas
          ref={canvasRef}
          style={{
            width: '100%',
            height: '220px',
            display: 'block',
            borderRadius: 'var(--radius-md)'
          }}
        />
      </div>

      {/* ── Spoken Sentence Repetition & Shadowing Section ── */}
      {data.repetition_items && data.repetition_items.length > 0 && (
        <div style={{ marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
            <Repeat size={14} color="#06b6d4" />
            <span style={{ fontSize: '11.5px', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#06b6d4', fontWeight: 600 }}>
              Sentence Repetition & Shadowing Practice
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {data.repetition_items.map((item, idx) => (
              <div
                key={idx}
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '10px', background: 'rgba(6, 182, 212, 0.15)', color: '#06b6d4', padding: '2px 8px', borderRadius: '8px', fontWeight: 600 }}>
                    {item.drill_type || 'Shadowing Drill'}
                  </span>
                  <button
                    onClick={() => handleListenPractice(item.target, idx)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: practicingIdx === idx ? '#06b6d4' : 'rgba(255, 255, 255, 0.08)',
                      border: 'none',
                      color: practicingIdx === idx ? '#000000' : '#ffffff',
                      borderRadius: 'var(--radius-full)',
                      padding: '3px 10px',
                      fontSize: '11px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {practicingIdx === idx ? <Volume2 size={12} /> : <Volume1 size={12} />}
                    <span>{practicingIdx === idx ? 'Playing Audio...' : 'Listen & Shadow'}</span>
                  </button>
                </div>

                <div style={{ fontSize: '13.5px', fontWeight: 500, color: 'var(--text-primary)' }}>
                  {bionicEnabled ? (
                    <span dangerouslySetInnerHTML={{ __html: bionicHtml(item.target, true) }} />
                  ) : (
                    <span>{item.target}</span>
                  )}
                </div>

                {item.audio_cue && (
                  <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <Mic size={11} color="var(--accent)" />
                    <span>Cadence Tip: {item.audio_cue}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Key Takeaways ── */}
      {data.key_takeaways && data.key_takeaways.length > 0 && (
        <div style={{ marginBottom: '14px' }}>
          <div style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-tertiary)', marginBottom: '8px' }}>
            Key Syntactical Rules to Remember
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {data.key_takeaways.map((rule, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '12.5px',
                  color: 'var(--text-primary)',
                  background: 'var(--surface-2)',
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)'
                }}
              >
                <CheckCircle2 size={13} color="var(--accent)" style={{ flexShrink: 0 }} />
                <span>{rule}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Footer ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingTop: '10px',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '11.5px',
          color: 'var(--text-tertiary)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <CheckCircle2 size={13} color="#10b981" />
          <span>Saved to Revision Store (Check anytime in Drawer &gt; Lectures)</span>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)' }}>
          ID: {data.id.slice(0, 14)}
        </div>
      </div>
    </motion.div>
  );
};
