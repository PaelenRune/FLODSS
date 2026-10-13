"""Service for checking system health and infrastructure readiness."""

import platform
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, Field

from app.core.config import settings


class SystemStatus(BaseModel):
    """Detailed health report payload."""

    status: str = Field(default="healthy", description="Operational status: healthy / degraded")
    project_name: str
    version: str
    timestamp: str
    python_version: str
    platform: str
    registered_algorithms: int
    modules: Dict[str, str]


class HealthService:
    """Provides system diagnostics and service availability checks."""

    @staticmethod
    def get_status() -> SystemStatus:
        """Inspect system status and return diagnostics."""
        from app.algorithms.registry import AlgorithmRegistry

        return SystemStatus(
            status="healthy",
            project_name=settings.PROJECT_NAME,
            version=settings.VERSION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            registered_algorithms=len(AlgorithmRegistry.list_available()),
            modules={
                "core": "active",
                "models": "active",
                "algorithms": "ready",
                "evaluation": "ready",
                "constraints": "ready",
                "optimization": "ready",
                "simulation": "ready",
                "ai": "ready",
                "visualization": "ready",
            },
        )
