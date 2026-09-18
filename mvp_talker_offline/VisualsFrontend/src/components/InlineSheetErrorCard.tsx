import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, RefreshCw, ChevronDown, ChevronUp, Terminal } from 'lucide-react';
import type { SheetErrorProps } from '../types';
import { useBuddyStore } from '../store';

interface Props {
  data: SheetErrorProps;
}

export function InlineSheetErrorCard({ data }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const { triggerLLMQuiz, triggerRevision, disputeAnswer, activeChapter } = useBuddyStore();

  const handleRetry = async () => {
    setRetrying(true);
    try {
      if (data.component_attempted === 'QuizCard') {
        await triggerLLMQuiz(activeChapter);
      } else if (data.component_attempted === 'BionicSketchNote') {
        await triggerRevision(activeChapter);
      } else if (data.component_attempted === 'ContentionResolver') {
        await disputeAnswer('Retry contention verification');
      } else {
        await triggerLLMQuiz(activeChapter);
      }
    } catch (err) {
      console.error('[InlineSheetErrorCard] Retry failed:', err);
    } finally {
      setRetrying(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      style={{
        margin: '16px 0',
        borderRadius: '16px',
        border: '1px solid rgba(239, 68, 68, 0.25)',
        background: 'linear-gradient(145deg, rgba(239, 68, 68, 0.05) 0%, rgba(20, 24, 39, 0.6) 100%)',
        backdropFilter: 'blur(12px)',
        overflow: 'hidden',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.35)',
        color: 'var(--text-primary)'
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 18px',
          borderBottom: '1px solid rgba(239, 68, 68, 0.12)',
          background: 'rgba(239, 68, 68, 0.06)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ef4444'
            }}
          >
            <AlertTriangle size={15} />
          </div>
          <div>
            <div style={{ fontSize: '13.5px', fontWeight: 600, color: '#f87171' }}>
              {data.title || 'Interactive Sheet Error'}
            </div>
            {data.component_attempted && (
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em'
                }}
              >
                Target: {data.component_attempted}
              </span>
            )}
          </div>
        </div>

        {data.req_id && (
          <div
            style={{
              fontSize: '10.5px',
              fontFamily: 'monospace',
              color: 'var(--text-tertiary)',
              background: 'rgba(0, 0, 0, 0.3)',
              padding: '2px 8px',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)'
            }}
          >
            {data.req_id}
          </div>
        )}
      </div>

      {/* Body content */}
      <div style={{ padding: '16px 18px' }}>
        <p style={{ margin: 0, fontSize: '13.5px', lineHeight: 1.55, color: 'var(--text-secondary)' }}>
          {data.message}
        </p>

        {/* Action button */}
        {data.retryable !== false && (
          <div style={{ marginTop: '14px', display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              onClick={handleRetry}
              disabled={retrying}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 14px',
                borderRadius: '8px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: '#fca5a5',
                fontSize: '12.5px',
                fontWeight: 600,
                cursor: retrying ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <RefreshCw size={13} className={retrying ? 'animate-spin' : ''} />
              {retrying ? 'Retrying Generation...' : 'Retry Sheet Generation'}
            </button>

            <button
              onClick={() => setExpanded(!expanded)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '7px 10px',
                borderRadius: '8px',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-tertiary)',
                fontSize: '12px',
                cursor: 'pointer'
              }}
            >
              <Terminal size={12} />
              <span>{expanded ? 'Hide Details' : 'View Diagnostics'}</span>
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>
        )}

        {/* Technical diagnostics accordion */}
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              style={{
                marginTop: '12px',
                padding: '10px 12px',
                borderRadius: '8px',
                background: 'rgba(0, 0, 0, 0.45)',
                border: '1px solid var(--border-subtle)',
                fontFamily: 'monospace',
                fontSize: '11.5px',
                lineHeight: 1.5,
                color: '#f87171',
                overflowX: 'auto'
              }}
            >
              <div><strong>Error Code:</strong> {data.error_code || 'GENUI_ERROR'}</div>
              {data.details && <div><strong>Trace:</strong> {data.details}</div>}
              {data.req_id && <div><strong>Req ID:</strong> {data.req_id}</div>}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
