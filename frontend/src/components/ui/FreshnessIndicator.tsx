/**
 * FreshnessIndicator — shows data freshness on every widget.
 *
 * RULE: This component MUST appear on EVERY card/widget that displays data.
 */

import React from 'react';

interface FreshnessIndicatorProps {
  lastUpdated: string | null;
  source?: string;
  className?: string;
}

function getRelativeTime(isoDate: string): string {
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${diffDay}d ago`;
}

function getStaleness(isoDate: string): 'fresh' | 'stale' | 'outdated' {
  const diffMs = Date.now() - new Date(isoDate).getTime();
  if (diffMs < 3_600_000) return 'fresh';
  if (diffMs < 86_400_000) return 'stale';
  return 'outdated';
}

const dotColors = {
  fresh: 'bg-success',
  stale: 'bg-warning',
  outdated: 'bg-error',
  none: 'bg-muted-foreground',
};

export function FreshnessIndicator({ lastUpdated, source, className = '' }: FreshnessIndicatorProps) {
  if (!lastUpdated) {
    return (
      <span className={`inline-flex items-center gap-1 text-xs text-muted-foreground ${className}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${dotColors.none}`} />
        No data
      </span>
    );
  }

  const staleness = getStaleness(lastUpdated);
  const relative = getRelativeTime(lastUpdated);

  return (
    <span className={`inline-flex items-center gap-1 text-xs text-muted-foreground ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColors[staleness]}`} />
      {relative}
      {source && <span className="text-muted-foreground">from {source}</span>}
    </span>
  );
}
