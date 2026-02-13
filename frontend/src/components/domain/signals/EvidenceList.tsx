import { Badge } from '@/components/ui/badge';
import {
  ExternalLink,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Newspaper,
  Ship,
  Cloud,
  Building,
  MessageCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate, formatPercentage } from '@/lib/formatters';
import type { EvidenceItem, SignalSource } from '@/types/signal';

interface EvidenceListProps {
  evidence: EvidenceItem[];
  className?: string;
}

const sourceConfig: Record<
  SignalSource,
  { icon: typeof Newspaper; color: string; bgColor: string }
> = {
  POLYMARKET: { icon: TrendingUp, color: 'text-accent', bgColor: 'bg-accent/10' },
  NEWS: { icon: Newspaper, color: 'text-info', bgColor: 'bg-info/10' },
  AIS: { icon: Ship, color: 'text-muted-foreground', bgColor: 'bg-muted' },
  RATES: { icon: TrendingUp, color: 'text-warning', bgColor: 'bg-warning/10' },
  WEATHER: { icon: Cloud, color: 'text-info', bgColor: 'bg-info/10' },
  GOVERNMENT: { icon: Building, color: 'text-warning', bgColor: 'bg-warning/10' },
  SOCIAL_MEDIA: { icon: MessageCircle, color: 'text-accent', bgColor: 'bg-accent/10' },
};

export function EvidenceList({ evidence, className }: EvidenceListProps) {
  // Sort by confidence (highest first)
  const sortedEvidence = [...evidence].sort((a, b) => b.confidence - a.confidence);

  return (
    <div aria-label="Evidence list" className={cn('space-y-3', className)}>
      {sortedEvidence.map((item, index) => (
        <EvidenceCard key={index} evidence={item} />
      ))}
    </div>
  );
}

interface EvidenceCardProps {
  evidence: EvidenceItem;
}

function EvidenceCard({ evidence }: EvidenceCardProps) {
  const config = sourceConfig[evidence.source_type];
  const Icon = config.icon;
  const isHighConfidence = evidence.confidence >= 0.8;

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className={cn('flex h-8 w-8 items-center justify-center rounded-lg', config.bgColor)}
          >
            <Icon className={cn('h-4 w-4', config.color)} />
          </div>
          <div>
            <p className="font-medium text-sm">{evidence.source_name}</p>
            <Badge variant="outline" className="text-[10px] mt-1">
              {evidence.source_type.replace('_', ' ')}
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isHighConfidence ? (
            <CheckCircle className="h-4 w-4 text-confidence-high" />
          ) : (
            <AlertCircle className="h-4 w-4 text-confidence-medium" />
          )}
          <span
            className={cn(
              'font-mono text-sm font-semibold font-tabular',
              isHighConfidence ? 'text-confidence-high' : 'text-confidence-medium',
            )}
          >
            {formatPercentage(evidence.confidence)}
          </span>
        </div>
      </div>

      {/* Data Point */}
      <p className="text-sm text-foreground leading-relaxed">{evidence.data_point}</p>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{formatDate(evidence.timestamp, { includeTime: true })}</span>

        {evidence.url && (
          <a
            href={evidence.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-accent hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            View source
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>
    </div>
  );
}

/**
 * Compact evidence summary for card views
 */
interface EvidenceSummaryProps {
  evidence: EvidenceItem[];
  maxShow?: number;
  className?: string;
}

export function EvidenceSummary({ evidence, maxShow = 3, className }: EvidenceSummaryProps) {
  const topEvidence = [...evidence].sort((a, b) => b.confidence - a.confidence).slice(0, maxShow);

  return (
    <div className={cn('space-y-2', className)}>
      {topEvidence.map((item, index) => {
        const config = sourceConfig[item.source_type];
        const Icon = config.icon;

        return (
          <div key={index} className="flex items-center gap-2 text-sm">
            <Icon className={cn('h-3.5 w-3.5 shrink-0', config.color)} />
            <span className="flex-1 truncate text-muted-foreground">
              {item.source_name}: {item.data_point}
            </span>
            <span className="font-mono text-xs font-tabular">
              {formatPercentage(item.confidence)}
            </span>
          </div>
        );
      })}

      {evidence.length > maxShow && (
        <p className="text-xs text-muted-foreground">+{evidence.length - maxShow} more sources</p>
      )}
    </div>
  );
}

export default EvidenceList;
