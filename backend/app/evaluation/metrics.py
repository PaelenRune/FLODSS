"""Standard metric definitions and result structures for layout evaluation."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Catalog of industrial engineering evaluation metrics."""

    MATERIAL_HANDLING_COST = "material_handling_cost"    # MHC ($ or cost units based on flow * distance * unit_cost)
    TOTAL_FLOW_DISTANCE = "total_flow_distance"          # Sum of (flow_volume * distance)
    RELATIONSHIP_SATISFACTION = "relationship_satisfaction"  # % or score of closeness relationships fulfilled
    AREA_UTILIZATION = "area_utilization"                # Department floor area / total facility area
    CONSTRAINT_VIOLATIONS = "constraint_violations"      # Total penalty or count of violated rules
    CONGESTION = "congestion"                            # Traffic density / bottleneck indicator
    SAFETY_SCORE = "safety_score"                        # Separation of hazardous and sensitive departments
    LAYOUT_COMPACTNESS = "layout_compactness"            # Perimeter to area ratio, bounding hull dispersion
    RECONFIGURATION_COST = "reconfiguration_cost"        # Cost to transition from an existing baseline layout


class MetricDirection(str, Enum):
    """Optimization direction for a metric."""

    MINIMIZE = "minimize"  # Smaller is better (e.g. costs, distances, violations)
    MAXIMIZE = "maximize"  # Larger is better (e.g. relationship satisfaction, safety score)


class EvaluationMetricResult(BaseModel):
    """Result of an individual metric evaluation."""

    metric_name: str = Field(..., description="Unique name/identifier of the metric")
    display_name: str = Field(..., description="Human-readable title")
    value: float = Field(..., description="Computed numerical score")
    unit: str = Field(default="", description="Measurement unit (e.g. '$', 'm*moves', '%')")
    direction: MetricDirection = Field(
        default=MetricDirection.MINIMIZE,
        description="Whether this metric should be minimized or maximized",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed breakdowns (e.g. pairwise costs, sub-components)",
    )
