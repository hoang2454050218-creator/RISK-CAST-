import { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { DecisionHeader } from './DecisionHeader';
import { ExecutiveSummary } from './ExecutiveSummary';
import { Q1WhatIsHappening } from './Q1WhatIsHappening';
import { Q2When } from './Q2When';
import { Q3HowBad } from './Q3HowBad';
import { Q4Why } from './Q4Why';
import { Q5WhatToDo } from './Q5WhatToDo';
import { Q6Confidence } from './Q6Confidence';
import { Q7IfNothing } from './Q7IfNothing';
import { ActionButtons } from './ActionButtons';
import { AuditTrailFooter } from './AuditTrailFooter';
import { cn } from '@/lib/utils';
import {
  staggerContainer,
  staggerItem,
  fadeInUp,
  springs,
  accordionContent,
  accordionIcon,
} from '@/lib/animations';
import type { Decision } from '@/types/decision';

// ── Tier system ─────────────────────────────────────────
type QuestionTier = 'primary' | 'secondary' | 'supporting';

interface QuestionDef {
  index: number;
  label: string;
  tier: QuestionTier;
}

const QUESTIONS: QuestionDef[] = [
  { index: 1, label: 'What is happening?', tier: 'primary' },
  { index: 2, label: 'When?', tier: 'supporting' },
  { index: 3, label: 'How bad?', tier: 'secondary' },
  { index: 4, label: 'Why?', tier: 'supporting' },
  { index: 5, label: 'What to do?', tier: 'primary' },
  { index: 6, label: 'Confidence?', tier: 'supporting' },
  { index: 7, label: 'If nothing?', tier: 'secondary' },
];

// ── Mini-nav pill bar ───────────────────────────────────
function QuestionNav({ activeQ, onSelect }: { activeQ: number; onSelect: (q: number) => void }) {
  return (
    <nav
      className="sticky top-0 z-20 -mx-1 mb-6 flex items-center gap-1 rounded-lg bg-background/80 backdrop-blur-md border border-border/50 p-1 overflow-x-auto scrollbar-none"
      aria-label="Jump to question"
    >
      {QUESTIONS.map(({ index, label, tier }) => (
        <button
          key={index}
          onClick={() => onSelect(index)}
          className={cn(
            'flex items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
            activeQ === index
              ? 'bg-accent text-white shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted',
            tier === 'primary' && activeQ !== index && 'font-semibold text-foreground/80',
          )}
          aria-current={activeQ === index ? 'true' : undefined}
        >
          <span className="font-mono">Q{index}</span>
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </nav>
  );
}

// ── Main view ───────────────────────────────────────────
interface SevenQuestionsViewProps {
  decision: Decision;
  onAcknowledge: () => void;
  onOverride: () => void;
  onEscalate: () => void;
  onRequestMore?: () => void;
  onBack?: () => void;
  isLoading?: boolean;
  className?: string;
}

export function SevenQuestionsView({
  decision,
  onAcknowledge,
  onOverride,
  onEscalate,
  onRequestMore,
  onBack,
  isLoading = false,
  className,
}: SevenQuestionsViewProps) {
  const q5Ref = useRef<HTMLDivElement>(null);
  const sectionRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const [activeQ, setActiveQ] = useState(1);
  const [showFullAnalysis, setShowFullAnalysis] = useState(false);

  // IntersectionObserver — track which Q section is visible
  useEffect(() => {
    const observers: IntersectionObserver[] = [];

    for (const q of QUESTIONS) {
      const el = sectionRefs.current[q.index];
      if (!el) continue;

      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) setActiveQ(q.index);
        },
        { rootMargin: '-20% 0px -60% 0px', threshold: 0 },
      );

      observer.observe(el);
      observers.push(observer);
    }

    return () => observers.forEach((o) => o.disconnect());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decision.decision_id]);

  const handleJumpToRecommendation = useCallback(() => {
    q5Ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, []);

  const handleNavSelect = useCallback((q: number) => {
    sectionRefs.current[q]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const setRef = useCallback(
    (q: number) => (el: HTMLDivElement | null) => {
      sectionRefs.current[q] = el;
      if (q === 5) (q5Ref as React.MutableRefObject<HTMLDivElement | null>).current = el;
    },
    [],
  );

  return (
    <motion.div
      className={cn('max-w-4xl mx-auto', className)}
      initial="hidden"
      animate="visible"
      variants={staggerContainer}
    >
      {/* Header with urgency and countdown */}
      <motion.div variants={fadeInUp}>
        <DecisionHeader
          decision={decision}
          showNavigation={!!onBack}
          onBack={onBack}
          className="mb-6"
        />
      </motion.div>

      {/* Executive Summary — TL;DR before the 7 questions */}
      <motion.div variants={fadeInUp} className="mb-8">
        <ExecutiveSummary decision={decision} onJumpToRecommendation={handleJumpToRecommendation} />
      </motion.div>

      {/* Q5: What to do? — always visible first (progressive disclosure) */}
      <motion.div variants={fadeInUp}>
        <div ref={setRef(5)} id="q5">
          <QuestionWrapper index={5} label="What to do?" tier="primary">
            {decision.q5_action && <Q5WhatToDo data={decision.q5_action} isRecommended />}
          </QuestionWrapper>
        </div>
      </motion.div>

      {/* Q6: Confidence — always visible */}
      <motion.div variants={fadeInUp} className="mt-6">
        <div ref={setRef(6)} id="q6">
          <QuestionWrapper index={6} label="Confidence?" tier="supporting">
            {decision.q6_confidence && <Q6Confidence data={decision.q6_confidence} decisionId={decision.decision_id} />}
          </QuestionWrapper>
        </div>
      </motion.div>

      {/* Show Full Analysis toggle */}
      <motion.div variants={fadeInUp} className="mt-6">
        <button
          onClick={() => setShowFullAnalysis((v) => !v)}
          className={cn(
            'w-full flex items-center justify-center gap-2 py-3 rounded-lg border transition-all text-sm font-medium',
            showFullAnalysis
              ? 'border-accent/30 bg-accent/5 text-accent'
              : 'border-border bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground',
          )}
        >
          <ChevronRight
            className={cn(
              'h-4 w-4 transition-transform',
              showFullAnalysis && 'rotate-90',
            )}
          />
          {showFullAnalysis ? 'Hide Full Analysis' : 'Show Full Analysis (Q1-Q4, Q7)'}
        </button>
      </motion.div>

      {/* Full Analysis — collapsible */}
      <AnimatePresence>
        {showFullAnalysis && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="overflow-hidden"
          >
            {/* Visual divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border/50" />
              </div>
              <div className="relative flex justify-center">
                <span className="bg-background px-3 text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                  Detailed Analysis
                </span>
              </div>
            </div>

            {/* Mini-nav pill bar */}
            <QuestionNav activeQ={activeQ} onSelect={handleNavSelect} />

            {/* THE REMAINING QUESTIONS */}
            <motion.div className="space-y-6 mt-4" variants={staggerContainer} initial="hidden" animate="visible">
              {/* Q1: What is happening? */}
              <div ref={setRef(1)} id="q1">
                <QuestionWrapper index={1} label="What is happening?" tier="primary">
                  {decision.q1_what && <Q1WhatIsHappening data={decision.q1_what} />}
                </QuestionWrapper>
              </div>

              {/* Q2: When? */}
              <div ref={setRef(2)} id="q2">
                <QuestionWrapper index={2} label="When?" tier="supporting">
                  {decision.q2_when && <Q2When data={decision.q2_when} />}
                </QuestionWrapper>
              </div>

              {/* Q3: How bad? */}
              <div ref={setRef(3)} id="q3">
                <QuestionWrapper index={3} label="How bad?" tier="secondary">
                  {decision.q3_severity && <Q3HowBad data={decision.q3_severity} />}
                </QuestionWrapper>
              </div>

              {/* Q4: Why? */}
              <div ref={setRef(4)} id="q4">
                <QuestionWrapper index={4} label="Why?" tier="supporting">
                  {decision.q4_why && <Q4Why data={decision.q4_why} />}
                </QuestionWrapper>
              </div>

              {/* Q7: If nothing? */}
              <div ref={setRef(7)} id="q7">
                <QuestionWrapper index={7} label="If nothing?" tier="secondary">
                  {decision.q7_inaction && <Q7IfNothing data={decision.q7_inaction} />}
                </QuestionWrapper>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Action buttons - sticky on mobile */}
      <motion.div variants={fadeInUp} className="mt-8">
        <ActionButtons
          onAcknowledge={onAcknowledge}
          onOverride={onOverride}
          onEscalate={onEscalate}
          onRequestMore={onRequestMore}
          isLoading={isLoading}
        acknowledgeLabel={`Accept: ${decision.q5_action?.recommended_action ?? 'Recommended Action'}`}
      />
    </motion.div>

      {/* Audit trail footer */}
      <motion.div variants={fadeInUp}>
        <AuditTrailFooter decision={decision} className="mt-6" />
      </motion.div>
    </motion.div>
  );
}

// ── Question wrapper with tier-based visual hierarchy ───
interface QuestionWrapperProps {
  index: number;
  label: string;
  children: React.ReactNode;
  tier: QuestionTier;
}

const TIER_STYLES: Record<QuestionTier, { wrapper: string; pill: string; pillActive: string }> = {
  primary: {
    wrapper: 'border-l-4 border-l-accent pl-1 shadow-sm',
    pill: 'bg-accent text-white shadow-lg shadow-accent/30',
    pillActive: 'bg-accent text-white',
  },
  secondary: {
    wrapper: '',
    pill: 'bg-muted text-muted-foreground',
    pillActive: 'bg-accent/80 text-white',
  },
  supporting: {
    wrapper: 'opacity-90',
    pill: 'bg-muted/60 text-muted-foreground/70',
    pillActive: 'bg-accent/60 text-white',
  },
};

function QuestionWrapper({ index, label, children, tier }: QuestionWrapperProps) {
  // Supporting tier: collapsed by default on mobile
  const [mobileExpanded, setMobileExpanded] = useState(tier !== 'supporting');
  const styles = TIER_STYLES[tier];

  return (
    <motion.div
      variants={staggerItem}
      className={cn('relative rounded-xl', styles.wrapper, tier === 'primary' && 'z-10')}
    >
      {/* Question number indicator (desktop sidebar) */}
      <motion.div
        className="absolute -left-14 top-4 hidden xl:flex items-center justify-center"
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: index * 0.1, ...springs.smooth }}
      >
        <span
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold',
            styles.pill,
          )}
        >
          Q{index}
        </span>
      </motion.div>

      {/* Primary tier glow effect */}
      {tier === 'primary' && (
        <motion.div
          className="absolute -inset-2 rounded-xl bg-gradient-to-r from-accent/5 via-purple-500/5 to-accent/5 blur-xl pointer-events-none"
          animate={{ opacity: [0.5, 0.8, 0.5] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        />
      )}

      {/* Supporting tier: mobile-only collapse toggle */}
      {tier === 'supporting' && (
        <button
          onClick={() => setMobileExpanded((v) => !v)}
          className="md:hidden w-full flex items-center justify-between rounded-lg bg-muted/30 border border-border/50 p-3 mb-1 text-left"
          aria-expanded={mobileExpanded}
        >
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold',
                styles.pill,
              )}
            >
              Q{index}
            </span>
            <span className="text-sm font-medium text-muted-foreground">{label}</span>
          </div>
          <motion.div animate={{ rotate: mobileExpanded ? 90 : 0 }} transition={springs.snappy}>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </motion.div>
        </button>
      )}

      {/* Content — on mobile, supporting tier is collapsible */}
      <div className={cn(tier === 'supporting' && !mobileExpanded && 'hidden md:block')}>
        <motion.div className="relative" whileHover={{ scale: 1.002 }} transition={springs.snappy}>
          {children}
        </motion.div>
      </div>
    </motion.div>
  );
}

