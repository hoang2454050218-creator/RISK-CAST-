/**
 * useSSE — Server-Sent Events hook for real-time notifications.
 *
 * Subscribes to GET /events/stream with token auth.
 * Auto-reconnects on error (EventSource built-in behavior).
 * Checks backend health before connecting to avoid spam.
 */

import { useEffect, useRef } from 'react';
import { createEventSource } from '@/lib/api-v2';
import { isBackendOnline } from '@/lib/api';

export interface SSEEvent {
  type: string;
  [key: string]: unknown;
}

export function useSSE(onEvent: (event: SSEEvent) => void) {
  const esRef = useRef<ReturnType<typeof createEventSource> | null>(null);
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  useEffect(() => {
    let cancelled = false;

    // Only connect SSE when backend is online
    isBackendOnline().then((online) => {
      if (cancelled || !online) return;

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
        // Silently handle SSE errors — backend may be offline
      };

      esRef.current = es;
    });

    return () => {
      cancelled = true;
      esRef.current?.close();
    };
  }, []);

  return esRef;
}
