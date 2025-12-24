# Release Management & Deployment Checklist

This checklist ensures safe, reliable deployments to production.

## Pre-Release Checklist

### Code Quality

- [ ] All unit tests passing (`pytest --cov=app --cov-fail-under=80`)
- [ ] All integration tests passing (`pytest -m integration`)
- [ ] End-to-end tests passing (`pytest -m e2e`)
- [ ] Code coverage >= 80%
- [ ] No critical security vulnerabilities (`safety check`, `bandit -r app/`)
- [ ] Code reviewed by at least one other developer
- [ ] All PR comments addressed
- [ ] Branch is up to date with main

### Database

- [ ] Database migrations tested in staging
- [ ] Rollback migration tested
- [ ] No backward-incompatible schema changes without deprecation period
- [ ] Indexes added for new queries
- [ ] No queries with N+1 problems
- [ ] Database backup completed before deployment

### Documentation

- [ ] CHANGELOG.md updated with new features/fixes
- [ ] API documentation updated (if API changed)
- [ ] User Guide updated (if UI changed)
- [ ] Runbook updated (if new operational procedures)
- [ ] Migration guide updated (if data model changed)

### Performance

- [ ] Load tested in staging (`python monitoring/performance_profiler.py --load-test`)
- [ ] No performance regressions (response times within 10% of baseline)
- [ ] Database query performance verified
- [ ] Cache hit rates acceptable (> 70%)
- [ ] No memory leaks detected

### Security

- [ ] No secrets committed to git
- [ ] All environment variables documented in `.env.example`
- [ ] Secrets rotated if needed
- [ ] AWS Secrets Manager updated
- [ ] OWASP top 10 vulnerabilities checked
- [ ] API rate limiting configured
- [ ] CORS settings verified

---

## Deployment Checklist

### Pre-Deployment (1 hour before)

#### 1. Notifications

- [ ] Announce deployment in #engineering Slack channel
- [ ] Update status page: "Scheduled Maintenance"
- [ ] Send email notification to users (if major changes)
- [ ] Notify on-call engineer

#### 2. Environment Preparation

- [ ] Verify staging environment is healthy
- [ ] Run full test suite one final time
- [ ] Create git tag for release (e.g., `v1.2.0`)
- [ ] Generate release notes from CHANGELOG

#### 3. Database Backup

```bash
# Create RDS snapshot
aws rds create-db-snapshot \
    --db-instance-identifier social-analytics-db \
    --db-snapshot-identifier manual-snapshot-$(date +%Y%m%d-%H%M%S)

# Verify snapshot completed
aws rds describe-db-snapshots \
    --db-snapshot-identifier manual-snapshot-TIMESTAMP
```

#### 4. Health Check Baseline

```bash
# Run health check and save baseline
python monitoring/health_check.py \
    --url https://api.example.com \
    --output-file baseline_health.json

# Run performance profile
python monitoring/performance_profiler.py \
    --url https://api.example.com \
    --output baseline_performance.json
```

### Deployment Steps

#### Step 1: Deploy Database Migrations (if needed)

```bash
# SSH into ECS task or run migration task
cd backend
alembic upgrade head

# Verify migrations applied
alembic current

# Test rollback (in staging first!)
# alembic downgrade -1
# alembic upgrade head
```

- [ ] Database migrations successful
- [ ] No migration errors in logs
- [ ] Rollback migration tested

#### Step 2: Deploy Application

```bash
# Set environment variable
export AWS_ACCOUNT_ID=YOUR_ACCOUNT_ID

# Run deployment
cd social_media_analytics_webapp
./deploy.sh deploy

# Wait for deployment to complete
# Monitor in AWS Console or:
aws ecs describe-services \
    --cluster social-analytics-cluster \
    --services backend-service
```

- [ ] Docker build successful
- [ ] Images pushed to ECR
- [ ] ECS tasks starting
- [ ] Health checks passing
- [ ] All tasks running

#### Step 3: Verify Deployment

```bash
# Check health
python monitoring/health_check.py \
    --url https://api.example.com

# Check API endpoints
curl https://api.example.com/health
curl https://api.example.com/health/ready
curl https://api.example.com/metrics

# Run smoke tests
pytest tests/smoke/
```

- [ ] Health checks passing
- [ ] All critical endpoints responding
- [ ] Database connectivity confirmed
- [ ] Redis connectivity confirmed
- [ ] Background jobs running
- [ ] WebSocket connections working

#### Step 4: Monitor

```bash
# Monitor logs for first 15 minutes
aws logs tail /ecs/social-analytics-backend --follow

# Watch CloudWatch dashboard
# https://console.aws.amazon.com/cloudwatch/home#dashboards:name=social-analytics-production

# Check for errors
aws logs filter-pattern "ERROR" \
    --log-group-name /ecs/social-analytics-backend \
    --start-time $(date -u -d '15 minutes ago' +%s)000
```

**Monitor for 15 minutes:**
- [ ] No error spike in logs
- [ ] Response times normal
- [ ] No 5XX errors
- [ ] CPU/Memory utilization normal
- [ ] Database connections stable
- [ ] No alerts triggered

### Post-Deployment

#### 1. Verification

- [ ] Run full end-to-end test suite
- [ ] Test critical user journeys manually:
  - [ ] User registration
  - [ ] User login
  - [ ] Add monitoring entity
  - [ ] Start monitoring job
  - [ ] View analytics
  - [ ] Export data
