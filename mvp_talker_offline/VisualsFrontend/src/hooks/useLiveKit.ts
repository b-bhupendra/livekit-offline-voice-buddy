import { useEffect, useRef, useState } from 'react';
import {
  Room,
  RoomEvent,
  Track,
  type RpcInvocationData
} from 'livekit-client';
import { useBuddyStore } from '../store';
import type { QuizQuestion, ContentionProps, GrammarMovementProps } from '../types';

const TOKEN_URL = 'http://localhost:8880/api/token?identity=web-user&room_name=buddy-room';

/**
 * Phase 0: Native LiveKit WebRTC Transport Hook.
 * Makes the browser a full LiveKit Room Participant:
 *  1. Mints JWT token from backend (/api/token) and joins room over WebRTC
 *  2. Routes live agent voice audio directly to WebRTC audio elements with zero host latency
 *  3. Routes browser microphone audio through room.localParticipant.setMicrophoneEnabled()
 *  4. Listens to text streams for topics: "transcript", "genui", "genui_token"
 *  5. Supports LiveKit RPC for answer evaluation and dispute resolution
 */
export function useLiveKit() {
  const roomRef = useRef<Room | null>(null);
  const [roomInstance, setRoomInstance] = useState<Room | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isVoiceActive = useBuddyStore((s) => s.isVoiceActive);

  // Sync microphone state with LiveKit local participant
  useEffect(() => {
    const room = roomRef.current;
    if (room && room.state === 'connected') {
      room.localParticipant.setMicrophoneEnabled(isVoiceActive).catch((err) => {
        console.warn('[LiveKit Mic] Failed to toggle microphone:', err);
      });
    }
  }, [isVoiceActive]);

  useEffect(() => {
    let cancelled = false;
    let room: Room | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    async function initLiveKit() {
      try {
        console.log('[LiveKit] Requesting access token from backend...');
        const res = await fetch(TOKEN_URL);
        if (!res.ok) {
          throw new Error(`Token endpoint responded with status ${res.status}`);
        }
        const tokenData = await res.json();
        if (cancelled) return;

        const livekitUrl = tokenData.url || 'ws://127.0.0.1:7880';
        console.log(`[LiveKit] Connecting to ${livekitUrl} as ${tokenData.identity}...`);

        room = new Room({
          adaptiveStream: true,
          dynacast: true,
          audioCaptureDefaults: {
            autoGainControl: true,
            echoCancellation: true,
            noiseSuppression: true,
          },
        });
        roomRef.current = room;

        // ── Remote Track Subscriptions (WebRTC Audio Playback) ────────
        room.on(RoomEvent.TrackSubscribed, (track, _publication, participant) => {
          if (track.kind === Track.Kind.Audio) {
            console.log(`[LiveKit] Subscribed to audio track from ${participant.identity}`);
            const el = track.attach();
            el.id = `livekit-audio-${participant.identity}`;
            document.body.appendChild(el);
          }
        });

        room.on(RoomEvent.TrackUnsubscribed, (track) => {
          track.detach().forEach((el) => el.remove());
        });

        // ── Text Stream Handlers ─────────────────────────────────────
        try {
          // Topic: "transcript" (conversational speech stream w/ interim updates)
          room.registerTextStreamHandler('transcript', async (reader) => {
            try {
              const raw = await reader.readAll();
              const payload = JSON.parse(raw);
              const isFinal = payload.is_final !== undefined ? payload.is_final : true;
              useBuddyStore.getState().appendTranscript(payload.speaker || 'agent', payload.text || '', isFinal);
            } catch (err) {
              console.error('[LiveKit TextStream] transcript parse error:', err);
            }
          });

          // Topic: "genui" (interactive artifact render stream)
          room.registerTextStreamHandler('genui', async (reader) => {
            try {
              const raw = await reader.readAll();
              const evt = JSON.parse(raw);
              const store = useBuddyStore.getState();

              if (evt.type === 'genui_render') {
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
                } else if (evt.component === 'GrammarMovement') {
                  store.pushInlineMovement(evt.props as unknown as GrammarMovementProps);
                } else if (evt.component === 'sheet_error') {
                  store.pushInlineSheetError(evt.props as any);
                } else if (evt.component === 'SyllabusProgressTree') {
                  if (evt.props?.new_chapter) {
                    store.setActiveChapter(evt.props.new_chapter);
                  }
                }
              }
            } catch (err) {
              console.error('[LiveKit TextStream] genui parse error:', err);
            }
          });

          // Topic: "genui_token" (live LLM typing token stream)
          room.registerTextStreamHandler('genui_token', async (reader) => {
            try {
              for await (const chunk of reader) {
                useBuddyStore.getState().appendStreamToken(chunk, 'llm');
              }
            } catch {
              const raw = await reader.readAll();
              useBuddyStore.getState().appendStreamToken(raw, 'llm');
            }
          });

          // Topic: "progress" (authoritative learner state push from backend)
          room.registerTextStreamHandler('progress', async (reader) => {
            try {
              const raw = await reader.readAll();
              const payload = JSON.parse(raw);
              useBuddyStore.getState().syncProgress(payload);
            } catch (err) {
              console.error('[LiveKit TextStream] progress parse error:', err);
            }
          });
        } catch (e) {
          console.warn('[LiveKit] registerTextStreamHandler notice:', e);
        }

        // ── Data Channel Fallback Listener ────────────────────────────
        room.on(RoomEvent.DataReceived, (payload, _participant, _kind, topic) => {
          try {
            const text = new TextDecoder().decode(payload);
            const data = JSON.parse(text);
            const store = useBuddyStore.getState();

            if (topic === 'transcript' || data.speaker) {
              const isFinal = data.is_final !== undefined ? data.is_final : true;
              store.appendTranscript(data.speaker, data.text, isFinal);
            } else if (topic === 'progress' || data.stage || (data.learner_state && data.roadmap)) {
              store.syncProgress(data);
            } else if (topic === 'genui' || data.type === 'genui_render') {
              if (data.component === 'QuizCard') {
                store.pushInlineQuiz(data.props?.questions || [], data.props?.source || 'llm_generated', data.props?.chapter || store.activeChapter);
              } else if (data.component === 'BionicSketchNote') {
                store.pushInlineNotes(data.props?.notes || {});
              } else if (data.component === 'ContentionResolver') {
                store.pushInlineDispute(data.props);
              } else if (data.component === 'GrammarMovement') {
                store.pushInlineMovement(data.props);
              } else if (data.component === 'sheet_error') {
                store.pushInlineSheetError(data.props || data);
              }
            } else if (topic === 'genui_token' || data.token) {
              store.appendStreamToken(data.token, data.role || 'llm');
            }
          } catch {
            // Ignore non-JSON raw packets
          }
        });

        // ── Client-side RPC Method Registrations ───────────────────────
        room.registerRpcMethod('renderGenUI', async (data: RpcInvocationData) => {
          try {
            const evt = JSON.parse(data.payload);
            const store = useBuddyStore.getState();
            if (evt.component === 'QuizCard') {
              store.pushInlineQuiz(evt.props?.questions || [], evt.props?.source || 'llm_generated', evt.props?.chapter || store.activeChapter);
            } else if (evt.component === 'BionicSketchNote') {
              store.pushInlineNotes(evt.props?.notes || {});
            } else if (evt.component === 'ContentionResolver') {
              store.pushInlineDispute(evt.props);
            } else if (evt.component === 'GrammarMovement') {
              store.pushInlineMovement(evt.props);
            } else if (evt.component === 'sheet_error') {
              store.pushInlineSheetError(evt.props || evt);
            }
            return JSON.stringify({ received: true });
          } catch (e) {
            return JSON.stringify({ error: String(e) });
          }
        });

        // ── Connection Lifecycle ──────────────────────────────────────
        room.on(RoomEvent.Connected, () => {
          console.log('[LiveKit] Successfully joined room as WebRTC participant!');
          setIsConnected(true);
          setRoomInstance(room);
          setError(null);
          const store = useBuddyStore.getState();
          store.setLivekitConnected(true);
          store.setLivekitRoom(room);
          store.setSseConnected(true); // Signal online status to UI
          // Hydrate syllabus and in-flight last sheet immediately via LiveKit RPC
          store.fetchSyllabus().catch((err) => {
            console.warn('[LiveKit] Initial syllabus hydration notice:', err);
          });
          store.fetchLastSheet().catch((err) => {
            console.warn('[LiveKit] Initial last sheet hydration notice:', err);
          });
        });

        room.on(RoomEvent.ParticipantConnected, (participant) => {
          const ident = participant.identity.toLowerCase();
          if (ident.includes('agent') || ident.includes('buddy') || participant.isAgent) {
            console.log(`[LiveKit] Agent participant ${participant.identity} connected. Hydrating syllabus and last sheet...`);
            useBuddyStore.getState().fetchSyllabus().catch(() => {});
            useBuddyStore.getState().fetchLastSheet().catch(() => {});
          }
        });

        room.on(RoomEvent.Disconnected, () => {
          console.warn('[LiveKit] Disconnected from room.');
          setIsConnected(false);
          setRoomInstance(null);
          const store = useBuddyStore.getState();
          store.setLivekitConnected(false);
          store.setLivekitRoom(null);
          store.setSseConnected(false);

          // Schedule reconnection retry
          if (!cancelled) {
            retryTimer = setTimeout(initLiveKit, 4000);
          }
        });

        // Connect room
        await room.connect(livekitUrl, tokenData.token);

      } catch (err) {
        console.warn('[LiveKit Transport] Connection notice:', err);
        setError(err instanceof Error ? err.message : String(err));
        setIsConnected(false);
        setRoomInstance(null);
        const store = useBuddyStore.getState();
        store.setLivekitConnected(false);
        store.setLivekitRoom(null);

        // Retry connecting
        if (!cancelled) {
          retryTimer = setTimeout(initLiveKit, 4000);
        }
      }
    }

    initLiveKit();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (room) {
        room.disconnect().catch(() => {});
      }
      setRoomInstance(null);
      useBuddyStore.getState().setLivekitConnected(false);
      useBuddyStore.getState().setLivekitRoom(null);
      // Clean up audio elements
      document.querySelectorAll('[id^="livekit-audio-"]').forEach((el) => el.remove());
    };
  }, []);

  return { isConnected, error, room: roomInstance };
}
