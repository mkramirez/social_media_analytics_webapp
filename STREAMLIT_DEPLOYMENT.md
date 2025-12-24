# Streamlit Cloud Deployment Guide

Complete guide to deploying the Social Media Analytics Platform to Streamlit Cloud.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Backend Deployment](#backend-deployment)
4. [Database Setup](#database-setup)
5. [Streamlit Cloud Deployment](#streamlit-cloud-deployment)
6. [Configuration](#configuration)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The Social Media Analytics Platform uses a **two-tier architecture**:

```
┌─────────────────────────────────────────────────────┐
│         Streamlit Cloud (Frontend)                  │
│  - Streamlit UI                                     │
│  - User interface pages                             │
│  - Charts and visualizations                        │
└────────────────┬────────────────────────────────────┘
                 │ HTTPS/REST API
                 │
┌────────────────▼────────────────────────────────────┐
│         Backend (FastAPI)                           │
│  - REST API endpoints                               │
│  - Background jobs (APScheduler)                    │
│  - Business logic                                   │
│  - Platform API integrations                        │
└────────────────┬────────────────────────────────────┘
                 │
      ┌──────────┼──────────┬──────────┐
      │          │          │          │
┌─────▼────┐ ┌──▼────┐ ┌───▼────┐ ┌──▼──────────┐
│PostgreSQL│ │ Redis │ │ AWS    │ │ Platform    │
│          │ │       │ │Secrets │ │ APIs        │
│(Database)│ │(Cache)│ │Manager │ │(Twitch,etc) │
└──────────┘ └───────┘ └────────┘ └─────────────┘
```

**Important:** Streamlit Cloud only hosts the frontend. You need to separately deploy the FastAPI backend.

---

## Prerequisites

### 1. Accounts Required

- **GitHub Account** - For source code repository
- **Streamlit Cloud Account** - For frontend hosting (free tier available)
- **Backend Hosting** - Choose one:
  - AWS (ECS + RDS + ElastiCache) - Recommended for production
  - Heroku (easier setup, good for testing)
  - Railway.app (modern alternative)
  - DigitalOcean App Platform
- **PostgreSQL Database** - Choose one:
  - AWS RDS PostgreSQL
  - Heroku Postgres
  - Supabase (free tier available)
  - ElephantSQL (free tier available)
- **Redis Instance** (Optional but recommended):
  - AWS ElastiCache
  - Redis Cloud (free tier available)
  - Heroku Redis

### 2. Platform API Credentials

You'll need API credentials for platforms you want to monitor:

- **Twitch**: Client ID + Client Secret from [Twitch Developer Console](https://dev.twitch.tv/console)
- **Twitter**: Bearer Token from [Twitter Developer Portal](https://developer.twitter.com/)
- **YouTube**: API Key from [Google Cloud Console](https://console.cloud.google.com/)
- **Reddit**: Client ID + Client Secret from [Reddit Apps](https://www.reddit.com/prefs/apps)

### 3. Local Development Environment

```bash
# Required software
- Python 3.11+
- Git
- PostgreSQL client (psql)
- Docker (optional, for local testing)
```

---

## Backend Deployment

### Option A: Deploy to Heroku (Easiest)

#### Step 1: Prepare Repository

```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/social_media_analytics_webapp.git
cd social_media_analytics_webapp
```

#### Step 2: Create Heroku App

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login to Heroku
heroku login

# Create app
heroku create social-analytics-backend

# Add PostgreSQL
heroku addons:create heroku-postgresql:essential-0

# Add Redis
heroku addons:create heroku-redis:mini
```

#### Step 3: Configure Environment Variables

```bash
# Set environment variables
heroku config:set ENVIRONMENT=production
heroku config:set DEBUG=false
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
heroku config:set JWT_SECRET_KEY=$(openssl rand -hex 32)

# Database URL is automatically set by Heroku Postgres addon
# Redis URL is automatically set by Heroku Redis addon
```

#### Step 4: Create Procfile

Create `Procfile` in the backend directory:

```
web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: cd backend && python -m app.services.scheduler_service
```

#### Step 5: Deploy

```bash
# Create backend-only branch (Heroku deploys from root)
git subtree push --prefix backend heroku main

# Or if that doesn't work:
git push heroku `git subtree split --prefix backend main`:main --force

# Run database migrations
heroku run -a social-analytics-backend "cd backend && alembic upgrade head"

# Check logs
heroku logs --tail
```

#### Step 6: Get Backend URL

```bash
heroku info
# Note the "Web URL" - this is your BACKEND_URL for Streamlit
```

### Option B: Deploy to AWS (Production)

Follow the comprehensive guide in `DEPLOYMENT.md` for AWS ECS deployment.

Quick overview:
1. Set up RDS PostgreSQL database
2. Set up ElastiCache Redis
3. Build and push Docker image to ECR
4. Deploy to ECS Fargate
5. Configure ALB with HTTPS
6. Set up CloudWatch monitoring

**Backend URL will be:** `https://your-alb-dns-name.region.elb.amazonaws.com`

### Option C: Deploy to Railway.app (Modern Alternative)

#### Step 1: Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

#### Step 2: Deploy Backend

```bash
cd backend
railway init
railway up

# Add PostgreSQL
railway add postgresql

# Add Redis
railway add redis

# Set environment variables
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
railway variables set SECRET_KEY=$(openssl rand -hex 32)
railway variables set JWT_SECRET_KEY=$(openssl rand -hex 32)

# Get backend URL
railway status
```

---

## Database Setup

### Initialize Database Schema

Once your backend is deployed, initialize the database:

```bash
# Option 1: Via Heroku
heroku run -a social-analytics-backend "python -c 'from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)'"

# Option 2: Via Railway
railway run python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"

# Option 3: Via Alembic (preferred)
heroku run -a social-analytics-backend "cd backend && alembic upgrade head"
```

### Verify Database

```bash
# Connect to database
heroku pg:psql -a social-analytics-backend

# Check tables
\dt

# You should see tables like:
# users, api_profiles, twitch_channels, twitter_users, etc.
```

---

## Streamlit Cloud Deployment

### Step 1: Prepare Frontend Code

Ensure your `frontend` directory has:

```
frontend/
├── streamlit_app.py          # Main app entry point
├── pages/                     # All page files
│   ├── 01_twitch.py
│   ├── 02_twitter.py
│   ├── 03_youtube.py
│   ├── 04_reddit.py
│   ├── 05_profile_management.py
│   ├── 06_jobs.py
│   ├── 07_analytics.py
│   ├── 08_export.py
│   ├── 09_realtime.py
│   └── 10_feedback.py
├── components/
│   └── api_client.py          # Backend API client
└── requirements.txt           # Python dependencies
```

### Step 2: Create requirements.txt

Create `frontend/requirements.txt`:

```txt
# Streamlit
streamlit==1.29.0

# HTTP client
requests==2.31.0

# Data manipulation
pandas==2.1.4
numpy==1.26.2

# Visualization
plotly==5.18.0
altair==5.2.0

# Utilities
python-dateutil==2.8.2
pytz==2023.3

# Optional: For better charts
matplotlib==3.8.2
seaborn==0.13.0
```

### Step 3: Push to GitHub

```bash
# Create new repository on GitHub
# Then push your code

git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

### Step 4: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub

2. **Create New App**
   - Click "New app"
   - Select your repository: `YOUR_USERNAME/social_media_analytics_webapp`
   - Set main file path: `frontend/streamlit_app.py`
   - Click "Advanced settings"

3. **Configure Advanced Settings**

   **Python version:** 3.11

   **Secrets:** Add the following in TOML format:

   ```toml
   # Backend configuration
   BACKEND_URL = "https://your-backend-url.herokuapp.com"

   # Or for AWS:
   # BACKEND_URL = "https://your-alb-dns-name.region.elb.amazonaws.com"
   ```

4. **Deploy**
   - Click "Deploy"
   - Wait for deployment (usually 2-5 minutes)
   - Your app will be available at: `https://your-app-name.streamlit.app`

### Step 5: Configure Custom Domain (Optional)

1. In Streamlit Cloud dashboard, go to Settings
2. Click "Custom domain"
3. Add your domain (e.g., `analytics.yourdomain.com`)
4. Update DNS records as instructed
5. SSL certificate is automatically provisioned

---

## Configuration

### Frontend Configuration (Streamlit)

Update `frontend/components/api_client.py` to use environment variable:

```python
import os
import streamlit as st

class APIClient:
    def __init__(self, access_token: str = None):
        # Try to get BACKEND_URL from Streamlit secrets, then environment
        self.base_url = (
            st.secrets.get("BACKEND_URL") or
            os.getenv("BACKEND_URL") or
            "http://localhost:8000"
        ).rstrip('/')

        self.access_token = access_token
        self.headers = {}
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
```

### Backend Configuration

Ensure these environment variables are set in your backend:

```bash
# Required
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Optional but recommended
REDIS_URL=redis://host:6379/0
SENTRY_DSN=your-sentry-dsn  # For error tracking
PAGERDUTY_INTEGRATION_KEY=your-key  # For alerts

# AWS (if using AWS services)
AWS_REGION=us-east-1
USE_AWS_SECRETS_MANAGER=false  # Set true if using Secrets Manager
```

### CORS Configuration

Update `backend/app/main.py` to allow Streamlit Cloud origin:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Local development
        "https://your-app-name.streamlit.app",  # Streamlit Cloud
        "https://analytics.yourdomain.com",  # Custom domain (if configured)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Testing

### Test Backend

```bash
# Health check
curl https://your-backend-url.herokuapp.com/health

# Expected response:
# {"status":"healthy","timestamp":"2025-12-22T10:00:00.000Z"}

# API documentation
# Visit: https://your-backend-url.herokuapp.com/docs
```

### Test Frontend

1. **Visit your Streamlit app:** `https://your-app-name.streamlit.app`

2. **Test user registration:**
   - Click "Register"
   - Create account
   - Verify email (check inbox)

3. **Test login:**
   - Login with credentials
   - Should redirect to dashboard

4. **Test platform integration:**
   - Go to Profile Management
   - Add API credentials for a platform
   - Go to platform page (e.g., Twitch)
   - Add a channel to monitor
   - Start monitoring
   - Verify data collection

### End-to-End Test

Run through complete user journey:

```
1. Register → 2. Login → 3. Add API Profile →
4. Add Channel → 5. Start Monitoring → 6. View Analytics →
7. Export Data → 8. Submit Feedback
```

---

## Troubleshooting

### Frontend Issues

**Problem:** "Connection Error" when accessing backend

**Solution:**
```python
# Check BACKEND_URL is correct in Streamlit secrets
# Test backend directly:
curl https://your-backend-url/health

# Check CORS settings allow your Streamlit domain
# Check backend logs for connection errors
```

**Problem:** Streamlit app shows "ModuleNotFoundError"

**Solution:**
```bash
# Ensure all dependencies in requirements.txt
# Check Python version is 3.11
# Redeploy app from Streamlit dashboard
```

**Problem:** Slow page loads

**Solution:**
```python
# Add caching to API calls:
import streamlit as st

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_analytics_data(user_id):
    return api.get(f"/api/analytics/dashboard?days=7")
```

### Backend Issues

**Problem:** Database connection errors

**Solution:**
```bash
# Check DATABASE_URL is correct
heroku config:get DATABASE_URL

# Verify database is accessible
heroku pg:info

# Check connection pool settings in app/database.py
# Increase pool size if needed:
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Increase from default 5
    max_overflow=40
)
```

**Problem:** Background jobs not running

**Solution:**
```bash
# Check scheduler is running
curl https://your-backend-url/health/ready

# Check Procfile has worker process
# For Heroku, scale worker:
heroku ps:scale worker=1

# Check scheduler logs
heroku logs --tail --ps worker
```

**Problem:** Memory errors

**Solution:**
```bash
# Upgrade dyno size (Heroku)
heroku ps:resize web=standard-1x

# Or optimize memory usage:
# - Reduce background worker threads
# - Implement pagination for large queries
# - Clear unused cache
```

### Common Errors

**"Invalid credentials"**
- Check JWT_SECRET_KEY matches between deployments
- Token may have expired (24-hour default)
- Re-login to get fresh token

**"Rate limit exceeded"**
- Platform API rate limit hit
- Increase monitoring intervals
- Check job execution logs for rate limit errors

**"Database timeout"**
- Slow query causing timeout
- Run database maintenance: `python maintenance/database_maintenance.py --operation analyze`
- Check slow query logs

---

## Monitoring in Production

### Streamlit Cloud Monitoring

```
Streamlit Cloud Dashboard:
- View app analytics
- Check resource usage
- View deployment logs
- Monitor user sessions
```

### Backend Monitoring

```bash
# Heroku logs
heroku logs --tail --app social-analytics-backend

# Check metrics
heroku ps --app social-analytics-backend

# Database metrics
heroku pg:info --app social-analytics-backend

# Redis metrics (if using Heroku Redis)
heroku redis:info --app social-analytics-backend
```

### Set Up Alerts

1. **Uptime Monitoring:** Use UptimeRobot or Pingdom
   - Monitor: `https://your-backend-url/health`
   - Alert if down for > 2 minutes

2. **Error Tracking:** Configure Sentry
   ```bash
   heroku config:set SENTRY_DSN=your-sentry-dsn
   ```

3. **Performance:** Use Heroku metrics or CloudWatch

---

## Scaling Considerations

### Streamlit Cloud (Frontend)

- **Free tier:** Limited to 1 app, shared resources
- **Streamlit for Teams:** Multiple apps, more resources
- **Enterprise:** Dedicated resources, SLA

### Backend Scaling

**Heroku:**
```bash
# Scale web dynos
heroku ps:scale web=2

# Scale workers
heroku ps:scale worker=2

# Upgrade database
heroku addons:upgrade heroku-postgresql:standard-0
```

**AWS:**
- ECS auto-scaling (2-10 tasks)
- RDS read replicas
- ElastiCache cluster mode

---

## Cost Estimates

### Development/Testing (Low Traffic)

**Streamlit Cloud:** Free (1 public app)
**Heroku:**
- Eco dyno: $5/month
- Essential Postgres: $5/month
- Mini Redis: $3/month
**Total: ~$13/month**

### Production (Medium Traffic)

**Streamlit Cloud:** Free or Teams ($250/month for team features)
**Heroku:**
- Standard-1x web dyno: $25/month
- Standard-0 Postgres: $50/month
- Premium-0 Redis: $15/month
- Worker dyno: $25/month
**Total: ~$115-365/month**

**AWS (Alternative):**
- ECS Fargate: $45/month
- RDS db.t3.medium: $140/month
- ElastiCache: $90/month
- ALB: $25/month
**Total: ~$300/month**

---

## Security Best Practices

1. **Never commit secrets to Git**
   ```bash
   # Use .gitignore
   echo ".env" >> .gitignore
   echo "*.key" >> .gitignore
   ```

2. **Use environment variables**
   - Streamlit: Use st.secrets
   - Backend: Use environment variables or AWS Secrets Manager

3. **Enable HTTPS**
   - Streamlit Cloud: Automatic
   - Backend: Use Heroku SSL or AWS ALB with ACM certificate

4. **Rotate credentials regularly**
   ```bash
   # Update JWT secret
   heroku config:set JWT_SECRET_KEY=$(openssl rand -hex 32)

   # This will invalidate all existing sessions
   # Users will need to log in again
   ```

5. **Monitor for security issues**
   - Enable dependabot on GitHub
   - Run security scans: `safety check`
   - Monitor Sentry for suspicious activity

---

## Maintenance

### Regular Tasks

**Weekly:**
- Check error logs
- Review performance metrics
- Update dependencies (if needed)

**Monthly:**
- Database maintenance
- Review user feedback
- Update documentation
- Security patches

**Quarterly:**
- Performance optimization
- Feature updates
- User survey
- Disaster recovery test

### Backup Strategy

**Database backups:**
```bash
# Heroku: Automatic daily backups (Standard tier and above)
heroku pg:backups:capture --app social-analytics-backend

# Manual backup
heroku pg:backups:download --app social-analytics-backend

# AWS: Automated snapshots configured in RDS
```

---

## Support Resources

- **Streamlit Docs:** https://docs.streamlit.io
- **Streamlit Community:** https://discuss.streamlit.io
- **Heroku Docs:** https://devcenter.heroku.com
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **PostgreSQL Docs:** https://www.postgresql.org/docs/

---

**Deployment successful!** 🎉

Your Social Media Analytics Platform is now live and accessible to users worldwide.

**Last Updated:** 2025-12-22
**Version:** 1.0.0
