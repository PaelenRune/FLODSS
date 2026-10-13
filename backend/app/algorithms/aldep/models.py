"""Data models and trace structures for ALDEP layout construction heuristic."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.geometry import BoundingBox
from app.models.representation import ContinuousLayout, GridLayout


class ALDEPSelectionStep(BaseModel):
    """Details of a single department selection decision in ALDEP sequence generation."""

    step_number: int = Field(..., description="Sequential step index (1-based)")
    last_department_id: Optional[str] = Field(None, description="Department placed in immediately preceding step")
    unplaced_candidates: List[str] = Field(default_factory=list, description="IDs of remaining unplaced departments")
    candidate_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Relationship score between each unplaced candidate and last_department_id",
    )
    threshold: float = Field(..., description="Applied selection threshold score T")
    eligible_candidates: List[str] = Field(
        default_factory=list,
        description="Candidates satisfying score >= T with last department",
    )
    selection_mode: str = Field(
        ...,
        description="Decision type: 'INITIAL_RANDOM', 'AFFINITY_MAX', 'AFFINITY_THRESHOLD', or 'RANDOM_FALLBACK'",
    )
    selected_department: str = Field(..., description="ID of department selected in this step")


class ALDEPDepartmentShapeDiagnostic(BaseModel):
    """Geometric and shape metrics for a department placed by ALDEP."""

    department_id: str = Field(..., description="Department identifier")
    required_area: float = Field(..., description="Required area in m² from problem specification")
    allocated_cells: int = Field(..., description="Number of discrete grid cells allocated")
    allocated_area: float = Field(..., description="Discretized area in m² (allocated_cells * cell_size²)")
    area_error: float = Field(..., description="Absolute area error |allocated_area - required_area| in m²")
    area_error_pct: float = Field(..., description="Area error as percentage of required area")
    bounding_box: BoundingBox = Field(..., description="Continuous bounding box enclosing all cells")
    is_rectangular: bool = Field(..., description="True if occupied cells form a solid rectangular block")
    aspect_ratio: float = Field(..., description="Aspect ratio of bounding box (max_dim / min_dim)")
    grid_cells: List[tuple[int, int]] = Field(
        default_factory=list,
        description="List of (row, col) cell coordinates occupied in GridLayout",
    )


class ALDEPCandidateResult(BaseModel):
    """Evaluation, layout, and diagnostic outcome for one ALDEP candidate alternative."""

    candidate_index: int = Field(..., description="Index of this candidate (0-based)")
    seed: int = Field(..., description="Random seed used for this candidate")
    department_order: List[str] = Field(..., description="Ordered sequence of department placements")
    layout_signature: str = Field(..., description="SHA-256 geometric signature of the layout")
    is_complete: bool = Field(..., description="True if all required departments were placed")
    is_feasible: bool = Field(..., description="True if layout meets all boundaries, non-overlap, and constraints")
    is_duplicate: bool = Field(default=False, description="True if an identical layout was already generated")
    duplicate_of_index: Optional[int] = Field(None, description="Index of first candidate sharing this signature")
    placed_department_count: int = Field(..., description="Number of departments successfully positioned")
    total_department_count: int = Field(..., description="Total required departments in problem")
    unplaced_departments: List[str] = Field(default_factory=list, description="IDs of departments that could not be placed")
    termination_reason: str = Field(..., description="Standardized solver completion/termination reason")
    material_handling_cost: Optional[float] = Field(None, description="Material Handling Cost (MHC)")
    flow_distance: Optional[float] = Field(None, description="Total Flow-Distance metric")
    relationship_score: Optional[float] = Field(None, description="Muther SLP closeness relationship score")
    area_utilization: Optional[float] = Field(None, description="Ratio of department area to facility area in %")
    shape_diagnostics: Dict[str, ALDEPDepartmentShapeDiagnostic] = Field(
        default_factory=dict,
        description="Per-department shape, discretization, and boundary diagnostics",
    )
    continuous_layout: ContinuousLayout = Field(..., description="Continuous 2D layout representation")
    grid_layout: Optional[GridLayout] = Field(None, description="Native discrete grid layout representation")
    selection_steps: List[ALDEPSelectionStep] = Field(
        default_factory=list,
        description="Step-by-step department selection history",
    )


class ALDEPExecutionTrace(BaseModel):
    """Complete explainability and candidate comparison trace across ALDEP runs."""

    algorithm_name: str = Field(default="aldep")
    algorithm_version: str = Field(default="1.0.0")
    number_of_candidates: int = Field(..., description="Total candidates requested")
    unique_candidate_count: int = Field(..., description="Number of geometrically unique candidates")
    feasible_candidate_count: int = Field(..., description="Number of fully feasible candidates")
    complete_candidate_count: int = Field(..., description="Number of complete candidates (all depts placed)")
    best_candidate_index: int = Field(..., description="Index of selected top-ranked candidate")
    best_candidate_seed: int = Field(..., description="Seed of selected top-ranked candidate")
    execution_time_seconds: float = Field(..., description="Total runtime across all candidate generations")
    best_selection_steps: List[ALDEPSelectionStep] = Field(
        default_factory=list,
        description="Selection trace for the best candidate layout",
    )


class ALDEPSolverResult(BaseModel):
    """Aggregate response returned by ALDEP solver containing best solution and all candidates."""

    algorithm_name: str = Field(default="aldep")
    algorithm_version: str = Field(default="1.0.0")
    best_candidate: ALDEPCandidateResult = Field(..., description="Primary top-ranked candidate solution")
    candidates: List[ALDEPCandidateResult] = Field(
        default_factory=list,
        description="All generated candidate layout alternatives",
    )
    trace: ALDEPExecutionTrace = Field(..., description="Overall solver execution summary and trace")
