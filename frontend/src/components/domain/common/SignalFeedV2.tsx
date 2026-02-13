/**
 * SignalFeedV2 — Real-time signal feed powered by V2 API + SSE.
 *
 * Displays active signals sorted by severity, auto-refreshes via polling,
 * and highlights new signals from SSE notifications.
 */

import { useState, useCallback } from 'react';
import { AlertTriangle, Zap, TrendingUp, Activity, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSignalsV2, useTriggerScan } from '@/hooks/useSignalsV2';
import { useSSE, type SSEEvent } from '@/hooks/useSSE';

const TYPE_ICONS: Record<string, typeof AlertTriangle> = {
  payment_risk: TrendingUp,
  payment_behavior_change: Activity,
  route_disruption: AlertTriangle,
  order_risk_composite: Zap,
};

const TYPE_LABELS: Record<string, string> = {
  payment_risk: 'Rủi ro thanh toán',
  payment_behavior_change: 'Thay đổi hành vi',
  route_disruption: 'Gián đoạn tuyến',
  order_risk_composite: 'Rủi ro đơn hàng',
};

function severityColor(score: number): string {
  if (score >= 70) return 'text-error bg-error/10 border-error/30';
  if (score >= 40) return 'text-warning bg-warning/10 border-warning/30';
  return 'text-info bg-info/10 border-info/30';
}

export function SignalFeedV2() {
  const { data, isLoading, refetch } = useSignalsV2({ active_only: true, limit: 10 });
  const triggerScan = useTriggerScan();
  const [newSignalIds, setNewSignalIds] = useState<Set<string>>(new Set());

  // SSE: highlight new signals
  const handleSSE = useCallback((event: SSEEvent) => {
    if (event.type === 'scan_completed' || event.type === 'signal_alert') {
      refetch();
    }
  }, [refetch]);

  useSSE(handleSSE);

  const signals = data?.signals || [];

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-warning" />
          <h3 className="text-sm font-semibold text-foreground">
            Signal Feed
          </h3>
          {data && (
            <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {data.total} active
            </span>
          )}
        </div>
        <button
          onClick={() => triggerScan.mutate()}
          disabled={triggerScan.isPending}
          className="text-muted-foreground hover:text-accent transition-colors disabled:animate-spin"
          title="Quét signal"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Signals list */}
      <div className="divide-y divide-border max-h-[400px] overflow-y-auto">
        {isLoading && (
          <div className="px-4 py-8 text-center text-xs text-muted-foreground">
            Đang tải signals...
          </div>
        )}

        {!isLoading && signals.length === 0 && (
          <div className="px-4 py-8 text-center text-xs text-muted-foreground">
            Không có signal nào active
          </div>
        )}

        <AnimatePresence>
          {signals.map((signal) => {
            const Icon = TYPE_ICONS[signal.signal_type] || AlertTriangle;
            const severity = signal.severity_score || 0;
            const ctx = signal.context as Record<string, string>;

            return (
              <motion.div
                key={signal.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="px-4 py-3 hover:bg-muted transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 p-1.5 rounded-md border ${severityColor(severity)}`}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-foreground truncate">
                        {TYPE_LABELS[signal.signal_type] || signal.signal_type}
                      </span>
                      <span className="text-[10px] font-mono text-muted-foreground shrink-0">
                        sev {severity.toFixed(0)}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5 truncate">
                      {ctx.customer_name || ctx.route_name || ctx.order_number || signal.entity_type}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-[10px] font-mono text-muted-foreground">
                      conf {(signal.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
