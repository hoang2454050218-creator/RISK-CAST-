import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ConfidenceGauge } from '@/components/charts/ConfidenceGauge';
import { AlertTriangle, TrendingUp, TrendingDown, Minus, Info, Eye, Brain, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatPercentage } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import type {
  Q6HowConfident as Q6Data,
  ConfidenceFactor,
  CalibrationFactor,
} from '@/types/decision';

interface Q6Props {
  data: Q6Data;
  decisionId?: string;
  className?: string;
}

export function Q6Confidence({ data, decisionId, className }: Q6Props) {
  const [showReasoningTrace, setShowReasoningTrace] = useState(false);

  // Get confidence color for border
  const confidenceBorderColors = {
    HIGH: 'border-l-success',
    MEDIUM: 'border-l-warning',
    LOW: 'border-l-error',
  };

  const confidenceGlow = {
    HIGH: 'shadow-md shadow-success/10',
    MEDIUM: '',
    LOW: '',
  };

  // Close reasoning modal on Escape
  useEffect(() => {
    if (!showReasoningTrace) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowReasoningTrace(false);
    };
    window.addEventListener('keydown', handleKey);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', handleKey);
      document.body.style.overflow = '';
    };
  }, [showReasoningTrace]);

  return (
    <>
      <section aria-labelledby="q6-heading">
        <Card
          className={cn(
            'border-l-4',
            confidenceBorderColors[data.overall_confidence],
            confidenceGlow[data.overall_confidence],
            className,
          )}
        >
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-4">
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={springs.smooth}
              >
                <CardTitle
                  id="q6-heading"
                  className="text-sm font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Q6: How Confident Are We?
                </CardTitle>
              </motion.div>

              {/* Reasoning Trace Button */}
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1, ...springs.bouncy }}
              >
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowReasoningTrace(true)}
                  className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  <motion.div whileHover={{ rotate: 10 }} transition={springs.snappy}>
                    <Brain className="h-3.5 w-3.5" />
                  </motion.div>
                  <span className="hidden sm:inline">View Reasoning</span>
                </Button>
              </motion.div>
            </div>
          </CardHeader>

          <CardContent className="space-y-5">
            {/* Main Confidence Display with Gauge */}
            <motion.div
              className="flex flex-col sm:flex-row items-center gap-6"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, ...springs.smooth }}
            >
              {/* Visual Confidence Gauge */}
              <ConfidenceGauge
                score={data.confidence_score}
                level={data.overall_confidence}
                factors={data.confidence_factors}
                size="lg"
                showFactors={false}
              />

              <motion.div
                className="space-y-2 text-center sm:text-left"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <p className="text-2xl font-semibold">{data.overall_confidence} Confidence</p>
                <p className="text-sm text-muted-foreground">
                  Based on {data.confidence_factors.length} factors
                </p>
                {/* Confidence explanation summary */}
                <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] font-mono text-muted-foreground/70 mt-1">
                  {data.confidence_factors.length > 0 && (
                    <span>{data.confidence_factors.length} factor{data.confidence_factors.length !== 1 ? 's' : ''} analyzed</span>
                  )}
                  {data.calibration?.historical_accuracy != null && (
                    <span>Hist. accuracy: {Math.round(data.calibration.historical_accuracy * 100)}%</span>
                  )}
                  {data.calibration?.sample_size != null && data.calibration.sample_size > 0 && (
                    <span>n={data.calibration.sample_size}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <Eye className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    Score:{' '}
                    <span className="font-mono font-semibold font-tabular">
                      {formatPercentage(data.confidence_score)}
                    </span>
                  </span>
                </div>
              </motion.div>
            </motion.div>

            {/* Confidence Factors with Visual Bars */}
            {data.confidence_factors.length > 0 && (
              <motion.div
                className="space-y-3 pt-2 border-t"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.35 }}
              >
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Contributing Factors
                </p>

                {/* Visual Factor Breakdown from Gauge component */}
                <div className="rounded-lg bg-muted/30 p-4">
                  {/* Factor Items */}
                  <motion.div
                    className="space-y-2"
                    variants={staggerContainer}
                    initial="hidden"
                    animate="visible"
                  >
                    {data.confidence_factors.map((factor, index) => (
                      <motion.div key={index} variants={staggerItem}>
                        <ConfidenceFactorItem factor={factor} index={index} />
                      </motion.div>
                    ))}
                  </motion.div>
                </div>
              </motion.div>
            )}

            {/* Calibration Context — "Is 82% good?" */}
            {data.calibration && (
              <CalibrationContext score={data.confidence_score} calibration={data.calibration} />
            )}

            {/* Key Uncertainties */}
            {data.key_uncertainties.length > 0 && (
              <motion.div
                className="space-y-3 pt-2 border-t"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  <motion.div
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity, repeatDelay: 2 }}
                  >
                    <AlertTriangle className="h-3.5 w-3.5 text-warning" />
                  </motion.div>
                  <span>Key Uncertainties</span>
                </div>

                <motion.ul
                  className="space-y-1.5"
                  variants={staggerContainer}
                  initial="hidden"
                  animate="visible"
                >
                  {data.key_uncertainties.map((uncertainty, index) => (
                    <motion.li
                      key={index}
                      className="flex items-start gap-2 text-sm text-muted-foreground"
                      variants={staggerItem}
                    >
                      <span className="text-error mt-0.5">•</span>
                      <span>{uncertainty}</span>
                    </motion.li>
                  ))}
                </motion.ul>
              </motion.div>
            )}

            {/* What Could Change */}
            {data.what_could_change.length > 0 && (
              <motion.div
                className="space-y-3 pt-2 border-t"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
              >
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  <Info className="h-3.5 w-3.5" />
                  <span>What Could Change This</span>
                </div>

                <motion.ul
                  className="space-y-1.5"
                  variants={staggerContainer}
                  initial="hidden"
                  animate="visible"
                >
                  {data.what_could_change.map((item, index) => (
                    <motion.li
                      key={index}
                      className="flex items-start gap-2 text-sm text-muted-foreground"
                      variants={staggerItem}
                    >
                      <span className="text-accent mt-0.5">•</span>
                      <span>{item}</span>
                    </motion.li>
                  ))}
                </motion.ul>
              </motion.div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* Reasoning Trace Modal — disclaimer until connected to live engine */}
      <AnimatePresence>
        {showReasoningTrace && (
          <>
            {/* Backdrop */}
            <motion.div
              className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowReasoningTrace(false)}
              aria-hidden="true"
            />

            {/* Modal */}
            <motion.div
              className="fixed inset-4 z-50 flex items-center justify-center sm:inset-8 md:inset-12"
              role="dialog"
              aria-modal="true"
              aria-labelledby="reasoning-modal-title"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={springs.smooth}
            >
              <div className="w-full max-w-lg max-h-full overflow-hidden rounded-xl bg-card border shadow-2xl flex flex-col">
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
                      <p className="text-xs text-muted-foreground">Decision analysis breakdown</p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowReasoningTrace(false)}
                  >
                    <X className="h-4 w-4" />
                    <span className="sr-only">Close</span>
                  </Button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-5">
                  {/* Disclaimer banner */}
                  <div className="rounded-lg bg-accent/5 border border-accent/20 p-5 text-center space-y-2">
                    <Brain className="h-8 w-8 text-accent mx-auto opacity-60" />
                    <p className="text-sm font-medium">
                      Live reasoning traces available when connected to RISKCAST engine
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Full step-by-step AI decision breakdown with audit trail
                    </p>
                  </div>

                  {/* Actual confidence factors from the decision data */}
                  {data.confidence_factors.length > 0 && (
                    <div className="space-y-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Current Confidence Factors
                      </p>
                      <div className="space-y-2">
                        {data.confidence_factors.map((factor, index) => (
                          <div
                            key={index}
                            className="flex items-center justify-between text-sm rounded-lg bg-muted/30 px-3 py-2"
                          >
                            <span className="font-medium">{factor.factor}</span>
                            <span
                              className={cn(
                                'font-mono text-xs font-semibold',
                                factor.contribution === 'POSITIVE'
                                  ? 'text-success'
                                  : factor.contribution === 'NEGATIVE'
                                    ? 'text-error'
                                    : 'text-muted-foreground',
                              )}
                            >
                              {factor.weight > 0 ? '+' : ''}
                              {formatPercentage(factor.weight, { decimals: 0 })}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Key uncertainties summary */}
                  {data.key_uncertainties.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Key Uncertainties
                      </p>
                      <ul className="space-y-1">
                        {data.key_uncertainties.map((u, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2 text-xs text-muted-foreground"
                          >
                            <span className="text-warning mt-0.5">•</span>
                            <span>{u}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-4 border-t bg-muted/10">
                  <div className="text-xs text-muted-foreground">
                    Overall: {data.overall_confidence} (
                    <span className="font-mono font-semibold">
                      {formatPercentage(data.confidence_score)}
                    </span>
                    )
                  </div>
                  {decisionId && (
                    <span className="text-[10px] font-mono text-muted-foreground/60">
                      {decisionId}
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

interface ConfidenceFactorItemProps {
  factor: ConfidenceFactor;
  index: number;
}

function ConfidenceFactorItem({ factor, index }: ConfidenceFactorItemProps) {
  const contributionConfig = {
    POSITIVE: {
      icon: TrendingUp,
      color: 'text-success',
      bgColor: 'bg-success/10',
      label: 'Increases confidence',
    },
    NEGATIVE: {
      icon: TrendingDown,
      color: 'text-error',
      bgColor: 'bg-error/10',
      label: 'Decreases confidence',
    },
    NEUTRAL: {
      icon: Minus,
      color: 'text-muted-foreground',
      bgColor: 'bg-muted',
      label: 'Neutral impact',
    },
  };

  const config = contributionConfig[factor.contribution];
  const Icon = config.icon;

  return (
    <motion.div
      className={cn('rounded-lg p-3 space-y-2', config.bgColor)}
      whileHover={{ scale: 1.01, x: 2 }}
      transition={springs.snappy}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <motion.div
            initial={{ rotate: -45, opacity: 0 }}
            animate={{ rotate: 0, opacity: 1 }}
            transition={{ delay: 0.1 * index, ...springs.smooth }}
          >
            <Icon className={cn('h-4 w-4 shrink-0', config.color)} />
          </motion.div>
          <span className="font-medium text-sm">{factor.factor}</span>
        </div>
        <motion.div
          className="flex items-center gap-1"
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 * index + 0.1 }}
        >
          <span className={cn('text-xs font-mono font-tabular', config.color)}>
            {factor.weight > 0 ? '+' : ''}
            {formatPercentage(factor.weight, { decimals: 0 })}
          </span>
        </motion.div>
      </div>

      <p className="text-xs text-muted-foreground pl-6">{factor.explanation}</p>
    </motion.div>
  );
}

// ── Calibration Context ──────────────────────────────────

interface CalibrationContextProps {
  score: number;
  calibration: NonNullable<Q6Data['calibration']>;
}

function CalibrationContext({ score, calibration }: CalibrationContextProps) {
  const { historical_accuracy, sample_size, relative_performance, calibration_factors } =
    calibration;

  const bandLow = Math.floor((score * 100) / 5) * 5;
  const bandHigh = bandLow + 5;

  const perfLabel: Record<typeof relative_performance, { text: string; color: string }> = {
    above_average: { text: 'ABOVE AVERAGE', color: 'text-success' },
    average: { text: 'AVERAGE', color: 'text-muted-foreground' },
    below_average: { text: 'BELOW AVERAGE', color: 'text-warning' },
  };

  const perf = perfLabel[relative_performance];

  const positiveFactors = calibration_factors.filter((f) => f.direction === 'positive');
  const negativeFactors = calibration_factors.filter((f) => f.direction === 'negative');

  return (
    <motion.div
      className="space-y-4 pt-2 border-t"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.4 }}
    >
      {/* Section header */}
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Calibration Context
      </p>

      {/* Accuracy card */}
      <div className="rounded-lg bg-muted/30 border border-border/50 p-4 space-y-3">
        {/* Accuracy bar */}
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between text-xs">
            <span className="text-muted-foreground">
              Historical accuracy at {bandLow}–{bandHigh}% confidence
            </span>
            <span className="font-mono font-semibold text-foreground">
              {formatPercentage(historical_accuracy)}
            </span>
          </div>

          <div className="relative h-2 w-full rounded-full bg-muted overflow-hidden">
            <motion.div
              className="absolute inset-y-0 left-0 rounded-full bg-accent"
              initial={{ width: 0 }}
              animate={{ width: `${historical_accuracy * 100}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
            {/* Marker for current score */}
            <motion.div
              className="absolute top-1/2 -translate-y-1/2 w-0.5 h-3 bg-foreground rounded-full"
              style={{ left: `${score * 100}%` }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            />
          </div>
        </div>

        <p className="text-xs text-muted-foreground">
          Past decisions at {bandLow}–{bandHigh}% confidence were correct{' '}
          <span className="font-semibold text-foreground">
            {formatPercentage(historical_accuracy)}
          </span>{' '}
          of the time{' '}
          <span className="text-muted-foreground/60">
            (based on {sample_size.toLocaleString()} decisions)
          </span>
          .
        </p>

        <p className="text-xs">
          This score is <span className={cn('font-semibold', perf.color)}>{perf.text}</span> for
          reroute decisions.
        </p>
      </div>

      {/* Calibration factors — + / - list */}
      {calibration_factors.length > 0 && (
        <div className="rounded-lg bg-muted/30 border border-border/50 p-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Confidence Factors
          </p>

          <div className="space-y-1.5">
            {positiveFactors.map((f, i) => (
              <CalibrationFactorRow key={`p-${i}`} factor={f} />
            ))}
            {negativeFactors.map((f, i) => (
              <CalibrationFactorRow key={`n-${i}`} factor={f} />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

const STRENGTH_LABEL: Record<CalibrationFactor['strength'], string> = {
  strong: 'Strong',
  moderate: 'Moderate',
  weak: 'Weak',
};

function CalibrationFactorRow({ factor }: { factor: CalibrationFactor }) {
  const isPositive = factor.direction === 'positive';

  return (
    <div className="flex items-start gap-2 text-sm">
      <span
        className={cn(
          'font-mono font-bold text-xs flex-shrink-0 mt-0.5',
          isPositive ? 'text-success' : 'text-error',
        )}
      >
        {isPositive ? '+' : '\u2013'}
      </span>
      <span
        className={cn(
          'text-xs font-semibold flex-shrink-0 mt-px',
          isPositive ? 'text-success/80' : 'text-error/80',
        )}
      >
        {STRENGTH_LABEL[factor.strength]}:
      </span>
      <span className="text-xs text-muted-foreground">{factor.description}</span>
    </div>
  );
}
