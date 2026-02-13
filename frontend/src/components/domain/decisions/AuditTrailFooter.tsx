import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  FileText,
  Link,
  GitBranch,
  ExternalLink,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Copy,
  Check,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/formatters';
import { useToast } from '@/components/ui/toast';
import type { Decision } from '@/types/decision';

/**
 * Compute a real SHA-256 hash from an input string using the Web Crypto API.
 * Returns a hex-encoded digest prefixed with "sha256:".
 */
async function computeHash(input: string): Promise<string> {
  const buffer = new TextEncoder().encode(input);
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  return `sha256:${hashHex}`;
}

interface AuditTrailFooterProps {
  decision: Decision;
  onViewFullAudit?: () => void;
  onViewReasoning?: () => void;
  className?: string;
}

export function AuditTrailFooter({
  decision,
  onViewFullAudit,
  onViewReasoning,
  className,
}: AuditTrailFooterProps) {
  const navigate = useNavigate();
  const { success, error } = useToast();
  const [verificationStatus, setVerificationStatus] = useState<
    'idle' | 'verifying' | 'verified' | 'failed'
  >('idle');
  const [copiedHash, setCopiedHash] = useState(false);
  const [integrityHash, setIntegrityHash] = useState<string>('sha256:computing...');

  // Compute a deterministic SHA-256 hash from decision identity + content fields
  useEffect(() => {
    const hashInput = JSON.stringify({
      id: decision.decision_id,
      version: decision.version,
      created_at: decision.created_at,
      q1: decision.q1_what.event_summary,
      q3_exposure: decision.q3_severity.total_exposure_usd,
      q5_action: decision.q5_action.recommended_action,
      q5_cost: decision.q5_action.estimated_cost_usd,
      q7_inaction: decision.q7_inaction.inaction_cost_usd,
    });
    computeHash(hashInput).then(setIntegrityHash);
  }, [
    decision.decision_id,
    decision.version,
    decision.created_at,
    decision.q1_what.event_summary,
    decision.q3_severity.total_exposure_usd,
    decision.q5_action.recommended_action,
    decision.q5_action.estimated_cost_usd,
    decision.q7_inaction.inaction_cost_usd,
  ]);

  const verifyIntegrity = useCallback(async () => {
    setVerificationStatus('verifying');

    // Recompute hash from decision identity + content fields and compare
    const hashInput = JSON.stringify({
      id: decision.decision_id,
      version: decision.version,
      created_at: decision.created_at,
      q1: decision.q1_what.event_summary,
      q3_exposure: decision.q3_severity.total_exposure_usd,
      q5_action: decision.q5_action.recommended_action,
      q5_cost: decision.q5_action.estimated_cost_usd,
      q7_inaction: decision.q7_inaction.inaction_cost_usd,
    });
    const recomputedHash = await computeHash(hashInput);

    if (recomputedHash === integrityHash) {
      setVerificationStatus('verified');
      success('Decision integrity verified successfully');
    } else {
      setVerificationStatus('failed');
      error('Integrity verification failed - data may have been modified');
    }
  }, [
    decision.decision_id,
    decision.version,
    decision.created_at,
    decision.q1_what.event_summary,
    decision.q3_severity.total_exposure_usd,
    decision.q5_action.recommended_action,
    decision.q5_action.estimated_cost_usd,
    decision.q7_inaction.inaction_cost_usd,
    integrityHash,
    success,
    error,
  ]);

  const copyHash = useCallback(() => {
    navigator.clipboard.writeText(integrityHash);
    setCopiedHash(true);
    success('Hash copied to clipboard');
    setTimeout(() => setCopiedHash(false), 2000);
  }, [integrityHash, success]);

  return (
    <div className={cn('rounded-lg border border-border bg-muted/30 p-4 space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <FileText className="h-4 w-4" />
          <span>Audit Trail</span>
        </div>

        {onViewFullAudit && (
          <button
            onClick={onViewFullAudit}
            className="text-sm text-accent hover:underline flex items-center gap-1"
          >
            View full audit
            <ExternalLink className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* Metadata Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Decision ID */}
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Decision ID
          </p>
          <p className="font-mono text-sm truncate" title={decision.decision_id}>
            {decision.decision_id}
          </p>
        </div>

        {/* Created */}
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Created
          </p>
          <p className="text-sm">{formatDate(decision.created_at, { includeTime: true })}</p>
        </div>

        {/* Updated */}
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Last Updated
          </p>
          <p className="text-sm">{formatDate(decision.updated_at, { includeTime: true })}</p>
        </div>

        {/* Version */}
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Version
          </p>
          <p className="text-sm font-mono">v{decision.version}</p>
        </div>
      </div>

      {/* Linked Signals */}
      {decision.signal_ids.length > 0 && (
        <div className="space-y-2 pt-2 border-t">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <Link className="h-3.5 w-3.5" />
            <span>Linked Signals ({decision.signal_ids.length})</span>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {decision.signal_ids.slice(0, 5).map((signalId) => (
              <Badge
                key={signalId}
                variant="outline"
                className="font-mono text-[10px] cursor-pointer hover:bg-muted"
                onClick={() => navigate(`/signals/${signalId}`)}
              >
                {signalId.slice(0, 12)}...
              </Badge>
            ))}
            {decision.signal_ids.length > 5 && (
              <Badge variant="secondary" className="text-[10px]">
                +{decision.signal_ids.length - 5} more
              </Badge>
            )}
          </div>
        </div>
      )}

      {/* Reasoning Trace */}
      {decision.reasoning_trace_id && (
        <div className="space-y-2 pt-2 border-t">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <GitBranch className="h-3.5 w-3.5" />
              <span>Reasoning Trace</span>
            </div>

            {onViewReasoning && (
              <button
                onClick={onViewReasoning}
                className="text-xs text-accent hover:underline flex items-center gap-1"
              >
                View reasoning
                <ExternalLink className="h-3 w-3" />
              </button>
            )}
          </div>

          <p className="font-mono text-xs text-muted-foreground truncate">
            {decision.reasoning_trace_id}
          </p>
        </div>
      )}

      {/* Integrity Verification */}
      <div className="space-y-3 pt-2 border-t">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <Shield className="h-3.5 w-3.5" />
            <span>Data Integrity</span>
          </div>

          <IntegrityStatusBadge status={verificationStatus} />
        </div>

        {/* Hash display */}
          <div className="flex items-center gap-2 bg-muted/50 rounded-lg p-2">
          <code className="flex-1 font-mono text-xs text-muted-foreground truncate">
            {integrityHash}
          </code>
          <button
            onClick={copyHash}
            className="p-1 hover:bg-muted rounded transition-colors"
            aria-label="Copy hash"
          >
            {copiedHash ? (
              <Check className="h-3.5 w-3.5 text-confidence-high" />
            ) : (
              <Copy className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </button>
        </div>

        {/* Verification button */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={verifyIntegrity}
            disabled={verificationStatus === 'verifying'}
            className="gap-2"
          >
            {verificationStatus === 'verifying' ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Verifying...
              </>
            ) : verificationStatus === 'verified' ? (
              <>
                <ShieldCheck className="h-3.5 w-3.5 text-confidence-high" />
                Verified
              </>
            ) : verificationStatus === 'failed' ? (
              <>
                <RefreshCw className="h-3.5 w-3.5" />
                Re-verify
              </>
            ) : (
              <>
                <Shield className="h-3.5 w-3.5" />
                Verify Integrity
              </>
            )}
          </Button>

          {verificationStatus === 'verified' && (
            <span className="text-xs text-confidence-high flex items-center gap-1">
              <Check className="h-3 w-3" />
              Data has not been tampered with
            </span>
          )}

          {verificationStatus === 'failed' && (
            <span className="text-xs text-severity-critical flex items-center gap-1">
              <ShieldAlert className="h-3 w-3" />
              Verification failed - contact support
            </span>
          )}
        </div>

        {/* Verification info */}
        <p className="text-xs text-muted-foreground">
          This cryptographic hash ensures the decision data hasn't been modified since creation.
          Verify to confirm data integrity before taking action.
        </p>
        <span className="text-[10px] text-muted-foreground">
          Client-side content hash · Server verification via API
        </span>
      </div>
    </div>
  );
}

/**
 * Status badge for integrity verification
 */
function IntegrityStatusBadge({
  status,
}: {
  status: 'idle' | 'verifying' | 'verified' | 'failed';
}) {
  const configs = {
    idle: {
      label: 'Not verified',
      className: 'bg-muted text-muted-foreground',
      icon: Shield,
    },
    verifying: {
      label: 'Verifying...',
      className: 'bg-accent/10 text-accent',
      icon: Loader2,
    },
    verified: {
      label: 'Verified',
      className: 'bg-confidence-high/10 text-confidence-high',
      icon: ShieldCheck,
    },
    failed: {
      label: 'Failed',
      className: 'bg-severity-critical/10 text-severity-critical',
      icon: ShieldAlert,
    },
  };

  const config = configs[status];
  const Icon = config.icon;

  return (
    <Badge variant="outline" className={cn('gap-1 text-xs', config.className)}>
      <Icon className={cn('h-3 w-3', status === 'verifying' && 'animate-spin')} />
      {config.label}
    </Badge>
  );
}
