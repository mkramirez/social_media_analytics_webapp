# Social Media Analytics Platform - Web App Version

Cloud-deployed multi-user web application for monitoring and analyzing social media platforms.

## Project Structure

```
social_media_analytics_webapp/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── database.py        # Database connection and session
│   │   ├── config.py          # Configuration management
│   │   ├── routers/           # API endpoints
│   │   │   ├── auth.py
│   │   │   ├── profiles.py
│   │   │   ├── twitch.py
│   │   │   ├── twitter.py
│   │   │   ├── youtube.py
│   │   │   ├── reddit.py
│   │   │   ├── jobs.py
│   │   │   ├── analytics.py
│   │   │   └── export.py
│   │   ├── models/            # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── profile.py
│   │   │   ├── platform_entities.py
│   │   │   ├── collected_data.py
│   │   │   └── jobs.py
│   │   ├── services/          # Business logic
│   │   │   ├── auth_service.py
│   │   │   ├── credential_service.py
│   │   │   ├── scheduler_service.py
│   │   │   ├── websocket_manager.py
│   │   │   └── s3_service.py
│   │   ├── middleware/        # Middleware components
│   │   │   ├── auth.py
│   │   │   └── rate_limit.py
│   │   ├── platforms/         # Platform-specific code (from desktop app)
│   │   │   ├── twitch/
│   │   │   │   ├── twitch_api.py
│   │   │   │   └── collector.py
│   │   │   ├── twitter/
│   │   │   ├── youtube/
│   │   │   └── reddit/
│   │   ├── analytics/         # Analytics engine (from desktop app)
│   │   │   ├── sentiment_analyzer.py
│   │   │   ├── engagement_calculator.py
│   │   │   └── trend_analyzer.py
│   │   ├── export/            # Export functionality (from desktop app)
│   │   │   └── export_manager.py
│   │   └── utils/             # Utility functions
│   │       ├── security.py
│   │       └── validators.py
│   ├── alembic/               # Database migrations
│   │   └── versions/
│   ├── tests/                 # Backend tests
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile            # Docker configuration
│
├── frontend/                  # Streamlit frontend
│   ├── streamlit_app.py      # Main Streamlit application
│   ├── pages/                 # Streamlit pages
│   │   ├── 01_home.py
│   │   ├── 02_profiles.py
│   │   ├── 03_twitch.py
│   │   ├── 04_twitter.py
│   │   ├── 05_youtube.py
│   │   ├── 06_reddit.py
│   │   ├── 07_analytics.py
│   │   ├── 08_export.py
│   │   └── 09_settings.py
│   ├── components/            # Reusable UI components
│   │   ├── charts.py
│   │   ├── api_client.py
│   │   └── auth_guard.py
│   ├── assets/               # Static assets (images, CSS)
│   ├── requirements.txt      # Frontend dependencies
│   └── Dockerfile           # Docker configuration
│
├── docker-compose.yml        # Local development setup
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore file
└── README.md                # This file
```

## Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **PostgreSQL** - Multi-user database
- **SQLAlchemy 2.0** - ORM with async support
- **APScheduler** - Background job scheduling
- **Redis** - Session storage and caching
- **AWS Secrets Manager** - Secure credential storage

### Frontend
- **Streamlit** - Rapid UI development
- **Plotly** - Interactive charts
- **Requests** - HTTP client for API calls

### Deployment
- **Backend**: AWS ECS Fargate (Docker)
- **Frontend**: Streamlit Cloud
- **Database**: AWS RDS PostgreSQL
- **Storage**: AWS S3 (exports)

## Features

- **Multi-user Authentication** - Secure JWT-based auth
- **Platform Monitoring**:
  - Twitch: Stream status, viewer counts, chat activity
  - Twitter: Tweet collection, sentiment analysis
  - YouTube: Video uploads, channel analytics
  - Reddit: Post submissions, community engagement
- **Background Jobs** - APScheduler for continuous monitoring
- **Analytics Dashboard** - Sentiment, engagement, trends
- **Data Export** - CSV and PDF reports
- **Real-time Updates** - WebSocket support
- **Secure Credentials** - Encrypted storage

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

### Local Development

1. **Clone and setup**:
   ```bash
   cd social_media_analytics_webapp
   ```

2. **Backend setup**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Database setup**:
   ```bash
   # Create PostgreSQL database
   createdb social_analytics

   # Run migrations
   alembic upgrade head
   ```

4. **Start backend**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. **Frontend setup** (new terminal):
   ```bash
   cd frontend
   pip install -r requirements.txt
   streamlit run streamlit_app.py
   ```

### Using Docker Compose

```bash
docker-compose up --build
```

Access:
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:8501

## Environment Variables

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/social_analytics

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret

# AWS (for production)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_BUCKET=social-analytics-exports

# API URL
API_BASE_URL=http://localhost:8000
```

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Deployment

### Backend (AWS ECS)
```bash
# Build and push Docker image
docker build -t social-analytics-backend:latest ./backend
docker tag social-analytics-backend:latest <ECR_URI>:latest
docker push <ECR_URI>:latest

# Deploy to ECS
aws ecs update-service --cluster social-analytics --service backend --force-new-deployment
```

### Frontend (Streamlit Cloud)
- Push to GitHub
- Connect repository in Streamlit Cloud
- Configure secrets in Streamlit Cloud dashboard
- Deploy

## Migration from Desktop Version

The desktop version (Tkinter) remains in `social_media_analytics_project/`.

**Migrated Code** (reused in web app):
- ✅ API clients (Twitch, Twitter, YouTube, Reddit)
- ✅ Analytics engine (sentiment, engagement, trends)
- ✅ Export functionality
- ✅ Database schemas (adapted to PostgreSQL)

**New Code** (web app only):
- Authentication system
- REST API endpoints
- Background job scheduler
- Streamlit UI
- Multi-user data isolation

## Testing

```bash
# Backend tests
cd backend
pytest

# With coverage
pytest --cov=app tests/
```

## License

Same as desktop version

## Version

Web App v1.0 (migrated from Desktop v1.0)

## Original Desktop Version

Located in: `C:\Users\vyajr\social_media_analytics_project\`
