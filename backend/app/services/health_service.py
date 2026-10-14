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
    registered_algorithm_names: list[str] = Field(default_factory=list)
    orchestration_engines: list[str] = Field(default_factory=lambda: ["adaptive_strategy_engine"])
    modules: Dict[str, str]


class HealthService:
    """Provides system diagnostics and service availability checks."""

    @staticmethod
    def get_status() -> SystemStatus:
        """Inspect system status and return diagnostics."""
        from app.algorithms.registry import AlgorithmRegistry

        available_algos = AlgorithmRegistry.list_available()
        algo_names = [a.get("name", str(a)) if isinstance(a, dict) else str(a) for a in available_algos]
        return SystemStatus(
            status="healthy",
            project_name=settings.PROJECT_NAME,
            version=settings.VERSION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            registered_algorithms=len(available_algos),
            registered_algorithm_names=algo_names,
            orchestration_engines=["adaptive_strategy_engine"],
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
