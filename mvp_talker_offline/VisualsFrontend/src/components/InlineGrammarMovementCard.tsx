import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRightLeft, RotateCcw, Play, BookOpen, Sparkles, CheckCircle2 } from 'lucide-react';
import type { GrammarMovementProps, GrammarRole } from '../types';

interface InlineGrammarMovementCardProps {
  data: GrammarMovementProps;
}

const ROLE_CONFIG: Record<
  GrammarRole,
  { label: string; color: string; bg: string; border: string }
> = {
  subject: {
    label: 'Subject',
    color: 'var(--role-subject, #38bdf8)',
    bg: 'var(--role-subject-soft, rgba(56, 189, 248, 0.12))',
    border: 'rgba(56, 189, 248, 0.35)',
  },
  aux: {
    label: 'Auxiliary',
    color: 'var(--role-aux, #a855f7)',
    bg: 'var(--role-aux-soft, rgba(168, 85, 247, 0.12))',
    border: 'rgba(168, 85, 247, 0.35)',
  },
  verb: {
    label: 'Verb',
    color: 'var(--role-verb, #10b981)',
    bg: 'var(--role-verb-soft, rgba(16, 185, 129, 0.12))',
    border: 'rgba(16, 185, 129, 0.35)',
  },
  object: {
    label: 'Object',
    color: 'var(--role-object, #f59e0b)',
    bg: 'var(--role-object-soft, rgba(245, 158, 11, 0.12))',
    border: 'rgba(245, 158, 11, 0.35)',
  },
  particle: {
    label: 'Particle',
    color: 'var(--role-particle, #ec4899)',
    bg: 'var(--role-particle-soft, rgba(236, 72, 153, 0.12))',
    border: 'rgba(236, 72, 153, 0.35)',
  },
  rest: {
    label: 'Adjunct',
    color: 'var(--text-secondary, #94a3b8)',
    bg: 'rgba(148, 163, 184, 0.08)',
    border: 'rgba(148, 163, 184, 0.2)',
  },
};

