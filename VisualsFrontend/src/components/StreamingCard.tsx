import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

interface StreamingCardProps {
  role: string;
  content: string;
}

export const StreamingCard: React.FC<StreamingCardProps> = ({ role, content }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        margin: '16px 0',
        padding: '16px 18px',
        background: 'var(--surface-1)',
        border: '1px dashed var(--border-strong)',
        borderRadius: 'var(--radius-md)',
        maxWidth: '700px',
        width: '100%',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)'
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '10px'
        }}
      >
        <Sparkles size={14} color="var(--accent)" className="pulse-beacon" />
        <span
          style={{
            fontSize: '11px',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--accent)',
            fontWeight: 600
          }}
        >
          Synthesizing {role} Artifact
        </span>
        <span
          style={{
            fontSize: '11px',
            padding: '2px 8px',
            background: 'var(--surface-2)',
            borderRadius: 'var(--radius-full)',
            color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)'
          }}
        >
          MCP Streaming
        </span>
      </div>

      <div
        style={{
          fontSize: '13px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap'
        }}
      >
        {content}
        <span className="cursor-blink" />
      </div>
    </motion.div>
  );
};
