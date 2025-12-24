"""
Public status page endpoint.

Provides a user-friendly status page showing system health.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any

from app.database import get_db
from app.services.logging_service import logger


router = APIRouter(prefix="/status", tags=["status"])


@router.get("", response_class=HTMLResponse)
async def get_status_page(db: Session = Depends(get_db)):
    """
    Public status page showing system health.
    """
    # Get component statuses
    components = await get_component_statuses(db)

    # Determine overall status
    overall_status = determine_overall_status(components)

    # Generate HTML
    html_content = generate_status_html(overall_status, components)

    return HTMLResponse(content=html_content)


async def get_component_statuses(db: Session) -> Dict[str, Dict[str, Any]]:
    """Get status of all components."""
    components = {}

    # API Status
    components["api"] = {
        "name": "API",
        "status": "operational",
        "description": "Core API services",
        "last_updated": datetime.utcnow()
    }

    # Database Status
    try:
        db.execute("SELECT 1")
        components["database"] = {
            "name": "Database",
            "status": "operational",
            "description": "PostgreSQL database",
            "last_updated": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        components["database"] = {
            "name": "Database",
            "status": "outage",
            "description": "PostgreSQL database - Connection failed",
            "last_updated": datetime.utcnow()
        }

    # Redis Status (non-critical)
    from app.services.redis_service import get_redis_client
    redis_client = get_redis_client()
    if redis_client:
        try:
            redis_client.ping()
            components["redis"] = {
                "name": "Cache",
                "status": "operational",
                "description": "Redis cache",
                "last_updated": datetime.utcnow()
            }
        except:
            components["redis"] = {
                "name": "Cache",
                "status": "degraded",
                "description": "Redis cache - Performance may be reduced",
                "last_updated": datetime.utcnow()
            }
    else:
        components["redis"] = {
            "name": "Cache",
            "status": "degraded",
            "description": "Redis cache unavailable - Performance may be reduced",
            "last_updated": datetime.utcnow()
        }

    # Background Jobs
    from app.services.scheduler_service import scheduler
    if scheduler and scheduler.running:
        components["scheduler"] = {
            "name": "Background Jobs",
            "status": "operational",
            "description": "Monitoring job scheduler",
            "last_updated": datetime.utcnow()
        }
    else:
        components["scheduler"] = {
            "name": "Background Jobs",
            "status": "outage",
            "description": "Monitoring jobs not running",
            "last_updated": datetime.utcnow()
        }

    # Platform APIs (external dependencies)
    components["platform_apis"] = {
        "name": "Platform APIs",
        "status": "operational",
        "description": "Twitch, Twitter, YouTube, Reddit",
        "last_updated": datetime.utcnow()
    }

    return components


def determine_overall_status(components: Dict[str, Dict[str, Any]]) -> str:
    """Determine overall system status."""
    statuses = [comp["status"] for comp in components.values()]

    if all(s == "operational" for s in statuses):
        return "operational"
    elif any(s == "outage" for s in statuses):
        # Check if critical component
        critical_components = ["api", "database"]
        for comp_id, comp in components.items():
            if comp_id in critical_components and comp["status"] == "outage":
                return "major_outage"
        return "partial_outage"
    elif any(s == "degraded" for s in statuses):
        return "degraded"
    else:
        return "operational"


def generate_status_html(overall_status: str, components: Dict[str, Dict[str, Any]]) -> str:
    """Generate HTML for status page."""

    # Status styling
    status_styles = {
        "operational": {
            "color": "#10b981",
            "bg": "#d1fae5",
            "text": "All Systems Operational",
            "icon": "✓"
        },
        "degraded": {
            "color": "#f59e0b",
            "bg": "#fef3c7",
            "text": "Degraded Performance",
            "icon": "⚠"
        },
        "partial_outage": {
            "color": "#ef4444",
            "bg": "#fee2e2",
            "text": "Partial Outage",
            "icon": "!"
        },
        "major_outage": {
            "color": "#dc2626",
            "bg": "#fecaca",
            "text": "Major Outage",
            "icon": "✗"
        }
    }

    component_status_styles = {
        "operational": {"color": "#10b981", "text": "Operational"},
        "degraded": {"color": "#f59e0b", "text": "Degraded"},
        "outage": {"color": "#ef4444", "text": "Outage"}
    }

    overall = status_styles.get(overall_status, status_styles["degraded"])

    # Generate component HTML
    components_html = ""
    for comp_id, comp in components.items():
        comp_style = component_status_styles.get(comp["status"], component_status_styles["degraded"])

        components_html += f"""
        <div style="padding: 16px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="margin: 0; font-size: 16px; font-weight: 600; color: #1f2937;">{comp['name']}</h3>
                    <p style="margin: 4px 0 0 0; font-size: 14px; color: #6b7280;">{comp['description']}</p>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 10px; height: 10px; border-radius: 50%; background: {comp_style['color']};"></div>
                    <span style="font-size: 14px; font-weight: 500; color: {comp_style['color']};">{comp_style['text']}</span>
                </div>
            </div>
        </div>
        """

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Media Analytics - System Status</title>
    <meta http-equiv="refresh" content="60">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f9fafb;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 8px;
        }}
        .header p {{
            font-size: 14px;
            color: #6b7280;
        }}
        .status-banner {{
            background: {overall['bg']};
            border: 2px solid {overall['color']};
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            margin-bottom: 32px;
        }}
        .status-banner h2 {{
            font-size: 24px;
            font-weight: 600;
            color: {overall['color']};
            margin-bottom: 8px;
        }}
        .status-banner p {{
            font-size: 14px;
            color: #6b7280;
        }}
        .last-updated {{
            text-align: center;
            font-size: 12px;
            color: #9ca3af;
            margin-top: 24px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }}
        .footer a {{
            color: #3b82f6;
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Social Media Analytics Platform</h1>
            <p>System Status</p>
        </div>

        <div class="status-banner">
            <h2>{overall['icon']} {overall['text']}</h2>
            <p>Monitoring {len(components)} components</p>
        </div>

        <div class="components">
            {components_html}
        </div>

        <p class="last-updated">
            Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} • Refreshes automatically every 60 seconds
        </p>

        <div class="footer">
            <p>Having issues? <a href="mailto:support@socialmediaanalytics.com">Contact Support</a></p>
            <p style="margin-top: 8px; font-size: 12px; color: #9ca3af;">
                <a href="/api/docs">API Documentation</a> •
                <a href="/health">Health Check</a> •
                <a href="/metrics">Metrics</a>
            </p>
        </div>
    </div>
</body>
</html>
    """

    return html
