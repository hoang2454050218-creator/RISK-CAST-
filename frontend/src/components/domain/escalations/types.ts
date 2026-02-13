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
    badge: 'bg-severity-critical/15 text-severity-critical border-severity-critical/40',
    gradient: 'from-severity-critical via-severity-critical to-severity-critical/80',
    glow: '',
    border: 'border-severity-critical/30',
    icon: Flame,
    accentColor: 'text-severity-critical',
    bgTint: 'bg-severity-critical/5',
  },
  HIGH: {
    label: 'High',
    badge: 'bg-severity-high/15 text-severity-high border-severity-high/40',
    gradient: 'from-severity-high via-severity-high to-severity-high/80',
    glow: '',
    border: 'border-severity-high/30',
    icon: AlertTriangle,
    accentColor: 'text-severity-high',
    bgTint: 'bg-severity-high/5',
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
    badge: 'bg-warning/15 text-warning border-warning/40',
    dotColor: 'bg-warning',
  },
  IN_REVIEW: {
    label: 'In Review',
    badge: 'bg-info/15 text-info border-info/40',
    dotColor: 'bg-info',
  },
  RESOLVED: {
    label: 'Resolved',
    badge: 'bg-success/15 text-success border-success/40',
    dotColor: 'bg-success',
  },
};
