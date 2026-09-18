import { useEffect, useRef } from 'react';
import { useBuddyStore } from '../store';
import type { GenUIEvent, TokenEvent, TranscriptEntry, QuizQuestion, ContentionProps } from '../types';

const SSE_URL = 'http://localhost:8880/api/stream';

/**
 * Connects to the backend SSE `/api/stream` endpoint.
 * Handles three event types:
 *   - `genui`       → genui_render (QuizCard, BionicSketchNote, ContentionResolver…)
 *   - `genui_token` → individual LLM output token → inline streaming card
 *   - `transcript`  → live speech transcript (user/agent)
 * Auto-reconnects with exponential backoff on disconnect.
 */
export function useSSE() {
  const retryDelay = useRef(1000);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;

      const es = new EventSource(SSE_URL);
      esRef.current = es;

      // ── Connected ──────────────────────────────────────────
      es.addEventListener('connected', () => {
        const store = useBuddyStore.getState();
        store.setSseConnected(true);
        retryDelay.current = 1000;
        console.log('[SSE] Connected to Buddy audio & grammar engine');
      });

      // ── genui_render (Inline Quiz, Inline Revision Notes, Dispute) ────
      es.addEventListener('genui', (e: MessageEvent) => {
        try {
          const evt = JSON.parse(e.data) as GenUIEvent;
          const store = useBuddyStore.getState();
          if (evt.component === 'QuizCard') {
            const questions = (evt.props?.questions as QuizQuestion[]) || [];
            const source = (evt.props?.source as 'bank' | 'llm_generated') || 'llm_generated';
            const chapter = (evt.props?.chapter as number) || store.activeChapter;
            store.pushInlineQuiz(questions, source, chapter);
          } else if (evt.component === 'BionicSketchNote') {
            const notes = (evt.props?.notes as Record<string, unknown>) || {};
            store.pushInlineNotes(notes);
          } else if (evt.component === 'ContentionResolver') {
            store.pushInlineDispute(evt.props as unknown as ContentionProps);
          }
        } catch (err) {
          console.error('[SSE] Failed to parse genui event:', err);
        }
      });

      // ── genui_token (live LLM token stream into timeline) ──────────────
      es.addEventListener('genui_token', (e: MessageEvent) => {
        try {
          const evt = JSON.parse(e.data) as TokenEvent;
          useBuddyStore.getState().appendStreamToken(evt.token, evt.role || 'llm');
        } catch { /* ignore */ }
      });

      // ── transcript (live conversational transcript) ────────────────────
      es.addEventListener('transcript', (e: MessageEvent) => {
        try {
          const entry = JSON.parse(e.data) as TranscriptEntry;
          const store = useBuddyStore.getState();
          store.appendTranscript(entry.speaker, entry.text);
        } catch { /* ignore */ }
      });

      // ── ping (keep-alive) ───────────────────────────────────
      es.addEventListener('ping', () => { /* keep-alive */ });

      es.onerror = () => {
        const store = useBuddyStore.getState();
        store.setSseConnected(false);
        es.close();
        if (!cancelled) {
          const delay = retryDelay.current;
          setTimeout(() => connect(), delay);
          retryDelay.current = Math.min(delay * 2, 30000);
        }
      };
    }

    connect();
    return () => {
      cancelled = true;
      esRef.current?.close();
      useBuddyStore.getState().setSseConnected(false);
    };
  }, []);
}
