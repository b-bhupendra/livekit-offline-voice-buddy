import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Scale, Check, Copy, ExternalLink, BookCheck, MessageCircle } from 'lucide-react';
import type { ContentionProps } from '../types';

export const InlineDisputeCard: React.FC<{ data: ContentionProps }> = ({ data }) => {
  const [copied, setCopied] = useState(false);

  const handleCopyRecast = () => {
    if (data.recommended_recast) {
      navigator.clipboard.writeText(data.recommended_recast);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

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
          marginBottom: '14px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Scale size={15} color="var(--accent)" />
          <span
            style={{
              fontSize: '11px',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--accent)',
              fontWeight: 600
            }}
          >
            Impartial Linguistic Arbitration
          </span>
        </div>
        <span
          style={{
            fontSize: '11px',
            color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)'
          }}
        >
          RAG + Corpus Analysis
        </span>
      </div>

      {/* ── Learner's Contention ── */}
      <div
        style={{
          padding: '12px 16px',
          background: 'var(--surface-1)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          marginBottom: '16px'
        }}
      >
        <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
          Contested Claim
        </div>
        <div style={{ fontSize: '14px', fontStyle: 'italic', color: 'var(--text-primary)', lineHeight: 1.5 }}>
          "{data.user_claim}"
        </div>
      </div>

      {/* ── Verdict Summary ── */}
      <div style={{ marginBottom: '18px' }}>
        <div style={{ fontSize: '14.5px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.5, marginBottom: '6px' }}>
          Arbitration Ruling
        </div>
        <div style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          {data.verdict}
        </div>
      </div>

      {/* ── Two-Column Breakdown: Formal vs Colloquial ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          marginBottom: '16px'
        }}
      >
        {/* Formal Rule */}
        <div
          style={{
            background: 'var(--surface-1)',
            padding: '12px 14px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <BookCheck size={13} color="var(--accent)" />
            <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase' }}>
              Formal Standard
            </span>
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {data.formal_rule}
          </div>
        </div>

        {/* Colloquial Usage */}
        <div
          style={{
            background: 'var(--surface-1)',
            padding: '12px 14px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <MessageCircle size={13} color="var(--warning)" />
            <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase' }}>
              Spoken / Descriptive
            </span>
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {data.colloquial_usage}
          </div>
        </div>
      </div>

      {/* ── Web & Reference Snippets (if present) ── */}
      {data.web_search_snippets && data.web_search_snippets.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '8px', letterSpacing: '0.06em' }}>
            External Corpus & Reference Citations
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {data.web_search_snippets.map((snip, idx) => (
              <div
                key={idx}
                style={{
                  padding: '8px 12px',
                  background: 'var(--surface-1)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{snip.title}</span>
                  {snip.url && (
                    <a
                      href={snip.url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '3px', textDecoration: 'none' }}
                    >
                      <ExternalLink size={11} />
                    </a>
                  )}
                </div>
                <div style={{ color: 'var(--text-secondary)', lineHeight: 1.4 }}>{snip.snippet}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Recommended Recast ── */}
      {data.recommended_recast && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--success-soft)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px'
          }}
        >
          <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.4 }}>
            <span style={{ color: 'var(--success)', fontWeight: 600, marginRight: '8px' }}>
              Recommended Recast:
            </span>
            {data.recommended_recast}
          </div>
          <button
            onClick={handleCopyRecast}
            style={{
              background: 'transparent',
              border: 'none',
              color: copied ? 'var(--success)' : 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
              marginLeft: '12px'
            }}
            title="Copy recommended recast"
          >
            {copied ? <Check size={15} color="var(--success)" /> : <Copy size={15} />}
          </button>
        </div>
      )}
    </motion.div>
  );
};
