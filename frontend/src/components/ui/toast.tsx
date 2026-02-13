import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toastVariants as motionVariants, springs } from '@/lib/animations';
import { create } from 'zustand';

// ============================================
// Toast Types
// ============================================

type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  onClose?: () => void;
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  updateToast: (id: string, toast: Partial<Toast>) => void;
  clearToasts: () => void;
}

// ============================================
// Toast Store
// ============================================

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],

  addToast: (toast) => {
    const id = typeof crypto !== 'undefined' && crypto.randomUUID
      ? `toast-${crypto.randomUUID()}`
      : `toast-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
    const newToast: Toast = {
      ...toast,
      id,
      duration: toast.duration ?? (toast.type === 'loading' ? Infinity : 5000),
    };

    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));

    // Auto dismiss
    if (newToast.duration !== Infinity) {
      setTimeout(() => {
        get().removeToast(id);
      }, newToast.duration);
    }

    return id;
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },

  updateToast: (id, toast) => {
    set((state) => ({
      toasts: state.toasts.map((t) => (t.id === id ? { ...t, ...toast } : t)),
    }));
  },

  clearToasts: () => {
    set({ toasts: [] });
  },
}));

// ============================================
// Toast Helpers
// ============================================

export const toast = {
  success: (title: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'title'>>) =>
    useToastStore.getState().addToast({ type: 'success', title, ...options }),

  error: (title: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'title'>>) =>
    useToastStore.getState().addToast({ type: 'error', title, ...options }),

  warning: (title: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'title'>>) =>
    useToastStore.getState().addToast({ type: 'warning', title, ...options }),

  info: (title: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'title'>>) =>
    useToastStore.getState().addToast({ type: 'info', title, ...options }),

  loading: (title: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'title'>>) =>
    useToastStore.getState().addToast({ type: 'loading', title, duration: Infinity, ...options }),

  dismiss: (id: string) => useToastStore.getState().removeToast(id),

  update: (id: string, toastUpdate: Partial<Toast>) =>
    useToastStore.getState().updateToast(id, toastUpdate),

  promise: async <T,>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: unknown) => string);
    },
  ): Promise<T> => {
    const id = toast.loading(messages.loading);

    try {
      const result = await promise;
      toast.update(id, {
        type: 'success',
        title: typeof messages.success === 'function' ? messages.success(result) : messages.success,
        duration: 5000,
      });

      // Auto dismiss after duration
      setTimeout(() => toast.dismiss(id), 5000);

      return result;
    } catch (error) {
      toast.update(id, {
        type: 'error',
        title: typeof messages.error === 'function' ? messages.error(error) : messages.error,
        duration: 5000,
      });

      setTimeout(() => toast.dismiss(id), 5000);

      throw error;
    }
  },
};

// ============================================
// useToast Hook (for component usage)
// ============================================

export function useToast() {
  return toast;
}

// ============================================
// Toast Component
// ============================================

const typeConfig = {
  success: {
    icon: CheckCircle2,
    className: 'bg-success/10 border-success/20 text-success',
    iconClassName: 'text-success',
  },
  error: {
    icon: AlertCircle,
    className: 'bg-error/10 border-error/20 text-error',
    iconClassName: 'text-error',
  },
  warning: {
    icon: AlertTriangle,
    className: 'bg-warning/10 border-warning/20 text-warning',
    iconClassName: 'text-warning',
  },
  info: {
    icon: Info,
    className: 'bg-info/10 border-info/20 text-info',
    iconClassName: 'text-info',
  },
  loading: {
    icon: Loader2,
    className: 'bg-muted border-border',
    iconClassName: 'text-muted-foreground animate-spin',
  },
};

interface ToastItemProps {
  toast: Toast;
  onClose: () => void;
}

function ToastItem({ toast: toastData, onClose }: ToastItemProps) {
  const config = typeConfig[toastData.type];
  const Icon = config.icon;
  const isUrgent = toastData.type === 'error' || toastData.type === 'warning';

  return (
    <motion.div
      layout
      role="alert"
      aria-live={isUrgent ? 'assertive' : 'polite'}
      variants={motionVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      className={cn(
        'relative flex items-start gap-3 rounded-lg border p-4 shadow-lg backdrop-blur-sm',
        'bg-card border-border',
        'min-w-[320px] max-w-[420px]',
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex h-6 w-6 shrink-0 items-center justify-center rounded-full',
          config.className,
        )}
      >
        <Icon className={cn('h-4 w-4', config.iconClassName)} />
      </div>

      {/* Content */}
      <div className="flex-1 space-y-1">
        <p className="text-sm font-medium text-foreground">{toastData.title}</p>
        {toastData.description && (
          <p className="text-sm text-muted-foreground">{toastData.description}</p>
        )}

        {/* Action button */}
        {toastData.action && (
          <button
            onClick={() => {
              toastData.action?.onClick();
              onClose();
            }}
            className="mt-2 text-sm font-medium text-accent hover:text-accent-hover transition-colors"
          >
            {toastData.action.label}
          </button>
        )}
      </div>

      {/* Close button */}
      <button
        onClick={onClose}
        aria-label="Dismiss notification"
        className="shrink-0 rounded-md p-1 hover:bg-muted transition-colors"
      >
        <X className="h-4 w-4 text-muted-foreground" />
      </button>

      {/* Progress bar for timed toasts */}
      {toastData.duration !== Infinity && toastData.type !== 'loading' && (
        <motion.div
          className={cn(
            'absolute bottom-0 left-0 h-1 rounded-b-lg',
            toastData.type === 'success' && 'bg-success',
            toastData.type === 'error' && 'bg-error',
            toastData.type === 'warning' && 'bg-warning',
            toastData.type === 'info' && 'bg-info',
          )}
          initial={{ width: '100%' }}
          animate={{ width: '0%' }}
          transition={{
            duration: (toastData.duration || 5000) / 1000,
            ease: 'linear',
          }}
        />
      )}
    </motion.div>
  );
}

// ============================================
// Toast Container
// ============================================

interface ToastContainerProps {
  position?:
    | 'top-right'
    | 'top-left'
    | 'bottom-right'
    | 'bottom-left'
    | 'top-center'
    | 'bottom-center';
  className?: string;
}

export function ToastContainer({ position = 'top-right', className }: ToastContainerProps) {
  const { toasts, removeToast } = useToastStore();

  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-center': 'top-4 left-1/2 -translate-x-1/2',
    'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
  };

  return (
    <div
      aria-live="polite"
      aria-label="Notifications"
      className={cn('fixed z-50 flex flex-col gap-2', positionClasses[position], className)}
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((t) => (
          <ToastItem
            key={t.id}
            toast={t}
            onClose={() => {
              t.onClose?.();
              removeToast(t.id);
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

// ============================================
// Standalone Toast Components
// ============================================

interface StandaloneToastProps {
  type: ToastType;
  title: string;
  description?: string;
  onClose?: () => void;
  className?: string;
}

export function ToastNotification({
  type,
  title,
  description,
  onClose,
  className,
}: StandaloneToastProps) {
  const config = typeConfig[type];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border p-4',
        'bg-card border-border shadow-md',
        className,
      )}
    >
      <div
        className={cn(
          'flex h-6 w-6 shrink-0 items-center justify-center rounded-full',
          config.className,
        )}
      >
        <Icon className={cn('h-4 w-4', config.iconClassName)} />
      </div>

      <div className="flex-1 space-y-1">
        <p className="text-sm font-medium">{title}</p>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>

      {onClose && (
        <button
          onClick={onClose}
          aria-label="Dismiss notification"
          className="shrink-0 rounded-md p-1 hover:bg-muted transition-colors"
        >
          <X className="h-4 w-4 text-muted-foreground" />
        </button>
      )}
    </div>
  );
}

// ============================================
// Toast Provider (wraps app and renders container)
// ============================================

interface ToastProviderProps {
  children: React.ReactNode;
  position?:
    | 'top-right'
    | 'top-left'
    | 'bottom-right'
    | 'bottom-left'
    | 'top-center'
    | 'bottom-center';
}

export function ToastProvider({ children, position = 'top-right' }: ToastProviderProps) {
  return (
    <>
      {children}
      <ToastContainer position={position} />
    </>
  );
}

export { type Toast, type ToastType };