- [ ] Verify real-time updates (WebSocket)
- [ ] Check all platform integrations

#### 2. Performance Validation

```bash
# Run performance tests
python monitoring/performance_profiler.py \
    --url https://api.example.com \
    --output post_deployment_performance.json

# Compare with baseline
diff baseline_performance.json post_deployment_performance.json
```

- [ ] Response times within acceptable range
- [ ] No performance degradation
- [ ] Throughput meets requirements

#### 3. Update Status

- [ ] Update status page to "Operational"
- [ ] Post completion message in Slack
- [ ] Send completion email (if needed)

#### 4. Documentation

- [ ] Update deployment log with:
  - [ ] Deployment time
  - [ ] Version deployed
  - [ ] Issues encountered
  - [ ] Rollback performed (if any)
- [ ] Tag release in GitHub
- [ ] Close related issues/tickets
- [ ] Update project board

---

## Rollback Procedure

### When to Rollback

Rollback immediately if:
- Critical functionality broken
- Error rate > 5%
- Response times > 2x baseline
- Database corruption detected
- Security vulnerability introduced

### Rollback Steps

#### 1. Decide to Rollback

- [ ] Severity assessment (P1/P2)
- [ ] Approval from team lead
- [ ] Notify in #engineering channel

#### 2. Rollback Application

```bash
# Option 1: Use deploy script
./deploy.sh rollback

# Option 2: Manual rollback
aws ecs update-service \
    --cluster social-analytics-cluster \
    --service backend-service \
    --task-definition social-analytics-backend:PREVIOUS_REVISION \
    --force-new-deployment

# Wait for rollback
aws ecs wait services-stable \
    --cluster social-analytics-cluster \
    --services backend-service
```

- [ ] Previous version deployed
- [ ] Health checks passing

#### 3. Rollback Database (if needed)

```bash
# If migrations were applied, rollback
cd backend
alembic downgrade -1

# Or restore from snapshot (last resort)
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier social-analytics-db-rollback \
    --db-snapshot-identifier manual-snapshot-TIMESTAMP
```

- [ ] Database migrations rolled back
- [ ] Or database restored from snapshot

#### 4. Verify Rollback

- [ ] System health confirmed
- [ ] Critical features working
- [ ] Error rates normal
- [ ] Monitoring for 30 minutes

#### 5. Post-Rollback

- [ ] Update status page
- [ ] Notify stakeholders
- [ ] Create incident ticket
- [ ] Schedule post-mortem

---

## Post-Deployment Monitoring

### First Hour

- [ ] Monitor CloudWatch dashboard continuously
- [ ] Watch error logs
- [ ] Check user feedback channels
- [ ] Verify background jobs running
- [ ] Monitor database performance

### First 24 Hours

- [ ] Check daily metrics summary
- [ ] Review Sentry errors (if any)
- [ ] Analyze CloudWatch alarms
- [ ] Review user feedback
- [ ] Check system resource utilization

### First Week

- [ ] Review metrics trends
- [ ] Analyze slow query logs
- [ ] Check for memory leaks
- [ ] Review user satisfaction
- [ ] Gather performance data

---

## Release Types

### Hotfix Release

For critical bugs in production:

1. Create hotfix branch from main
2. Fix issue with minimal changes
3. Fast-track testing (critical tests only)
4. Deploy immediately
5. Full regression testing post-deployment

**Timeline:** < 2 hours from detection to deployment

### Minor Release

For bug fixes and small features:

1. Complete testing in staging
2. Schedule deployment during business hours
3. Monitor closely for first hour
4. Full post-deployment validation

**Timeline:** 1 week sprint, deploy weekly

### Major Release

For significant features or breaking changes:

1. Beta testing period (staging available to select users)
2. Complete regression testing
3. Performance testing under load
4. Schedule during maintenance window
5. Rollback plan documented and tested
6. Extended monitoring (24-48 hours)

**Timeline:** 2-4 week sprint, deploy monthly

---

## Emergency Procedures

### Database Emergency

If database is unavailable:

1. Check RDS instance status
2. Failover to read replica (if Multi-AZ)
3. Restore from snapshot if corruption
4. Enable maintenance mode on status page

### Complete Outage

If entire system is down:

1. Declare P1 incident
2. Activate incident response team
3. Check all AWS services status
4. Enable static maintenance page
5. Communicate with users every 15 minutes

---

## Metrics to Track

### Deployment Metrics

- **Deployment Frequency:** How often we deploy
- **Lead Time:** Code commit to production
- **MTTR (Mean Time To Recovery):** Average time to recover from failures
- **Change Failure Rate:** % of deployments causing issues

### Performance Metrics

- **Uptime:** Target 99.9%
- **Response Time P99:** < 1 second
- **Error Rate:** < 1%
- **Throughput:** Requests per second

---

## Continuous Improvement

After each deployment:

1. **Post-Deployment Review** (within 24 hours)
   - What went well?
   - What could be improved?
   - Any unexpected issues?

2. **Update Documentation**
   - Update runbook with new procedures
   - Improve deployment scripts
   - Enhance monitoring

3. **Automation**
   - Identify manual steps to automate
   - Improve CI/CD pipeline
   - Add new automated tests

---

**Remember:** It's better to delay a deployment than to rush and cause an outage. When in doubt, rollback first, investigate later.

**Last Updated:** 2025-12-22
**Version:** 1.0.0
