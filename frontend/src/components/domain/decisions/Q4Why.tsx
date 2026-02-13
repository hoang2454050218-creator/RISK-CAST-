import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CausalChainDiagram } from '@/components/charts/CausalChainDiagram';
import { FileText, History, ChevronRight, CheckCircle, AlertCircle, Workflow } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate, formatPercentage } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import type { Q4WhyIsThisHappening as Q4Data, CausalLink, EvidenceSource } from '@/types/decision';

interface Q4Props {
  data: Q4Data;
  className?: string;
}

export function Q4Why({ data, className }: Q4Props) {
  return (
    <section aria-labelledby="q4-heading">
      <Card className={cn('border-l-4 border-l-muted-foreground/50', className)}>
        <CardHeader className="pb-3">
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={springs.smooth}
          >
            <CardTitle
              id="q4-heading"
              className="text-sm font-semibold uppercase tracking-wide text-muted-foreground"
            >
              Q4: Why Is This Happening?
            </CardTitle>
          </motion.div>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Root Cause - Main explanation */}
          <motion.div
            className="space-y-2"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, ...springs.smooth }}
          >
            <motion.p
              className="text-lg font-semibold leading-snug text-primary"
              whileHover={{ x: 2 }}
              transition={springs.snappy}
            >
              {data.root_cause}
            </motion.p>
          </motion.div>

          {/* Causal Chain VISUAL DIAGRAM - CRITICAL REQUIREMENT */}
          {data.causal_chain.length > 0 && (
            <motion.div
              className="space-y-3"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, ...springs.smooth }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <motion.div
                  animate={{ rotate: [0, 360] }}
                  transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
                >
                  <Workflow className="h-3.5 w-3.5" />
                </motion.div>
                <span>Causal Chain Diagram</span>
              </div>

              {/* Visual Flowchart Diagram */}
              <div className="rounded-lg bg-muted/30 p-4">
                <CausalChainDiagram causalChain={data.causal_chain} rootCause={data.root_cause} />
              </div>

              {/* Detailed Chain List (expandable) */}
              <details className="group">
                <summary className="flex items-center gap-2 cursor-pointer text-xs text-muted-foreground hover:text-foreground transition-colors">
                  <motion.div
                    className="transition-transform group-open:rotate-90"
                    whileHover={{ scale: 1.1 }}
                  >
                    <ChevronRight className="h-3.5 w-3.5" />
                  </motion.div>
                  <span>View detailed chain steps</span>
                </summary>
                <motion.div
                  className="mt-3 space-y-2 pl-5"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  transition={springs.smooth}
                >
                  {data.causal_chain.map((link, index) => (
                    <CausalLinkItem
                      key={index}
                      link={link}
                      isLast={index === data.causal_chain.length - 1}
                      index={index}
                    />
                  ))}
                </motion.div>
              </details>
            </motion.div>
          )}

          {/* Evidence Sources */}
          {data.evidence_sources.length > 0 && (
            <motion.div
              className="space-y-3 pt-2 border-t"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <FileText className="h-3.5 w-3.5" />
                <span>Evidence Sources ({data.evidence_sources.length})</span>
              </div>

              <motion.div
                className="space-y-2"
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {data.evidence_sources.map((source, index) => (
                  <motion.div key={index} variants={staggerItem}>
                    <EvidenceSourceItem source={source} />
                  </motion.div>
                ))}
              </motion.div>
            </motion.div>
          )}

          {/* Historical Precedent */}
          {data.historical_precedent && (
            <motion.div
              className="space-y-2 pt-2 border-t"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <History className="h-3.5 w-3.5" />
                <span>Historical Precedent</span>
              </div>
              <motion.p
                className="text-sm text-muted-foreground leading-relaxed"
                whileHover={{ x: 2 }}
                transition={springs.snappy}
              >
                {data.historical_precedent}
              </motion.p>
            </motion.div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

interface CausalLinkItemProps {
  link: CausalLink;
  isLast: boolean;
  index: number;
}

function CausalLinkItem({ link, isLast, index }: CausalLinkItemProps) {
  const confidenceColor =
    link.confidence >= 0.8
      ? 'text-success'
      : link.confidence >= 0.6
        ? 'text-warning'
        : 'text-error';

  const bgColor =
    link.confidence >= 0.8 ? 'bg-success' : link.confidence >= 0.6 ? 'bg-warning' : 'bg-error';

  return (
    <motion.div
      className="flex items-start gap-3"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.1 * index, ...springs.smooth }}
    >
      {/* Connector line */}
      <div className="flex flex-col items-center pt-2">
        <motion.div
          className={cn('h-2 w-2 rounded-full', bgColor)}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.1 * index + 0.1, ...springs.bouncy }}
        />
        {!isLast && (
          <motion.div
            className="w-0.5 h-8 bg-border mt-1"
            initial={{ scaleY: 0 }}
            animate={{ scaleY: 1 }}
            transition={{ delay: 0.1 * index + 0.2, duration: 0.3 }}
            style={{ transformOrigin: 'top' }}
          />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium">{link.from_event}</span>
          <motion.div
            animate={{ x: [0, 3, 0] }}
            transition={{ duration: 1, repeat: Infinity, repeatDelay: 2 }}
          >
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          </motion.div>
          <span className="text-sm font-medium">{link.to_event}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">{link.relationship}</span>
          <span className={cn('text-xs font-mono font-tabular', confidenceColor)}>
            ({formatPercentage(link.confidence)} confidence)
          </span>
        </div>
      </div>
    </motion.div>
  );
}

interface EvidenceSourceItemProps {
  source: EvidenceSource;
}

function EvidenceSourceItem({ source }: EvidenceSourceItemProps) {
  const isHighConfidence = source.confidence >= 0.8;

  return (
    <motion.div
      className="rounded-lg bg-muted/30 p-3 space-y-2"
      whileHover={{
        scale: 1.01,
        backgroundColor: 'rgba(var(--muted), 0.4)',
      }}
      transition={springs.snappy}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[10px]">
            {source.source_type}
          </Badge>
          <span className="text-sm font-medium">{source.source_name}</span>
        </div>
        <motion.div className="flex items-center gap-1" whileHover={{ scale: 1.05 }}>
          {isHighConfidence ? (
            <CheckCircle className="h-3.5 w-3.5 text-success" />
          ) : (
            <AlertCircle className="h-3.5 w-3.5 text-warning" />
          )}
          <span
            className={cn(
              'text-xs font-mono font-tabular',
              isHighConfidence ? 'text-success' : 'text-warning',
            )}
          >
            {formatPercentage(source.confidence)}
          </span>
        </motion.div>
      </div>

      <p className="text-sm text-muted-foreground">{source.data_point}</p>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span>{formatDate(source.timestamp, { includeTime: true })}</span>
      </div>
    </motion.div>
  );
}
