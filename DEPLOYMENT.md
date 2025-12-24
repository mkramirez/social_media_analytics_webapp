# Production Deployment Guide

## Overview

This guide covers deploying the Social Media Analytics Platform to production using AWS services.

## Architecture

```
Internet
    ↓
Application Load Balancer (HTTPS)
    ↓
AWS ECS Fargate (Backend API)
    ↓
┌─────────────┬──────────────┬───────────────────┐
RDS PostgreSQL   Redis Cache   AWS Secrets Manager
(Multi-AZ)      (ElastiCache)  (Credentials)
```

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Docker installed locally
- Domain name (optional, for custom domain)

## Infrastructure Components

### 1. Database - Amazon RDS PostgreSQL

**Specifications:**
- Engine: PostgreSQL 15
- Instance: db.t3.medium (production), db.t3.small (staging)
- Multi-AZ: Enabled (production)
- Automated backups: 7 days retention
- Encryption: Enabled (AES-256)

**Setup:**
```bash
# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier social-analytics-db \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --master-username admin \
    --master-user-password YOUR_STRONG_PASSWORD \
    --allocated-storage 100 \
    --multi-az \
    --backup-retention-period 7 \
    --storage-encrypted \
    --vpc-security-group-ids sg-xxxxx \
    --db-subnet-group-name social-analytics-subnet-group
```

### 2. Cache - Amazon ElastiCache for Redis

**Specifications:**
- Engine: Redis 7.0
- Node type: cache.t3.medium
- Number of replicas: 2 (Multi-AZ)
- Encryption: In-transit and at-rest

**Setup:**
```bash
# Create Redis cluster
aws elasticache create-replication-group \
    --replication-group-id social-analytics-redis \
    --replication-group-description "Social Analytics Cache" \
    --engine redis \
    --cache-node-type cache.t3.medium \
    --num-cache-clusters 3 \
    --automatic-failover-enabled \
    --transit-encryption-enabled \
    --at-rest-encryption-enabled \
    --cache-subnet-group-name social-analytics-subnet-group
```

### 3. Secrets Management - AWS Secrets Manager

**Store secrets:**
```bash
# Database credentials
aws secretsmanager create-secret \
    --name production/social-analytics/database/main \
    --description "Database credentials" \
    --secret-string '{"host":"xxx.rds.amazonaws.com","port":"5432","username":"admin","password":"xxx","database":"social_analytics"}'

# Redis URL
aws secretsmanager create-secret \
    --name production/social-analytics/redis/url \
    --secret-string "redis://xxx.cache.amazonaws.com:6379/0"

# Application secrets
aws secretsmanager create-secret \
    --name production/social-analytics/encryption/secret-key \
    --secret-string "your-secret-key-here"

aws secretsmanager create-secret \
    --name production/social-analytics/jwt/secret-key \
    --secret-string "your-jwt-secret-key-here"
```

### 4. Container Registry - Amazon ECR

**Create repositories:**
```bash
# Backend repository
aws ecr create-repository \
    --repository-name social-analytics/backend \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256

# Frontend repository
aws ecr create-repository \
    --repository-name social-analytics/frontend \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256
```

### 5. Container Orchestration - Amazon ECS Fargate

**Cluster setup:**
```bash
# Create ECS cluster
aws ecs create-cluster \
    --cluster-name social-analytics-cluster \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy \
        capacityProvider=FARGATE,weight=1,base=1 \
        capacityProvider=FARGATE_SPOT,weight=4
```

### 6. Load Balancer - Application Load Balancer

**Setup:**
```bash
# Create ALB
aws elbv2 create-load-balancer \
    --name social-analytics-alb \
    --subnets subnet-xxx subnet-yyy \
    --security-groups sg-xxxxx \
    --scheme internet-facing \
    --type application

# Create target group
aws elbv2 create-target-group \
    --name social-analytics-backend-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id vpc-xxxxx \
    --target-type ip \
    --health-check-enabled \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3
```

## Deployment Steps

### Step 1: Build Docker Images

```bash
# Backend
cd backend
docker build -t social-analytics-backend:latest .

# Frontend
cd ../frontend
docker build -t social-analytics-frontend:latest .
```

### Step 2: Push to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag images
docker tag social-analytics-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/social-analytics/backend:latest
docker tag social-analytics-frontend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/social-analytics/frontend:latest

# Push images
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/social-analytics/backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/social-analytics/frontend:latest
```

### Step 3: Register Task Definition

```bash
# Update aws/ecs-task-definition.json with your values
aws ecs register-task-definition \
    --cli-input-json file://aws/ecs-task-definition.json
```

### Step 4: Create ECS Service

```bash
# Backend service
aws ecs create-service \
    --cluster social-analytics-cluster \
    --service-name backend-service \
    --task-definition social-analytics-backend:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=backend,containerPort=8000" \
    --health-check-grace-period-seconds 60
```

### Step 5: Configure Auto Scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/social-analytics-cluster/backend-service \
    --min-capacity 2 \
    --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/social-analytics-cluster/backend-service \
    --policy-name cpu-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

### Step 6: Configure CloudWatch Monitoring

```bash
# Create log group
aws logs create-log-group --log-group-name /ecs/social-analytics-backend

# Create alarms
aws cloudwatch put-metric-alarm \
    --alarm-name social-analytics-high-cpu \
    --alarm-description "Alert when CPU exceeds 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2
