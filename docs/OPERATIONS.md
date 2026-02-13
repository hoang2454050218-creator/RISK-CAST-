# RISKCAST Operations Runbook

## Overview

This document provides operational guidance for running RISKCAST in production.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           RISKCAST Platform                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │   OMEN   │───▶│  ORACLE  │───▶│ RISKCAST │───▶│ ALERTER  │          │
│  │ (Signals)│    │ (Reality)│    │(Decisions)│   │(WhatsApp)│          │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│       │               │               │               │                  │
│       ▼               ▼               ▼               ▼                  │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                    PostgreSQL + Redis                        │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Health Checks

### Endpoints

| Endpoint | Purpose | Usage |
|----------|---------|-------|
| `GET /live` | Liveness probe | Kubernetes liveness |
| `GET /ready` | Readiness probe | Kubernetes readiness |
| `GET /health` | Full health check | Dashboard/monitoring |
| `GET /circuits` | Circuit breaker status | Debugging |

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3
```

## Circuit Breakers

### Services with Circuit Breakers

| Service | Failure Threshold | Recovery Timeout | Notes |
|---------|------------------|------------------|-------|
| Polymarket | 5 failures | 60s | External prediction market |
| Twilio | 3 failures | 30s | Critical for alerts |
| AIS | 5 failures | 45s | Vessel tracking |
| News APIs | 10 failures | 120s | Tolerant of failures |
| Database | 3 failures | 15s | Fast recovery needed |
| Redis | 5 failures | 10s | Cache, degraded mode OK |

### States

- **CLOSED**: Normal operation
- **OPEN**: Service unhealthy, requests fail fast
- **HALF_OPEN**: Testing recovery

### Resetting a Circuit

```bash
# Via API (use with caution in production)
curl -X POST https://api.riskcast.io/circuits/polymarket/reset

# Via Redis (preferred)
redis-cli DEL "circuit:polymarket:state"
```

## Database Operations

### Connection Pool Settings

```python
# Production settings
POOL_SIZE = 20
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30
POOL_RECYCLE = 1800  # 30 minutes
```

### Common Queries

```sql
-- Active decisions by customer
SELECT customer_id, COUNT(*) as count, SUM(exposure_usd) as total_exposure
FROM decisions
WHERE is_expired = false
GROUP BY customer_id
ORDER BY total_exposure DESC;

-- Decisions by severity
SELECT severity, COUNT(*) as count
FROM decisions
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY severity;

-- Customer activity
SELECT customer_id, MAX(created_at) as last_decision
FROM decisions
GROUP BY customer_id
ORDER BY last_decision DESC
LIMIT 20;
```

### Maintenance Tasks

```bash
# Clean expired decisions (run daily)
curl -X POST https://api.riskcast.io/admin/cleanup-expired

# Vacuum analyze (weekly)
psql -c "VACUUM ANALYZE decisions;"
```

## Redis Operations

### Key Patterns

| Pattern | Purpose | TTL |
|---------|---------|-----|
| `decision:{id}` | Decision cache | 5 min |
| `customer:{id}:context` | Customer context | 10 min |
| `rate_limit:{api_key}` | Rate limiting | 1 min |
| `idempotency:{key}` | Idempotency | 24 hrs |

### Memory Management

```bash
# Check memory usage
redis-cli INFO memory

# Flush expired keys (if needed)
redis-cli --scan --pattern "decision:*" | xargs redis-cli UNLINK
```

## Incident Response

### Severity Levels

| Level | Criteria | Response Time | Escalation |
|-------|----------|---------------|------------|
| P1 | Service down, no decisions generated | < 15 min | Immediate |
| P2 | Degraded, some features unavailable | < 1 hour | Engineering |
| P3 | Performance issues | < 4 hours | On-call |
| P4 | Minor issues | Next business day | Ticket |

### Common Issues

#### 1. High Latency

**Symptoms**: API response times > 500ms

**Investigation**:
```bash
# Check database connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Check Redis latency
redis-cli --latency

# Check circuit breaker status
curl https://api.riskcast.io/circuits
```

**Resolution**:
1. Check for slow queries in database
2. Scale up if connection pool exhausted
3. Reset circuit breakers if stuck open

#### 2. Decision Generation Failures

**Symptoms**: `/decisions/generate` returning errors

**Investigation**:
```bash
# Check service logs
kubectl logs -l app=riskcast --tail=100

# Check OMEN status
curl https://api.riskcast.io/signals/health

# Check ORACLE status
curl https://api.riskcast.io/oracle/health
```

**Resolution**:
1. If OMEN failing: Check Polymarket API status
2. If ORACLE failing: Check AIS/rates APIs
3. If database failing: Check connection pool

#### 3. Alert Delivery Failures

**Symptoms**: WhatsApp messages not being sent

**Investigation**:
```bash
# Check Twilio circuit breaker
curl https://api.riskcast.io/circuits | jq '.circuit_breakers.twilio'

# Check alert queue
psql -c "SELECT status, COUNT(*) FROM alerts GROUP BY status;"
```

**Resolution**:
1. Check Twilio status page
2. Verify credentials in environment
3. Reset Twilio circuit breaker if stuck

## Deployment

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | Yes |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | Yes |
| `POLYMARKET_API_KEY` | Polymarket API key | No |
| `ENVIRONMENT` | development/staging/production | Yes |
| `LOG_LEVEL` | DEBUG/INFO/WARNING/ERROR | No |

### Rolling Deployment

```bash
# Update deployment
kubectl set image deployment/riskcast riskcast=riskcast:v1.2.3

# Watch rollout
kubectl rollout status deployment/riskcast

# Rollback if needed
kubectl rollout undo deployment/riskcast
```

### Database Migrations

```bash
# Run migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check current version
alembic current
```

## Monitoring

### Key Metrics

| Metric | Warning | Critical |
|--------|---------|----------|
| API latency p95 | > 500ms | > 2s |
| Error rate | > 1% | > 5% |
| Decision generation rate | < 50/min | < 10/min |
| Circuit breaker open | 1 service | > 2 services |
| Database connections | > 80% pool | > 95% pool |

### Prometheus Queries

```promql
# API latency p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Decision generation rate
rate(decisions_generated_total[5m])
```

### Grafana Dashboards

- **RISKCAST Overview**: Overall system health
- **API Performance**: Request latency, error rates
- **Decision Pipeline**: Generation times, success rates
- **External Services**: Circuit breaker status, API health

## Contacts

| Role | Contact |
|------|---------|
| On-call Engineer | PagerDuty rotation |
| Platform Lead | platform-lead@company.com |
| Database Admin | dba@company.com |
| Security | security@company.com |

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2024-01-15 | 1.0 | Initial runbook |
| 2024-02-01 | 1.1 | Added circuit breaker docs |
| 2024-02-05 | 1.2 | Added PostgreSQL migration |
