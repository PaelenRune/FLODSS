"""Configuration parameters for CRAFT pairwise rectangular improvement heuristic."""

from enum import Enum
from pydantic import BaseModel, Field
from app.services.geometry_engine import DistanceMetricType


class CRAFTTraceLevel(str, Enum):
    """Granularity of execution trace reporting."""
    SUMMARY = "SUMMARY"
    DETAILED = "DETAILED"


class CRAFTConfig(BaseModel):
    """Configuration options controlling the CRAFT improvement heuristic."""

    max_iterations: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum pairwise exchange iterations before forced termination",
    )
    min_improvement_threshold: float = Field(
        default=0.01,
        ge=0.0,
        description="Minimum absolute reduction in Material Handling Cost required to accept a swap",
    )
    allow_rotational_swaps: bool = Field(
        default=True,
        description="Allow 90-degree dimension rotation when departments match transversely (wA=hB and hA=wB)",
    )
    distance_metric: DistanceMetricType = Field(
        default=DistanceMetricType.MANHATTAN,
        description="Distance computation metric between department centroids (default: Manhattan / Rectilinear)",
    )
    default_cost_per_unit_distance: float = Field(
        default=1.0,
        gt=0.0,
        description="Fallback transport cost per unit distance when unspecified on individual flows",
    )
    numerical_tolerance: float = Field(
        default=1e-4,
        ge=0.0,
        description="Floating-point tolerance for geometric and cost equality checks",
    )
    trace_level: str = Field(
        default="SUMMARY",
        description="Execution trace detail level: 'SUMMARY' or 'DETAILED'",
    )
