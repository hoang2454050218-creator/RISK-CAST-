import { AlertTriangle, Flame, Shield } from 'lucide-react';

export type EscalationPriority = 'CRITICAL' | 'HIGH' | 'NORMAL';
export type EscalationStatus = 'PENDING' | 'IN_REVIEW' | 'RESOLVED';

export interface Escalation {
  id: string;
  decision_id: string;
  title: string;
  reason: string;
  priority: EscalationPriority;
  status: EscalationStatus;
  exposure_usd: number;
  customer: string;
  created_at: string;
  sla_deadline: string;
  assigned_to?: string;
}

export const priorityConfig: Record<
  EscalationPriority,
  {
    label: string;
    badge: string;
    gradient: string;
    glow: string;
    border: string;
    icon: typeof AlertTriangle;
    accentColor: string;
    bgTint: string;
  }
> = {
  CRITICAL: {
    label: 'Critical',
    badge: 'bg-red-500/15 text-red-500 dark:text-red-400 border-red-500/40',
    gradient: 'from-red-500 via-red-500 to-rose-600',
    glow: '',
    border: 'border-red-500/30 dark:border-red-500/40',
    icon: Flame,
    accentColor: 'text-red-500 dark:text-red-400',
    bgTint: 'bg-red-500/5 dark:bg-red-500/5',
  },
  HIGH: {
    label: 'High',
    badge: 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/40',
    gradient: 'from-orange-500 via-orange-500 to-amber-500',
    glow: '',
    border: 'border-orange-500/30 dark:border-orange-500/30',
    icon: AlertTriangle,
    accentColor: 'text-orange-500 dark:text-orange-400',
    bgTint: 'bg-orange-500/5 dark:bg-orange-500/5',
  },
  NORMAL: {
    label: 'Normal',
    badge: 'bg-muted text-muted-foreground border-border',
    gradient: 'from-muted-foreground via-muted-foreground to-muted-foreground',
    glow: '',
    border: 'border-border',
    icon: Shield,
    accentColor: 'text-muted-foreground',
    bgTint: '',
  },
};

export const statusConfig: Record<
  EscalationStatus,
  { label: string; badge: string; dotColor: string }
> = {
  PENDING: {
    label: 'Pending',
    badge: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/40',
    dotColor: 'bg-amber-500',
  },
  IN_REVIEW: {
    label: 'In Review',
    badge: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/40',
    dotColor: 'bg-blue-500',
  },
  RESOLVED: {
    label: 'Resolved',
    badge: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/40',
    dotColor: 'bg-emerald-500',
  },
};
