import { useEffect, useRef, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import {
  Check,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  MessageSquare,
  Clock,
  CheckCircle2,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';

interface ActionButtonsProps {
  onAcknowledge: () => void;
  onOverride: () => void;
  onEscalate: () => void;
  onRequestMore?: () => void;
  onDefer?: () => void;
  isLoading?: boolean;
  acknowledgeLabel?: string;
  className?: string;
}

export function ActionButtons({
  onAcknowledge,
  onOverride,
  onEscalate,
  onRequestMore,
  onDefer,
  isLoading = false,
  acknowledgeLabel = 'Accept Recommendation',
  className,
}: ActionButtonsProps) {
  const [flashKey, setFlashKey] = useState<string | null>(null);
  const acknowledgeRef = useRef<HTMLButtonElement>(null);
  const overrideRef = useRef<HTMLButtonElement>(null);
  const escalateRef = useRef<HTMLButtonElement>(null);

  // Brief visual flash on the button when shortcut fires
  const flashButton = useCallback((key: string) => {
    setFlashKey(key);
    setTimeout(() => setFlashKey(null), 200);
  }, []);

  // Keyboard shortcut listeners
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Guard: don't fire when typing in inputs/textareas/selects/contenteditable
      const target = e.target as HTMLElement;
      const tagName = target.tagName.toLowerCase();
      if (
        tagName === 'input' ||
        tagName === 'textarea' ||
        tagName === 'select' ||
        target.isContentEditable
      ) {
        return;
      }

      // Guard: don't fire if a modal/dialog is open
      if (document.querySelector('[role="dialog"], [role="alertdialog"]')) {
        return;
      }

      // Guard: don't fire during loading
      if (isLoading) return;

      switch (e.key) {
        case 'Enter':
          e.preventDefault();
          flashButton('acknowledge');
          onAcknowledge();
          break;
        case 'o':
        case 'O':
          e.preventDefault();
          flashButton('override');
          onOverride();
          break;
        case 'e':
        case 'E':
          e.preventDefault();
          flashButton('escalate');
          onEscalate();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isLoading, onAcknowledge, onOverride, onEscalate, flashButton]);

  return (
    <motion.div
      className={cn(
        'sticky bottom-0 z-20',
        'bg-background/80 backdrop-blur-xl',
        'border-t border-border',
        'pt-4 pb-6 -mx-6 px-6 mt-6',
        'space-y-4',
        className,
      )}
      initial="hidden"
      animate="visible"
      variants={staggerContainer}
    >
      {/* Primary Action - The main CTA */}
      <motion.div variants={staggerItem}>
        <Button
          ref={acknowledgeRef}
          onClick={onAcknowledge}
          disabled={isLoading}
          size="xl"
          variant="premium"
          className={cn(
            'w-full gap-3 h-14 text-base font-semibold relative overflow-hidden group',
            flashKey === 'acknowledge' && 'ring-2 ring-accent ring-offset-2 ring-offset-background',
          )}
          isLoading={isLoading}
          loadingText="Processing..."
        >
          {!isLoading && (
            <>
              <motion.div
                className="flex items-center gap-3"
                whileHover={{ x: 2 }}
                transition={springs.snappy}
              >
                <CheckCircle2 className="h-5 w-5" />
                <span>{acknowledgeLabel}</span>
              </motion.div>

              {/* Animated arrow */}
              <motion.div
                className="absolute right-6 opacity-0 group-hover:opacity-100"
                initial={{ x: -10, opacity: 0 }}
                whileHover={{ x: 0, opacity: 1 }}
                transition={springs.snappy}
              >
                <Zap className="h-5 w-5" />
              </motion.div>
            </>
          )}
        </Button>
      </motion.div>

      {/* Secondary Actions */}
      <motion.div className="flex gap-3" variants={staggerItem}>
        <Button
          ref={overrideRef}
          variant="outline"
          onClick={onOverride}
          disabled={isLoading}
          className={cn(
            'flex-1 gap-2 h-11',
            flashKey === 'override' && 'ring-2 ring-accent ring-offset-2 ring-offset-background',
          )}
          enableHoverAnimation
        >
          <RefreshCw className="h-4 w-4" />
          Override
        </Button>

        <Button
          ref={escalateRef}
          variant="outline"
          onClick={onEscalate}
          disabled={isLoading}
          className={cn(
            'flex-1 gap-2 h-11',
            flashKey === 'escalate' && 'ring-2 ring-accent ring-offset-2 ring-offset-background',
          )}
          enableHoverAnimation
        >
          <AlertTriangle className="h-4 w-4" />
          Escalate
        </Button>
      </motion.div>

      {/* Tertiary Actions */}
      {(onRequestMore || onDefer) && (
        <motion.div className="flex gap-2 pt-1" variants={staggerItem}>
          {onRequestMore && (
            <Button
              variant="ghost"
              onClick={onRequestMore}
              disabled={isLoading}
              size="sm"
              className="flex-1 gap-2 text-muted-foreground hover:text-foreground"
            >
              <MessageSquare className="h-4 w-4" />
              Request More Info
            </Button>
          )}

          {onDefer && (
            <Button
              variant="ghost"
              onClick={onDefer}
              disabled={isLoading}
              size="sm"
              className="flex-1 gap-2 text-muted-foreground hover:text-foreground"
            >
              <Clock className="h-4 w-4" />
              Defer Decision
            </Button>
          )}
        </motion.div>
      )}

      {/* Keyboard shortcut hint */}
      <motion.div
        className="flex justify-center gap-4 text-[10px] text-muted-foreground/60 pt-2"
        variants={staggerItem}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <span>
          <kbd className="px-1.5 py-0.5 rounded bg-muted text-[9px] mr-1">Enter</kbd>
          Accept
        </span>
        <span>
          <kbd className="px-1.5 py-0.5 rounded bg-muted text-[9px] mr-1">O</kbd>
          Override
        </span>
        <span>
          <kbd className="px-1.5 py-0.5 rounded bg-muted text-[9px] mr-1">E</kbd>
          Escalate
        </span>
      </motion.div>
    </motion.div>
  );
}

/**
 * Compact action buttons for card view
 */
interface CompactActionButtonsProps {
  onAcknowledge: () => void;
  onViewDetails: () => void;
  isLoading?: boolean;
  className?: string;
}

export function CompactActionButtons({
  onAcknowledge,
  onViewDetails,
  isLoading = false,
  className,
}: CompactActionButtonsProps) {
  return (
    <motion.div
      className={cn('flex gap-2', className)}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
    >
      <Button
        onClick={onAcknowledge}
        disabled={isLoading}
        size="sm"
        className="flex-1 gap-1.5"
        isLoading={isLoading}
      >
        {!isLoading && <Check className="h-3.5 w-3.5" />}
        Accept
      </Button>

      <Button
        variant="outline"
        onClick={onViewDetails}
        disabled={isLoading}
        size="sm"
        className="gap-1.5 group"
      >
        View Details
        <motion.div animate={{ y: [0, 2, 0] }} transition={{ duration: 1.5, repeat: Infinity }}>
          <ChevronDown className="h-3.5 w-3.5" />
        </motion.div>
      </Button>
    </motion.div>
  );
}

/**
 * Floating action button for quick actions
 */
interface FloatingActionButtonProps {
  onClick: () => void;
  icon?: React.ReactNode;
  label: string;
  variant?: 'default' | 'urgent' | 'success';
  className?: string;
}

export function FloatingActionButton({
  onClick,
  icon,
  label,
  variant = 'default',
  className,
}: FloatingActionButtonProps) {
  const variantStyles = {
    default: 'bg-accent hover:bg-accent-hover text-white shadow-lg shadow-accent/30',
    urgent:
      'bg-urgency-urgent hover:bg-urgency-urgent/90 text-white shadow-lg shadow-urgency-urgent/30',
    success: 'bg-success hover:bg-success/90 text-white shadow-lg shadow-success/30',
  };

  return (
    <motion.button
      onClick={onClick}
      className={cn(
        'fixed bottom-6 right-6 z-50',
        'flex items-center gap-2 px-6 py-3 rounded-full',
        'font-medium text-sm',
        'transition-colors',
        variantStyles[variant],
        className,
      )}
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0, opacity: 0 }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      transition={springs.bouncy}
    >
      {icon}
      {label}
    </motion.button>
  );
}
