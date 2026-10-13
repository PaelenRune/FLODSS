"""CRAFT (Computerized Relative Allocation of Facilities Technique) pairwise improvement package."""

from app.algorithms.craft.config import CRAFTConfig, CRAFTTraceLevel
from app.algorithms.craft.models import (
    CRAFTTerminationReason,
    CRAFTSwapCandidate,
    CRAFTSwapStep,
    CRAFTTraceStep,
    CRAFTExecutionTrace,
    CRAFTSolverResult,
)
from app.algorithms.craft.eligibility import (
    check_pair_eligibility,
    find_eligible_pairs,
    detect_unequal_adjacent_pairs,
    is_department_fixed,
)
from app.algorithms.craft.swapper import (
    create_swapped_layout,
    validate_candidate_swap,
)
from app.algorithms.craft.scoring import compute_mhc
from app.algorithms.craft.solver import CRAFTAlgorithm

__all__ = [
    "CRAFTConfig",
    "CRAFTTraceLevel",
    "CRAFTTerminationReason",
    "CRAFTSwapCandidate",
    "CRAFTSwapStep",
    "CRAFTTraceStep",
    "CRAFTExecutionTrace",
    "CRAFTSolverResult",
    "check_pair_eligibility",
    "find_eligible_pairs",
    "detect_unequal_adjacent_pairs",
    "is_department_fixed",
    "create_swapped_layout",
    "validate_candidate_swap",
    "compute_mhc",
    "CRAFTAlgorithm",
]
