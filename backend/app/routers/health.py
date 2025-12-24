"""Health check and monitoring endpoints for production."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import psutil
import os

from app.database import get_db
from app.services.redis_service import is_redis_available, get_redis_client
from app.services.logging_service import app_metrics
from app.services.websocket_service import websocket_manager
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns 200 if application is running.
    Used by load balancers for liveness probes.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe for Kubernetes/ECS.

    Checks if application is ready to serve traffic.
    Verifies database and Redis connectivity.
    """
    checks = {
        "database": False,
        "redis": False,
        "scheduler": False
    }

    errors = []

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        errors.append(f"Database: {str(e)}")

    # Check Redis
    try:
        checks["redis"] = is_redis_available()
        if not checks["redis"]:
            errors.append("Redis: Not available")
    except Exception as e:
        errors.append(f"Redis: {str(e)}")

    # Check scheduler
    try:
        from app.services.scheduler_service import get_scheduler
        scheduler = get_scheduler()
        checks["scheduler"] = scheduler is not None and scheduler.running
        if not checks["scheduler"]:
            errors.append("Scheduler: Not running")
    except Exception as e:
        errors.append(f"Scheduler: {str(e)}")

    # Determine overall status
    all_checks_passed = all(checks.values())

    if all_checks_passed:
        return {
            "status": "ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "checks": checks,
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe for Kubernetes/ECS.

    Returns 200 if application process is alive.
    Kubernetes will restart pod if this fails.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "pid": os.getpid()
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with component status.

    Provides comprehensive system health information.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "components": {},
        "system": {}
    }

    # Database health
    try:
        result = db.execute(text("SELECT version()"))
        db_version = result.scalar()
        health_status["components"]["database"] = {
            "status": "healthy",
            "type": "postgresql",
            "version": db_version.split()[1] if db_version else "unknown"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Redis health
    try:
        if is_redis_available():
            redis_client = get_redis_client()
            redis_info = redis_client.info()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "version": redis_info.get("redis_version", "unknown"),
                "used_memory": redis_info.get("used_memory_human", "unknown")
            }
        else:
            health_status["components"]["redis"] = {
                "status": "unavailable",
                "message": "Redis not configured or unreachable"
            }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Scheduler health
    try:
        from app.services.scheduler_service import get_scheduler
        scheduler = get_scheduler()
        if scheduler and scheduler.running:
            jobs = scheduler.get_jobs()
            health_status["components"]["scheduler"] = {
                "status": "healthy",
                "running": True,
                "active_jobs": len(jobs)
            }
        else:
            health_status["components"]["scheduler"] = {
                "status": "unhealthy",
                "running": False
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["scheduler"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # WebSocket health
    try:
        health_status["components"]["websocket"] = {
            "status": "healthy",
            "active_connections": websocket_manager.get_connection_count(),
            "active_users": len(websocket_manager.get_active_users())
        }
    except Exception as e:
        health_status["components"]["websocket"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # System metrics
    try:
        health_status["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "process_count": len(psutil.pids())
        }
    except Exception as e:
        health_status["system"] = {
            "error": f"Unable to gather system metrics: {str(e)}"
        }

    return health_status


@router.get("/metrics")
async def application_metrics():
    """
    Application metrics endpoint.

    Returns performance and usage metrics.
    Can be scraped by Prometheus or CloudWatch.
    """
    metrics = app_metrics.get_metrics()

    # Add additional calculated metrics
    metrics["cache"]["hit_rate_percent"] = app_metrics.get_cache_hit_rate()
    metrics["requests"]["error_rate_percent"] = app_metrics.get_error_rate()

    # Add WebSocket metrics
    metrics["websocket"]["active_connections"] = websocket_manager.get_connection_count()
    metrics["websocket"]["active_users"] = len(websocket_manager.get_active_users())

    return metrics


@router.get("/metrics/prometheus")
async def prometheus_metrics():
    """
    Metrics in Prometheus format.

    Outputs metrics that can be scraped by Prometheus.
    """
    metrics = app_metrics.get_metrics()

    lines = []

    # Request metrics
    lines.append(f"# HELP http_requests_total Total HTTP requests")
    lines.append(f"# TYPE http_requests_total counter")
    lines.append(f"http_requests_total {metrics['requests']['total']}")

    lines.append(f"# HELP http_requests_success Successful HTTP requests")
    lines.append(f"# TYPE http_requests_success counter")
    lines.append(f"http_requests_success {metrics['requests']['success']}")

    lines.append(f"# HELP http_requests_error Failed HTTP requests")
    lines.append(f"# TYPE http_requests_error counter")
    lines.append(f"http_requests_error {metrics['requests']['error']}")

    # Background job metrics
    lines.append(f"# HELP background_jobs_total Total background job runs")
    lines.append(f"# TYPE background_jobs_total counter")
    lines.append(f"background_jobs_total {metrics['background_jobs']['total_runs']}")

    lines.append(f"# HELP background_jobs_success Successful background jobs")
    lines.append(f"# TYPE background_jobs_success counter")
    lines.append(f"background_jobs_success {metrics['background_jobs']['successful_runs']}")

    lines.append(f"# HELP background_jobs_failed Failed background jobs")
    lines.append(f"# TYPE background_jobs_failed counter")
    lines.append(f"background_jobs_failed {metrics['background_jobs']['failed_runs']}")

    # Cache metrics
    lines.append(f"# HELP cache_hits Cache hits")
    lines.append(f"# TYPE cache_hits counter")
    lines.append(f"cache_hits {metrics['cache']['hits']}")

    lines.append(f"# HELP cache_misses Cache misses")
    lines.append(f"# TYPE cache_misses counter")
    lines.append(f"cache_misses {metrics['cache']['misses']}")

    lines.append(f"# HELP cache_hit_rate Cache hit rate percentage")
    lines.append(f"# TYPE cache_hit_rate gauge")
    lines.append(f"cache_hit_rate {app_metrics.get_cache_hit_rate()}")

    # WebSocket metrics
    ws_connections = websocket_manager.get_connection_count()
    lines.append(f"# HELP websocket_connections Active WebSocket connections")
    lines.append(f"# TYPE websocket_connections gauge")
    lines.append(f"websocket_connections {ws_connections}")

    lines.append(f"# HELP websocket_messages_sent Total WebSocket messages sent")
    lines.append(f"# TYPE websocket_messages_sent counter")
    lines.append(f"websocket_messages_sent {metrics['websocket']['total_messages_sent']}")

    # Uptime
    lines.append(f"# HELP uptime_seconds Application uptime in seconds")
    lines.append(f"# TYPE uptime_seconds counter")
    lines.append(f"uptime_seconds {metrics['uptime_seconds']}")

    return "\n".join(lines)


@router.get("/status")
async def status_overview():
    """
    Simple status overview for monitoring dashboards.

    Returns high-level application status.
    """
    metrics = app_metrics.get_metrics()

    return {
        "status": "operational",
        "uptime_hours": round(metrics["uptime_seconds"] / 3600, 2),
        "total_requests": metrics["requests"]["total"],
        "error_rate_percent": round(app_metrics.get_error_rate(), 2),
        "cache_hit_rate_percent": round(app_metrics.get_cache_hit_rate(), 2),
        "active_websocket_connections": websocket_manager.get_connection_count(),
        "background_jobs_running": metrics["background_jobs"]["total_runs"],
        "timestamp": datetime.utcnow().isoformat()
    }
