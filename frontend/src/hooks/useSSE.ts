/**
 * useSSE — Server-Sent Events hook for real-time notifications.
 *
 * Subscribes to GET /events/stream with token auth.
 * Auto-reconnects on error (EventSource built-in behavior).
 */

import { useEffect, useRef, useCallback } from 'react';
import { createEventSource } from '@/lib/api-v2';

export interface SSEEvent {
  type: string;
  [key: string]: unknown;
}

export function useSSE(onEvent: (event: SSEEvent) => void) {
  const esRef = useRef<EventSource | null>(null);
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  useEffect(() => {
    const es = createEventSource();

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        callbackRef.current(data);
      } catch {
        // Skip malformed events
      }
    };

    es.onerror = () => {
      // EventSource auto-reconnects — just log
      console.warn('SSE reconnecting...');
    };

    esRef.current = es;
    return () => es.close();
  }, []);

  return esRef;
}