export const InlineGrammarMovementCard: React.FC<InlineGrammarMovementCardProps> = ({ data }) => {
  const [isTransformed, setIsTransformed] = useState(false);
  const [showExplanation, setShowExplanation] = useState(true);

  const activeTokens = isTransformed ? data.transformed_tokens : data.initial_tokens;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
      style={{
        margin: '20px 0',
        background: 'var(--surface-2, #18181b)',
        border: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.08))',
        borderRadius: 'var(--radius-lg, 16px)',
        padding: '24px',
        maxWidth: '740px',
        width: '100%',
        boxShadow: 'var(--shadow-glass, 0 8px 32px rgba(0, 0, 0, 0.37))',
        backdropFilter: 'blur(12px)',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
      }}
    >
      {/* ── Top Header Badge Bar ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '28px',
              height: '28px',
              borderRadius: '8px',
              background: 'var(--accent-gradient, linear-gradient(135deg, #6366f1, #8b5cf6))',
              color: '#fff',
            }}
          >
            <ArrowRightLeft size={16} />
          </div>
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: 'var(--accent-light, #a5b4fc)',
              }}
            >
              Syntactic Movement Engine
            </span>
            <h3
              style={{
                fontSize: '17px',
                fontWeight: 600,
                color: 'var(--text-primary, #ffffff)',
                margin: '2px 0 0 0',
              }}
            >
              {data.title}
            </h3>
          </div>
        </div>

        {data.chapter && (
          <span
            style={{
              fontSize: '12px',
              fontWeight: 600,
              padding: '4px 10px',
              borderRadius: '999px',
              background: 'rgba(99, 102, 241, 0.15)',
              color: 'var(--accent-light, #a5b4fc)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
            }}
          >
            Chapter {data.chapter}
          </span>
        )}
      </div>

      {/* ── Rule summary ── */}
      <div
        style={{
          fontSize: '13.5px',
          lineHeight: '1.5',
          color: 'var(--text-secondary, #94a3b8)',
          background: 'rgba(255, 255, 255, 0.02)',
          borderLeft: '3px solid var(--accent, #6366f1)',
          padding: '8px 14px',
          borderRadius: '0 8px 8px 0',
        }}
      >
        {data.rule}
      </div>

      {/* ── Visual Movement Stage ── */}
      <div
        style={{
          background: 'var(--surface-1, #0f172a)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          borderRadius: 'var(--radius-md, 12px)',
          padding: '24px 20px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px',
        }}
      >
        <div
          style={{
            fontSize: '11px',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: 'var(--text-tertiary, #64748b)',
            alignSelf: 'flex-start',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <Sparkles size={12} color="var(--accent-light)" />
          Current Stage: <strong style={{ color: isTransformed ? 'var(--role-verb, #10b981)' : 'var(--text-secondary, #cbd5e1)' }}>
            {isTransformed ? 'Transformed Structure' : 'Base Declarative Structure'}
          </strong>
        </div>

        {/* Tokens Container with Layout tweening */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '12px',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '76px',
            padding: '8px 0',
            width: '100%',
          }}
        >
          {activeTokens.map((token) => {
            const roleStyle = ROLE_CONFIG[token.role] || ROLE_CONFIG.rest;
            return (
              <motion.div
                key={token.id}
                layoutId={token.id}
                transition={{
                  type: 'spring',
                  stiffness: 350,
                  damping: 25,
                }}
                style={{
                  display: 'inline-flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '4px',
                  background: roleStyle.bg,
                  border: `1px solid ${roleStyle.border}`,
                  borderRadius: '10px',
                  padding: '8px 14px',
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                  cursor: 'default',
                  userSelect: 'none',
                }}
              >
                <span
                  style={{
                    fontSize: '16px',
                    fontWeight: 600,
                    color: '#ffffff',
                    letterSpacing: '0.01em',
                  }}
                >
                  {token.text}
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    color: roleStyle.color,
                  }}
                >
                  {roleStyle.label}
                </span>
              </motion.div>
            );
          })}
        </div>

        {/* Control Button Bar */}
        <div
          style={{
            display: 'flex',
            gap: '10px',
            marginTop: '8px',
          }}
        >
          <button
            onClick={() => setIsTransformed((prev) => !prev)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              background: isTransformed
                ? 'rgba(255, 255, 255, 0.08)'
                : 'var(--accent-gradient, linear-gradient(135deg, #6366f1, #8b5cf6))',
              color: '#ffffff',
              border: isTransformed ? '1px solid rgba(255, 255, 255, 0.15)' : 'none',
              borderRadius: '8px',
              padding: '8px 18px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: isTransformed ? 'none' : '0 4px 14px rgba(99, 102, 241, 0.35)',
            }}
          >
            {isTransformed ? (
              <>
                <RotateCcw size={14} /> Revert to Base
              </>
            ) : (
              <>
                <Play size={14} /> Animate Transformation
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Explanation & Citation Accordion ── */}
      {data.explanation && (
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            borderRadius: '10px',
            padding: '12px 16px',
          }}
        >
          <div
            onClick={() => setShowExplanation((prev) => !prev)}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BookOpen size={14} color="var(--accent-light, #a5b4fc)" />
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary, #cbd5e1)' }}>
                Pedagogical Breakdown
              </span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-tertiary, #64748b)' }}>
              {showExplanation ? 'Hide' : 'Show Details'}
            </span>
          </div>

          <AnimatePresence>
            {showExplanation && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                style={{ overflow: 'hidden' }}
              >
                <p
                  style={{
                    fontSize: '13px',
                    lineHeight: '1.6',
                    color: 'var(--text-secondary, #94a3b8)',
                    margin: '10px 0 6px 0',
                  }}
                >
                  {data.explanation}
                </p>
                {data.rule_citation && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '11px',
                      color: 'var(--accent-light, #a5b4fc)',
                      marginTop: '8px',
                    }}
                  >
                    <CheckCircle2 size={12} />
                    <span>Citation: {data.rule_citation}</span>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  );
};
