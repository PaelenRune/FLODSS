"""Explainability and execution trace models for CORELAP decisions."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CORELAPTraceStep(BaseModel):
    """Diagnostic audit record of a single department placement decision in CORELAP."""

    step_number: int = Field(..., description="1-based sequence index")
    selected_department: str = Field(..., description="ID of department selected for placement")
    tcr: float = Field(..., description="Total Closeness Rating of the selected department")
    placed_relationship_score: float = Field(
        ..., description="Sum of closeness weights with already placed departments"
    )
    candidate_count: int = Field(..., description="Total candidate coordinate positions considered")
    selected_candidate: Optional[Dict[str, float]] = Field(
        default=None, description="Chosen placement bounding box (x, y, width, height)"
    )
    candidate_score: float = Field(..., description="Evaluated score of the chosen candidate position")
    neighbors: List[str] = Field(
        default_factory=list, description="IDs of already placed departments directly adjacent to this placement"
    )
    rejected_candidates: int = Field(
        default=0, description="Number of candidate positions rejected due to bounds or overlap"
    )
    rejection_reasons: Dict[str, int] = Field(
        default_factory=dict, description="Counts of rejection causes (out_of_bounds, overlap, reserved_zone)"
    )
    candidate_diagnostics: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Detailed candidate diagnostics when trace_level == 'DETAILED'"
    )


class CORELAPExecutionTrace(BaseModel):
    """Complete step-by-step history of CORELAP layout construction."""

    algorithm_name: str = "corelap_deterministic_v1"
    algorithm_version: str = "1.0.0"
    total_departments: int
    placed_count: int
    execution_success: bool
    is_complete: bool = False
    placed_department_count: int = 0
    total_department_count: int = 0
    unplaced_departments: List[str] = Field(default_factory=list)
    termination_reason: Optional[str] = None
    placement_order: List[str] = Field(default_factory=list)
    tcr_values: Dict[str, float] = Field(default_factory=dict)
    steps: List[CORELAPTraceStep] = Field(default_factory=list)
    failure_reason: Optional[str] = None
    execution_time_seconds: Optional[float] = None
