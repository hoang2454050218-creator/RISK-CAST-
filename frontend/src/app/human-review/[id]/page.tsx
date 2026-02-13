import { useParams, Link, useNavigate } from 'react-router';
import { useState, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { CompactCountdown } from '@/components/domain/common/CountdownTimer';
import { useToast } from '@/components/ui/toast';
import { useUser } from '@/contexts/user-context';
import { useEscalationDetail } from '@/hooks/useEscalationDetail';
import { ErrorState } from '@/components/ui/states';
import {
  ArrowLeft,
  Clock,
  User,
  FileText,
  CheckCircle,
  XCircle,
  MessageSquare,
  Send,
  History,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDate } from '@/lib/formatters';

type EscalationPriority = 'critical' | 'high' | 'normal';
type EscalationStatus = 'pending' | 'in_review' | 'approved' | 'rejected';

const priorityConfig: Record<
  EscalationPriority,
  { label: string; className: string; sla: string; slaHours: number }
> = {
  critical: { label: 'Critical', className: 'bg-urgency-immediate text-white', sla: '2 hours', slaHours: 2 },
  high: { label: 'High', className: 'bg-urgency-urgent text-white', sla: '24 hours', slaHours: 24 },
  normal: { label: 'Normal', className: 'bg-muted text-muted-foreground', sla: '72 hours', slaHours: 72 },
};

const statusConfig: Record<EscalationStatus, { label: string; className: string }> = {
  pending: {
    label: 'Pending',
    className: 'bg-warning/15 text-warning border border-warning/30',
  },
  in_review: {
    label: 'In Review',
    className: 'bg-info/15 text-info border border-info/30',
  },
  approved: {
    label: 'Approved',
    className:
      'bg-success/15 text-success border border-success/30',
  },
  rejected: {
    label: 'Rejected',
    className: 'bg-error/15 text-error border border-error/30',
  },
};

interface TimelineEntry {
  id: string;
  icon: 'event' | 'comment';
  user: string;
  message: string;
  timestamp: string;
}

export function EscalationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useUser();
  const [comment, setComment] = useState('');
  const [pendingAction, setPendingAction] = useState<'approve' | 'reject' | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const { success, warning } = useToast();

  const { data: escalation, isLoading, error, refetch } = useEscalationDetail(id);

  // Local state for optimistic comment / assignment updates
  const [addedComments, setAddedComments] = useState<
    Array<{ id: string; author: string; text: string; timestamp: string }>
  >([]);
  const [assignedOverride, setAssignedOverride] = useState<string | null | undefined>(undefined);

  const allComments = useMemo(
    () => [...(escalation?.comments ?? []), ...addedComments],
    [escalation?.comments, addedComments],
  );

  const assignedTo =
    assignedOverride !== undefined ? assignedOverride : (escalation?.assignedTo ?? null);

  // Merge timeline + comments into a single sorted list
  const mergedTimeline = useMemo<TimelineEntry[]>(() => {
    if (!escalation) return [];
    const entries: TimelineEntry[] = [
      ...(escalation.timeline ?? []).map((t, i) => ({
        id: `tl_${i}`,
        icon: 'event' as const,
        user: t.actor,
        message: t.action,
        timestamp: t.timestamp,
      })),
      ...allComments.map((c) => ({
        id: c.id,
        icon: 'comment' as const,
        user: c.author,
        message: c.text,
        timestamp: c.timestamp,
      })),
    ];
    return entries.sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );
  }, [escalation, allComments]);

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-6 w-48 bg-muted animate-pulse rounded" />
        <div className="h-10 w-72 bg-muted animate-pulse rounded" />
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 h-64 bg-muted animate-pulse rounded-xl" />
          <div className="h-64 bg-muted animate-pulse rounded-xl" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return <ErrorState error={error} onRetry={refetch} title="Failed to load escalation" />;
  }

  // Not found
  if (!escalation) {
    return (
      <ErrorState
        title="Escalation not found"
        description={`No escalation found with ID "${id}".`}
        onRetry={() => navigate('/human-review')}
      />
    );
  }

  const priority = priorityConfig[escalation.priority];
  const status = statusConfig[escalation.status];
  const slaDeadline = new Date(
    new Date(escalation.escalatedAt).getTime() + priority.slaHours * 3600000,
  );
  const isOverdue = slaDeadline < new Date();
  const isResolved = escalation.status === 'approved' || escalation.status === 'rejected';

  const handleAddComment = () => {
    if (comment.trim()) {
      setAddedComments((prev) => [
        ...prev,
        {
          id: `local_${Date.now()}`,
          author: user.name,
          text: comment.trim(),
          timestamp: new Date().toISOString(),
        },
      ]);
      success('Comment added successfully');
      setComment('');
    }
  };

  const handleConfirmAction = async () => {
    if (!pendingAction) return;
    const action = pendingAction;
    setIsProcessing(true);

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsProcessing(false);
    setPendingAction(null);

    if (action === 'approve') {
      success('Escalation approved — decision sent to customer.');
      navigate('/human-review');
    } else {
      warning('Escalation rejected — alternative recommendation required.');
    }
  };

  const handleAssignToMe = () => {
    setAssignedOverride(user.name);
    success(`Escalation assigned to ${user.name}`);
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[{ label: 'Human Review', href: '/human-review' }, { label: escalation.id }]}
      />

      {/* Back Navigation */}
      <div className="flex items-center gap-4">
        <Link to="/human-review">
          <Button variant="ghost" size="sm" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Human Review
          </Button>
        </Link>
      </div>

      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={priority.className}>{priority.label}</Badge>
            <Badge className={status.className}>{status.label}</Badge>
            {isOverdue && !isResolved && (
              <Badge className="bg-severity-critical text-white animate-pulse">SLA Breached</Badge>
            )}
          </div>
          <h1 className="text-2xl font-semibold">{escalation.decision?.title ?? 'Escalation Review'}</h1>
          <p className="text-sm text-muted-foreground">
            Escalation ID: <code className="font-mono bg-muted px-1 rounded">{escalation.id}</code>
          </p>
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className="text-right">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">SLA Deadline</p>
            {!isResolved ? (
              <CompactCountdown
                deadline={slaDeadline}
                className={cn('text-xl font-semibold', isOverdue && 'text-severity-critical')}
              />
            ) : (
              <p className="text-severity-low font-semibold">
                {escalation.status === 'approved' ? 'Approved' : 'Rejected'}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      {!isResolved && (
        <Card className="border-2 border-accent">
          <CardContent className="p-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="font-semibold">Review Actions</h3>
                <p className="text-sm text-muted-foreground">
                  Approve or reject the original recommendation
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  className="gap-2"
                  onClick={() => setPendingAction('reject')}
                >
                  <XCircle className="h-4 w-4" />
                  Reject & Override
                </Button>
                <Button className="gap-2" onClick={() => setPendingAction('approve')}>
                  <CheckCircle className="h-4 w-4" />
                  Approve Decision
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Escalation Details */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Escalation Details</CardTitle>
            <CardDescription>Full context for this human review request</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">
                Reason for Escalation
              </h4>
              <p className="text-sm leading-relaxed">{escalation.reason}</p>
            </div>

            <div className="pt-4 border-t">
              <h4 className="text-sm font-medium text-muted-foreground mb-3">
                Original AI Recommendation
              </h4>
              <div className="rounded-lg bg-muted/50 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{escalation.decision?.recommendedAction ?? 'N/A'}</span>
                  <Badge variant="outline" className="font-mono">
                    {formatCurrency(escalation.decision?.exposure ?? 0)}
                  </Badge>
                </div>
                <Link to={`/decisions/${escalation.decisionId}`}>
                  <Button variant="outline" size="sm" className="gap-2">
                    <FileText className="h-4 w-4" />
                    View Full Decision
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Customer Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Customer</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="p-3 rounded-lg border">
                <p className="font-semibold">{escalation.customer?.name ?? 'Unknown Customer'}</p>
                <p className="text-sm text-muted-foreground">{escalation.customer?.contact ?? ''}</p>
                <p className="text-lg font-mono font-semibold font-tabular mt-2">
                  {formatCurrency(escalation.decision?.exposure ?? 0)}
                </p>
                <p className="text-xs text-muted-foreground">Total Exposure</p>
              </div>
            </CardContent>
          </Card>

          {/* Assignment */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Assignment</CardTitle>
            </CardHeader>
            <CardContent>
              {assignedTo ? (
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10 text-accent">
                    <User className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="font-medium">{assignedTo}</p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-4">
                  <User className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">Not yet assigned</p>
                  <Button variant="outline" size="sm" className="mt-2" onClick={handleAssignToMe}>
                    Assign to Me
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Meta Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Priority SLA</span>
                <span className="font-mono">{priority.sla}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span className="font-mono">
                  {formatDate(escalation.escalatedAt, { relative: true })}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Decision ID</span>
                <Link
                  to={`/decisions/${escalation.decisionId}`}
                  className="font-mono text-accent hover:underline"
                >
                  {escalation.decisionId.slice(0, 10)}...
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Activity Timeline */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Activity Timeline
          </CardTitle>
          <CardDescription>History of actions and comments on this escalation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mergedTimeline.map((entry, index) => {
              const EntryIcon = entry.icon === 'comment' ? MessageSquare : Clock;
              return (
                <div key={entry.id} className="flex gap-4">
                  <div className="relative">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
                      <EntryIcon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    {index < mergedTimeline.length - 1 && (
                      <div className="absolute left-4 top-8 h-full w-px bg-border" />
                    )}
                  </div>
                  <div className="flex-1 pb-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">{entry.user}</span>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(entry.timestamp, { relative: true })}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">{entry.message}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Add Comment */}
          {!isResolved && (
            <div className="mt-6 pt-4 border-t">
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Add a comment..."
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  maxLength={1000}
                  className="flex-1 h-10 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                  onKeyDown={(e) => e.key === 'Enter' && handleAddComment()}
                />
                <Button onClick={handleAddComment} className="gap-2">
                  <Send className="h-4 w-4" />
                  Send
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Approve/Reject Confirmation */}
      <ConfirmationDialog
        isOpen={pendingAction !== null}
        onConfirm={handleConfirmAction}
        onCancel={() => setPendingAction(null)}
        title={
          pendingAction === 'approve' ? 'Approve this decision?' : 'Reject this recommendation?'
        }
        description={
          pendingAction === 'approve'
            ? `The recommended "${escalation.decision?.recommendedAction ?? 'action'}" (${formatCurrency(escalation.decision?.exposure ?? 0)}) will be committed and sent to the customer.`
            : `You are rejecting the AI recommendation. An alternative action will need to be provided. This will be logged for audit.`
        }
        confirmLabel={pendingAction === 'approve' ? 'Approve & Send' : 'Reject'}
        variant={pendingAction === 'approve' ? 'default' : 'danger'}
        isLoading={isProcessing}
      />
    </div>
  );
}

export default EscalationDetailPage;
