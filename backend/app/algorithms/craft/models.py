"""Data models for CRAFT pairwise improvement heuristic results and execution traces."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.representation import ContinuousLayout


class CRAFTTerminationReason(str, Enum):
    """Formal termination reasons for CRAFT improvement heuristic."""

    NO_IMPROVING_SWAP = "NO_IMPROVING_SWAP"
    NO_ELIGIBLE_SWAPS = "NO_ELIGIBLE_SWAPS"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    INVALID_INITIAL_LAYOUT = "INVALID_INITIAL_LAYOUT"


class CRAFTSwapCandidate(BaseModel):
    """Evaluation record of a proposed 2-way department swap."""

    dept_a: str = Field(..., description="First department in proposed exchange")
    dept_b: str = Field(..., description="Second department in proposed exchange")
    is_rotational: bool = Field(default=False, description="True if swap involves 90-degree dimension rotation")
    is_feasible: bool = Field(default=True, description="True if swapped layout satisfies all hard constraints")
    rejection_reason: Optional[str] = Field(default=None, description="Detailed explanation if infeasible")
    mhc_before: float = Field(..., description="Material handling cost before swap")
    mhc_after: float = Field(..., description="Material handling cost after swap")
    improvement: float = Field(..., description="Cost reduction: mhc_before - mhc_after")


class CRAFTSwapStep(BaseModel):
    """Record of an accepted pairwise exchange."""

    iteration: int = Field(..., description="Iteration number where this swap occurred")
    dept_a: str = Field(..., description="First department exchanged")
    dept_b: str = Field(..., description="Second department exchanged")
    is_rotational: bool = Field(default=False, description="True if swap involved 90-degree dimension rotation")
    mhc_before: float = Field(..., description="Material handling cost prior to exchange")
    mhc_after: float = Field(..., description="Material handling cost after exchange")
    improvement: float = Field(..., description="Cost reduction achieved by this step")
    cumulative_improvement: float = Field(..., description="Total cost reduction from initial baseline")
    layout_signature: str = Field(..., description="Deterministic geometric signature after exchange")


class CRAFTTraceStep(BaseModel):
    """Step-by-step diagnostic log for an individual CRAFT iteration."""

    iteration: int = Field(..., description="Iteration index (1-based)")
    current_mhc: float = Field(..., description="Current layout Material Handling Cost")
    candidate_pairs: int = Field(..., description="Total eligible department pairs evaluated")
    feasible_candidates: int = Field(..., description="Number of candidate swaps passing all geometric and hard constraints")
    rejected_candidates: int = Field(..., description="Number of candidate swaps rejected due to feasibility violations")
    rejection_breakdown: Dict[str, int] = Field(default_factory=dict, description="Counts of rejection causes")
    selected_swap: Optional[CRAFTSwapStep] = Field(default=None, description="Best swap accepted, or None if stopping")
    mhc_before: float = Field(..., description="MHC before iteration")
    mhc_after: float = Field(..., description="MHC after iteration")
    improvement: float = Field(..., description="MHC reduction achieved in this iteration")
    cumulative_improvement: float = Field(..., description="Cumulative MHC reduction from initial layout")
    layout_signature: str = Field(..., description="Geometric signature at end of iteration")
    candidate_evaluations: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Detailed list of all candidate evaluations when trace_level == 'DETAILED'",
    )


class CRAFTExecutionTrace(BaseModel):
    """Comprehensive execution history for CRAFT run."""

    algorithm_name: str = Field(default="craft_pairwise_rectangular_v1")
    algorithm_version: str = Field(default="1.0.0")
    initial_mhc: float = Field(..., description="Initial layout Material Handling Cost")
    final_mhc: float = Field(..., description="Final optimized Material Handling Cost")
    absolute_improvement: float = Field(..., description="Total cost reduction: initial_mhc - final_mhc")
    percentage_improvement: float = Field(..., description="Percentage cost reduction relative to initial_mhc")
    total_iterations: int = Field(..., description="Total iterations executed")
    total_swaps_accepted: int = Field(..., description="Total successful department exchanges accepted")
    termination_reason: str = Field(..., description="Formal stopping condition reason")
    steps: List[CRAFTTraceStep] = Field(default_factory=list, description="Iteration logs")
    execution_time_seconds: float = Field(default=0.0, description="Runtime duration in seconds")


class CRAFTSolverResult(BaseModel):
    """Standard domain result returned by CRAFT improvement solver."""

    algorithm_name: str = Field(default="craft_pairwise_rectangular_v1")
    algorithm_version: str = Field(default="1.0.0")
    initial_layout_signature: str = Field(..., description="Geometric signature of initial baseline")
    final_layout_signature: str = Field(..., description="Geometric signature of final optimized layout")
    is_complete: bool = Field(default=True, description="True if all problem departments are placed")
    is_feasible: bool = Field(default=True, description="True if final layout satisfies all hard constraints")
    termination_reason: str = Field(..., description="Formal stopping condition reason")
    iterations: int = Field(..., description="Number of improvement iterations completed")
    accepted_swaps: List[CRAFTSwapStep] = Field(default_factory=list, description="Sequence of accepted department swaps")
    initial_mhc: float = Field(..., description="Initial Material Handling Cost")
    final_mhc: float = Field(..., description="Final Material Handling Cost")
    absolute_improvement: float = Field(..., description="Initial MHC - Final MHC")
    percentage_improvement: float = Field(..., description="Percentage improvement relative to initial MHC")
    trace: CRAFTExecutionTrace = Field(..., description="Step-by-step optimization history")
    final_layout: ContinuousLayout = Field(..., description="Optimized continuous layout representation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Auxiliary algorithm diagnostics")
