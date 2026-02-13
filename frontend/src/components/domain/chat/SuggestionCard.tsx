/**
 * SuggestionCard — Enterprise action card with accept/reject + reason codes.
 */

import { useState } from 'react';
import { Check, X, ChevronDown, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Suggestion } from '@/lib/api-v2';

const TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  cancel_order: { label: 'Cancel Order', color: 'text-error bg-error/10 border-error/20' },
  require_prepayment: { label: 'Require Prepayment', color: 'text-warning bg-warning/10 border-warning/20' },
  split_shipment: { label: 'Split Shipment', color: 'text-info bg-info/10 border-info/20' },
  delay_shipment: { label: 'Delay Shipment', color: 'text-warning bg-warning/10 border-warning/20' },
  increase_monitoring: { label: 'Increase Monitoring', color: 'text-action-reroute bg-action-reroute/10 border-action-reroute/20' },
  contact_customer: { label: 'Contact Customer', color: 'text-accent bg-accent/10 border-accent/20' },
};

const REASON_CODES = [
  { code: 'vip_client', label: 'VIP Client' },
  { code: 'high_margin', label: 'High Margin' },
  { code: 'low_priority', label: 'Low Priority' },
  { code: 'incorrect', label: 'Incorrect' },
  { code: 'other', label: 'Other' },
];

interface SuggestionCardProps {
  suggestion: Suggestion;
  onFeedback: (decision: 'accepted' | 'rejected', reasonCode?: string) => void;
}

export function SuggestionCard({ suggestion, onFeedback }: SuggestionCardProps) {
  const [showReasons, setShowReasons] = useState(false);
  const [decided, setDecided] = useState<string | null>(null);

  const config = TYPE_CONFIG[suggestion.type] || { label: suggestion.type, color: 'text-muted-foreground bg-muted border-border' };

  if (decided) {
    return (
      <motion.div
        initial={{ scale: 1 }}
        animate={{ scale: 0.98, opacity: 0.7 }}
        className={`rounded-xl border px-4 py-3 text-sm ${
          decided === 'accepted'
            ? 'border-success/20 bg-success/10 text-success'
            : 'border-border bg-muted/50 text-muted-foreground line-through'
        }`}
      >
        <div className="flex items-center gap-2">
          {decided === 'accepted' ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
          <span className="text-xs">{decided === 'accepted' ? 'Accepted' : 'Rejected'}</span>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border ${config.color} p-4 backdrop-blur-sm`}
    >
      <div className="flex items-start gap-3">
        <div className="h-7 w-7 rounded-lg bg-background/80 flex items-center justify-center shrink-0">
          <Zap className="h-3.5 w-3.5" />
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">
            {config.label}
          </span>
          <p className="text-sm mt-1 leading-relaxed">{suggestion.text}</p>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-current/10">
        <button
          onClick={() => { setDecided('accepted'); onFeedback('accepted'); }}
          className="flex items-center gap-1.5 rounded-lg bg-success hover:bg-success/90 text-success-foreground text-xs font-semibold px-4 py-2 transition-all hover:shadow-lg hover:shadow-success/20 active:scale-95"
        >
          <Check className="h-3.5 w-3.5" /> Accept
        </button>
        <button
          onClick={() => setShowReasons(!showReasons)}
          className="flex items-center gap-1.5 rounded-lg bg-background/80 hover:bg-background text-xs font-medium px-4 py-2 transition-all border border-current/10"
        >
          <X className="h-3.5 w-3.5" /> Reject
          <ChevronDown className={`h-3 w-3 transition-transform ${showReasons ? 'rotate-180' : ''}`} />
        </button>
      </div>

      <AnimatePresence>
        {showReasons && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="flex flex-wrap gap-1.5 mt-3 pt-2">
              {REASON_CODES.map((r) => (
                <button
                  key={r.code}
                  onClick={() => { setDecided('rejected'); onFeedback('rejected', r.code); setShowReasons(false); }}
                  className="rounded-lg border border-current/20 bg-background/50 text-xs px-3 py-1.5 hover:bg-background/80 transition-all active:scale-95"
                >
                  {r.label}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
