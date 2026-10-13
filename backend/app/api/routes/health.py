"""Health check API endpoints."""

from fastapi import APIRouter
from app.services.health_service import HealthService, SystemStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=SystemStatus, summary="System Health & Readiness")
def get_health() -> SystemStatus:
    """Check health, infrastructure readiness, and active modules."""
    return HealthService.get_status()
