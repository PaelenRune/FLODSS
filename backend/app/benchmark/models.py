"""Data models for Phase 7.1: Benchmark & Algorithm Comparison."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.evaluation.config import EvaluationConfig


class BenchmarkConfig(BaseModel):
    """Reproducible configuration parameters for cross-algorithm benchmark execution."""

    problem_ids: List[str] = Field(
        default_factory=lambda: ["FLP_ACADEMIC_4", "FLP_MEDIUM_6", "FLP_INDUSTRIAL_10"],
        description="Benchmark problem identifiers to evaluate",
    )
    aldep_seeds: List[int] = Field(
        default_factory=lambda: [42, 101, 2024, 777, 999],
        description="Random seeds for ALDEP candidate generation",
    )
    aldep_candidates_per_seed: int = Field(
        default=20,
        description="Number of stochastic layout candidates generated per seed",
    )
    aldep_cell_size: float = Field(
        default=5.0,
        description="Grid cell dimension in meters for ALDEP discretization",
    )
    aldep_strip_width_cells: int = Field(
        default=2,
        description="Strip width in grid cells for ALDEP serpentine sweep",
    )
    aldep_allow_strip_splitting: bool = Field(
        default=True,
        description="True for classical ALDEP strip-splitting; False for rigid rectangular adaptation",
    )
    craft_max_iterations: int = Field(
        default=50,
        description="Maximum improvement iterations for CRAFT pairwise swaps",
    )
    evaluation_config: EvaluationConfig = Field(
        default_factory=EvaluationConfig,
        description="Unified evaluation parameters applied identically to all solutions",
    )


class ALDEPCandidateRecord(BaseModel):
    """Individual candidate evaluation record within ALDEP stochastic trials."""

    problem_id: str
    seed: int
    candidate_id: str
    candidate_index: int
    completion_status: bool
    placed_department_count: int
    total_department_count: int
    geometric_feasibility: bool
    hard_constraint_violations: int
    layout_signature: str
    is_duplicate: bool
    duplicate_of_id: Optional[str] = None
    mhc: Optional[float] = None
    flow_distance: Optional[float] = None
    relationship_satisfaction: Optional[float] = None
    execution_time_seconds: float
    failure_reason: Optional[str] = None


class ALDEPProblemSummary(BaseModel):
    """Statistical aggregation for ALDEP performance on a specific problem."""

    problem_id: str
    total_trials: int
    complete_count: int
    completion_rate: float
    feasible_count: int
    feasibility_rate: float
    unique_layout_count: int
    duplicate_count: int
    best_mhc: Optional[float] = None
    median_mhc: Optional[float] = None
    worst_mhc: Optional[float] = None
    std_mhc: Optional[float] = None
    sample_size_mhc: int
    sample_description: str
    best_feasible_signature: Optional[str] = None
    mean_runtime_seconds: float
    total_runtime_seconds: float


class CORELAPRunRecord(BaseModel):
    """Execution record for deterministic CORELAP construction."""

    problem_id: str
    selected_mode: str
    completion: bool
    feasibility: bool
    placed_department_count: int
    total_department_count: int
    unplaced_departments: List[str]
    mhc: Optional[float] = None
    relationship_score: Optional[float] = None
    flow_distance: Optional[float] = None
    hard_constraint_violations: int = 0
    termination_reason: str
    failure_diagnostics: Optional[Any] = None
    layout_signature: Optional[str] = None
    runtime_seconds: float


class CRAFTRunRecord(BaseModel):
    """Execution record for CRAFT improvement heuristic on a valid initial baseline."""

    problem_id: str
    initial_source: str
    initial_mhc: float
    final_mhc: float
    absolute_improvement: float
    percentage_improvement: float
    accepted_swaps: int
    termination_reason: str
    initial_layout_signature: str
    final_layout_signature: str
    runtime_seconds: float


class BenchmarkComparisonRow(BaseModel):
    """Unified tabular row for cross-algorithm benchmark comparison."""

    algorithm: str
    problem_id: str
    run_or_seed: str
    complete: bool
    feasible: bool
    mhc: Optional[float] = None
    flow_distance: Optional[float] = None
    relationship_satisfaction: Optional[float] = None
    constraint_violations: int = 0
    runtime_seconds: float
    notes: Optional[str] = None


class BenchmarkResult(BaseModel):
    """Comprehensive artifact containing all experimental logs, summaries, and tables."""

    run_id: str
    timestamp: str
    config: BenchmarkConfig
    comparison_table: List[BenchmarkComparisonRow]
    aldep_summaries: Dict[str, ALDEPProblemSummary]
    aldep_candidates: List[ALDEPCandidateRecord]
    corelap_records: List[CORELAPRunRecord]
    craft_records: List[CRAFTRunRecord]
    metadata: Dict[str, Any] = Field(default_factory=dict)
