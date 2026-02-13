/**
 * Demo Mode Banner — Shown when the app falls back to mock data.
 *
 * Persistent, unmissable banner that informs users they are viewing
 * simulated data. Critical for trust: operators must never make
 * real decisions on fabricated data without knowing it.
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, RefreshCw, X, Wifi } from 'lucide-react';
import { useDataSourceStatus, dataSourceStatus } from '@/lib/data-source-status';

export function DemoModeBanner() {
  const { isUsingMockData, lastRealDataAt } = useDataSourceStatus();
  const [isRetrying, setIsRetrying] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  const handleRetry = useCallback(async () => {
    setIsRetrying(true);
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      const res = await fetch('/health', { signal: controller.signal });
      clearTimeout(timeout);
      if (res.ok) {
        dataSourceStatus.setRealDataReceived();
        setIsDismissed(false);
      }
    } catch {
      // Still offline
    } finally {
      setIsRetrying(false);
    }
  }, []);

  const show = isUsingMockData && !isDismissed;

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <div className="relative flex items-center justify-center gap-3 border-b border-warning/20 bg-warning/5 px-4 py-2.5">
            {/* Animated warning icon */}
            <div className="flex items-center gap-2 text-warning">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span className="text-xs font-semibold tracking-wide uppercase">
                Demo Mode
              </span>
            </div>

            {/* Description */}
            <span className="text-xs text-warning/80">
              Live data unavailable. Displaying simulated data.
              {lastRealDataAt && (
                <span className="ml-1 text-muted-foreground">
                  Last real data: {lastRealDataAt.toLocaleTimeString()}
                </span>
              )}
            </span>

            {/* Retry button */}
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="inline-flex items-center gap-1.5 rounded-md border border-warning/20 bg-warning/10 px-2.5 py-1 text-[11px] font-medium text-warning hover:bg-warning/15 transition-colors disabled:opacity-50"
            >
              {isRetrying ? (
                <RefreshCw className="h-3 w-3 animate-spin" />
              ) : (
                <Wifi className="h-3 w-3" />
              )}
              {isRetrying ? 'Connecting...' : 'Retry'}
            </button>

            {/* Dismiss (temporarily) */}
            <button
              onClick={() => setIsDismissed(true)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-warning/40 hover:text-warning/70 transition-colors"
              aria-label="Dismiss demo mode banner"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
