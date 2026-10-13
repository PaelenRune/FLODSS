"""Data models for Phase 8: Feasible Rectangular Layout Generator."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.geometry import Point2D, Dimensions2D, BoundingBox
from app.models.representation import ContinuousLayout


class GeneratorStrategy(str, Enum):
    """Search paradigm for generating feasible rectangular layouts."""

    FREE_RECTANGLE_DFS = "free_rectangle_dfs"
    SLICING_TREE_DECOMPOSITION = "slicing_tree_decomposition"
    GUILLOTINE_ROW_PACKING = "guillotine_row_packing"


class DepartmentOrderingStrategy(str, Enum):
    """Department sequencing heuristic for constructive placement."""

    MOST_CONSTRAINED_FIRST = "most_constrained_first"
    LARGEST_AREA_FIRST = "largest_area_first"
    FLOW_VOLUME_DESCENDING = "flow_volume_descending"
    RELATIONSHIP_WEIGHT_DESCENDING = "relationship_weight_descending"


class GeneratorTerminationReason(str, Enum):
    """Explicit termination status of constructive search."""

    SUCCESS_FEASIBLE_FOUND = "SUCCESS_FEASIBLE_FOUND"
    SEARCH_BUDGET_EXHAUSTED = "SEARCH_BUDGET_EXHAUSTED"
    SEARCH_SPACE_EXHAUSTED = "SEARCH_SPACE_EXHAUSTED"
    PRE_FEASIBILITY_FAILED = "PRE_FEASIBILITY_FAILED"
    TIMEOUT = "TIMEOUT"


class GeneratorConfig(BaseModel):
    """Configurable search budget and algorithmic options for feasible generator."""

    strategy: GeneratorStrategy = Field(
        default=GeneratorStrategy.FREE_RECTANGLE_DFS,
        description="Search paradigm",
    )
    ordering_strategy: DepartmentOrderingStrategy = Field(
        default=DepartmentOrderingStrategy.MOST_CONSTRAINED_FIRST,
        description="Priority sorting order for placing departments",
    )
    max_nodes: int = Field(
        default=3000,
        ge=10,
        le=50000,
        description="Maximum search tree nodes to explore",
    )
    max_backtracks: int = Field(
        default=1500,
        ge=0,
        le=20000,
        description="Maximum backtracking steps permitted",
    )
    max_runtime_seconds: float = Field(
        default=10.0,
        gt=0.1,
        le=120.0,
        description="Hard wall-clock timeout in seconds",
    )
    max_shape_alternatives: int = Field(
        default=8,
        ge=1,
        le=30,
        description="Maximum legal rectangular shape alternatives to consider per department",
    )
    candidate_limit_per_department: int = Field(
        default=12,
        ge=1,
        le=50,
        description="Maximum candidate spatial placements to test per department at each node",
    )
    tolerance: float = Field(
        default=1e-4,
        description="Floating-point geometric tolerance in meters",
    )
    random_seed: Optional[int] = Field(
        default=42,
        description="Deterministic random seed if stochastic tie-breaking is utilized",
    )


class PreFeasibilityReport(BaseModel):
    """Pre-search analytical verification of problem solvability."""

    is_feasible: bool = Field(..., description="True if problem passes initial physical preconditions")
    errors: List[str] = Field(default_factory=list, description="Fatal consistency violations")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal notices")
    total_required_area: float
    facility_available_area: float
    area_utilization: float
    unconstrained_departments: List[str] = Field(default_factory=list)
    constrained_departments: List[str] = Field(default_factory=list)
    department_shape_counts: Dict[str, int] = Field(default_factory=dict)


class GeneratorResult(BaseModel):
    """Standardized output model for Feasible Layout Generator."""

    success: bool = Field(..., description="True only if complete and feasible layout was produced")
    complete: bool = Field(..., description="True if all departments were successfully placed")
    feasible: bool = Field(..., description="True if central validation passed 100% with zero violations")
    problem_id: str
    strategy: str
    layout: Optional[ContinuousLayout] = None
    layout_signature: Optional[str] = None
    placed_department_count: int = 0
    total_department_count: int = 0
    nodes_explored: int = 0
    backtracks: int = 0
    candidates_rejected: int = 0
    runtime_seconds: float = 0.0
    termination_reason: GeneratorTerminationReason
    failure_diagnostics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostics of rejections by constraint category if search failed",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
