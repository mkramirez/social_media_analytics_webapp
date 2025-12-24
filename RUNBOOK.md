# Operational Runbook

This runbook provides step-by-step procedures for handling common operational issues with the Social Media Analytics Platform.

## Table of Contents

1. [High Availability Issues](#high-availability-issues)
2. [Performance Degradation](#performance-degradation)
3. [Database Issues](#database-issues)
4. [Background Job Failures](#background-job-failures)
5. [Cache/Redis Issues](#cacheredis-issues)
6. [API Rate Limiting](#api-rate-limiting)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Rollback Procedures](#rollback-procedures)
9. [Incident Response](#incident-response)

---

## High Availability Issues

### Symptom: Service Unavailable (503 Errors)

**Diagnosis:**
```bash
# Check ECS service health
aws ecs describe-services --cluster social-analytics-cluster --services backend-service

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN

# Check application logs
aws logs tail /ecs/social-analytics-backend --follow
```

**Common Causes & Solutions:**

1. **All ECS tasks unhealthy**
   ```bash
   # Check why tasks are failing
   aws ecs describe-tasks --cluster social-analytics-cluster --tasks TASK_ARN

   # Force new deployment
   aws ecs update-service --cluster social-analytics-cluster \
       --service backend-service --force-new-deployment
   ```

2. **Database connection failure**
   ```bash
   # Check RDS instance status
   aws rds describe-db-instances --db-instance-identifier social-analytics-db

   # Check security groups allow ECS → RDS traffic
   # Verify connection from ECS task:
   aws ecs execute-command --cluster social-analytics-cluster \
       --task TASK_ID --interactive --command "/bin/bash"
   # Then: psql $DATABASE_URL -c "SELECT 1"
   ```

3. **Out of memory/CPU**
   ```bash
   # Check resource utilization
   aws cloudwatch get-metric-statistics --namespace AWS/ECS \
       --metric-name MemoryUtilization --dimensions Name=ServiceName,Value=backend-service

   # Scale up if needed
   aws ecs update-service --cluster social-analytics-cluster \
       --service backend-service --desired-count 4
   ```

---

## Performance Degradation

### Symptom: Slow Response Times (> 2 seconds)

**Diagnosis:**
```bash
# Run performance profiler
python monitoring/performance_profiler.py --url https://api.example.com

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
    --metric-name TargetResponseTime --statistics Average

# Check database performance
python maintenance/database_maintenance.py --operation stats
```

**Common Causes & Solutions:**

1. **Slow database queries**
   ```bash
   # Find slow queries
   python maintenance/database_maintenance.py --operation check

   # Run ANALYZE to update statistics
   python maintenance/database_maintenance.py --operation analyze

   # Add missing indexes (check slow query report)
   # CREATE INDEX idx_name ON table_name(column_name);
   ```

2. **High cache miss rate**
   ```bash
   # Check Redis health
   redis-cli -h REDIS_HOST ping

   # Check cache stats
   redis-cli -h REDIS_HOST info stats

   # Increase Redis memory if needed (AWS ElastiCache console)
   ```

3. **Too many concurrent requests**
   ```bash
   # Scale ECS tasks
   aws ecs update-service --cluster social-analytics-cluster \
       --service backend-service --desired-count 6

   # Enable auto-scaling if not already enabled
   ```

---

## Database Issues

### Symptom: Database Connection Pool Exhausted

**Diagnosis:**
```bash
# Check active connections
python maintenance/database_maintenance.py --operation check

# Or directly via psql:
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity"
```

**Solution:**
```bash
# Kill idle connections
psql $DATABASE_URL -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND state_change < now() - interval '15 minutes'"

# Restart application to reset connection pool
aws ecs update-service --cluster social-analytics-cluster \
    --service backend-service --force-new-deployment
```

### Symptom: Database Disk Space Full

**Diagnosis:**
```bash
# Check RDS storage
aws rds describe-db-instances --db-instance-identifier social-analytics-db \
    --query 'DBInstances[0].[AllocatedStorage,DBInstanceStatus]'

# Check CloudWatch FreeStorageSpace metric
```

**Solution:**
```bash
# Cleanup old data
python maintenance/database_maintenance.py --operation cleanup --days 90

# Run VACUUM FULL to reclaim space
python maintenance/database_maintenance.py --operation vacuum

# Or increase storage (via AWS Console or CLI)
aws rds modify-db-instance --db-instance-identifier social-analytics-db \
    --allocated-storage 200 --apply-immediately
```

---

## Background Job Failures

### Symptom: Monitoring Jobs Not Running

**Diagnosis:**
```bash
# Check scheduler status
curl https://api.example.com/health/ready | jq '.checks.scheduler'

# Check job execution history
curl https://api.example.com/api/jobs -H "Authorization: Bearer $TOKEN"

# Check application logs for scheduler errors
aws logs filter-pattern "ERROR" --log-group-name /ecs/social-analytics-backend
```

**Common Causes & Solutions:**

1. **Scheduler not running**
   ```bash
   # Restart application
   aws ecs update-service --cluster social-analytics-cluster \
       --service backend-service --force-new-deployment

   # Check logs after restart
   aws logs tail /ecs/social-analytics-backend --follow
   ```

2. **API rate limits**
   ```bash
   # Check job execution logs for rate limit errors
   # Increase job intervals via API:
   curl -X PUT https://api.example.com/api/jobs/JOB_ID \
       -H "Authorization: Bearer $TOKEN" \
       -d '{"interval_minutes": 120}'
   ```

3. **Invalid API credentials**
   ```bash
   # Update API credentials in Secrets Manager
   aws secretsmanager update-secret \
       --secret-id production/social-analytics/twitch/credentials \
       --secret-string '{"client_id":"NEW_ID","client_secret":"NEW_SECRET"}'

   # Restart application to pick up new credentials
   aws ecs update-service --cluster social-analytics-cluster \
       --service backend-service --force-new-deployment
   ```

---

## Cache/Redis Issues

### Symptom: Redis Connection Failures

**Diagnosis:**
```bash
# Check Redis cluster status
aws elasticache describe-cache-clusters \
    --cache-cluster-id social-analytics-redis

# Test connection
redis-cli -h REDIS_ENDPOINT ping
```

**Solution:**
```bash
# Application degrades gracefully without Redis, but performance suffers

# Restart Redis node (if unhealthy)
aws elasticache reboot-cache-cluster \
    --cache-cluster-id social-analytics-redis \
    --cache-node-ids-to-reboot 0001

# Update application to use new Redis endpoint if changed
```

### Symptom: High Cache Eviction Rate

**Diagnosis:**
```bash
# Check evictions
redis-cli -h REDIS_ENDPOINT info stats | grep evicted_keys

# Check memory usage
redis-cli -h REDIS_ENDPOINT info memory
```

**Solution:**
```bash
# Scale up Redis node type via AWS Console
# Or adjust maxmemory-policy:
redis-cli -h REDIS_ENDPOINT CONFIG SET maxmemory-policy allkeys-lru
```

---

## API Rate Limiting

### Symptom: Platform API Rate Limits Exceeded

**Diagnosis:**
```bash
# Check job execution logs for rate limit errors
curl https://api.example.com/api/jobs/JOB_ID/executions \
    -H "Authorization: Bearer $TOKEN" | jq '.[] | select(.status=="rate_limited")'
```

**Solution:**
```bash
# Option 1: Increase monitoring intervals
# For all Twitch jobs:
for job_id in $(curl https://api.example.com/api/jobs?platform=twitch \
    -H "Authorization: Bearer $TOKEN" | jq -r '.[].id'); do
    curl -X PUT https://api.example.com/api/jobs/$job_id \
        -H "Authorization: Bearer $TOKEN" \
        -d '{"interval_minutes": 120}'
done

# Option 2: Pause non-critical jobs temporarily
curl -X POST https://api.example.com/api/jobs/JOB_ID/pause \
    -H "Authorization: Bearer $TOKEN"

# Option 3: Upgrade API tier with platform (Twitch, Twitter, etc.)
```

---

## Monitoring & Alerts

### Set Up New Alert

```bash
# Create CloudWatch alarm
python monitoring/cloudwatch_setup.py \
    --environment production \
    --alert-email ops@example.com

# Test alert
aws cloudwatch set-alarm-state \
    --alarm-name production-alb-high-response-time \
    --state-value ALARM \
    --state-reason "Testing alert"
```

### Silence Alerts (During Maintenance)

```bash
# Disable CloudWatch alarms
aws cloudwatch disable-alarm-actions \
    --alarm-names production-ecs-high-cpu production-rds-high-cpu

# Re-enable after maintenance
aws cloudwatch enable-alarm-actions \
    --alarm-names production-ecs-high-cpu production-rds-high-cpu
```

---

## Rollback Procedures

### Rollback Application Deployment

```bash
# Option 1: Use deploy script
cd social_media_analytics_webapp
./deploy.sh rollback

# Option 2: Manual rollback via AWS CLI
# Get previous task definition revision
aws ecs describe-services --cluster social-analytics-cluster \
    --services backend-service \
    --query 'services[0].taskDefinition'

# Update to previous revision
aws ecs update-service --cluster social-analytics-cluster \
    --service backend-service \
    --task-definition social-analytics-backend:PREVIOUS_REVISION \
    --force-new-deployment

# Wait for rollback
aws ecs wait services-stable --cluster social-analytics-cluster \
    --services backend-service
```

### Rollback Database Migration

```bash
# If using Alembic:
cd backend
alembic downgrade -1  # Rollback 1 migration

# Or restore from RDS snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier social-analytics-db-restored \
    --db-snapshot-identifier manual-snapshot-before-deploy

# Update application to point to restored database
```

---

## Incident Response

### Severity Levels

- **P1 (Critical)**: Complete outage, data loss, security breach
- **P2 (High)**: Partial outage, severe degradation
- **P3 (Medium)**: Minor degradation, non-critical features down
- **P4 (Low)**: Cosmetic issues, no user impact

### P1 Incident Response Procedure

1. **Declare Incident**
   ```bash
   # Trigger PagerDuty
   # Update status page: https://status.example.com
   # Notify team via Slack
   ```

2. **Assess Impact**
   ```bash
   # Check health dashboard
   curl https://api.example.com/health/detailed

   # Check error rates
   python monitoring/metrics_dashboard.py --url https://api.example.com --console-only

   # Check CloudWatch alarms
   aws cloudwatch describe-alarms --state-value ALARM
   ```

3. **Mitigate**
   - Follow relevant runbook procedure above
   - If cause unknown, rollback recent deployment
   - Scale up resources as temporary measure

4. **Communicate**
   - Update status page every 15 minutes
   - Post in #incidents Slack channel
   - Email affected customers if needed

5. **Resolve**
   - Verify service is healthy
   - Monitor for 30 minutes after resolution
   - Update status page to "Resolved"

6. **Post-Mortem**
   - Schedule within 48 hours
   - Document timeline, root cause, action items
   - Update runbook with lessons learned

---

## Useful Commands Reference

### Check Overall System Health
```bash
# Run comprehensive health check
python monitoring/health_check.py --url https://api.example.com

# Check all ECS services
aws ecs list-services --cluster social-analytics-cluster

# Check CloudWatch dashboard
# Visit: https://console.aws.amazon.com/cloudwatch/home#dashboards:name=social-analytics-production
```

### Access Application Logs
```bash
# Tail logs
aws logs tail /ecs/social-analytics-backend --follow

# Search for errors in last hour
aws logs filter-pattern "ERROR" \
    --log-group-name /ecs/social-analytics-backend \
    --start-time $(date -u -d '1 hour ago' +%s)000
```

### Database Maintenance
```bash
# Run full maintenance
python maintenance/database_maintenance.py --operation full

# Just cleanup old data
python maintenance/database_maintenance.py --operation cleanup --days 90
```

### Performance Testing
```bash
# Profile endpoints
python monitoring/performance_profiler.py --url https://api.example.com

# Load test
python monitoring/performance_profiler.py --url https://api.example.com \
    --load-test --duration 60 --concurrent-users 50
```

---

## Escalation Path

1. **On-Call Engineer** (immediate response)
2. **Engineering Lead** (if issue persists > 1 hour)
3. **CTO** (if P1 incident > 2 hours or data loss)

**Contact Information:**
- On-Call Rotation: PagerDuty
- Engineering Lead: eng-lead@example.com
- CTO: cto@example.com
- AWS Support: https://console.aws.amazon.com/support/home

---

**Last Updated:** 2025-12-22
**Maintained By:** Platform Engineering Team

**Remember:** When in doubt, check logs, check metrics, check health endpoints. Most issues can be resolved with a restart or rollback.
