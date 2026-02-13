import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ActionBadge } from '@/components/domain/common/ActionBadge';
import { CostDisplay } from '@/components/domain/common/CostDisplay';
import { CountdownTimer } from '@/components/domain/common/CountdownTimer';
import {
  Sparkles,
  Scale,
  ListChecks,
  AlertTriangle,
  Info,
  ChevronDown,
  TrendingUp,
  TrendingDown,
  Minus,
  BarChart3,
  Check,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/formatters';
import type { Q5WhatToDoNow as Q5Data, AlternativeAction } from '@/types/decision';

interface Q5Props {
  data: Q5Data;
  isRecommended?: boolean;
  className?: string;
}

export function Q5WhatToDo({ data, isRecommended = true, className }: Q5Props) {
  const deadline = new Date(data.deadline);
  const [showAlternatives, setShowAlternatives] = useState(false);

  return (
    <section aria-labelledby="q5-heading">
      <Card
        className={cn(
          'border-l-4 border-l-accent',
          isRecommended && 'ring-2 ring-accent/20',
          className,
        )}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2">
              <CardTitle
                id="q5-heading"
                className="text-sm font-semibold uppercase tracking-wide text-muted-foreground"
              >
                Q5: What To Do Now?
              </CardTitle>
              {isRecommended && (
                <Badge variant="secondary" className="gap-1">
                  <Sparkles className="h-3 w-3" />
                  Recommended
                </Badge>
              )}
            </div>
            <ActionBadge action={data.recommended_action} size="lg" />
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Action Summary - The main recommendation */}
          <div className="rounded-lg bg-accent/5 border border-accent/20 p-4">
            <p className="text-lg font-semibold leading-snug text-primary">{data.action_summary}</p>
          </div>

          {/* Action Deadline */}
          <CountdownTimer deadline={deadline} label="Action deadline" size="md" />

          {/* Cost & Benefit */}
          <div className="grid gap-6 sm:grid-cols-2">
            <CostDisplay
              amount={data.estimated_cost_usd}
              confidenceInterval={data.cost_ci_90}
              label="Estimated Cost"
              size="lg"
            />

            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Expected Benefit
              </p>
              <p className="font-mono text-3xl font-semibold text-severity-low font-tabular">
                {formatCurrency(data.expected_benefit_usd)}
              </p>
              <p className="text-sm text-muted-foreground">Net savings vs. inaction</p>
            </div>
          </div>

          {/* Action Details */}
          {data.action_details && Object.keys(data.action_details).length > 0 && (
            <ActionDetailsSection details={data.action_details} />
          )}

          {/* Implementation Steps */}
          {data.implementation_steps.length > 0 && (
            <div className="space-y-3 pt-2 border-t">
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <ListChecks className="h-3.5 w-3.5" />
                <span>Implementation Steps</span>
              </div>

              <ol className="space-y-2">
                {data.implementation_steps.map((step, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/10 text-xs font-semibold text-accent">
                      {index + 1}
                    </span>
                    <span className="text-sm pt-0.5">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Alternatives with Enhanced Comparison */}
          {data.alternatives && data.alternatives.length > 0 && (
            <button
              onClick={() => setShowAlternatives(!showAlternatives)}
              className="mt-4 flex items-center gap-2 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', showAlternatives && 'rotate-180')} />
              {showAlternatives ? 'Hide' : 'Show'} {data.alternatives.length} alternative{data.alternatives.length > 1 ? 's' : ''}
            </button>
          )}
          {showAlternatives && data.alternatives && data.alternatives.length > 0 && (
            <AlternativesComparison recommended={data} alternatives={data.alternatives} />
          )}

          {/* Assumptions & Limitations - CRITICAL FOR TRUST */}
          <AssumptionsSection actionType={data.recommended_action} />
        </CardContent>
      </Card>
    </section>
  );
}

interface ActionDetailsSectionProps {
  details: Q5Data['action_details'];
}

function ActionDetailsSection({ details }: ActionDetailsSectionProps) {
  const detailItems: { label: string; value: string }[] = [];

  if (details.new_route) {
    detailItems.push({ label: 'New Route', value: details.new_route });
  }
  if (details.carrier) {
    detailItems.push({ label: 'Carrier', value: details.carrier });
  }
  if (details.vessel) {
    detailItems.push({ label: 'Vessel', value: details.vessel });
  }
  if (details.delay_days) {
    detailItems.push({ label: 'Delay Duration', value: `${details.delay_days} days` });
  }
  if (details.coverage_type) {
    detailItems.push({ label: 'Coverage Type', value: details.coverage_type });
  }
  if (details.premium_usd) {
    detailItems.push({ label: 'Premium', value: formatCurrency(details.premium_usd) });
  }
  if (details.instrument) {
    detailItems.push({ label: 'Instrument', value: details.instrument });
  }
  if (details.notional_usd) {
    detailItems.push({ label: 'Notional', value: formatCurrency(details.notional_usd) });
  }

  if (detailItems.length === 0) return null;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {detailItems.map(({ label, value }) => (
        <div key={label} className="rounded-lg bg-muted/50 p-3 space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="text-sm font-medium">{value}</p>
        </div>
      ))}
    </div>
  );
}

/**
 * AlternativesComparison - Enhanced comparison view for action alternatives
 */
interface AlternativesComparisonProps {
  recommended: Q5Data;
  alternatives: AlternativeAction[];
}

function AlternativesComparison({ recommended, alternatives }: AlternativesComparisonProps) {
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  return (
    <div className="space-y-3 pt-2 border-t">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          <Scale className="h-3.5 w-3.5" />
          <span>Alternative Options ({alternatives.length})</span>
        </div>

        {/* View Toggle */}
        <div className="flex items-center rounded-md border text-xs">
          <button
            onClick={() => setViewMode('cards')}
            className={cn(
              'px-2.5 py-1 rounded-l-md transition-colors',
              viewMode === 'cards' ? 'bg-muted' : 'hover:bg-muted',
            )}
          >
            Cards
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={cn(
              'px-2.5 py-1 rounded-r-md flex items-center gap-1 transition-colors',
              viewMode === 'table' ? 'bg-muted' : 'hover:bg-muted',
            )}
          >
            <BarChart3 className="h-3 w-3" />
            Compare
          </button>
        </div>
      </div>

      {viewMode === 'cards' ? (
        <div className="space-y-2">
          {alternatives.map((alt, index) => (
            <AlternativeActionCardEnhanced
              key={index}
              alternative={alt}
              recommendedCost={recommended.estimated_cost_usd}
              isExpanded={expandedIndex === index}
              onToggle={() => setExpandedIndex(expandedIndex === index ? null : index)}
            />
          ))}
        </div>
      ) : (
        <ComparisonTable recommended={recommended} alternatives={alternatives} />
      )}
    </div>
  );
}

/**
 * Enhanced Alternative Action Card with expandable details
 */
interface AlternativeActionCardEnhancedProps {
  alternative: AlternativeAction;
  recommendedCost: number;
  isExpanded: boolean;
  onToggle: () => void;
}

function AlternativeActionCardEnhanced({
  alternative,
  recommendedCost,
  isExpanded,
  onToggle,
}: AlternativeActionCardEnhancedProps) {
  const costDiff = alternative.cost_usd - recommendedCost;
  const isCheaper = costDiff < 0;
  const isSameCost = Math.abs(costDiff) < 100; // $100 tolerance

  return (
    <div
      className={cn(
        'rounded-lg border transition-all',
        isExpanded ? 'bg-muted/30 border-accent/30' : 'border-border hover:bg-muted/20',
      )}
    >
      <button onClick={onToggle} className="w-full p-3 text-left">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1">
            <ActionBadge action={alternative.action_type} size="sm" />
            <span className="text-sm font-medium">{alternative.summary}</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Cost comparison indicator */}
            <div className="flex items-center gap-1.5 text-sm">
              <span className="font-mono font-semibold font-tabular">
                {formatCurrency(alternative.cost_usd)}
              </span>
              {!isSameCost && (
                <span
                  className={cn(
                    'flex items-center text-xs px-1.5 py-0.5 rounded',
                    isCheaper
                      ? 'text-confidence-high bg-confidence-high/10'
                      : 'text-severity-high bg-severity-high/10',
                  )}
                >
                  {isCheaper ? (
                    <TrendingDown className="h-3 w-3 mr-0.5" />
                  ) : (
                    <TrendingUp className="h-3 w-3 mr-0.5" />
                  )}
                  {isCheaper ? '' : '+'}
                  {formatCurrency(Math.abs(costDiff), { compact: true })}
                </span>
              )}
              {isSameCost && (
                <span className="flex items-center text-xs text-muted-foreground px-1.5 py-0.5 rounded bg-muted">
                  <Minus className="h-3 w-3 mr-0.5" />
                  Same
                </span>
              )}
            </div>

            <div className={cn('transition-transform', isExpanded && 'rotate-180')}>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </div>

        <p className="text-xs text-muted-foreground mt-1.5 line-clamp-1">
          <span className="font-medium">Trade-off:</span> {alternative.trade_off}
        </p>
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-1 space-y-3 border-t">
          {/* Detailed Trade-off */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Trade-off Analysis</p>
            <p className="text-sm">{alternative.trade_off}</p>
          </div>

          {/* Pros and Cons */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-confidence-high flex items-center gap-1">
                <Check className="h-3 w-3" /> Advantages
              </p>
              <ul className="space-y-1 text-xs">
                {getAlternativeAdvantages(alternative.action_type).map((adv, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-muted-foreground">
                    <span className="text-confidence-high mt-0.5">•</span>
                    {adv}
                  </li>
                ))}
              </ul>
            </div>

            <div className="space-y-1.5">
              <p className="text-xs font-medium text-severity-high flex items-center gap-1">
                <X className="h-3 w-3" /> Disadvantages
              </p>
              <ul className="space-y-1 text-xs">
                {getAlternativeDisadvantages(alternative.action_type).map((dis, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-muted-foreground">
                    <span className="text-severity-high mt-0.5">•</span>
                    {dis}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Why Not Recommended */}
          <div className="rounded-lg bg-muted/50 p-2.5">
            <p className="text-xs font-medium text-muted-foreground mb-1">Why not recommended?</p>
            <p className="text-xs">{getWhyNotRecommended(alternative.action_type, costDiff)}</p>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Comparison Table View
 */
interface ComparisonTableProps {
  recommended: Q5Data;
  alternatives: AlternativeAction[];
}

function ComparisonTable({ recommended, alternatives }: ComparisonTableProps) {
  const allOptions = [
    {
      action_type: recommended.recommended_action,
      summary: 'Recommended Action',
      cost_usd: recommended.estimated_cost_usd,
      isRecommended: true,
    },
    ...alternatives.map((a) => ({ ...a, isRecommended: false })),
  ];

  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-3 py-2 font-medium">Option</th>
              <th className="text-right px-3 py-2 font-medium">Cost</th>
              <th className="text-center px-3 py-2 font-medium">vs Recommended</th>
              <th className="text-center px-3 py-2 font-medium">Risk Level</th>
              <th className="text-center px-3 py-2 font-medium">Complexity</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {allOptions.map((opt, index) => (
              <tr
                key={index}
                className={cn('transition-colors', opt.isRecommended && 'bg-accent/5')}
              >
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    <ActionBadge action={opt.action_type} size="sm" />
                    {opt.isRecommended && (
                      <Badge variant="secondary" className="text-xs py-0">
                        <Sparkles className="h-2.5 w-2.5 mr-0.5" />
                        Best
                      </Badge>
                    )}
                  </div>
                </td>
                <td className="px-3 py-2.5 text-right font-mono font-tabular">
                  {formatCurrency(opt.cost_usd)}
                </td>
                <td className="px-3 py-2.5 text-center">
                  {opt.isRecommended ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <CostDifferenceBadge diff={opt.cost_usd - recommended.estimated_cost_usd} />
                  )}
                </td>
                <td className="px-3 py-2.5 text-center">
                  <RiskIndicator actionType={opt.action_type} />
                </td>
                <td className="px-3 py-2.5 text-center">
                  <ComplexityIndicator actionType={opt.action_type} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CostDifferenceBadge({ diff }: { diff: number }) {
  const isCheaper = diff < 0;
  const isNeutral = Math.abs(diff) < 100;

  if (isNeutral) {
    return <span className="text-xs text-muted-foreground">~</span>;
  }

  return (
    <span
      className={cn(
        'inline-flex items-center text-xs px-1.5 py-0.5 rounded font-mono',
        isCheaper
          ? 'text-confidence-high bg-confidence-high/10'
          : 'text-severity-high bg-severity-high/10',
      )}
    >
      {isCheaper ? '' : '+'}
      {formatCurrency(diff, { compact: true })}
    </span>
  );
}

function RiskIndicator({ actionType }: { actionType: string }) {
  const riskLevels: Record<string, { level: 'low' | 'medium' | 'high'; label: string }> = {
    REROUTE: { level: 'low', label: 'Low' },
    DELAY: { level: 'medium', label: 'Med' },
    INSURE: { level: 'low', label: 'Low' },
    HEDGE: { level: 'medium', label: 'Med' },
    MONITOR: { level: 'high', label: 'High' },
    DO_NOTHING: { level: 'high', label: 'High' },
  };

  const risk = riskLevels[actionType] || { level: 'medium', label: 'Med' };

  const colors = {
    low: 'text-confidence-high bg-confidence-high/10',
    medium: 'text-confidence-medium bg-confidence-medium/10',
    high: 'text-severity-high bg-severity-high/10',
  };

  return (
    <span className={cn('text-xs px-1.5 py-0.5 rounded', colors[risk.level])}>{risk.label}</span>
  );
}

function ComplexityIndicator({ actionType }: { actionType: string }) {
  const complexity: Record<string, number> = {
    REROUTE: 3,
    DELAY: 1,
    INSURE: 2,
    HEDGE: 4,
    MONITOR: 1,
    DO_NOTHING: 0,
  };

  const level = complexity[actionType] ?? 2;

  return (
    <div className="flex items-center justify-center gap-0.5">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={cn('w-1.5 h-3 rounded-sm', i <= level ? 'bg-accent' : 'bg-muted')}
        />
      ))}
    </div>
  );
}

// Helper functions for alternative details
function getAlternativeAdvantages(actionType: string): string[] {
  const advantages: Record<string, string[]> = {
    REROUTE: [
      'Avoids disruption entirely',
      'Predictable delivery time',
      'Maintains customer commitments',
    ],
    DELAY: ['No additional cost', 'Flexible timing', 'Situation may resolve'],
    INSURE: ['Financial protection', 'Peace of mind', 'Covers worst-case scenario'],
    HEDGE: ['Market risk protection', 'Cost certainty', 'Professional execution'],
    MONITOR: ['No immediate action needed', 'Preserves options', 'Low commitment'],
    DO_NOTHING: ['Zero cost', 'No effort required', 'Risk may not materialize'],
  };
  return advantages[actionType] || ['Cost-effective option'];
}

function getAlternativeDisadvantages(actionType: string): string[] {
  const disadvantages: Record<string, string[]> = {
    REROUTE: ['Higher cost', 'Longer transit time', 'May require rebooking'],
    DELAY: ['Uncertain timeline', 'Holding costs', 'Customer impact'],
    INSURE: ['Premium cost', 'Coverage limits', 'Claims process'],
    HEDGE: ['Complexity', 'Counterparty risk', 'May not cover all losses'],
    MONITOR: ['Risk exposure continues', 'May miss action window', 'Stress/uncertainty'],
    DO_NOTHING: ['Full exposure to risk', 'Potential large losses', 'No mitigation'],
  };
  return disadvantages[actionType] || ['Limited protection'];
}

function getWhyNotRecommended(actionType: string, costDiff: number): string {
  const reasons: Record<string, string> = {
    REROUTE:
      costDiff > 0
        ? 'Higher cost outweighs benefits given current risk level'
        : 'Recommended action provides better risk-adjusted return',
    DELAY:
      'Uncertainty in timeline creates higher expected cost when factoring holding fees and customer impact',
    INSURE:
      'Premium cost reduces net benefit; direct action more cost-effective for this risk level',
    HEDGE: 'Complexity and counterparty risk not justified for this exposure level',
    MONITOR: 'Current risk level requires proactive action; waiting increases expected losses',
    DO_NOTHING: 'Expected losses significantly exceed cost of recommended action',
  };
  return reasons[actionType] || 'Does not provide optimal risk-adjusted return for this scenario';
}

/**
 * AssumptionsSection - Display assumptions and limitations
 * CRITICAL: Required by audit framework for trust building
 */
interface AssumptionsSectionProps {
  actionType: string;
}

function AssumptionsSection({ actionType }: AssumptionsSectionProps) {
  // Get assumptions based on action type
  const assumptions = getAssumptions(actionType);
  const limitations = getLimitations();

  return (
    <div className="space-y-4 pt-3 border-t">
      {/* Assumptions */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-severity-high">
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>Assumptions in this recommendation</span>
        </div>
        <ul className="space-y-1.5 rounded-lg bg-severity-high/5 border border-severity-high/20 p-3">
          {assumptions.map((assumption, index) => (
            <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
              <span className="text-severity-high mt-0.5">•</span>
              <span>{assumption}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Limitations */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          <Info className="h-3.5 w-3.5" />
          <span>Limitations</span>
        </div>
        <ul className="space-y-1.5 rounded-lg bg-muted/30 p-3">
          {limitations.map((limitation, index) => (
            <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
              <span className="text-muted-foreground mt-0.5">•</span>
              <span>{limitation}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function getAssumptions(actionType: string): string[] {
  const commonAssumptions = [
    'Customer can execute action within the specified deadline',
    'No further escalation of the current disruption',
  ];

  const actionAssumptions: Record<string, string[]> = {
    REROUTE: [
      'Carrier has available capacity on the alternative route',
      'New route does not encounter additional disruptions',
      'Booking window remains open until deadline',
      ...commonAssumptions,
    ],
    DELAY: [
      'Situation will improve within the delay period',
      'Storage facilities are available at origin port',
      'No additional holding costs beyond estimates',
      ...commonAssumptions,
    ],
    INSURE: [
      'Insurance provider will accept the application',
      'Coverage terms match expected loss scenarios',
      'Claims process will be straightforward if needed',
      ...commonAssumptions,
    ],
    MONITOR: [
      'Data sources remain available and accurate',
      'Situation does not deteriorate rapidly',
      'There is time to act if conditions change',
      ...commonAssumptions,
    ],
    DO_NOTHING: [
      'Estimated losses are within acceptable risk tolerance',
      'Situation does not worsen beyond projections',
      ...commonAssumptions,
    ],
    HEDGE: [
      'Hedging instruments are available at quoted prices',
      'Counterparty risk is acceptable',
      ...commonAssumptions,
    ],
  };

  return actionAssumptions[actionType] || commonAssumptions;
}

function getLimitations(): string[] {
  return [
    'Freight rate predictions have ±15% uncertainty',
    'AIS data may be up to 2 hours old',
    'Model performance based on historical patterns',
    'External factors may change rapidly',
  ];
}
