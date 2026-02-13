/**
 * Decision Detail Page
 *
 * Data flow: useDecision(id) → React Query → API → mock fallback
 * States: loading → error → not found → data
 */

import { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router';
import { SevenQuestionsView } from '@/components/domain/decisions/SevenQuestionsView';
import { VerdictBanner } from '@/components/domain/decisions/VerdictBanner';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { NotFoundState } from '@/components/ui/not-found-state';
import { ErrorState } from '@/components/ui/error-state';
import { SkeletonDecisionView } from '@/components/ui/skeleton';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import {
  useDecision,
  useAcknowledgeDecision,
  useOverrideDecision,
  useEscalateDecision,
} from '@/hooks';
import { useToast } from '@/components/ui/toast';
import { useUser } from '@/contexts/user-context';
import { formatCurrency } from '@/lib/formatters';

type PendingAction = 'acknowledge' | 'override' | 'escalate' | null;

export function DecisionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [overrideAction, setOverrideAction] = useState<string>('DELAY');
  const [overrideReason, setOverrideReason] = useState('');
  const [escalateReason, setEscalateReason] = useState('');
  const [escalatePriority, setEscalatePriority] = useState<string>('high');
  const [showRequestDialog, setShowRequestDialog] = useState(false);
  const [requestMoreText, setRequestMoreText] = useState('');
  const { user } = useUser();
  const { success, info, warning, error: showError } = useToast();

  // ─── React Query ──────────────────────────────────────
  const { data: decision, isLoading, error } = useDecision(id);
  const acknowledgeMutation = useAcknowledgeDecision();
  const overrideMutation = useOverrideDecision();
  const escalateMutation = useEscalateDecision();

  const isMutating =
    acknowledgeMutation.isPending || overrideMutation.isPending || escalateMutation.isPending;
  const exposure = decision ? formatCurrency(decision.q3_severity?.total_exposure_usd ?? 0) : '';

  // ─── Confirmation gates ───────────────────────────────
  const handleAcknowledgeRequest = useCallback(() => setPendingAction('acknowledge'), []);
  const handleOverrideRequest = useCallback(() => setPendingAction('override'), []);
  const handleEscalateRequest = useCallback(() => setPendingAction('escalate'), []);
  const cancelAction = useCallback(() => {
    setPendingAction(null);
    setOverrideReason('');
    setEscalateReason('');
  }, []);

  const handleConfirm = useCallback(async () => {
    if (!pendingAction || !decision) return;
    const action = pendingAction;
    setPendingAction(null);

    try {
      switch (action) {
        case 'acknowledge':
          await acknowledgeMutation.mutateAsync({
            decision_id: decision.decision_id,
            acknowledged_by: user.name,
          });
          success('Decision acknowledged — action committed.');
          navigate('/decisions');
          break;
        case 'override':
          await overrideMutation.mutateAsync({
            decision_id: decision.decision_id,
            override_action: overrideAction,
            reason: overrideReason,
            overridden_by: user.name,
          });
          setOverrideReason('');
          info('Override recorded — alternative action logged.');
          break;
        case 'escalate':
          await escalateMutation.mutateAsync({
            decision_id: decision.decision_id,
            reason: escalateReason,
            priority: escalatePriority,
            escalated_by: user.name,
          });
          setEscalateReason('');
          warning('Escalation created — routed to human review queue.');
          navigate('/human-review');
          break;
      }
    } catch {
      showError('Action failed. Please retry.');
    }
  }, [
    pendingAction,
    decision,
    user,
    acknowledgeMutation,
    overrideMutation,
    escalateMutation,
    overrideAction,
    overrideReason,
    escalateReason,
    escalatePriority,
    navigate,
    success,
    info,
    warning,
    showError,
  ]);

  const handleRequestMore = useCallback(() => {
    setShowRequestDialog(true);
  }, []);

  const handleSubmitRequest = useCallback(() => {
    if (requestMoreText.trim().length === 0) return;
    setShowRequestDialog(false);
    setRequestMoreText('');
    success('Information request submitted — additional intelligence will be gathered.');
  }, [requestMoreText, success]);

  // ─── States ───────────────────────────────────────────
  if (isLoading) return <SkeletonDecisionView />;

  if (error) {
    return (
      <ErrorState
        error={error}
        onRetry={() => window.location.reload()}
        title="Failed to load decision"
      />
    );
  }

  if (!decision) {
    return <NotFoundState entity="decision" id={id} backTo="/decisions" />;
  }

  // ─── Dialog config ────────────────────────────────────
  // Build business-context confirmation messages
  const actionType = decision.q5_action?.recommended_action ?? '';
  const actionCost = formatCurrency(decision.q5_action?.estimated_cost_usd ?? 0, { compact: true });
  const savings = formatCurrency(
    Math.max(0, (decision.q3_severity?.total_exposure_usd ?? 0) - (decision.q5_action?.estimated_cost_usd ?? 0)),
    { compact: true },
  );
  const inactionCost = formatCurrency(decision.q7_inaction?.inaction_cost_usd ?? 0, { compact: true });
  const shipmentsCount = decision.q3_severity?.shipments_affected ?? 0;

  const dialogConfig: Record<
    Exclude<PendingAction, null>,
    {
      title: string;
      description: string;
      confirmLabel: string;
      variant: 'default' | 'warning' | 'danger';
    }
  > = {
    acknowledge: {
      title: `Proceed with ${actionType}?`,
      description: `This will cost ${actionCost} and protect ${exposure} in exposure across ${shipmentsCount} shipment${shipmentsCount !== 1 ? 's' : ''}. Estimated savings: ${savings}. Action chain begins immediately upon confirmation.`,
      confirmLabel: `Confirm ${actionType}`,
      variant: 'default',
    },
    override: {
      title: 'Choose a different action?',
      description: `You're choosing an alternative to the recommended ${actionType} (${actionCost}). Your choice and reasoning will be logged. If no action is taken, potential loss is ${inactionCost}.`,
      confirmLabel: 'Confirm Override',
      variant: 'warning',
    },
    escalate: {
      title: 'Need a second opinion?',
      description: `${exposure} in exposure will be sent to the human review queue. A senior analyst will assess within the SLA window. Note: every hour of delay may increase costs.`,
      confirmLabel: 'Send to Review',
      variant: 'danger',
    },
  };

  const activeDialog = pendingAction ? dialogConfig[pendingAction] : null;

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[{ label: 'Decisions', href: '/decisions' }, { label: decision.decision_id ?? id ?? 'Unknown' }]}
        className="mb-1"
      />

      {decision && (
        <VerdictBanner
          decision={decision}
          onAct={() => {
            document.getElementById('action-buttons')?.scrollIntoView({ behavior: 'smooth' });
          }}
          className="mb-4"
        />
      )}

      <SevenQuestionsView
        decision={decision}
        onAcknowledge={handleAcknowledgeRequest}
        onOverride={handleOverrideRequest}
        onEscalate={handleEscalateRequest}
        onRequestMore={handleRequestMore}
        onBack={() => navigate('/decisions')}
        isLoading={isMutating}
      />

      {/* Request More Info Dialog */}
      {showRequestDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-xl border border-border bg-background p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-foreground">Request Additional Information</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              What additional information do you need?
            </p>
            <textarea
              value={requestMoreText}
              onChange={(e) => setRequestMoreText(e.target.value)}
              placeholder="Describe the intelligence or data you need..."
              rows={4}
              className="mt-4 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              autoFocus
            />
            <div className="mt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowRequestDialog(false);
                  setRequestMoreText('');
                }}
                className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitRequest}
                disabled={requestMoreText.trim().length === 0}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Submit Request
              </button>
            </div>
          </div>
        </div>
      )}

      {activeDialog && (
        <ConfirmationDialog
          isOpen={pendingAction !== null}
          onConfirm={handleConfirm}
          onCancel={cancelAction}
          title={activeDialog.title}
          description={activeDialog.description}
          confirmLabel={activeDialog.confirmLabel}
          variant={activeDialog.variant}
          isLoading={isMutating}
          confirmDisabled={
            (pendingAction === 'override' && overrideReason.trim().length < 10) ||
            (pendingAction === 'escalate' && escalateReason.trim().length < 10)
          }
        >
          {pendingAction === 'override' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Alternative Action</label>
                <select
                  value={overrideAction}
                  onChange={(e) => setOverrideAction(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="DELAY">Delay Shipment</option>
                  <option value="REROUTE">Reroute</option>
                  <option value="INSURE">Insure</option>
                  <option value="MONITOR">Monitor Only</option>
                  <option value="DO_NOTHING">Do Nothing</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Justification <span className="text-muted-foreground">(min 10 characters)</span>
                </label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Explain why you are overriding the AI recommendation..."
                  rows={3}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                />
                <p className="text-[11px] text-muted-foreground mt-1">
                  {overrideReason.trim().length}/10 characters minimum — logged for audit trail
                </p>
              </div>
            </div>
          )}
          {pendingAction === 'escalate' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Priority</label>
                <select
                  value={escalatePriority}
                  onChange={(e) => setEscalatePriority(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="critical">Critical — Immediate attention</option>
                  <option value="high">High — Within hours</option>
                  <option value="medium">Medium — Within 24h</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Reason for Escalation <span className="text-muted-foreground">(min 10 characters)</span>
                </label>
                <textarea
                  value={escalateReason}
                  onChange={(e) => setEscalateReason(e.target.value)}
                  placeholder="Why does this decision require human review..."
                  rows={3}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                />
                <p className="text-[11px] text-muted-foreground mt-1">
                  {escalateReason.trim().length}/10 characters minimum
                </p>
              </div>
            </div>
          )}
        </ConfirmationDialog>
      )}
    </div>
  );
}

export default DecisionDetailPage;
