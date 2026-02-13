# Deployment Runbook

## Overview

This runbook covers deployment procedures for the RISKCAST platform.

## Pre-Deployment Checklist

- [ ] All tests passing in CI
- [ ] Code review approved
- [ ] Changelog updated
- [ ] Database migrations tested
- [ ] Feature flags configured
- [ ] Rollback plan documented
- [ ] On-call notified

## Deployment Environments

| Environment | Cluster | Purpose |
|-------------|---------|---------|
| Development | riskcast-dev | Feature development |
| Staging | riskcast-staging | Pre-production testing |
| Production | riskcast-prod | Live traffic |

## Standard Deployment

### 1. Build and Push Image

```bash
# Build image
docker build -t riskcast/api:${VERSION} .

# Push to registry
docker push riskcast/api:${VERSION}
```

### 2. Deploy to Staging

```bash
# Update image in staging
kubectl set image deployment/riskcast-api \
    api=riskcast/api:${VERSION} \
    -n riskcast-staging

# Watch rollout
kubectl rollout status deployment/riskcast-api -n riskcast-staging

# Run smoke tests
./scripts/smoke-tests.sh staging
```

### 3. Deploy to Production

```bash
# Update image in production
kubectl set image deployment/riskcast-api \
    api=riskcast/api:${VERSION} \
    -n riskcast-prod

# Watch rollout
kubectl rollout status deployment/riskcast-api -n riskcast-prod

# Monitor metrics
# Watch error rate, latency, CPU in Grafana
```

### 4. Verify Deployment

```bash
# Check pod status
kubectl get pods -n riskcast-prod -l app=riskcast

# Check logs
kubectl logs -n riskcast-prod -l app=riskcast --tail=50

# Test health endpoint
curl https://api.riskcast.io/health

# Test API endpoint
curl -H "X-API-Key: $TEST_KEY" https://api.riskcast.io/v1/decisions
```

## Database Migrations

### Running Migrations

```bash
# 1. Check current schema version
kubectl exec -n riskcast-prod deployment/riskcast-api -- \
    python -c "from app.db import SchemaVersionService; ..."

# 2. Run migrations
kubectl exec -n riskcast-prod deployment/riskcast-api -- \
    alembic upgrade head

# 3. Verify migration
kubectl exec -n riskcast-prod deployment/riskcast-api -- \
    alembic current
```

### Rolling Back Migrations

```bash
# 1. Check current and target versions
alembic history

# 2. Rollback to specific version
alembic downgrade <revision>

# 3. Verify rollback
alembic current
```

## Feature Flag Deployment

For features behind flags, enable gradually:

```bash
# 1. Deploy with flag disabled
kubectl set image deployment/riskcast-api api=riskcast/api:${VERSION}

# 2. Enable for internal users (10%)
curl -X POST https://api.riskcast.io/admin/feature-flags \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d '{"key": "new_feature", "percentage": 10}'

# 3. Monitor metrics

# 4. Increase to 50%
curl -X POST https://api.riskcast.io/admin/feature-flags \
    -d '{"key": "new_feature", "percentage": 50}'

# 5. Full rollout (100%)
curl -X POST https://api.riskcast.io/admin/feature-flags \
    -d '{"key": "new_feature", "percentage": 100}'
```

## Rollback Procedures

### Quick Rollback (< 5 minutes)

```bash
# Rollback to previous revision
kubectl rollout undo deployment/riskcast-api -n riskcast-prod

# Verify rollback
kubectl rollout status deployment/riskcast-api -n riskcast-prod
```

### Rollback to Specific Version

```bash
# Check rollout history
kubectl rollout history deployment/riskcast-api -n riskcast-prod

# Rollback to specific revision
kubectl rollout undo deployment/riskcast-api \
    --to-revision=<revision> \
    -n riskcast-prod
```

### Full Rollback (with database)

```bash
# 1. Stop deployments
kubectl scale deployment/riskcast-api --replicas=0 -n riskcast-prod

# 2. Rollback database
alembic downgrade <previous_revision>

# 3. Deploy previous version
kubectl set image deployment/riskcast-api \
    api=riskcast/api:${PREVIOUS_VERSION}

# 4. Scale up
kubectl scale deployment/riskcast-api --replicas=5 -n riskcast-prod
```

## Canary Deployments

### Setup Canary

```bash
# 1. Deploy canary (1 pod)
kubectl apply -f deploy/kubernetes/canary/deployment-canary.yaml

# 2. Route 10% traffic to canary
kubectl apply -f deploy/kubernetes/canary/virtualservice-10.yaml

# 3. Monitor canary metrics
# Watch error rate comparison in Grafana

# 4. If successful, increase to 50%
kubectl apply -f deploy/kubernetes/canary/virtualservice-50.yaml

# 5. Full rollout
kubectl set image deployment/riskcast-api api=riskcast/api:${VERSION}
kubectl delete -f deploy/kubernetes/canary/
```

## Blue-Green Deployments

```bash
# 1. Deploy green environment
kubectl apply -f deploy/kubernetes/green/

# 2. Run smoke tests against green
./scripts/smoke-tests.sh green

# 3. Switch traffic to green
kubectl patch service riskcast-api -p '{"spec":{"selector":{"version":"green"}}}'

# 4. Monitor

# 5. Clean up blue (after validation period)
kubectl delete -f deploy/kubernetes/blue/
```

## Emergency Procedures

### Emergency Rollback

```bash
# Immediate rollback without waiting
kubectl rollout undo deployment/riskcast-api -n riskcast-prod

# Pause further rollouts
kubectl rollout pause deployment/riskcast-api -n riskcast-prod
```

### Disable Feature Immediately

```bash
# Via feature flag
curl -X POST https://api.riskcast.io/admin/feature-flags \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d '{"key": "problematic_feature", "enabled": false}'
```

### Scale Down Under Attack

```bash
# Enable rate limiting
kubectl apply -f deploy/kubernetes/rate-limit-strict.yaml

# Scale up to handle load
kubectl scale deployment/riskcast-api --replicas=20 -n riskcast-prod

# Block suspicious IPs (via WAF)
aws waf update-ip-set --ip-set-id xxx --change-token xxx --updates ...
```

## Post-Deployment Checklist

- [ ] Verify all pods healthy
- [ ] Check error rates (should be < 0.1%)
- [ ] Check latency (p99 < 500ms)
- [ ] Verify critical paths working
- [ ] Update deployment log
- [ ] Notify team of successful deployment

## Monitoring During Deployment

### Key Metrics to Watch

1. **Error Rate**: Should stay below 0.1%
2. **Latency**: p99 should stay under 500ms
3. **CPU/Memory**: Should stay under 70%
4. **Request Rate**: Should remain stable

### Grafana Queries

```promql
# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Latency p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Request rate
rate(http_requests_total[5m])
```

## Deployment Schedule

| Day | Allowed | Notes |
|-----|---------|-------|
| Monday | Yes | Avoid before 10am |
| Tuesday | Yes | Preferred |
| Wednesday | Yes | Preferred |
| Thursday | Yes | Before 2pm only |
| Friday | No | Emergency only |
| Weekend | No | Emergency only |

## Contact List

| Role | Contact | When to Reach |
|------|---------|---------------|
| On-call | @oncall | Any deployment issue |
| SRE Lead | @sre-lead | SEV1/SEV2 |
| DB Admin | @dba | Migration issues |
| Security | @security | Security concerns |
