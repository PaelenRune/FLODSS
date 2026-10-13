"""Centralized configuration for evaluation engine, distance metrics, and objective weights."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.services.geometry_engine import DistanceMetricType


class EvaluationConfig(BaseModel):
    """Centralized configuration parameters controlling evaluation behavior.
    
    Eliminates magic numbers and provides deterministic, reproducible scoring.
    """

    distance_metric: DistanceMetricType = Field(
        default=DistanceMetricType.MANHATTAN,
        description="Spatial metric for calculating inter-department distances (Manhattan or Euclidean)",
    )
    default_cost_per_unit_distance: float = Field(
        default=1.0,
        gt=0,
        description="Fallback material handling cost per unit distance when unspecified on a flow",
    )
    normalization_method: str = Field(
        default="min_max",
        description="Multi-layout normalization technique ('min_max' or 'linear_range')",
    )
    numerical_tolerance: float = Field(
        default=1e-4,
        ge=0,
        description="Floating point comparison tolerance for geometry and constraints",
    )
    adjacency_tolerance: float = Field(
        default=1e-4,
        ge=0,
        description="Geometric tolerance for touching borders / shared walls",
    )
    objective_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional objective weight overrides (e.g. {'material_handling_cost': 1.0, 'flow_distance': 0.8})",
    )
    max_top_contributors: int = Field(
        default=10,
        gt=0,
        description="Maximum number of top cost/distance flows to report in detailed diagnostics",
    )
    engine_version: str = Field(
        default="1.0.0",
        description="Semantic version of the evaluation engine for academic reproducibility",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
