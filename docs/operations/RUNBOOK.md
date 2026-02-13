# RISKCAST Operations Runbook

## Overview

This runbook provides operational procedures for managing the RISKCAST Decision Intelligence Platform in production.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Startup/Shutdown Procedures](#startupshutdown-procedures)
3. [Health Monitoring](#health-monitoring)
4. [Common Issues & Resolution](#common-issues--resolution)
5. [Scaling Procedures](#scaling-procedures)
6. [Incident Response](#incident-response)
7. [Maintenance Windows](#maintenance-windows)
8. [Backup & Recovery](#backup--recovery)

---

## System Architecture

### Components

| Component | Purpose | Port | Health Endpoint |
|-----------|---------|------|-----------------|
| API Gateway | REST API | 8000 | /health |
| PostgreSQL | Database | 5432 | pg_isready |
| Redis | Cache/Queue | 6379 | PING |
| Worker | Background tasks | - | /health/worker |

### Dependencies

```
External APIs:
├── Polymarket API (signals)
├── News APIs (signals)
├── AIS Providers (tracking)
├── Freight Rate APIs (pricing)
└── WhatsApp Business API (alerts)
```

---

## Startup/Shutdown Procedures

### Application Startup

```bash
# 1. Verify dependencies are running
docker-compose ps

# 2. Check database migrations
alembic current
alembic upgrade head

# 3. Start application
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. Verify health
curl http://localhost:8000/health
```

### Expected Startup Sequence

```
1. Database connection established
2. Redis connection established
3. Core services initialized:
   - Tracing
   - Cache
   - Encryption
   - Event bus
   - Circuit breakers
4. API routes registered
5. Background tasks scheduled
6. Health check passes
```

### Application Shutdown

```bash
# Graceful shutdown (SIGTERM)
kill -TERM <pid>

# Or via Docker
docker-compose stop riskcast-api

# Verify shutdown
docker-compose ps
```

### Shutdown Sequence

```
1. Stop accepting new requests
2. Complete in-flight requests (30s timeout)
3. Flush event queues
4. Close database connections
5. Close Redis connections
6. Stop tracing
```

---

## Health Monitoring

### Health Check Endpoints

```bash
# Basic health
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/detailed

# Component health
curl http://localhost:8000/health/components
```

### Expected Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:00:00Z",
  "components": {
    "database": {"status": "healthy", "latency_ms": 5},
    "redis": {"status": "healthy", "latency_ms": 2},
    "omen": {"status": "healthy"},
    "oracle": {"status": "healthy"},
    "riskcast": {"status": "healthy"},
    "alerter": {"status": "healthy"}
  }
}
```

### Status Definitions

| Status | Description | Action |
|--------|-------------|--------|
| healthy | All components operational | None |
| degraded | Some components impaired | Monitor, may need investigation |
| unhealthy | Critical component failed | Immediate investigation |

### Key Metrics to Monitor

```
# Request metrics
riskcast_http_requests_total
riskcast_http_request_duration_ms

# Business metrics
riskcast_signals_detected_total
riskcast_decisions_generated_total
riskcast_alerts_sent_total
riskcast_alerts_failed_total

# Infrastructure
riskcast_circuit_breaker_state
riskcast_cache_hit_rate
riskcast_db_connection_pool_size
```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Error rate | > 1% | > 5% |
| P95 latency | > 500ms | > 2000ms |
| Alert failure rate | > 5% | > 20% |
| Circuit breaker open | Any | Multiple |
| Database connections | > 80% | > 95% |
| Memory usage | > 70% | > 90% |

---

## Common Issues & Resolution

### Issue: High API Latency

**Symptoms:**
- P95 latency > 500ms
- Slow dashboard response

**Investigation:**
```bash
# Check database
docker exec -it riskcast-db psql -U riskcast -c "SELECT * FROM pg_stat_activity;"

# Check Redis
docker exec -it riskcast-redis redis-cli INFO stats

# Check circuit breakers
curl http://localhost:8000/health/circuit-breakers
```

**Resolution:**
1. Check for slow queries in logs
2. Verify Redis cache hit rate
3. Check external API latency
4. Consider scaling if load-related

### Issue: Alert Delivery Failures

**Symptoms:**
- `riskcast_alerts_failed_total` increasing
- Customers not receiving alerts

**Investigation:**
```bash
# Check WhatsApp circuit breaker
curl http://localhost:8000/health/circuit-breakers | jq '.whatsapp'

# Check alert queue
curl http://localhost:8000/admin/alerts/queue

# Check WhatsApp API status
curl -I https://graph.facebook.com/health
```

**Resolution:**
1. Verify WhatsApp API credentials
2. Check rate limits (max 1000/day per number)
3. Reset circuit breaker if needed:
   ```bash
   curl -X POST http://localhost:8000/admin/circuit-breakers/whatsapp/reset
   ```

### Issue: Signal Detection Stopped

**Symptoms:**
- No new signals detected
- `riskcast_signals_detected_total` flat

**Investigation:**
```bash
# Check scheduler
curl http://localhost:8000/health/scheduler

# Check Polymarket circuit breaker
curl http://localhost:8000/health/circuit-breakers | jq '.polymarket'

# Check source API status
curl -I https://clob.polymarket.com/health
```

**Resolution:**
1. Verify API keys are valid
2. Check for API changes/deprecations
3. Reset circuit breaker
4. Manual signal refresh:
   ```bash
   curl -X POST http://localhost:8000/admin/signals/refresh
   ```

### Issue: Database Connection Pool Exhausted

**Symptoms:**
- "Connection pool exhausted" errors
- Requests timing out

**Investigation:**
```bash
# Check active connections
docker exec -it riskcast-db psql -U riskcast -c \
  "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Check for long-running queries
docker exec -it riskcast-db psql -U riskcast -c \
  "SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
   FROM pg_stat_activity 
   WHERE state = 'active' 
   ORDER BY duration DESC;"
```

**Resolution:**
1. Kill long-running queries:
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE duration > '5 minutes';
   ```
2. Increase pool size (temporary)
3. Investigate and fix query performance

### Issue: Memory Leak

**Symptoms:**
- Steadily increasing memory usage
- OOM kills

**Investigation:**
```bash
# Check container memory
docker stats riskcast-api

# Check Python memory
curl http://localhost:8000/admin/debug/memory
```

**Resolution:**
1. Rolling restart of API pods
2. Analyze memory profile
3. Check for circular references
4. Verify cache TTLs

---

## Scaling Procedures

### Horizontal Scaling (API)

```bash
# Scale API pods
kubectl scale deployment riskcast-api --replicas=5

# Or with Docker Compose
docker-compose up -d --scale api=5
```

### Database Scaling

**Read Replicas:**
```bash
# Add read replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier riskcast-replica-1 \
  --source-db-instance-identifier riskcast-primary
```

**Connection Pooling:**
```yaml
# pgbouncer.ini
[databases]
riskcast = host=db.internal port=5432 dbname=riskcast

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 50
```

### Redis Scaling

```bash
# Check memory usage
redis-cli INFO memory

# If > 80%, increase maxmemory
redis-cli CONFIG SET maxmemory 4gb
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| SEV1 | Total outage | 15 minutes | API down, database offline |
| SEV2 | Major degradation | 30 minutes | Alerts not sending, high error rate |
| SEV3 | Minor issue | 2 hours | Slow response, single customer affected |
| SEV4 | Low impact | Next business day | UI bug, documentation issue |

### Incident Process

1. **Detection**
   - Alert fires or customer reports issue
   
2. **Acknowledge**
   - Update incident status
   - Notify stakeholders
   
3. **Investigate**
   - Check logs, metrics, dashboards
   - Identify root cause
   
4. **Mitigate**
   - Apply immediate fix
   - Verify recovery
   
5. **Resolve**
   - Confirm full recovery
   - Close incident
   
6. **Post-mortem**
   - Document timeline
   - Identify improvements

### Communication Templates

**Initial notification:**
```
INCIDENT: [SEV-X] Brief description
STATUS: Investigating
IMPACT: Description of customer impact
UPDATES: Will provide update in 30 minutes
```

**Update:**
```
INCIDENT UPDATE: [SEV-X] Brief description
STATUS: Mitigating
ROOT CAUSE: Brief description
ETA: XX minutes to resolution
```

**Resolution:**
```
INCIDENT RESOLVED: [SEV-X] Brief description
DURATION: XX minutes
ROOT CAUSE: Brief description
NEXT STEPS: Post-mortem scheduled for DATE
```

---

## Maintenance Windows

### Scheduled Maintenance

**Standard window:** Sunday 02:00-06:00 UTC

**Procedure:**
1. Announce 7 days in advance
2. Create maintenance banner
3. Scale down non-critical components
4. Perform maintenance
5. Verify health
6. Scale back up
7. Remove maintenance banner

### Database Maintenance

```bash
# Vacuum and analyze
docker exec -it riskcast-db psql -U riskcast -c "VACUUM ANALYZE;"

# Reindex (if needed)
docker exec -it riskcast-db psql -U riskcast -c "REINDEX DATABASE riskcast;"
```

### Cache Maintenance

```bash
# Clear stale keys
redis-cli SCAN 0 MATCH "riskcast:expired:*" COUNT 1000

# Memory defragmentation
redis-cli MEMORY DOCTOR
```

---

## Backup & Recovery

### Backup Schedule

| Data | Frequency | Retention | Location |
|------|-----------|-----------|----------|
| Database | Daily | 30 days | S3 |
| Database | Hourly | 24 hours | S3 |
| Redis | Daily | 7 days | S3 |
| Logs | Real-time | 90 days | CloudWatch |

### Manual Backup

```bash
# Database backup
pg_dump -h localhost -U riskcast -d riskcast | gzip > backup_$(date +%Y%m%d).sql.gz

# Upload to S3
aws s3 cp backup_*.sql.gz s3://riskcast-backups/db/
```

### Recovery Procedures

**Database Recovery:**
```bash
# Download backup
aws s3 cp s3://riskcast-backups/db/backup_20240115.sql.gz ./

# Restore
gunzip -c backup_20240115.sql.gz | psql -h localhost -U riskcast -d riskcast
```

**Point-in-Time Recovery:**
```bash
# AWS RDS
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier riskcast-primary \
  --target-db-instance-identifier riskcast-recovery \
  --restore-time 2024-01-15T10:00:00Z
```

---

## Contacts

| Role | Name | Contact |
|------|------|---------|
| On-call Engineer | Rotation | PagerDuty |
| Database Admin | TBD | - |
| Security | TBD | - |
| Product | TBD | - |

---

## Appendix

### Useful Commands

```bash
# View logs
docker-compose logs -f api

# Enter container shell
docker exec -it riskcast-api bash

# Check API routes
curl http://localhost:8000/openapi.json | jq '.paths | keys'

# Database shell
docker exec -it riskcast-db psql -U riskcast

# Redis shell
docker exec -it riskcast-redis redis-cli
```

### Log Locations

| Log | Location |
|-----|----------|
| API | stdout (Docker) |
| Nginx | /var/log/nginx/*.log |
| PostgreSQL | /var/log/postgresql/*.log |
| System | /var/log/syslog |
