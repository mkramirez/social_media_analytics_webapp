# Setup Instructions - Social Media Analytics Web App

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (for local database)
- Git (optional, for version control)

## Quick Start (Local Development)

### 1. Start Infrastructure Services

Start PostgreSQL and Redis using Docker Compose:

```bash
cd C:\Users\vyajr\social_media_analytics_webapp
docker-compose up -d
```

Verify services are running:
```bash
docker-compose ps
```

You should see `db` and `redis` services running.

### 2. Set Up Backend

#### Create virtual environment:
```bash
cd backend
python -m venv venv
```

#### Activate virtual environment:
Windows:
```bash
venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

#### Install dependencies:
```bash
pip install -r requirements.txt
```

#### Configure environment:
Create `.env` file in project root (copy from `.env.example`):
```bash
cd ..
copy .env.example .env
```

Edit `.env` and update the DATABASE_URL if needed:
```
DATABASE_URL=postgresql://socialanalytics:devpassword@localhost:5432/social_analytics
```

#### Run database migrations (Phase 1 will create migrations):
```bash
cd backend
# Will be: alembic upgrade head
```

#### Start the backend:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

The backend API should now be running at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. Set Up Frontend (After Phase 1 completion)

Open a new terminal:

```bash
cd C:\Users\vyajr\social_media_analytics_webapp\frontend
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The frontend should open automatically at: http://localhost:8501

## Development Workflow

1. **Make code changes** in `backend/app/` or `frontend/`
2. **Backend auto-reloads** with `--reload` flag
3. **Frontend auto-reloads** when you save files
4. **Check API docs** at http://localhost:8000/docs
5. **Test endpoints** using the interactive Swagger UI

## Database Management

### Access PostgreSQL:
```bash
docker exec -it social_media_analytics_webapp-db-1 psql -U socialanalytics -d social_analytics
```

### Common psql commands:
```sql
\dt          -- List tables
\d tablename -- Describe table
SELECT * FROM users;  -- Query users
\q           -- Quit
```

### Reset database:
```bash
docker-compose down -v
docker-compose up -d
cd backend
alembic upgrade head
```

## Troubleshooting

### Port already in use:
```bash
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill the process (Windows)
taskkill /PID <PID> /F
```

### Database connection issues:
```bash
# Check if PostgreSQL is running
docker-compose ps

# Check PostgreSQL logs
docker-compose logs db

# Restart services
docker-compose restart
```

### Module import errors:
Make sure you're in the right directory and virtual environment is activated:
```bash
# Should be in backend/ directory
cd backend

# Activate venv
venv\Scripts\activate

# Reinstall requirements
pip install -r requirements.txt
```

## Next Steps (Phase 1)

1. ✅ Project structure created
2. ✅ Backend foundation setup
3. 🔄 Create database models (User, Profile)
4. 🔄 Implement authentication endpoints
5. 🔄 Create Streamlit login/register pages
6. 🔄 Test end-to-end auth flow

## Project Status

- **Desktop Version**: `C:\Users\vyajr\social_media_analytics_project\` (unchanged, still working)
- **Web Version**: `C:\Users\vyajr\social_media_analytics_webapp\` (new, in development)

The desktop version remains fully functional. All new development happens in the web app folder.
