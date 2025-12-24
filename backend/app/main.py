"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db

# Import routers
from app.routers import auth, profiles, twitch, twitter, youtube, reddit, analytics, export, websocket, health
# Other routers will be added in later phases
# from app.routers import jobs

# Import middlewares
from app.middleware import (
    CacheMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    HTTPSRedirectMiddleware,
    RequestValidationMiddleware,
    AuditLogMiddleware
)

# Create FastAPI application
app = FastAPI(
    title="Social Media Analytics API",
    description="Multi-platform social media monitoring and analytics API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security middlewares (Phase 6: Security & Production)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(RequestValidationMiddleware, max_content_length=10 * 1024 * 1024)
app.add_middleware(AuditLogMiddleware)

# Add caching middleware (Phase 5: Performance)
app.add_middleware(
    CacheMiddleware,
    default_ttl=300,  # 5 minutes
    cache_prefixes=["/api/analytics", "/api/export/summary"]
)

# Add rate limiting middleware (Phase 5: Performance)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    # Initialize database (create tables if they don't exist)
    init_db()

    # Start APScheduler for background monitoring jobs
    from app.services.scheduler_service import start_scheduler
    start_scheduler()

    print("🚀 FastAPI application started!")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    print(f"🗄️  Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    print(f"⏰ Background scheduler: Active")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    # Shutdown APScheduler
    from app.services.scheduler_service import shutdown_scheduler
    shutdown_scheduler()

    print("👋 FastAPI application shutting down...")


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "Social Media Analytics API",
        "version": "1.0.0",
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs"
    }


# Include routers
app.include_router(health.router, tags=["Health & Monitoring"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(twitch.router, prefix="/api/twitch", tags=["Twitch"])
app.include_router(twitter.router, prefix="/api/twitter", tags=["Twitter"])
app.include_router(youtube.router, prefix="/api/youtube", tags=["YouTube"])
app.include_router(reddit.router, prefix="/api/reddit", tags=["Reddit"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(websocket.router, prefix="/api", tags=["WebSocket"])
# Other routers will be added in later phases
# app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
