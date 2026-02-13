/**
 * MorningBriefCard — Displays today's morning brief on the dashboard.
 *
 * Bloomberg-style: compact, data-dense, priority items highlighted.
 */

import { Sun, AlertCircle, ChevronRight, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useBrief } from '@/hooks/useBrief';
import { Link } from 'react-router';

const SEVERITY_COLORS: Record<string, string> = {
  payment_risk: 'bg-error',
  payment_behavior_change: 'bg-warning',
  route_disruption: 'bg-warning',
  order_risk_composite: 'bg-info',
};

export function MorningBriefCard() {
  const { data: brief, isLoading, error } = useBrief();

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg border border-border bg-card overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-warning/10 to-warning/5 border-b border-border">
        <div className="flex items-center gap-2">
          <Sun className="h-4 w-4 text-warning" />
          <h3 className="text-sm font-semibold text-foreground">
            Morning Brief
          </h3>
        </div>
        <span className="text-[10px] text-muted-foreground font-mono">
          {new Date().toLocaleDateString('vi-VN', { weekday: 'short', day: 'numeric', month: 'short' })}
        </span>
      </div>

      {/* Content */}
      <div className="p-4">
        {isLoading && (
          <div className="flex items-center justify-center py-6 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            <span className="text-xs">Đang tạo brief...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 py-4 text-muted-foreground text-xs">
            <AlertCircle className="h-4 w-4" />
            Brief chưa sẵn sàng
          </div>
        )}

        {brief && (
          <>
            {/* Brief text — truncated */}
            <p className="text-sm text-foreground leading-relaxed line-clamp-4">
              {brief.content}
            </p>

            {/* Priority items */}
            {brief.priority_items.length > 0 && (
              <div className="mt-3 space-y-1.5">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                  Cần chú ý
                </p>
                {brief.priority_items.slice(0, 3).map((item, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs text-muted-foreground"
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                        SEVERITY_COLORS[item.signal_type] || 'bg-muted-foreground'
                      }`}
                    />
                    <span className="truncate">{item.summary}</span>
                    <span className="ml-auto shrink-0 font-mono text-[10px] text-muted-foreground">
                      {item.severity_score.toFixed(0)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Link to chat */}
            <Link
              to="/chat"
              className="flex items-center gap-1 mt-3 pt-3 border-t border-border text-xs text-accent hover:text-accent-hover transition-colors"
            >
              Hỏi thêm về brief
              <ChevronRight className="h-3 w-3" />
            </Link>
          </>
        )}
      </div>
    </motion.div>
  );
}
