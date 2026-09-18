/**
 * Transport Configuration & Rollout Status
 * 
 * Establishes native LiveKit WebRTC transport as the single authoritative production transport:
 *  - Native WebRTC bidirectional audio tracks (mic publishing + speaker subscription)
 *  - Real-time WebRTC Text Streams (topics: 'transcript', 'genui', 'progress')
 *  - Native participant-to-agent RPC invocations
 *  - In-flight reconnect hydration via get_last_sheet RPC
 * 
 * Legacy Server-Sent Events (SSE) and HTTP polling bridges are formally retired and deprecated.
 */

export type TransportMode = 'webrtc' | 'sse_deprecated';

export interface TransportConfig {
  mode: TransportMode;
  isWebRTCStable: boolean;
  version: string;
  deprecatedTransports: string[];
  features: {
    audioWebRTC: boolean;
    textStreams: boolean;
    clientRpc: boolean;
    inFlightReconnect: boolean;
  };
}

export const TRANSPORT_CONFIG: TransportConfig = {
  mode: (import.meta.env.VITE_LIVEKIT_TRANSPORT_MODE || 'webrtc') as TransportMode,
  isWebRTCStable: true,
  version: '1.0.0',
  deprecatedTransports: ['sse_bridge', 'fastmcp_stdio_bridge', 'http_poll_bridge'],
  features: {
    audioWebRTC: true,
    textStreams: true,
    clientRpc: true,
    inFlightReconnect: true,
  },
};

export function getActiveTransportInfo(): string {
  return `Transport: ${TRANSPORT_CONFIG.mode.toUpperCase()} (WebRTC verified stable; legacy bridges [${TRANSPORT_CONFIG.deprecatedTransports.join(', ')}] retired)`;
}
