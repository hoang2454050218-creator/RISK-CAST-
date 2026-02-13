import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import {
  X,
  Brain,
  ChevronRight,
  Database,
  Search,
  Calculator,
  CheckCircle2,
  Clock,
  ExternalLink,
  Copy,
  Check,
  Sparkles,
  GitBranch,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/formatters';
import { useToast } from '@/components/ui/toast';

export interface ReasoningStep {
  id: string;
  type: 'input' | 'retrieval' | 'analysis' | 'calculation' | 'decision' | 'output';
  title: string;
  description: string;
  details?: string;
  data?: Record<string, unknown>;
  confidence?: number;
  timestamp: string;
  duration_ms?: number;
  sources?: Array<{
    name: string;
    url?: string;
    reliability: 'high' | 'medium' | 'low';
  }>;
}

export interface ReasoningTrace {
  trace_id: string;
  decision_id: string;
  model_version: string;
  started_at: string;
  completed_at: string;
  total_duration_ms: number;
  steps: ReasoningStep[];
  final_confidence: number;
  audit_hash: string;
}

interface ReasoningTraceModalProps {
  isOpen: boolean;
  onClose: () => void;
  trace: ReasoningTrace;
}

export function ReasoningTraceModal({ isOpen, onClose, trace }: ReasoningTraceModalProps) {
  const [activeStep, setActiveStep] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const { success } = useToast();

  // Close on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      window.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      window.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  const copyTraceId = useCallback(() => {
    navigator.clipboard.writeText(trace.audit_hash);
    setCopied(true);
    success('Audit hash copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  }, [trace.audit_hash, success]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="fixed inset-4 z-50 flex items-center justify-center sm:inset-8 md:inset-12"
        role="dialog"
        aria-modal="true"
        aria-labelledby="reasoning-modal-title"
      >
        <div className="w-full max-w-4xl max-h-full overflow-hidden rounded-xl bg-card border shadow-2xl flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b bg-muted/30">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-accent/10">
                <Brain className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h2 id="reasoning-modal-title" className="text-lg font-semibold">
                  AI Reasoning Trace
                </h2>
                <p className="text-xs text-muted-foreground">
                  Full decision-making process breakdown
                </p>
              </div>
            </div>

            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
              <span className="sr-only">Close</span>
            </Button>
          </div>

          {/* Metadata Bar */}
          <div className="flex flex-wrap items-center gap-4 px-4 py-2 border-b bg-muted/10 text-xs">
            <div className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Model:</span>
              <span className="font-mono">{trace.model_version}</span>
            </div>

            <div className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Duration:</span>
              <span className="font-mono">{trace.total_duration_ms}ms</span>
            </div>

            <div className="flex items-center gap-1.5">
              <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Audit Hash:</span>
              <code className="font-mono bg-muted px-1 rounded">
                {trace.audit_hash.slice(0, 12)}...
              </code>
              <button
                onClick={copyTraceId}
                className="p-0.5 hover:bg-muted rounded"
                aria-label="Copy audit hash"
              >
                {copied ? (
                  <Check className="h-3 w-3 text-confidence-high" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {/* Timeline */}
            <div className="relative space-y-0">
              {/* Vertical line */}
              <div className="absolute left-5 top-6 bottom-6 w-0.5 bg-border" />

              {trace.steps.map((step, index) => (
                <ReasoningStepItem
                  key={step.id}
                  step={step}
                  index={index}
                  isFirst={index === 0}
                  isLast={index === trace.steps.length - 1}
                  isActive={activeStep === step.id}
                  onClick={() => setActiveStep(activeStep === step.id ? null : step.id)}
                />
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-4 border-t bg-muted/30">
            <div className="text-xs text-muted-foreground">
              Started: {formatDate(trace.started_at, { includeTime: true })}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Final Confidence:</span>
              <span
                className={cn(
                  'px-2 py-0.5 rounded font-mono text-sm font-semibold',
                  trace.final_confidence >= 0.7 && 'bg-confidence-high/10 text-confidence-high',
                  trace.final_confidence >= 0.4 &&
                    trace.final_confidence < 0.7 &&
                    'bg-confidence-medium/10 text-confidence-medium',
                  trace.final_confidence < 0.4 && 'bg-confidence-low/10 text-confidence-low',
                )}
              >
                {Math.round(trace.final_confidence * 100)}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

interface ReasoningStepItemProps {
  step: ReasoningStep;
  index: number;
  isFirst: boolean;
  isLast: boolean;
  isActive: boolean;
  onClick: () => void;
}

function ReasoningStepItem({ step, index, isActive, onClick }: ReasoningStepItemProps) {
  const stepConfig = {
    input: { icon: Database, color: 'text-blue-500', bg: 'bg-blue-500/10' },
    retrieval: { icon: Search, color: 'text-purple-500', bg: 'bg-purple-500/10' },
    analysis: { icon: Brain, color: 'text-amber-500', bg: 'bg-amber-500/10' },
    calculation: { icon: Calculator, color: 'text-green-500', bg: 'bg-green-500/10' },
    decision: { icon: CheckCircle2, color: 'text-accent', bg: 'bg-accent/10' },
    output: { icon: Sparkles, color: 'text-pink-500', bg: 'bg-pink-500/10' },
  };

  const config = stepConfig[step.type];
  const Icon = config.icon;

  return (
    <div className="relative pl-12 pb-4">
      {/* Step indicator */}
      <div
        className={cn(
          'absolute left-2.5 w-5 h-5 rounded-full flex items-center justify-center ring-4 ring-card',
          config.bg,
        )}
      >
        <Icon className={cn('h-3 w-3', config.color)} />
      </div>

      {/* Content */}
      <button
        onClick={onClick}
        className={cn(
          'w-full text-left rounded-lg border transition-colors',
          isActive ? 'bg-muted/50 border-accent/50' : 'bg-card hover:bg-muted',
        )}
      >
        <div className="p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-muted-foreground">Step {index + 1}</span>
              <span className={cn('text-xs px-1.5 py-0.5 rounded', config.bg, config.color)}>
                {step.type.toUpperCase()}
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {step.duration_ms && <span className="font-mono">{step.duration_ms}ms</span>}
              <ChevronRight
                className={cn('h-4 w-4 transition-transform', isActive && 'rotate-90')}
              />
            </div>
          </div>

          <h4 className="font-medium mt-1">{step.title}</h4>
          <p className="text-sm text-muted-foreground mt-0.5">{step.description}</p>

          {/* Expanded details */}
          {isActive && (
            <div className="mt-3 pt-3 border-t space-y-3">
              {step.details && (
                  <div className="text-sm bg-muted/50 rounded p-3">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Details</p>
                  <p className="whitespace-pre-wrap">{step.details}</p>
                </div>
              )}

              {step.data && Object.keys(step.data).length > 0 && (
                  <div className="text-sm bg-muted/50 rounded p-3">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Data</p>
                  <pre className="text-xs font-mono overflow-x-auto">
                    {JSON.stringify(step.data, null, 2)}
                  </pre>
                </div>
              )}

              {step.sources && step.sources.length > 0 && (
                <div className="text-sm">
                  <p className="text-xs font-medium text-muted-foreground mb-2">Sources</p>
                  <div className="space-y-1">
                    {step.sources.map((source, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span
                          className={cn(
                            'w-2 h-2 rounded-full',
                            source.reliability === 'high' && 'bg-confidence-high',
                            source.reliability === 'medium' && 'bg-confidence-medium',
                            source.reliability === 'low' && 'bg-confidence-low',
                          )}
                        />
                        <span>{source.name}</span>
                        {source.url && (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-accent hover:underline flex items-center gap-0.5"
                            onClick={(e) => e.stopPropagation()}
                          >
                            View <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {step.confidence !== undefined && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground">Step confidence:</span>
                  <span
                    className={cn(
                      'font-mono font-semibold',
                      step.confidence >= 0.7 && 'text-confidence-high',
                      step.confidence >= 0.4 && step.confidence < 0.7 && 'text-confidence-medium',
                      step.confidence < 0.4 && 'text-confidence-low',
                    )}
                  >
                    {Math.round(step.confidence * 100)}%
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </button>
    </div>
  );
}

// Generate mock reasoning trace for a decision
export function generateMockReasoningTrace(decisionId: string): ReasoningTrace {
  const startTime = new Date(Date.now() - 5000);

  return {
    trace_id: `trace_${Date.now()}`,
    decision_id: decisionId,
    model_version: 'RISKCAST-v2.3.1',
    started_at: startTime.toISOString(),
    completed_at: new Date().toISOString(),
    total_duration_ms: 4847,
    steps: [
      {
        id: 'step_1',
        type: 'input',
        title: 'Input Gathering',
        description: 'Collected signal data, customer profile, and market context',
        details:
          'Received Houthi attack signal from OMEN with 87% probability. Matched to customer context with 3 affected shipments.',
        data: {
          signal_id: 'sig_001',
          probability: 0.87,
          affected_shipments: 3,
          total_exposure: 235000,
        },
        timestamp: startTime.toISOString(),
        duration_ms: 156,
        sources: [
          { name: 'OMEN Signal Engine', reliability: 'high' },
          { name: 'Customer Profile DB', reliability: 'high' },
        ],
      },
      {
        id: 'step_2',
        type: 'retrieval',
        title: 'Historical Data Retrieval',
        description: 'Retrieved similar historical events and their outcomes',
        details:
          'Found 23 similar Houthi-related disruption events in the past 18 months. Analyzed reroute success rates, delay patterns, and cost impacts.',
        data: {
          historical_events: 23,
          avg_delay_days: 12,
          reroute_success_rate: 0.94,
          avg_cost_increase: 0.35,
        },
        confidence: 0.89,
        timestamp: new Date(startTime.getTime() + 156).toISOString(),
        duration_ms: 523,
        sources: [
          { name: 'Historical Event DB', reliability: 'high' },
          { name: 'Market Intelligence', reliability: 'medium' },
        ],
      },
      {
        id: 'step_3',
        type: 'analysis',
        title: 'Impact Analysis',
        description: 'Calculated exposure, delay estimates, and cost projections',
        details:
          'Using Monte Carlo simulation with 10,000 iterations to estimate cost range. Factored in current freight rates, fuel surcharges, and alternative route availability.',
        data: {
          base_exposure: 235000,
          delay_range_days: [7, 14],
          cost_increase_pct: [0.28, 0.42],
          confidence_interval: '95%',
        },
        confidence: 0.82,
        timestamp: new Date(startTime.getTime() + 679).toISOString(),
        duration_ms: 1245,
      },
      {
        id: 'step_4',
        type: 'calculation',
        title: 'Alternative Evaluation',
        description: 'Scored and ranked 4 possible actions based on cost-benefit analysis',
        details:
          'Evaluated REROUTE, DELAY, INSURE, and MONITOR options. Reroute via Cape of Good Hope emerged as optimal with highest expected value.',
        data: {
          alternatives_evaluated: 4,
          optimal_action: 'REROUTE',
          expected_savings: 42500,
          implementation_complexity: 'medium',
        },
        confidence: 0.85,
        timestamp: new Date(startTime.getTime() + 1924).toISOString(),
        duration_ms: 892,
      },
      {
        id: 'step_5',
        type: 'decision',
        title: 'Confidence Calibration',
        description: 'Aggregated all factors to determine final confidence score',
        details:
          'Weighted average of data quality (0.9), source reliability (0.85), historical accuracy (0.78), and model certainty (0.82). Applied Bayesian updating based on recent prediction performance.',
        data: {
          data_quality_score: 0.9,
          source_reliability: 0.85,
          historical_accuracy: 0.78,
          model_certainty: 0.82,
          final_confidence: 0.76,
        },
        confidence: 0.76,
        timestamp: new Date(startTime.getTime() + 2816).toISOString(),
        duration_ms: 734,
      },
      {
        id: 'step_6',
        type: 'output',
        title: 'Decision Compilation',
        description: 'Generated final decision object with all 7 questions answered',
        details:
          'Compiled decision with specific action (REROUTE via MSC), cost ($8,500), deadline (Feb 5, 6PM UTC), and inaction cost ($15,000+ after 24h).',
        timestamp: new Date(startTime.getTime() + 3550).toISOString(),
        duration_ms: 297,
      },
    ],
    final_confidence: 0.76,
    audit_hash: 'sha256:7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f',
  };
}

export default ReasoningTraceModal;
