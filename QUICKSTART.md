# Quick Start Guide - Phase 1

## Prerequisites
- Python 3.11+ installed
- Docker Desktop installed and running

## Step-by-Step Setup (5 minutes)

### 1. Start Database Services

Open a terminal and run:

```bash
cd C:\Users\vyajr\social_media_analytics_webapp
docker-compose up -d
```

Wait for PostgreSQL and Redis to start (~30 seconds). Verify they're running:

```bash
docker-compose ps
```

You should see both `db` and `redis` services with status "Up".

### 2. Set Up Backend

Open a **new terminal** and run:

```bash
cd C:\Users\vyajr\social_media_analytics_webapp\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

This will:
- Create a virtual environment
- Activate it
- Install all dependencies (~2-3 minutes)

### 3. Start the Backend API

With the virtual environment still activated:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

You should see:
```
🚀 FastAPI application started!
📊 Environment: development
🗄️  Database: localhost:5432/social_analytics
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**✅ Backend is ready!** Visit http://localhost:8000/docs to see the API documentation.

### 4. Start the Frontend

Open a **third terminal** and run:

```bash
cd C:\Users\vyajr\social_media_analytics_webapp\frontend
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Your browser should automatically open to http://localhost:8501

**✅ Frontend is ready!**

## Testing the Application

### Register a New Account

1. On the login page, click **"Create Account"**
2. Fill in the registration form:
   - Email: `test@example.com`
   - Username: `testuser`
   - Password: `Test123!@#` (must meet requirements)
   - Confirm password
3. Click **"Register"**

You should be automatically logged in!

### Login

1. If you're not logged in, enter:
   - Username: `testuser` (or your email)
   - Password: `Test123!@#`
2. Click **"Login"**

### Test the API Directly

Visit http://localhost:8000/docs and try:

1. **POST /api/auth/register** - Register a new user
2. **POST /api/auth/login** - Get a JWT token
3. **GET /api/auth/me** - Get current user info (requires token)

## What's Working in Phase 1

✅ **Backend Features:**
- User registration with validation
- Secure login with JWT tokens
- Password hashing (bcrypt)
- Session management
- PostgreSQL database
- API documentation (Swagger UI)

✅ **Frontend Features:**
- Login page
- Registration page
- Session persistence
- API health checks
- Responsive UI

## Troubleshooting

### "Cannot connect to server"
- Make sure the backend is running (Step 3)
- Check if port 8000 is available
- Visit http://localhost:8000/health to verify

### "Database connection error"
- Make sure Docker is running
- Check if PostgreSQL container is up: `docker-compose ps`
- Restart services: `docker-compose restart`

### "Port already in use"
```bash
# Windows - find and kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### "ModuleNotFoundError"
- Make sure virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt`

## Next Steps

**Phase 1 is complete!** 🎉

Phase 2 will add:
- Twitch platform integration
- Channel monitoring
- Background jobs with APScheduler
- Real-time updates

## Stopping the Application

### Stop Frontend:
Press `Ctrl+C` in the Streamlit terminal

### Stop Backend:
Press `Ctrl+C` in the Uvicorn terminal

### Stop Database:
```bash
docker-compose down
```

To completely reset (deletes all data):
```bash
docker-compose down -v
```

## Project Structure

```
social_media_analytics_webapp/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── main.py       # API entry point ✅
│   │   ├── models/       # Database models ✅
│   │   ├── routers/      # API endpoints ✅
│   │   ├── services/     # Business logic ✅
│   │   └── middleware/   # Auth middleware ✅
│   └── requirements.txt
│
├── frontend/             # Streamlit frontend
│   ├── streamlit_app.py  # Main app ✅
│   └── components/       # Reusable components ✅
│
├── docker-compose.yml    # PostgreSQL + Redis ✅
├── .env                  # Environment variables ✅
└── README.md            # Documentation ✅
```

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review backend logs in the terminal
3. Check database logs: `docker-compose logs db`
4. Verify `.env` file configuration

---

**Version**: Phase 1 Complete
**Next Phase**: Twitch Integration (Phase 2)
