import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { BookOpen, Eye, AlertTriangle, MessageSquareQuote } from 'lucide-react';
import { bionicHtml } from '../../utils/bionic';

interface NoteRule {
  title?: string;
  body?: string;
  citation?: string;
  type?: string;
}

interface InlineNotesCardProps {
  notes: {
    title?: string;
    chapter?: number;
    overview?: string;
    rules?: NoteRule[];
    pitfalls?: string[];
    colloquial_alternatives?: string[];
    [key: string]: unknown;
  };
}

export const InlineNotesCard: React.FC<InlineNotesCardProps> = ({ notes }) => {
  const [bionicEnabled, setBionicEnabled] = useState(true);

  const title = notes.title || 'Chapter Revision & Grammar Synthesis';
  const overview = notes.overview || 'Core syntactical rules and spoken patterns synthesized for rapid review.';
  const rules = (notes.rules as NoteRule[]) || [];
  const pitfalls = (notes.pitfalls as string[]) || [];
  const colloquial = (notes.colloquial_alternatives as string[]) || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      style={{
        margin: '20px 0',
        background: 'var(--surface-2)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: '22px 24px',
        maxWidth: '700px',
        width: '100%',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.25)'
      }}
    >
      {/* ── Header Bar ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BookOpen size={15} color="var(--accent)" />
          <span
            style={{
              fontSize: '11px',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-tertiary)',
              fontWeight: 600
            }}
          >
            Artifact · Revision Notes
          </span>
          {notes.chapter && (
            <span
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                background: 'var(--surface-3)',
                borderRadius: 'var(--radius-full)',
                color: 'var(--text-secondary)'
              }}
            >
              Chapter {notes.chapter}
            </span>
          )}
        </div>

        {/* Bionic Reading Toggle */}
        <button
          onClick={() => setBionicEnabled(!bionicEnabled)}
          style={{
            background: bionicEnabled ? 'var(--accent-soft)' : 'var(--surface-1)',
            border: `1px solid ${bionicEnabled ? 'var(--accent)' : 'var(--border-subtle)'}`,
            color: bionicEnabled ? 'var(--accent)' : 'var(--text-secondary)',
            fontSize: '11.5px',
            padding: '3px 10px',
            borderRadius: 'var(--radius-full)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            fontWeight: 500,
            transition: 'all 0.15s ease'
          }}
          title="Toggle Bionic fixation bolding to accelerate reading comprehension"
        >
          <Eye size={12} />
          <span>Bionic Eye {bionicEnabled ? 'On' : 'Off'}</span>
        </button>
      </div>

      {/* ── Title & Overview ── */}
      <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
        {title}
      </div>

      <div
        style={{
          fontSize: '13.5px',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
          marginBottom: '18px'
        }}
        dangerouslySetInnerHTML={{ __html: bionicHtml(overview, bionicEnabled) }}
      />

      {/* ── Key Rules ── */}
      {rules.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '11.5px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '8px', letterSpacing: '0.06em' }}>
            Core Syntactical Rules
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {rules.map((rule, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px 14px',
                  background: 'var(--surface-1)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {rule.title}
                  </span>
                  {rule.citation && (
                    <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                      {rule.citation}
                    </span>
                  )}
                </div>
                {rule.body && (
                  <div
                    style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}
                    dangerouslySetInnerHTML={{ __html: bionicHtml(rule.body, bionicEnabled) }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Pitfalls ── */}
      {pitfalls.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '11.5px', textTransform: 'uppercase', color: 'var(--warning)', marginBottom: '8px', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <AlertTriangle size={12} />
            <span>Common Traps to Avoid</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {pitfalls.map((pitfall, idx) => (
              <div
                key={idx}
                style={{
                  padding: '8px 12px',
                  background: 'var(--warning-soft)',
                  borderLeft: '2px solid var(--warning)',
                  borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                  fontSize: '12.5px',
                  color: 'var(--text-primary)',
                  lineHeight: 1.4
                }}
                dangerouslySetInnerHTML={{ __html: bionicHtml(pitfall, bionicEnabled) }}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Colloquial Alternatives ── */}
      {colloquial.length > 0 && (
        <div>
          <div style={{ fontSize: '11.5px', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: '8px', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <MessageSquareQuote size={12} />
            <span>Natural Spoken Alternatives</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {colloquial.map((item, idx) => (
              <div
                key={idx}
                style={{
                  padding: '8px 12px',
                  background: 'var(--surface-1)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12.5px',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.4
                }}
                dangerouslySetInnerHTML={{ __html: bionicHtml(item, bionicEnabled) }}
              />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
};
