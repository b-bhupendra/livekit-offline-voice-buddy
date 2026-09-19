import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  GraduationCap,
  Eye,
  Sparkles,
  CheckCircle2,
  Volume2,
  Repeat,
  Briefcase,
  MessageSquare,
  Mic,
  Volume1,
  Code2,
  Compass,
  BookMarked,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import type { CanvasLectureProps } from '../../types';
import { bionicHtml } from '../../utils/bionic';
import { useBuddyStore } from '../../store';

interface InlineCanvasLectureCardProps {
  data: CanvasLectureProps;
}

export const InlineCanvasLectureCard: React.FC<InlineCanvasLectureCardProps> = ({ data }) => {
  const [bionicEnabled, setBionicEnabled] = useState(false);
  const [activeInteractiveMode, setActiveInteractiveMode] = useState<'unitary' | 'divided'>('unitary');
  const [activeWorkplaceIdx, setActiveWorkplaceIdx] = useState<number>(0);
  const [practicingIdx, setPracticingIdx] = useState<number | null>(null);
  const [selectedTreeNode, setSelectedTreeNode] = useState<string>('agreement');
  const [reinterpretingStyle, setReinterpretingStyle] = useState<string | null>(null);
  const [showCitations, setShowCitations] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const rawCanvasType = (data.canvas_type || 'particle_classifier').toLowerCase();
  const cfg = (data.canvas_config || {}) as Record<string, any>;
  const sessionType = data.session_type || 'grammar_mastery';

  // Normalize canvas type into 5 canonical primitives
  const canvasType =
    rawCanvasType.includes('tree') || rawCanvasType.includes('hierarchy')
      ? 'tree'
      : rawCanvasType.includes('balance') || rawCanvasType.includes('scale') || rawCanvasType.includes('concord')
      ? 'balance'
      : rawCanvasType.includes('flow') || rawCanvasType.includes('cadence') || rawCanvasType.includes('repetition')
      ? 'flow'
      : rawCanvasType.includes('matrix') || rawCanvasType.includes('workplace') || rawCanvasType.includes('soften')
      ? 'matrix'
      : 'classifier';

  // Session metadata
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

  // Speech preview for repetition/shadowing
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

  // Reinterpretation action trigger
  const handleRequestAnalogy = async (style: 'software' | 'workplace' | 'everyday') => {
    setReinterpretingStyle(style);
    try {
      await useBuddyStore.getState().requestReinterpretation(style, data.topic);
    } finally {
      setTimeout(() => setReinterpretingStyle(null), 1500);
    }
  };

  // Canvas Drawing Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 640);
    let height = (canvas.height = 230);

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
      x: 80 + (idx % 3) * ((width - 160) / 2) + Math.random() * 30,
      y: 40 + Math.floor(idx / 3) * 65,
      vx: (Math.random() - 0.5) * 0.7,
      vy: (Math.random() - 0.5) * 0.7,
      radius: 28
    }));

    let scaleAngle = activeInteractiveMode === 'unitary' ? -0.12 : 0.12;
    let waveOffset = 0;
    let pulseT = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);
      pulseT += 0.04;

      // 1. Syntactic Tree Primitive
      if (canvasType === 'tree') {
        const cx = width / 2;
        const cy = 30;

        // Tree layout coordinates
        const root = { x: cx, y: cy, label: 'S (Sentence)', role: 'Clause Root' };
        const np = { x: cx - width * 0.22, y: cy + 60, label: 'NP (Subject)', role: 'Subject Noun Phrase' };
        const vp = { x: cx + width * 0.22, y: cy + 60, label: 'VP (Predicate)', role: 'Verb Phrase' };

        // Leaves
        const det = { x: np.x - 45, y: np.y + 60, label: 'Det', text: '"The"' };
        const noun = { x: np.x + 45, y: np.y + 60, label: 'Noun', text: '"committee"' };
        const aux = { x: vp.x - 65, y: vp.y + 60, label: 'Aux', text: activeInteractiveMode === 'unitary' ? '"has"' : '"have"' };
        const verb = { x: vp.x, y: vp.y + 60, label: 'Verb', text: '"voted"' };
        const obj = { x: vp.x + 65, y: vp.y + 60, label: 'NP', text: '"unanimously"' };

        // Draw connecting branches with bezier curves
        ctx.strokeStyle = 'rgba(99, 102, 241, 0.4)';
        ctx.lineWidth = 2;

        const drawBranch = (p1: { x: number; y: number }, p2: { x: number; y: number }, active = false) => {
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y + 12);
          ctx.bezierCurveTo(p1.x, (p1.y + p2.y) / 2, p2.x, (p1.y + p2.y) / 2, p2.x, p2.y - 12);
          ctx.strokeStyle = active ? '#38bdf8' : 'rgba(148, 163, 184, 0.25)';
          ctx.lineWidth = active ? 2.5 : 1.5;
          ctx.stroke();
        };

        drawBranch(root, np);
        drawBranch(root, vp);
        drawBranch(np, det);
        drawBranch(np, noun);
        drawBranch(vp, aux, true);
        drawBranch(vp, verb);
        drawBranch(vp, obj);

        // Agreement arc between Head Noun and Auxiliary Verb
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([4, 4]);
        ctx.moveTo(noun.x, noun.y + 20);
        ctx.quadraticCurveTo(cx, height - 25, aux.x, aux.y + 20);
        ctx.strokeStyle = activeInteractiveMode === 'unitary' ? '#60a5fa' : '#34d399';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.restore();

        // Agreement indicator label
        ctx.fillStyle = activeInteractiveMode === 'unitary' ? '#60a5fa' : '#34d399';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(
          activeInteractiveMode === 'unitary' ? '⇄ Grammatical Concord: Singular (Unit)' : '⇄ Notional Concord: Plural (Members)',
          cx,
          height - 10
        );

        // Helper to draw node pills
        const drawNode = (
          pt: { x: number; y: number; label: string; text?: string },
          highlight = false,
          color = '#6366f1'
        ) => {
          const w = pt.text ? 72 : 84;
          const h = pt.text ? 36 : 24;
          ctx.fillStyle = highlight ? 'rgba(99, 102, 241, 0.25)' : 'rgba(15, 23, 42, 0.85)';
          ctx.strokeStyle = highlight ? color : 'rgba(148, 163, 184, 0.3)';
          ctx.lineWidth = highlight ? 1.5 : 1;
          ctx.roundRect(pt.x - w / 2, pt.y - h / 2, w, h, [6]);
          ctx.fill();
          ctx.stroke();

          ctx.fillStyle = highlight ? '#ffffff' : '#cbd5e1';
          ctx.font = '600 11px Inter, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(pt.label, pt.x, pt.text ? pt.y - 3 : pt.y + 4);

          if (pt.text) {
            ctx.fillStyle = color;
            ctx.font = 'bold 11px Inter, sans-serif';
            ctx.fillText(pt.text, pt.x, pt.y + 11);
          }
        };

        drawNode(root, false, '#818cf8');
        drawNode(np, false, '#38bdf8');
        drawNode(vp, false, '#818cf8');
        drawNode(det);
        drawNode(noun, true, activeInteractiveMode === 'unitary' ? '#60a5fa' : '#34d399');
        drawNode(aux, true, activeInteractiveMode === 'unitary' ? '#60a5fa' : '#34d399');
        drawNode(verb);
        drawNode(obj);

      // 2. Concord Balance Scale Primitive
      } else if (canvasType === 'balance') {
        const centerX = width / 2;
        const centerY = 125;
        const beamLength = Math.min(width * 0.72, 350);

        const targetAngle = activeInteractiveMode === 'unitary' ? -0.14 : 0.14;
        scaleAngle += (targetAngle - scaleAngle) * 0.08;

        // Base Stand
        ctx.strokeStyle = '#475569';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - 20);
        ctx.lineTo(centerX, centerY + 65);
        ctx.moveTo(centerX - 42, centerY + 65);
        ctx.lineTo(centerX + 42, centerY + 65);
        ctx.stroke();

        // Glowing Fulcrum
        ctx.fillStyle = '#6366f1';
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - 20);
        ctx.lineTo(centerX - 15, centerY + 6);
        ctx.lineTo(centerX + 15, centerY + 6);
        ctx.closePath();
        ctx.fill();

        // Beam
        ctx.save();
        ctx.translate(centerX, centerY - 20);
        ctx.rotate(scaleAngle);

        ctx.strokeStyle = '#94a3b8';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(-beamLength / 2, 0);
        ctx.lineTo(beamLength / 2, 0);
        ctx.stroke();

        // Left Pan: Unitary
        ctx.fillStyle = activeInteractiveMode === 'unitary' ? '#3b82f6' : '#334155';
        ctx.fillRect(-beamLength / 2 - 38, 15, 76, 28);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('IS / HAS', -beamLength / 2, 33);

        // Right Pan: Divided
        ctx.fillStyle = activeInteractiveMode === 'divided' ? '#10b981' : '#334155';
        ctx.fillRect(beamLength / 2 - 38, 15, 76, 28);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('ARE / HAVE', beamLength / 2, 33);

        ctx.restore();

        // Status pill
        ctx.fillStyle = activeInteractiveMode === 'unitary' ? 'rgba(59, 130, 246, 0.12)' : 'rgba(16, 185, 129, 0.12)';
        ctx.strokeStyle = activeInteractiveMode === 'unitary' ? '#3b82f6' : '#10b981';
        ctx.lineWidth = 1.2;
        ctx.roundRect(width / 2 - 180, 14, 360, 36, [8]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#f8fafc';
        ctx.font = '12px Inter, sans-serif';
        ctx.textAlign = 'center';
        const statusText =
          activeInteractiveMode === 'unitary'
            ? 'Unified Entity (Unitary Concord): "The committee has approved the plan."'
            : 'Individual Members (Notional Concord): "The committee are divided in opinion."';
        ctx.fillText(statusText, width / 2, 37);

      // 3. Cadence Flow Waveform Primitive
      } else if (canvasType === 'flow') {
        waveOffset += 0.045;
        const centerY = height / 2 + 10;
        const barCount = 38;
        const barWidth = (width - 60) / barCount;

        ctx.fillStyle = 'rgba(6, 182, 212, 0.04)';
        ctx.fillRect(10, 10, width - 20, height - 20);

        for (let i = 0; i < barCount; i++) {
          const x = 30 + i * barWidth;
          const sine = Math.sin(i * 0.32 + waveOffset);
          const isStressed = i % 6 === 2 || i % 6 === 3;
          const barHeight = isStressed ? Math.max(16, Math.abs(sine) * 75 + 25) : Math.max(8, Math.abs(sine) * 35 + 8);

          ctx.fillStyle = isStressed ? '#38bdf8' : i % 2 === 0 ? '#818cf8' : '#334155';
          ctx.roundRect(x, centerY - barHeight / 2, barWidth - 4, barHeight, [3]);
          ctx.fill();

          if (isStressed && Math.sin(pulseT) > 0) {
            ctx.fillStyle = '#38bdf8';
            ctx.beginPath();
            ctx.arc(x + (barWidth - 4) / 2, centerY - barHeight / 2 - 6, 2.5, 0, Math.PI * 2);
            ctx.fill();
          }
        }

        // Header pill
        ctx.fillStyle = 'rgba(6, 182, 212, 0.16)';
        ctx.strokeStyle = '#06b6d4';
        ctx.lineWidth = 1;
        ctx.roundRect(width / 2 - 165, 12, 330, 28, [6]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('STRESS-TIMED CADENCE • BEAT RECOGNITION', width / 2, 30);

        ctx.fillStyle = '#94a3b8';
        ctx.font = '11px Inter, sans-serif';
        ctx.fillText('Notice how content words take the primary beat while function words compress.', width / 2, height - 12);

      // 4. Workplace Matrix Primitive
      } else if (canvasType === 'matrix') {
        const pairs = (cfg.pairs as Array<{ direct: string; softened: string; tone: string }>) || [
          { direct: 'Send me the project files now.', softened: 'Could you possibly send over the project files when you have a moment?', tone: 'Polite Inquiry' },
          { direct: 'You misunderstood my proposal.', softened: 'I might not have been clear; let me clarify the main point.', tone: 'Diplomatic Pivot' }
        ];
        const activePair = pairs[activeWorkplaceIdx % pairs.length];
        const colW = (width - 40) / 2;

        // Direct
        ctx.fillStyle = 'rgba(239, 68, 68, 0.08)';
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.roundRect(14, 20, colW - 10, height - 42, [8]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#f87171';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('BLUNT / DIRECT REGISTER', 26, 44);

        ctx.fillStyle = '#ffffff';
        ctx.font = '12px Inter, sans-serif';
        ctx.fillText(`"${activePair.direct}"`, 26, 75);

        // Softened
        ctx.fillStyle = 'rgba(16, 185, 129, 0.08)';
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.roundRect(colW + 14, 20, colW - 10, height - 42, [8]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#34d399';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.fillText(`SOFTENED (${activePair.tone.toUpperCase()})`, colW + 26, 44);

        ctx.fillStyle = '#ffffff';
        ctx.font = '12px Inter, sans-serif';
        ctx.fillText(`"${activePair.softened.slice(0, 44)}..."`, colW + 26, 75);

        ctx.fillStyle = '#94a3b8';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Modal auxiliaries (could, would) and past frames soften imperative tone.', width / 2, height - 12);

      // 5. Default: Particle Classifier
      } else {
        const colWidth = (width - 40) / 2;

        ctx.fillStyle = 'rgba(59, 130, 246, 0.08)';
        ctx.strokeStyle = 'rgba(59, 130, 246, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.roundRect(14, 18, colWidth - 10, height - 36, [10]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#60a5fa';
        ctx.font = 'bold 11.5px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('COUNTABLE / SENSORY [Many • Few • Units]', 26, 42);

        ctx.fillStyle = 'rgba(168, 85, 247, 0.08)';
        ctx.strokeStyle = 'rgba(168, 85, 247, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.roundRect(colWidth + 14, 18, colWidth - 10, height - 36, [10]);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#c084fc';
        ctx.font = 'bold 11.5px Inter, sans-serif';
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

          const pillW = 88;
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
  }, [canvasType, activeInteractiveMode, activeWorkplaceIdx, selectedTreeNode, cfg]);

  const citations = data.citations || [
    { text: 'Collective Concord & Syntactic Inversion', source: 'Oxford Guide to English Grammar § 2.4', rule: 'Rule 12' }
  ];

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
        maxWidth: '740px',
        width: '100%',
        boxShadow: '0 12px 36px rgba(0, 0, 0, 0.45)',
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
              width: '32px',
              height: '32px',
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
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
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
              Curriculum Topic: {data.topic} • Visual Engine: {canvasType.toUpperCase()}
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
            padding: '12px 16px',
            background: 'rgba(59, 130, 246, 0.08)',
            border: '1px solid rgba(59, 130, 246, 0.25)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px'
          }}
        >
          <Volume2 size={16} color="var(--accent)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '13.5px', lineHeight: 1.55, color: 'var(--text-primary)', fontStyle: 'italic' }}>
            "{data.spoken_summary}"
          </div>
        </div>
      )}

      {/* ── Educational Lecture Paragraphs ── */}
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

      {/* ── Interactive HTML5 Canvas Visualizer ── */}
      <div
        style={{
          background: '#090d16',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          padding: '14px',
          marginBottom: '18px',
          position: 'relative'
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '10px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sparkles size={13} color="var(--accent)" />
            <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--accent)', fontWeight: 600 }}>
              Interactive Visual Primitive: {canvasType}
            </span>
          </div>

          {(canvasType === 'balance' || canvasType === 'tree') && (
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
                Unitary Concord
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
                Divided Concord
              </button>
              {canvasType === 'tree' && (
                <button
                  onClick={() => setSelectedTreeNode(selectedTreeNode === 'agreement' ? 'constituents' : 'agreement')}
                  style={{
                    background: 'rgba(56, 189, 248, 0.15)',
                    border: '1px solid rgba(56, 189, 248, 0.35)',
                    borderRadius: 'var(--radius-full)',
                    padding: '3px 10px',
                    fontSize: '11px',
                    color: '#38bdf8',
                    cursor: 'pointer'
                  }}
                >
                  {selectedTreeNode === 'agreement' ? '⇄ Concord Focus' : '🌲 Tree Focus'}
                </button>
              )}
            </div>
          )}

          {canvasType === 'matrix' && (
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
            height: '230px',
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

      {/* ── Key Syntactical Rules ── */}
      {data.key_takeaways && data.key_takeaways.length > 0 && (
        <div style={{ marginBottom: '18px' }}>
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

      {/* ── NEW: Analogy Reinterpretation Trigger Action Bar ── */}
      <div
        style={{
          marginTop: '16px',
          marginBottom: '16px',
          padding: '14px 16px',
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(6, 182, 212, 0.05) 100%)',
          border: '1px solid rgba(99, 102, 241, 0.25)',
          borderRadius: 'var(--radius-lg)',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
            <Sparkles size={14} color="var(--accent)" />
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
              Reinterpret with Alternative Pedagogical Model
            </span>
          </div>
          <span style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>
            Instant Voice & Visual Sync
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={() => handleRequestAnalogy('software')}
            disabled={reinterpretingStyle !== null}
            style={{
              flex: 1,
              minWidth: '150px',
              padding: '8px 12px',
              background: reinterpretingStyle === 'software' ? 'var(--accent)' : 'var(--surface-2)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: reinterpretingStyle === 'software' ? '#ffffff' : 'var(--text-primary)',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.15s ease'
            }}
          >
            <Code2 size={13} color={reinterpretingStyle === 'software' ? '#ffffff' : '#38bdf8'} />
            <span>{reinterpretingStyle === 'software' ? 'Re-interpreting...' : '⚡ Software Analogy'}</span>
          </button>

          <button
            onClick={() => handleRequestAnalogy('workplace')}
            disabled={reinterpretingStyle !== null}
            style={{
              flex: 1,
              minWidth: '150px',
              padding: '8px 12px',
              background: reinterpretingStyle === 'workplace' ? '#10b981' : 'var(--surface-2)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: reinterpretingStyle === 'workplace' ? '#ffffff' : 'var(--text-primary)',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.15s ease'
            }}
          >
            <Briefcase size={13} color={reinterpretingStyle === 'workplace' ? '#ffffff' : '#34d399'} />
            <span>{reinterpretingStyle === 'workplace' ? 'Re-interpreting...' : '💼 Workplace Style'}</span>
          </button>

          <button
            onClick={() => handleRequestAnalogy('everyday')}
            disabled={reinterpretingStyle !== null}
            style={{
              flex: 1,
              minWidth: '150px',
              padding: '8px 12px',
              background: reinterpretingStyle === 'everyday' ? '#f59e0b' : 'var(--surface-2)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: reinterpretingStyle === 'everyday' ? '#ffffff' : 'var(--text-primary)',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.15s ease'
            }}
          >
            <Compass size={13} color={reinterpretingStyle === 'everyday' ? '#ffffff' : '#fbbf24'} />
            <span>{reinterpretingStyle === 'everyday' ? 'Re-interpreting...' : '🌱 Everyday Intuition'}</span>
          </button>
        </div>
      </div>

      {/* ── NEW: Expandable Textbook Citation Pill ── */}
      <div style={{ marginBottom: '14px' }}>
        <button
          onClick={() => setShowCitations(!showCitations)}
          style={{
            background: 'transparent',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            color: 'var(--text-tertiary)',
            cursor: 'pointer',
            padding: '2px 0'
          }}
        >
          <BookMarked size={12} color="var(--accent)" />
          <span>Curriculum Source Citations & Textbook Alignment</span>
          {showCitations ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {showCitations && (
          <div
            style={{
              marginTop: '6px',
              padding: '8px 12px',
              background: 'var(--surface-0)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              fontSize: '11.5px',
              color: 'var(--text-secondary)'
            }}
          >
            {citations.map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', margin: '2px 0' }}>
                <span style={{ color: 'var(--accent)', fontWeight: 600 }}>•</span>
                <span>{typeof c === 'string' ? c : `${c.source}: ${c.text} (${c.rule || 'Verified'})`}</span>
              </div>
            ))}
          </div>
        )}
      </div>

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