/**
 * Mobile-optimized accordion view for 7 Questions
 */
interface SevenQuestionsAccordionProps {
  decision: Decision;
  onAcknowledge: () => void;
  onOverride: () => void;
  onEscalate: () => void;
  className?: string;
}

export function SevenQuestionsAccordion({
  decision,
  onAcknowledge,
  onOverride,
  onEscalate,
  className,
}: SevenQuestionsAccordionProps) {
  const [expandedQuestion, setExpandedQuestion] = useState<number | null>(5); // Start with Q5 expanded

  const questions = [
    {
      num: 1,
      title: 'What is happening?',
      component: decision.q1_what ? <Q1WhatIsHappening data={decision.q1_what} /> : null,
    },
    { num: 2, title: 'When?', component: decision.q2_when ? <Q2When data={decision.q2_when} /> : null },
    { num: 3, title: 'How bad is it?', component: decision.q3_severity ? <Q3HowBad data={decision.q3_severity} /> : null },
    { num: 4, title: 'Why?', component: decision.q4_why ? <Q4Why data={decision.q4_why} /> : null },
    {
      num: 5,
      title: 'What to do?',
      component: decision.q5_action ? <Q5WhatToDo data={decision.q5_action} isRecommended /> : null,
      isHighlighted: true,
    },
    {
      num: 6,
      title: 'Confidence?',
      component: decision.q6_confidence ? <Q6Confidence data={decision.q6_confidence} decisionId={decision.decision_id} /> : null,
    },
    { num: 7, title: 'If nothing?', component: decision.q7_inaction ? <Q7IfNothing data={decision.q7_inaction} /> : null },
  ];

  return (
    <motion.div
      className={cn('space-y-2', className)}
      initial="hidden"
      animate="visible"
      variants={staggerContainer}
    >
      {questions.map((q, index) => (
        <motion.div
          key={q.num}
          variants={staggerItem}
          className={cn(
            'rounded-xl overflow-hidden border bg-card',
            q.isHighlighted && 'ring-2 ring-accent/50 shadow-lg shadow-accent/10',
          )}
        >
          <motion.button
            onClick={() => setExpandedQuestion(expandedQuestion === q.num ? null : q.num)}
            className={cn(
              'w-full flex items-center justify-between p-4 text-left',
              'hover:bg-muted transition-colors',
            )}
            whileTap={{ scale: 0.99 }}
          >
            <div className="flex items-center gap-3">
              <motion.span
                className={cn(
                  'flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold',
                  q.isHighlighted
                    ? 'bg-accent text-white shadow-md shadow-accent/30'
                    : 'bg-accent/10 text-accent',
                )}
                whileHover={{ scale: 1.1 }}
                transition={springs.snappy}
              >
                Q{q.num}
              </motion.span>
              <span className="font-medium">{q.title}</span>
              {q.isHighlighted && (
                <span className="text-[10px] uppercase tracking-wider text-accent font-semibold bg-accent/10 px-2 py-0.5 rounded-full">
                  Recommended
                </span>
              )}
            </div>

            <motion.div
              animate={{ rotate: expandedQuestion === q.num ? 180 : 0 }}
              transition={springs.snappy}
            >
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            </motion.div>
          </motion.button>

          <AnimatePresence initial={false}>
            {expandedQuestion === q.num && (
              <motion.div
                initial="hidden"
                animate="visible"
                exit="exit"
                variants={accordionContent}
                className="overflow-hidden"
              >
                <div className="p-4 border-t bg-muted/10">{q.component}</div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      ))}

      {/* Action buttons */}
      <motion.div variants={fadeInUp} className="mt-6 pt-4">
        <ActionButtons
          onAcknowledge={onAcknowledge}
          onOverride={onOverride}
          onEscalate={onEscalate}
          acknowledgeLabel={`Accept: ${decision.q5_action?.recommended_action ?? 'Recommended Action'}`}
        />
      </motion.div>
    </motion.div>
  );
}