```

## Monitoring & Logging

### CloudWatch Logs

Logs are automatically sent to CloudWatch Logs:
- Backend API: `/ecs/social-analytics-backend`
- Frontend: `/ecs/social-analytics-frontend`

### CloudWatch Metrics

Monitor these key metrics:
- **CPUUtilization**: Should be < 70% on average
- **MemoryUtilization**: Should be < 80% on average
- **TargetResponseTime**: Should be < 500ms for p99
- **HTTPCode_Target_5XX_Count**: Should be minimal

### Health Checks

ECS performs health checks on:
- Liveness: `/health/live`
- Readiness: `/health/ready`

ALB health checks:
- Path: `/health`
- Interval: 30 seconds
- Timeout: 5 seconds

## Security Considerations

### Network Security

1. **VPC Configuration:**
   - Private subnets for ECS tasks
   - Public subnets for ALB only
   - NAT Gateway for outbound internet access

2. **Security Groups:**
   - ALB: Allow inbound 443 (HTTPS) from 0.0.0.0/0
   - ECS: Allow inbound 8000 from ALB security group only
   - RDS: Allow inbound 5432 from ECS security group only
   - Redis: Allow inbound 6379 from ECS security group only

### Encryption

- **In-Transit:**
  - HTTPS/TLS 1.2+ for all external connections
  - SSL for RDS connections
  - TLS for Redis connections

- **At-Rest:**
  - RDS: AES-256 encryption
  - Redis: AES-256 encryption
  - Secrets Manager: Encrypted by default
  - EBS volumes: Encrypted

### IAM Roles

**Task Execution Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "*"
    }
  ]
}
```

**Task Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "s3:PutObject",
        "s3:GetObject",
        "cloudwatch:PutMetricData",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## Cost Optimization

### Estimated Monthly Costs

**Production Environment:**
- ECS Fargate (2 tasks, always on): ~$45
- RDS PostgreSQL (db.t3.medium, Multi-AZ): ~$140
- ElastiCache Redis (3 nodes): ~$90
- ALB: ~$25
- Data transfer: ~$10
- CloudWatch Logs/Metrics: ~$10
- **Total: ~$320/month**

**Staging Environment:**
- ECS Fargate (1 task): ~$23
- RDS PostgreSQL (db.t3.small, Single-AZ): ~$35
- ElastiCache Redis (single node): ~$30
- **Total: ~$90/month**

### Cost Reduction Strategies

1. Use Fargate Spot for non-critical tasks (70% savings)
2. Schedule auto-scaling to reduce tasks during off-hours
3. Enable S3 lifecycle policies for exports
4. Use Reserved Instances for RDS (40% savings)
5. Enable CloudWatch Logs retention policies

## Disaster Recovery

### Backup Strategy

1. **RDS Automated Backups:**
   - Daily snapshots with 7-day retention
   - Enable point-in-time recovery

2. **Manual Snapshots:**
   - Weekly manual snapshots before major deployments
   - Store in separate region for disaster recovery

3. **Redis Backups:**
   - Automatic snapshots every 24 hours
   - 7-day retention period

### Recovery Procedures

**RDS Failure:**
```bash
# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier social-analytics-db-restored \
    --db-snapshot-identifier manual-snapshot-name
```

**Complete Region Failure:**
1. Deploy to secondary region using stored snapshots
2. Update DNS to point to new region
3. Restore from cross-region RDS snapshot

## Rollback Procedures

**Application Rollback:**
```bash
# Update service to previous task definition
aws ecs update-service \
    --cluster social-analytics-cluster \
    --service backend-service \
    --task-definition social-analytics-backend:PREVIOUS_REVISION
```

**Database Rollback:**
```bash
# Restore from point-in-time
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier social-analytics-db \
    --target-db-instance-identifier social-analytics-db-restored \
    --restore-time 2025-01-15T12:00:00Z
```

## Maintenance

### Updates and Patching

1. **Application Updates:**
   - Blue-green deployment using ECS
   - Zero-downtime deployments

2. **Database Updates:**
   - Schedule during maintenance window
   - Test on staging first
   - Create snapshot before update

3. **Security Patches:**
   - Automated scanning via ECR
   - Monthly review and updates

### Performance Tuning

1. Monitor slow queries using RDS Performance Insights
2. Optimize indexes based on query patterns
3. Adjust ECS task CPU/memory based on metrics
4. Tune Redis cache policies based on hit rates

## Support and Troubleshooting

### Common Issues

**503 Service Unavailable:**
- Check ECS task health
- Verify target group health
- Check security group rules

**Slow Response Times:**
- Check RDS Performance Insights
- Review CloudWatch metrics for bottlenecks
- Verify Redis cache hit rates

**High Costs:**
- Review CloudWatch detailed billing
- Check for idle resources
- Optimize auto-scaling policies

### Useful Commands

```bash
# View ECS service status
aws ecs describe-services \
    --cluster social-analytics-cluster \
    --services backend-service

# View task logs
aws logs tail /ecs/social-analytics-backend --follow

# Check RDS status
aws rds describe-db-instances \
    --db-instance-identifier social-analytics-db

# View CloudWatch alarms
aws cloudwatch describe-alarms --state-value ALARM
```

## Next Steps

After deployment:

1. Configure custom domain with Route 53
2. Set up SSL certificate with ACM
3. Configure WAF rules for additional security
4. Set up CloudFront CDN (optional)
5. Implement automated backup testing
6. Create runbook for common issues
7. Set up PagerDuty/SNS alerts

---

**Last Updated:** 2025-12-22
**Version:** 1.0.0
