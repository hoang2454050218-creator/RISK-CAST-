import { useState, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { NotFoundState } from '@/components/ui/not-found-state';
import { ErrorState } from '@/components/ui/states';
import { SkeletonCard } from '@/components/ui/skeleton';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { useToast } from '@/components/ui/toast';
import { StatCard } from '@/components/domain/common/StatCard';
import { EvidenceList } from '@/components/domain/signals';
import { useSignal, useDismissSignal } from '@/hooks';
import {
  ArrowLeft,
  AlertTriangle,
  Globe,
  TrendingUp,
  Clock,
  ExternalLink,
  Ship,
  Users,
  DollarSign,
  CheckCircle,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDate, formatPercentage } from '@/lib/formatters';
import type { SignalStatus, EventType } from '@/types/signal';

const statusConfig: Record<
  SignalStatus,
  { label: string; icon: typeof CheckCircle; className: string }
> = {
  ACTIVE: { label: 'Active', icon: AlertTriangle, className: 'bg-severity-high text-white' },
  CONFIRMED: { label: 'Confirmed', icon: CheckCircle, className: 'bg-severity-low text-white' },
  EXPIRED: { label: 'Expired', icon: Clock, className: 'bg-muted text-muted-foreground' },
  DISMISSED: { label: 'Dismissed', icon: XCircle, className: 'bg-muted text-muted-foreground' },
};

const eventTypeConfig: Record<EventType, { label: string; color: string }> = {
  ROUTE_DISRUPTION: {
    label: 'Route Disruption',
    color: 'bg-severity-critical/10 text-severity-critical',
  },
  PORT_CONGESTION: { label: 'Port Congestion', color: 'bg-severity-high/10 text-severity-high' },
  WEATHER_EVENT: {
    label: 'Weather Event',
    color: 'bg-info/10 text-info',
  },
  GEOPOLITICAL: {
    label: 'Geopolitical',
    color: 'bg-action-reroute/10 text-action-reroute',
  },
  RATE_SPIKE: { label: 'Rate Spike', color: 'bg-warning/10 text-warning' },
  CARRIER_ISSUE: {
    label: 'Carrier Issue',
    color: 'bg-warning/10 text-warning',
  },
  CUSTOMS_DELAY: { label: 'Customs Delay', color: 'bg-muted text-muted-foreground' },
};

export function SignalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { success, warning, error: showError } = useToast();

  // ─── React Query ──────────────────────────────────────
  const { data: signal, isLoading, error, refetch, isRefetching } = useSignal(id);
  const dismissMutation = useDismissSignal();

  const [showDismissConfirm, setShowDismissConfirm] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleRefresh = useCallback(() => {
    refetch();
    success('Signal data refreshed');
  }, [refetch, success]);

  const handleDismiss = useCallback(async () => {
    if (!signal) return;
    try {
      await dismissMutation.mutateAsync({ signalId: signal.signal_id });
      setShowDismissConfirm(false);
      warning('Signal dismissed — removed from active monitoring.');
      navigate('/signals');
    } catch {
      showError('Failed to dismiss. Please retry.');
    }
  }, [signal, dismissMutation, navigate, warning, showError]);

  const handleGenerateDecision = useCallback(async () => {
    setIsGenerating(true);
    await new Promise(r => setTimeout(r, 1500));
    const newId = `dec_${Date.now().toString(36)}`;
    setIsGenerating(false);
    success(`Decision ${newId} generated from signal`);
    navigate(`/decisions/dec_a1b2c3d4e5f6g7h8i9j0`); // Navigate to existing mock decision
  }, [navigate, success]);

  // ─── Guard states ─────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-48 rounded-lg bg-muted animate-pulse" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} title="Failed to load signal" />;
  }

  if (!signal) {
    return <NotFoundState entity="signal" id={id} backTo="/signals" />;
  }

  const status = statusConfig[signal.status] ?? statusConfig.ACTIVE;
  const eventType = eventTypeConfig[signal.event_type] ?? { label: 'Unknown', color: 'bg-muted text-muted-foreground' };
  const StatusIcon = status.icon;

  return (
    <div className="space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs items={[{ label: 'Signals', href: '/signals' }, { label: signal.signal_id }]} />

      {/* Back Navigation */}
      <div className="flex items-center gap-4">
        <Link to="/signals">
          <Button variant="ghost" size="sm" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Signals
          </Button>
        </Link>
      </div>

      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={status.className}>
              <StatusIcon className="h-3 w-3 mr-1" />
              {status.label}
            </Badge>
            <Badge className={eventType.color}>{eventType.label}</Badge>
          </div>
          <h1 className="text-2xl font-semibold">{signal.event_title ?? 'Untitled Signal'}</h1>
          <p className="text-sm text-muted-foreground">
            Signal ID: <code className="font-mono bg-muted px-1 rounded">{signal.signal_id}</code>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            className="gap-2"
            onClick={handleRefresh}
            disabled={isRefetching}
          >
            <RefreshCw className={cn('h-4 w-4', isRefetching && 'animate-spin')} />
            {isRefetching ? 'Refreshing...' : 'Refresh'}
          </Button>
          {signal.status === 'ACTIVE' && (
            <Button
              variant="destructive"
              className="gap-2"
              onClick={() => setShowDismissConfirm(true)}
            >
              <XCircle className="h-4 w-4" />
              Dismiss Signal
            </Button>
          )}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={TrendingUp}
          label="Probability"
          value={formatPercentage(signal.probability ?? 0)}
          sublabel="Event likelihood"
          accentColor="blue"
          urgent={(signal.probability ?? 0) > 0.7}
        />
        <StatCard
          icon={CheckCircle}
          label="Confidence"
          value={formatPercentage(signal.confidence ?? 0)}
          sublabel="Data quality"
          accentColor="emerald"
        />
        <StatCard
          icon={DollarSign}
          label="Est. Impact"
          value={formatCurrency(signal.estimated_impact_usd || 0, { compact: true })}
          sublabel={`${signal.customers_affected || 0} customers affected`}
          accentColor="amber"
        />
        <StatCard
          icon={Ship}
          label="Shipments"
          value={signal.shipments_affected?.toString() || '0'}
          sublabel="At risk"
          accentColor="blue"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Signal Details */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Signal Details</CardTitle>
            <CardDescription>Full event description and context</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">Description</h4>
              <p className="text-sm leading-relaxed">{signal.event_description ?? ''}</p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">
                  Affected Chokepoints
                </h4>
                <div className="flex flex-wrap gap-2">
                  {(signal.affected_chokepoints ?? []).length > 0 ? (
                    (signal.affected_chokepoints ?? []).map((cp) => (
                      <Badge key={cp} variant="outline" className="font-mono">
                        {cp}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">None specific</span>
                  )}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">Affected Routes</h4>
                <div className="flex flex-wrap gap-2">
                  {(signal.affected_routes ?? []).map((route) => (
                    <Badge key={route} variant="outline">
                      {route}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">Affected Regions</h4>
              <div className="flex flex-wrap gap-2">
                {(signal.affected_regions ?? []).map((region) => (
                  <Badge key={region} variant="outline" className="gap-1">
                    <Globe className="h-3 w-3" />
                    {region}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t">
              <h4 className="text-sm font-medium text-muted-foreground mb-2">Timeline</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created</span>
                  <span className="font-mono">{formatDate(signal.created_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Last Updated</span>
                  <span className="font-mono">{formatDate(signal.updated_at)}</span>
                </div>
                {signal.expires_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Expires</span>
                    <span className="font-mono">{formatDate(signal.expires_at)}</span>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Related Decisions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Related Decisions
            </CardTitle>
            <CardDescription>Decisions generated from this signal</CardDescription>
          </CardHeader>
          <CardContent>
            {(signal.decision_ids ?? []).length > 0 ? (
              <div className="space-y-2">
                {(signal.decision_ids ?? []).map((decisionId) => (
                  <Link key={decisionId} to={`/decisions/${decisionId}`}>
                    <div className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted transition-colors">
                      <code className="text-sm font-mono text-muted-foreground">
                        {decisionId.slice(0, 15)}...
                      </code>
                      <ExternalLink className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <AlertTriangle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">No decisions generated yet</p>
                <Button
                  variant="premium"
                  size="default"
                  className="mt-4 gap-2"
                  onClick={handleGenerateDecision}
                  disabled={isGenerating}
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    'Generate Decision'
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Evidence Section */}
      <Card>
        <CardHeader>
          <CardTitle>Evidence Sources</CardTitle>
          <CardDescription>
            Data points supporting this signal ({(signal.evidence ?? []).length} sources)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <EvidenceList evidence={signal.evidence ?? []} />
        </CardContent>
      </Card>

      {/* Dismiss Confirmation */}
      <ConfirmationDialog
        isOpen={showDismissConfirm}
        onConfirm={handleDismiss}
        onCancel={() => setShowDismissConfirm(false)}
        title="Dismiss this signal?"
        description={`"${signal.event_title ?? 'Untitled Signal'}" will be removed from active monitoring. ${signal.shipments_affected ? `${signal.shipments_affected} shipments are currently flagged.` : ''} This action is logged for audit.`}
        confirmLabel="Dismiss Signal"
        variant="danger"
        isLoading={dismissMutation.isPending}
      />
    </div>
  );
}

export default SignalDetailPage;
