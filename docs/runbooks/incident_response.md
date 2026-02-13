# Incident Response Runbook

## Overview

This runbook covers incident response procedures for the RISKCAST platform.

## Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| SEV1 | Critical - System down | 15 minutes | Complete outage, data loss |
| SEV2 | Major - Degraded service | 1 hour | Partial outage, high error rates |
| SEV3 | Minor - Limited impact | 4 hours | Single feature broken |
| SEV4 | Low - Minimal impact | 24 hours | UI issues, minor bugs |

## SEV1 - Critical Incident Response

### 1. Immediate Actions (0-15 minutes)

```bash
# Check service health
curl https://api.riskcast.io/health

# Check pod status
kubectl get pods -n riskcast-prod -o wide

# Check recent events
kubectl get events -n riskcast-prod --sort-by='.lastTimestamp' | tail -20

# Check logs
kubectl logs -n riskcast-prod -l app=riskcast --tail=100 --since=5m
```

### 2. Escalation Path

1. **On-call Engineer** - First responder
2. **Team Lead** - If not resolved in 15 minutes
3. **Engineering Manager** - If not resolved in 30 minutes
4. **VP Engineering** - If not resolved in 1 hour

### 3. Communication Template

```
INCIDENT: [Brief description]
SEVERITY: SEV1
STATUS: [Investigating/Identified/Monitoring/Resolved]
IMPACT: [User-facing impact]
START TIME: [ISO timestamp]
NEXT UPDATE: [Expected time]
```

## Common Issues and Resolutions

### API Not Responding

**Symptoms:**
- HTTP 503 errors
- Timeout errors
- Health check failures

**Diagnosis:**

```bash
# Check deployment status
kubectl get deployment riskcast-api -n riskcast-prod

# Check replica count
kubectl get pods -n riskcast-prod -l app=riskcast | wc -l

# Check resource usage
kubectl top pods -n riskcast-prod

# Check for OOM kills
kubectl describe pods -n riskcast-prod | grep -A5 "OOMKilled"
```

**Resolution:**

```bash
# Restart pods (rolling)
kubectl rollout restart deployment/riskcast-api -n riskcast-prod

# Scale up if overloaded
kubectl scale deployment/riskcast-api --replicas=10 -n riskcast-prod

# Rollback if recent deployment
kubectl rollout undo deployment/riskcast-api -n riskcast-prod
```

### Database Connection Issues

**Symptoms:**
- Connection timeout errors
- "too many connections" errors
- Slow queries

**Diagnosis:**

```bash
# Check RDS metrics in AWS Console
# Look for: CPU, connections, IOPS

# Check connection pool in logs
kubectl logs -n riskcast-prod -l app=riskcast | grep -i "connection"

# Connect to RDS directly
psql -h riskcast-prod.xxxxx.us-east-1.rds.amazonaws.com -U riskcast_admin -d riskcast
```

**Resolution:**

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND query_start < now() - interval '10 minutes';

-- Check for locks
SELECT * FROM pg_locks WHERE NOT granted;
```

### Redis Connection Issues

**Symptoms:**
- Cache miss spikes
- Slow response times
- Redis timeout errors

**Diagnosis:**

```bash
# Check Redis cluster status
aws elasticache describe-replication-groups --replication-group-id riskcast-prod

# Connect to Redis
redis-cli -h riskcast-prod.xxxxx.cache.amazonaws.com -p 6379

# Check memory usage
redis-cli INFO memory

# Check connected clients
redis-cli CLIENT LIST | wc -l
```

**Resolution:**

```bash
# Clear cache if corrupted
redis-cli FLUSHDB

# Check slow queries
redis-cli SLOWLOG GET 10
```

### High Error Rates

**Symptoms:**
- Error rate > 1%
- Alerts firing
- Customer complaints

**Diagnosis:**

```bash
# Check error logs
kubectl logs -n riskcast-prod -l app=riskcast | grep -i "error" | tail -50

# Check Prometheus metrics
# Query: rate(http_requests_total{status=~"5.."}[5m])

# Check recent changes
kubectl rollout history deployment/riskcast-api -n riskcast-prod
```

**Resolution:**

1. Identify error pattern
2. Check if related to recent deployment
3. Rollback if necessary
4. Fix root cause

### External API Failures (Polymarket, AIS)

**Symptoms:**
- OMEN signal generation failures
- ORACLE reality updates failing
- Specific API timeout errors

**Diagnosis:**

```bash
# Check circuit breaker status
curl https://api.riskcast.io/health/dependencies

# Check API-specific logs
kubectl logs -n riskcast-prod -l app=riskcast | grep -i "polymarket\|ais"
```

**Resolution:**

1. Circuit breaker should auto-engage
2. Check external API status pages
3. Manually disable data source if needed:
   
   ```python
   # Via feature flags
   POST /admin/feature-flags
   {"key": "enable_polymarket", "enabled": false}
   ```

## Recovery Procedures

### Full Database Recovery

```bash
# 1. Stop application
kubectl scale deployment/riskcast-api --replicas=0 -n riskcast-prod

# 2. Restore from snapshot (AWS Console or CLI)
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier riskcast-prod-restored \
    --db-snapshot-identifier riskcast-prod-snapshot-xxxx

# 3. Update connection string in secrets
kubectl edit secret riskcast-secrets -n riskcast-prod

# 4. Restart application
kubectl scale deployment/riskcast-api --replicas=5 -n riskcast-prod
```

### Cache Recovery

```bash
# Redis should auto-recover
# If manual intervention needed:

# 1. Clear corrupted cache
redis-cli FLUSHALL

# 2. Warm cache (decisions will re-cache on demand)
# No manual action needed - cache is lazy-loaded
```

## Post-Incident

### Required Actions

1. **Update status page** - Within 30 minutes of resolution
2. **Write incident report** - Within 24 hours
3. **Schedule postmortem** - Within 48 hours

### Incident Report Template

```markdown
# Incident Report: [Title]

## Summary
[1-2 sentences describing the incident]

## Timeline
- HH:MM - Incident started
- HH:MM - Alert fired
- HH:MM - Engineer paged
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Incident resolved

## Root Cause
[Detailed explanation]

## Impact
- Duration: X hours Y minutes
- Affected users: N
- Failed requests: N
- Revenue impact: $X (if applicable)

## Resolution
[What was done to fix it]

## Action Items
- [ ] Immediate fix applied
- [ ] Root cause prevention
- [ ] Monitoring improvement
- [ ] Runbook update

## Lessons Learned
[What we learned]
```

## Monitoring Dashboards

- **Grafana**: https://monitoring.riskcast.io/grafana
- **Prometheus**: https://monitoring.riskcast.io/prometheus
- **CloudWatch**: AWS Console > CloudWatch > Dashboards > RISKCAST

## Contact Information

| Role | Name | Phone | Slack |
|------|------|-------|-------|
| On-call | Rotation | +1-xxx-xxx-xxxx | @oncall |
| Team Lead | [Name] | +1-xxx-xxx-xxxx | @teamlead |
| DBA | [Name] | +1-xxx-xxx-xxxx | @dba |
| DevOps | [Name] | +1-xxx-xxx-xxxx | @devops |
