# Technical Overview & Features

Complete technical documentation of the Social Media Analytics Platform including features, architecture, APIs, and dependencies.

## Table of Contents

1. [Platform Features](#platform-features)
2. [Technical Architecture](#technical-architecture)
3. [Platform API Integrations](#platform-api-integrations)
4. [Python Packages](#python-packages)
5. [Database Schema](#database-schema)
6. [Security Features](#security-features)
7. [Performance Optimizations](#performance-optimizations)
8. [Monitoring & Operations](#monitoring--operations)

---

## Platform Features

### 1. Multi-Platform Social Media Monitoring

Monitor and analyze data from **4 major platforms:**

#### Twitch
- **Features:**
  - Track live streams and viewer counts
  - Monitor stream schedules and uptime
  - Analyze game categories and trends
  - Track viewer engagement over time
  - Single and bulk channel addition
  - Automated background monitoring
- **Data Collected:**
  - Stream title and category
  - Viewer count (real-time)
  - Stream start/end times
  - Stream duration
  - Is live status
- **Monitoring Frequency:** Every 15-120 minutes (configurable)

#### Twitter
- **Features:**
  - Track tweets from specific users
  - Monitor tweet engagement (likes, retweets, replies)
  - Analyze posting frequency
  - Sentiment analysis on tweet content
  - Track trending topics
  - Single and bulk user addition
- **Data Collected:**
  - Tweet text and metadata
  - Engagement metrics (likes, retweets, replies)
  - Tweet timestamp
  - Tweet ID for deduplication
- **Monitoring Frequency:** Every 30-120 minutes (configurable)

#### YouTube
- **Features:**
  - Track channel videos and uploads
  - Monitor video performance (views, likes, comments)
  - Analyze upload frequency
  - Track channel growth
  - Compare videos performance
  - Top performing videos identification
- **Data Collected:**
  - Video title, description
  - View count, like count, comment count
  - Upload timestamp
  - Video ID and metadata
- **Monitoring Frequency:** Every 60-120 minutes (configurable)

#### Reddit
- **Features:**
  - Monitor subreddit posts
  - Track post engagement (upvotes, comments)
  - Analyze subreddit activity
  - Monitor top posts
  - Track upvote ratio trends
  - Community sentiment analysis
- **Data Collected:**
  - Post title and content
  - Score (upvotes - downvotes)
  - Comment count
  - Upvote ratio
  - Post author and timestamp
- **Monitoring Frequency:** Every 30-120 minutes (configurable)

### 2. Analytics Engine

#### Sentiment Analysis
- **Technology:** Hugging Face Transformers (cardiffnlp/twitter-roberta-base-sentiment-latest)
- **Features:**
  - AI-powered sentiment analysis on text content
  - Positive, neutral, negative classification
  - Compound sentiment score (-1 to +1)
  - Batch processing for efficiency
  - Caching for repeated text analysis
- **Applies To:** Twitter tweets, YouTube video titles, Reddit posts
- **Accuracy:** State-of-the-art transformer model trained on social media data

#### Engagement Analytics
- **Platform-Specific Metrics:**
  - **Twitter:** Engagement rate = (likes + retweets + replies) / followers × 100
  - **YouTube:** Like ratio = likes / (likes + dislikes) × 100
  - **Reddit:** Upvote ratio = upvotes / (upvotes + downvotes)
  - **Twitch:** Average viewers, peak viewers, stream consistency
- **Features:**
  - Total engagement calculation
  - Average engagement per post/video
  - Engagement trends over time
  - Top performing content identification
  - Cross-platform comparison

#### Trend Analysis
- **Features:**
  - Time series analysis of engagement metrics
  - Posting frequency analysis
  - Growth rate calculation
  - Trend forecasting (simple moving average)
  - Best posting times identification
  - Day/hour heatmap generation
- **Visualization:**
  - Line charts for trends
  - Heatmaps for posting times
  - Bar charts for comparisons
  - Interactive Plotly charts

#### Best Posting Times
- **Features:**
  - Analyze historical data to find optimal posting times
  - Generate 24-hour × 7-day heatmap
  - Identify top 5 hours and top 3 days
  - Platform-specific recommendations
- **Use Case:** Schedule content for maximum engagement

### 3. Data Export

- **CSV Export:**
  - Export all platform data to CSV
  - Single platform or combined export
  - Date range filtering (7, 30, 90 days)
  - Streaming responses for large datasets
- **Summary Reports:**
  - JSON format comprehensive reports
  - Include analytics, engagement, sentiment
  - Date range customization
  - Platform selection

### 4. Real-Time Updates

- **WebSocket Integration:**
  - Live updates when new data is collected
  - Real-time monitoring job status
  - Instant notifications for events
  - Bi-directional communication
- **Update Types:**
  - Platform data updates (new tweets, videos, etc.)
  - Monitoring job status changes
  - Analytics refresh notifications
  - System alerts

### 5. Background Job Management

- **APScheduler Integration:**
  - Automated data collection jobs
  - Configurable monitoring intervals
  - Job persistence (survives app restarts)
  - Concurrent job execution
- **Job Control:**
  - Start/stop monitoring
  - Pause/resume jobs
  - View job execution history
  - Error tracking and retry logic
- **Scalability:** Supports 100+ concurrent monitoring jobs

### 6. User Management

- **Authentication:**
  - JWT-based authentication
  - Secure password hashing (bcrypt, cost=12)
  - Email verification workflow
  - Password reset via email
  - Session management
- **Multi-User Support:**
  - Complete data isolation between users
  - Per-user API credential storage
  - User-specific monitoring jobs
  - Individual analytics and exports

### 7. API Credential Management

- **Profile System:**
  - Store API credentials securely per platform
  - Multiple profiles per platform (different accounts)
  - Encrypted credential storage
  - Profile-based monitoring entity assignment
- **Security:**
  - Credentials encrypted at rest
  - Never exposed in API responses
  - Optional AWS Secrets Manager integration

### 8. Feedback System

- **User Feedback Collection:**
  - Bug reports
  - Feature requests
  - General feedback and questions
  - Satisfaction ratings (1-5 stars)
  - Screenshot attachment support
- **Admin Features:**
  - Feedback status tracking
  - Assignment to team members
  - Admin notes and resolution tracking
  - Feedback statistics and trends

---

## Technical Architecture

### Backend Stack

**Framework:** FastAPI
- Async/await support for high performance
- Automatic API documentation (Swagger/OpenAPI)
- Data validation with Pydantic
- Built-in security features
- WebSocket support

**Database:** PostgreSQL
- Relational database for structured data
- ACID compliance for data integrity
- Advanced indexing for performance
- Full-text search capabilities
- JSON column support for flexible data

**Cache:** Redis
- Session storage
- Response caching
- Rate limiting
- WebSocket connection management
- Pub/sub for real-time updates

**Background Jobs:** APScheduler
- Cron-like scheduling
- Job persistence in PostgreSQL
- Concurrent job execution (ThreadPoolExecutor)
- Error handling and retry logic
- Dynamic job management (add/remove at runtime)

**ORM:** SQLAlchemy 2.0
- Async support
- Type hints for IDE support
- Migration management with Alembic
- Connection pooling
- Relationship management

### Frontend Stack

**Framework:** Streamlit
- Python-native UI framework
- Automatic reactivity
- Built-in components (charts, forms, tables)
- Session state management
- Easy deployment to Streamlit Cloud

**Visualization:** Plotly + Altair
- Interactive charts
- Responsive design
- Export to PNG/SVG
- Zoom, pan, hover interactions

**HTTP Client:** requests
- Backend API communication
- Authentication header management
- Error handling
- JSON serialization

### Infrastructure Components

**Deployment:**
- Backend: AWS ECS Fargate (Docker containers)
- Frontend: Streamlit Cloud
- Database: AWS RDS PostgreSQL (Multi-AZ)
- Cache: AWS ElastiCache Redis
- Load Balancer: AWS Application Load Balancer
- Secrets: AWS Secrets Manager

**Monitoring:**
- Error Tracking: Sentry
- Alerting: PagerDuty
- Metrics: CloudWatch + Prometheus
- Logging: CloudWatch Logs (structured JSON)
- Health Checks: Custom /health endpoints

**CI/CD:**
- Version Control: Git/GitHub
- Automated Testing: pytest + GitHub Actions
- Deployment: AWS CLI + deploy.sh script
- Database Migrations: Alembic

---

## Platform API Integrations

### Twitch API

**Authentication:** OAuth 2.0 Client Credentials Flow

**Required Credentials:**
- Client ID (from Twitch Developer Console)
- Client Secret (from Twitch Developer Console)

**Setup Instructions:**
1. Go to https://dev.twitch.tv/console
2. Click "Register Your Application"
3. Fill in:
   - Name: "Social Analytics Monitor"
   - OAuth Redirect URLs: http://localhost
   - Category: Analytics Tool
4. Copy Client ID and Client Secret

**API Endpoints Used:**
- `GET /helix/streams` - Get live stream information
- `GET /helix/users` - Get user/channel information
- `GET /helix/channels` - Get channel details

**Rate Limits:**
- 800 requests per minute per client ID
- Rate limit headers included in responses

**Implementation:**
```python
# File: backend/app/twitch/twitch_api.py
class TwitchAPI:
    def get_stream_info(self, broadcaster_id: str):
        # Fetches current stream status
```

### Twitter API v2

**Authentication:** Bearer Token (OAuth 2.0 App-Only)

**Required Credentials:**
- Bearer Token (from Twitter Developer Portal)

**Setup Instructions:**
1. Go to https://developer.twitter.com/
2. Create a new project and app
3. Navigate to "Keys and Tokens"
4. Generate Bearer Token
5. Copy Bearer Token

**API Endpoints Used:**
- `GET /2/users/by/username/:username` - Get user ID
- `GET /2/users/:id/tweets` - Get user tweets
- `GET /2/tweets` - Get tweet details

**Rate Limits:**
- 300 requests per 15 minutes (app-level)
- 900 requests per 15 minutes (user-level)

**Implementation:**
```python
# File: backend/app/twitter/twitter_api.py
class TwitterAPI:
    def get_user_tweets(self, user_id: str, max_results: int = 100):
        # Fetches recent tweets from user
```

### YouTube Data API v3

**Authentication:** API Key

**Required Credentials:**
- API Key (from Google Cloud Console)

**Setup Instructions:**
1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable "YouTube Data API v3"
4. Go to Credentials → Create Credentials → API Key
5. Copy API Key
6. (Optional) Restrict API key to YouTube Data API v3

**API Endpoints Used:**
- `GET /youtube/v3/channels` - Get channel information
- `GET /youtube/v3/search` - Search for videos
- `GET /youtube/v3/videos` - Get video statistics

**Rate Limits:**
- 10,000 quota units per day (default)
- Different operations cost different units
- Search: 100 units, Videos: 1 unit

**Implementation:**
```python
# File: backend/app/youtube/youtube_api.py
class YouTubeAPI:
    def get_channel_videos(self, channel_id: str, max_results: int = 50):
        # Fetches recent videos from channel
```

### Reddit API

**Authentication:** OAuth 2.0 Client Credentials

**Required Credentials:**
- Client ID (from Reddit App Preferences)
- Client Secret (from Reddit App Preferences)
- User Agent (unique identifier for your app)

**Setup Instructions:**
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Select "script" as app type
4. Fill in name and description
5. Redirect URI: http://localhost:8000
6. Copy Client ID (under app name) and Client Secret

**API Endpoints Used:**
- `GET /r/:subreddit/new` - Get new posts
- `GET /r/:subreddit/hot` - Get hot posts
- `GET /r/:subreddit/about` - Get subreddit info

**Rate Limits:**
- 60 requests per minute
- User agent must be unique and descriptive

**Implementation:**
```python
# File: backend/app/reddit/reddit_api.py
class RedditAPI:
    def get_subreddit_posts(self, subreddit: str, limit: int = 100):
        # Fetches recent posts from subreddit
```

---

## Python Packages

### Backend Dependencies (requirements.txt)

#### Core Framework
```python
fastapi==0.104.1           # Modern async web framework
uvicorn[standard]==0.24.0  # ASGI server for FastAPI
pydantic==2.5.2           # Data validation using type hints
```

**Why:** FastAPI provides high performance, automatic API docs, and built-in validation. Uvicorn is the recommended ASGI server. Pydantic ensures type safety.

#### Database
```python
sqlalchemy==2.0.23        # SQL toolkit and ORM
psycopg2-binary==2.9.9    # PostgreSQL adapter
alembic==1.13.0           # Database migration tool
```

**Why:** SQLAlchemy provides robust ORM with async support. psycopg2 is the PostgreSQL driver. Alembic handles schema migrations safely.

#### Authentication & Security
```python
python-jose[cryptography]==3.3.0  # JWT tokens
passlib[bcrypt]==1.7.4           # Password hashing
python-multipart==0.0.6          # Form data parsing
bcrypt==4.1.1                    # Bcrypt hashing
```

**Why:** JWT for stateless authentication. Bcrypt for secure password hashing (industry standard). Passlib provides unified interface.

#### Background Jobs
```python
apscheduler==3.10.4       # Job scheduling library
```

**Why:** APScheduler allows persistent, cron-like job scheduling with PostgreSQL job store for reliability.

#### Caching
```python
redis==5.0.1              # Redis client
hiredis==2.2.3           # C parser for Redis (performance)
```

**Why:** Redis provides fast in-memory caching, session storage, and pub/sub. hiredis improves performance.

#### Platform APIs
```python
requests==2.31.0          # HTTP library
tweepy==4.14.0           # Twitter API wrapper (optional)
prawcore==2.3.0          # Reddit API core (optional)
```

**Why:** requests for HTTP calls to platform APIs. Tweepy and prawcore simplify platform integrations but can be replaced with direct API calls.

#### Analytics & ML
```python
transformers==4.35.2      # Hugging Face transformers
torch==2.1.1             # PyTorch (transformer backend)
sentencepiece==0.1.99    # Tokenization
pandas==2.1.4            # Data analysis
numpy==1.26.2            # Numerical computing
scikit-learn==1.3.2      # Machine learning utilities
```

**Why:** Transformers for state-of-the-art sentiment analysis. PyTorch as the backend. Pandas for data manipulation. NumPy for numerical operations. Scikit-learn for ML utilities.

#### Monitoring & Logging
```python
sentry-sdk[fastapi]==1.39.1  # Error tracking
python-json-logger==2.0.7    # Structured JSON logging
prometheus-client==0.19.0    # Metrics exposition
```

**Why:** Sentry captures and reports errors with full context. JSON logging for CloudWatch. Prometheus for metrics.

#### AWS Integration
```python
boto3==1.34.0            # AWS SDK
```

**Why:** Interact with AWS services (Secrets Manager, CloudWatch, S3, etc.)

#### Testing
```python
pytest==7.4.3            # Testing framework
pytest-asyncio==0.21.1   # Async test support
pytest-cov==4.1.0        # Coverage reporting
httpx==0.25.2           # Async HTTP client for testing
faker==20.1.0           # Test data generation
```

**Why:** pytest is the standard Python testing framework. Coverage ensures code quality. httpx for async API testing.

#### Utilities
```python
python-dateutil==2.8.2   # Date utilities
pytz==2023.3            # Timezone support
email-validator==2.1.0   # Email validation
```

**Why:** Reliable date/time handling, timezone support, email validation for user registration.

### Frontend Dependencies (frontend/requirements.txt)

#### UI Framework
```python
streamlit==1.29.0        # Web app framework
```

**Why:** Streamlit allows building interactive web apps with pure Python. No HTML/CSS/JS needed.

#### HTTP Client
```python
requests==2.31.0         # HTTP library
```

**Why:** Communicate with FastAPI backend via REST API.

#### Data & Visualization
```python
pandas==2.1.4           # Data manipulation
plotly==5.18.0          # Interactive charts
altair==5.2.0           # Declarative visualizations
matplotlib==3.8.2       # Static plots (optional)
```

**Why:** Pandas for data processing. Plotly for interactive charts. Altair for elegant declarative visualizations.

#### Utilities
```python
python-dateutil==2.8.2  # Date utilities
pytz==2023.3           # Timezone support
```

**Why:** Handle dates and timezones consistently.

---

## Database Schema

### User Management

**users** table:
- id (Primary Key)
- email (Unique, Indexed)
- hashed_password
- is_active, is_verified
- created_at, updated_at

**api_profiles** table:
- id (Primary Key)
- user_id (Foreign Key → users)
- platform (twitch, twitter, youtube, reddit)
- profile_name
- Credentials (client_id, client_secret, bearer_token, api_key, user_agent)
- created_at, updated_at

### Platform Entities

**twitch_channels** table:
- id, user_id, profile_id
- channel_name, broadcaster_id
- created_at

**twitter_users** table:
- id, user_id, profile_id
- username, twitter_user_id
- created_at

**youtube_channels** table:
- id, user_id, profile_id
- channel_name, channel_id
- created_at

**reddit_subreddits** table:
- id, user_id, profile_id
- subreddit_name
- created_at

### Platform Data

**twitch_stream_records** table:
- id, channel_id
- stream_id, title, game_name
- viewer_count, started_at, ended_at
- is_live, recorded_at
- Indexes: channel_id, recorded_at, is_live

**tweets** table:
- id, twitter_user_id
- tweet_id (Unique), text
- created_at, likes, retweets, replies
- fetched_at
- Indexes: twitter_user_id, created_at, tweet_id

**youtube_videos** table:
- id, channel_id
- video_id (Unique), title, description
- published_at, view_count, like_count, comment_count
- fetched_at
- Indexes: channel_id, published_at, video_id

**reddit_posts** table:
- id, subreddit_id
- post_id (Unique), title, content, author
- created_at, score, num_comments, upvote_ratio
- fetched_at
- Indexes: subreddit_id, created_at, post_id

### Monitoring & Jobs

**monitoring_jobs** table:
- id, user_id, platform, entity_id
- job_id (APScheduler job ID)
- interval_minutes, is_active
- created_at, updated_at

**job_executions** table:
- id, job_id
- started_at, completed_at
- status (success, failed, rate_limited)
- records_collected, error_message

### Analytics

**sentiment_cache** table:
- id, text_hash (MD5, Unique)
- negative, neutral, positive, compound
- created_at
- Index: text_hash (for quick lookups)

**analytics_reports** table (optional):
- id, user_id, report_type
- report_data (JSON)
- created_at

### Feedback

**feedback** table:
- id, user_id
- type (bug, feature_request, improvement, question, other)
- status (new, reviewing, planned, in_progress, completed, wont_fix)
- title, description
- page_url, browser_info, screenshot_url
- satisfaction_rating, feature_rating
- admin_notes, assigned_to
- created_at, updated_at, resolved_at

### Performance Indexes

**Key indexes for performance:**
- All foreign keys (user_id, profile_id, channel_id, etc.)
- Timestamp columns (created_at, recorded_at, fetched_at)
- Status flags (is_active, is_live)
- Unique constraints (email, tweet_id, video_id, etc.)
- Composite indexes for common queries:
  - (user_id, created_at DESC) for user's recent data
  - (channel_id, recorded_at DESC) for entity's timeline
  - (user_id, platform) for platform filtering

---

## Security Features

### Authentication & Authorization

1. **JWT Tokens:**
   - 24-hour expiration (configurable)
   - HS256 algorithm
   - Includes user email in payload
   - Stateless (no server-side session storage)

2. **Password Security:**
   - Bcrypt hashing (cost factor 12)
   - Minimum 8 characters
   - Complexity requirements
   - Never stored in plain text
   - Never logged or exposed in API

3. **Multi-User Isolation:**
   - All queries filtered by user_id
   - Row-level security
   - No cross-user data access

### API Security

1. **CORS (Cross-Origin Resource Sharing):**
   - Whitelist allowed origins
   - Credentials allowed
   - Preflight request handling

2. **Rate Limiting:**
   - Per-user rate limits (Redis-based)
   - 100 requests per 15 minutes default
   - 429 Too Many Requests response
   - Retry-After header

3. **Request Validation:**
   - Pydantic models for all inputs
   - Type checking
   - Size limits (max 10MB request body)
   - SQL injection prevention (parameterized queries)
   - XSS prevention (input sanitization)

### Data Security

1. **Encryption:**
   - TLS/HTTPS for all communications
   - At-rest encryption for database (AWS RDS)
   - Encrypted Redis cache
   - Secrets Manager for sensitive credentials

2. **Credential Storage:**
   - API credentials encrypted before storage
   - AES-256 encryption
   - Environment variables for keys
   - AWS Secrets Manager integration (optional)

3. **Audit Logging:**
   - All security events logged
   - Failed login attempts tracked
   - Suspicious activity detection
   - IP address logging

### Security Headers

- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Frame-Options (Clickjacking protection)
- X-Content-Type-Options (MIME sniffing protection)
- X-XSS-Protection

---

## Performance Optimizations

### Backend Optimizations

1. **Database:**
   - Connection pooling (20 connections, 40 overflow)
   - Strategic indexes on all queries
   - ANALYZE for query planner optimization
   - Pagination for large result sets
   - Batch inserts for bulk operations

2. **Caching:**
   - Redis caching for expensive operations
   - Sentiment analysis cache (MD5 hashing)
   - Response caching for read-heavy endpoints
   - 5-minute TTL for analytics
   - Cache invalidation on updates

3. **Async/Await:**
   - FastAPI async endpoints
   - Non-blocking I/O operations
   - Concurrent platform API calls
   - ThreadPoolExecutor for background jobs

4. **Query Optimization:**
   - Lazy loading for relationships
   - Selective field loading
   - Query result caching
   - Avoid N+1 queries

### Frontend Optimizations

1. **Streamlit Caching:**
   - @st.cache_data for expensive computations
   - TTL-based cache invalidation
   - User-scoped caching

2. **Pagination:**
   - Lazy loading of large datasets
   - Virtual scrolling for tables
   - Limit initial data load

3. **Efficient Visualizations:**
   - Plotly for interactive charts
   - Downsample data for charts (max 1000 points)
   - Client-side rendering

---

## Monitoring & Operations

### Health Checks

1. **/health** - Basic liveness probe
2. **/health/ready** - Readiness probe (checks DB, Redis, scheduler)
3. **/health/live** - Kubernetes liveness
4. **/health/detailed** - Comprehensive status

### Metrics

1. **Application Metrics:**
   - Total requests, success rate, error rate
   - Response time percentiles (P50, P95, P99)
   - Active users, active jobs
   - WebSocket connections

2. **Background Job Metrics:**
   - Jobs executed, success/failure counts
   - Average execution time
   - Rate limit hits
   - Queue depth

3. **Cache Metrics:**
   - Hit rate, miss rate
   - Total hits/misses
   - Cache size

4. **Database Metrics:**
   - Connection pool utilization
   - Query performance
   - Slow query log
   - Table sizes

### Logging

1. **Structured JSON Logging:**
   - timestamp, level, message, context
   - Request ID for tracing
   - User ID (when authenticated)
   - IP address
   - CloudWatch integration

2. **Log Levels:**
   - DEBUG: Development details
   - INFO: General information
   - WARNING: Potential issues
   - ERROR: Error events
   - CRITICAL: System failures

### Error Tracking

1. **Sentry Integration:**
   - Automatic exception capture
   - Stack traces with context
   - User identification
   - Breadcrumb trail
   - Performance monitoring

2. **Alerts:**
   - PagerDuty for critical issues
   - CloudWatch alarms for AWS services
   - Email notifications for deployments
   - Slack integration for team updates

---

## API Documentation

**Automatic Documentation:**
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

**Key Endpoint Categories:**
1. Authentication (`/api/auth/`)
2. Platform APIs (`/api/twitch/`, `/api/twitter/`, etc.)
3. Profile Management (`/api/profiles/`)
4. Background Jobs (`/api/jobs/`)
5. Analytics (`/api/analytics/`)
6. Export (`/api/export/`)
7. Feedback (`/api/feedback/`)
8. Health & Metrics (`/health`, `/metrics`)

---

## Development Setup

### Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-test.txt

# Create .env file
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
pip install -r requirements.txt

# Start frontend
streamlit run streamlit_app.py
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m e2e
```

---

## Deployment Architecture

```
                    Internet
                       │
                       ▼
              ┌────────────────┐
              │ Route 53 (DNS) │
              └────────┬───────┘
                       │
        ┌──────────────┼──────────────┐
        │                             │
        ▼                             ▼
┌───────────────┐            ┌────────────────┐
│ Streamlit     │            │  ALB (HTTPS)   │
│ Cloud         │◄─REST API─►│  AWS           │
│ (Frontend)    │            └───────┬────────┘
└───────────────┘                    │
                                     ▼
                            ┌────────────────┐
                            │  ECS Fargate   │
                            │  (Backend)     │
                            └───────┬────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
          ┌───────────┐     ┌──────────┐     ┌──────────┐
          │ RDS       │     │ElastiCache│    │ Secrets  │
          │PostgreSQL │     │  Redis    │    │ Manager  │
          └───────────┘     └──────────┘     └──────────┘
```

---

**This platform represents a complete, production-ready social media analytics solution with enterprise-grade features, security, and scalability.**

**Last Updated:** 2025-12-22
**Version:** 1.0.0
