"""CRAFT (Computerized Relative Allocation of Facilities Technique) pairwise improvement solver."""

import time
from typing import Any, Dict, List, Optional, Tuple, Union
from app.algorithms.base import (
    BaseImprovementAlgorithm,
    AlgorithmCategory,
    ValidationResult,
)
from app.algorithms.registry import register_algorithm, AlgorithmRegistry
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution, SolverTerminationReason
from app.models.representation import ContinuousLayout
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator
from app.constraints.engine import ConstraintEngine
from app.evaluation.engine import EvaluationEngine
from app.algorithms.craft.config import CRAFTConfig
from app.algorithms.craft.models import (
    CRAFTTerminationReason,
    CRAFTSwapStep,
    CRAFTTraceStep,
    CRAFTExecutionTrace,
    CRAFTSolverResult,
)
from app.algorithms.craft.eligibility import (
    find_eligible_pairs,
    detect_unequal_adjacent_pairs,
)
from app.algorithms.craft.swapper import (
    create_swapped_layout,
    validate_candidate_swap,
)
from app.algorithms.craft.scoring import compute_mhc


def _normalize_initial_layout(
    problem: FacilityLayoutProblem,
    initial_layout: Union[ContinuousLayout, LayoutSolution, Dict[str, Any]],
) -> ContinuousLayout:
    """Validate and convert raw layout representation into a strict ContinuousLayout."""
    if isinstance(initial_layout, ContinuousLayout):
        layout = initial_layout
    elif isinstance(initial_layout, LayoutSolution):
        if not initial_layout.is_complete:
            raise ValueError(
                f"Initial layout is incomplete ({initial_layout.placed_department_count} of "
                f"{initial_layout.total_department_count} placed). CRAFT requires a complete initial layout."
            )
        layout = ContinuousLayout.from_layout_solution(
            initial_layout,
            facility_width=problem.facility.width,
            facility_height=problem.facility.height,
            reserved_zones=problem.facility.reserved_zones if hasattr(problem.facility, "reserved_zones") else None,
        )
    elif isinstance(initial_layout, dict):
        if "placements" in initial_layout:
            layout = ContinuousLayout.model_validate(initial_layout)
        else:
            raise ValueError("Layout dict must contain 'placements' key.")
    else:
        raise TypeError(f"Unsupported layout type: {type(initial_layout)}")

    # Completeness verification
    required_ids = {d.id for d in problem.departments}
    placed_ids = set(layout.placements.keys())
    missing = required_ids - placed_ids
    if missing:
        raise ValueError(
            f"Initial layout is missing placements for required departments: {sorted(list(missing))}. "
            "CRAFT cannot operate on incomplete layouts."
        )

    # Feasibility verification
    val_result = LayoutValidator.validate(problem, layout)
    if not val_result.is_valid:
        raise ValueError(
            f"Initial layout is geometrically infeasible: {'; '.join(val_result.errors)}"
        )

    constraint_engine = ConstraintEngine()
    violations = constraint_engine.check_all(problem, layout)
    hard_violations = [v for v in violations if v.classification.value == "hard"]
    if hard_violations:
        raise ValueError(
            f"Initial layout violates hard constraints: {'; '.join(v.message for v in hard_violations)}"
        )

    return layout


@register_algorithm("craft")
class CRAFTAlgorithm(BaseImprovementAlgorithm):
    """Deterministic CRAFT v1.0 pairwise exchange improvement heuristic for continuous rectangular layouts.
    
    Academic Reference:
        Buffa, E. S., Armour, G. C., & Vollmann, T. E. (1964).
        "Allocating facilities with CRAFT." Harvard Business Review, 42(2), 136-158.
    """

    @property
    def name(self) -> str:
        return "craft_pairwise_rectangular_v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AlgorithmCategory:
        return AlgorithmCategory.IMPROVEMENT

    @property
    def default_parameters(self) -> Dict[str, Any]:
        return CRAFTConfig().model_dump()

    @property
    def supported_problem_types(self) -> List[str]:
        return [
            "complete_initial_layout",
            "pairwise_exchange",
            "continuous_rectangular",
            "equal_dimensions",
            "transverse_rotation",
            "fixed_positions",
            "reserved_zones",
        ]

    @property
    def metadata(self) -> Dict[str, Any]:
        base_meta = super().metadata
        base_meta.update({
            "literature_reference": "Buffa, Armour & Vollmann (1964) 'Allocating facilities with CRAFT'",
            "scope": "Continuous rectangular pairwise swaps (equal dimensions & transverse rotation)",
            "objective": "Material Handling Cost (MHC) minimization",
            "search_strategy": "Steepest descent / best improvement with deterministic tie-breaking",
        })
        return base_meta

    def validate(self, problem: FacilityLayoutProblem) -> ValidationResult:
        """Validate whether the problem satisfies baseline prerequisites for CRAFT improvement."""
        errors: List[str] = []
        warnings: List[str] = []

        if not problem.departments:
            errors.append("Problem contains no departments.")
        if not problem.flows:
            warnings.append("Problem defines no flows; CRAFT cannot optimize zero material handling flows.")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def improve(
        self,
        problem: FacilityLayoutProblem,
        initial_layout: Union[ContinuousLayout, LayoutSolution, Dict[str, Any]],
        **kwargs,
    ) -> LayoutSolution:
        """Execute CRAFT improvement search and return a standard LayoutSolution."""
        solution, _ = self.solve_with_result(problem, initial_layout, **kwargs)
        return solution

    def solve_with_result(
        self,
        problem: FacilityLayoutProblem,
        initial_layout: Union[ContinuousLayout, LayoutSolution, Dict[str, Any]],
        **kwargs,
    ) -> Tuple[LayoutSolution, CRAFTSolverResult]:
        """Execute CRAFT search, returning both the LayoutSolution and detailed CRAFTSolverResult."""
        start_time = time.time()

        # Merge parameters
        param_dict = self.parameters.copy()
        param_dict.update(kwargs)
        config = CRAFTConfig(**{k: v for k, v in param_dict.items() if k in CRAFTConfig.model_fields})

        # Step 0: Normalize and validate initial baseline layout
        current_layout = _normalize_initial_layout(problem, initial_layout)
        initial_signature = generate_layout_signature(current_layout)
        initial_mhc = compute_mhc(problem, current_layout, config)

        current_mhc = initial_mhc
        cumulative_improvement = 0.0
        accepted_swaps: List[CRAFTSwapStep] = []
        trace_steps: List[CRAFTTraceStep] = []
        termination_reason = CRAFTTerminationReason.NO_IMPROVING_SWAP.value

        iteration = 0

        # Step 1: Main Optimization Loop
        while iteration < config.max_iterations:
            iteration += 1

            # Discover all physically eligible pairs in deterministic lexicographical order
            eligible_pairs = find_eligible_pairs(problem, current_layout, config)

            if not eligible_pairs:
                termination_reason = (
                    CRAFTTerminationReason.NO_ELIGIBLE_SWAPS.value
                    if not accepted_swaps
                    else CRAFTTerminationReason.NO_IMPROVING_SWAP.value
                )
                break

            best_candidate: Optional[Tuple[str, str, bool, ContinuousLayout, float, float]] = None
            best_improvement = -float("inf")
            feasible_count = 0
            rejected_count = 0
            rejection_breakdown: Dict[str, int] = {}
            candidate_evals: List[Dict[str, Any]] = []

            for dept_a, dept_b, is_rot in eligible_pairs:
                cand_layout = create_swapped_layout(current_layout, dept_a, dept_b, is_rotational=is_rot)
                is_valid, reject_reason = validate_candidate_swap(problem, cand_layout, config)

                if not is_valid:
                    rejected_count += 1
                    reason_key = reject_reason or "Unknown violation"
                    rejection_breakdown[reason_key] = rejection_breakdown.get(reason_key, 0) + 1
                    if config.trace_level == "DETAILED":
                        candidate_evals.append({
                            "pair": (dept_a, dept_b),
                            "is_rotational": is_rot,
                            "is_feasible": False,
                            "rejection_reason": reject_reason,
                            "mhc_after": None,
                            "improvement": None,
                        })
                    continue

                feasible_count += 1
                cand_mhc = compute_mhc(problem, cand_layout, config)
                imp = round(current_mhc - cand_mhc, 4)

                if config.trace_level == "DETAILED":
                    candidate_evals.append({
                        "pair": (dept_a, dept_b),
                        "is_rotational": is_rot,
                        "is_feasible": True,
                        "rejection_reason": None,
                        "mhc_after": cand_mhc,
                        "improvement": imp,
                    })

                # Steepest descent / best improvement selection
                if imp > best_improvement + config.numerical_tolerance:
                    best_candidate = (dept_a, dept_b, is_rot, cand_layout, cand_mhc, imp)
                    best_improvement = imp
                elif abs(imp - best_improvement) <= config.numerical_tolerance:
                    # Deterministic tie-breaking: pick lexicographically smaller pair
                    if best_candidate is not None:
                        curr_pair = (dept_a, dept_b)
                        existing_pair = (best_candidate[0], best_candidate[1])
                        if curr_pair < existing_pair:
                            best_candidate = (dept_a, dept_b, is_rot, cand_layout, cand_mhc, imp)
                            best_improvement = imp

            # Check if an improvement exceeding the threshold was found
            if best_candidate is None or best_improvement < config.min_improvement_threshold:
                termination_reason = CRAFTTerminationReason.NO_IMPROVING_SWAP.value
                trace_steps.append(
                    CRAFTTraceStep(
                        iteration=iteration,
                        current_mhc=current_mhc,
                        candidate_pairs=len(eligible_pairs),
                        feasible_candidates=feasible_count,
                        rejected_candidates=rejected_count,
                        rejection_breakdown=rejection_breakdown,
                        selected_swap=None,
                        mhc_before=current_mhc,
                        mhc_after=current_mhc,
                        improvement=0.0,
                        cumulative_improvement=round(cumulative_improvement, 4),
                        layout_signature=generate_layout_signature(current_layout),
                        candidate_evaluations=candidate_evals if config.trace_level == "DETAILED" else None,
                    )
                )
                break

            # Accept the best candidate exchange
            d_a, d_b, is_rot, next_layout, next_mhc, imp = best_candidate
            cumulative_improvement += imp
            next_sig = generate_layout_signature(next_layout)

            swap_step = CRAFTSwapStep(
                iteration=iteration,
                dept_a=d_a,
                dept_b=d_b,
                is_rotational=is_rot,
                mhc_before=current_mhc,
                mhc_after=next_mhc,
                improvement=imp,
                cumulative_improvement=round(cumulative_improvement, 4),
                layout_signature=next_sig,
            )
            accepted_swaps.append(swap_step)

            trace_steps.append(
                CRAFTTraceStep(
                    iteration=iteration,
                    current_mhc=current_mhc,
                    candidate_pairs=len(eligible_pairs),
                    feasible_candidates=feasible_count,
                    rejected_candidates=rejected_count,
                    rejection_breakdown=rejection_breakdown,
                    selected_swap=swap_step,
                    mhc_before=current_mhc,
                    mhc_after=next_mhc,
                    improvement=imp,
                    cumulative_improvement=round(cumulative_improvement, 4),
                    layout_signature=next_sig,
                    candidate_evaluations=candidate_evals if config.trace_level == "DETAILED" else None,
                )
            )

            current_layout = next_layout
            current_mhc = next_mhc

        if iteration >= config.max_iterations and termination_reason != CRAFTTerminationReason.NO_IMPROVING_SWAP.value:
            termination_reason = CRAFTTerminationReason.MAX_ITERATIONS_REACHED.value

        exec_time = round(time.time() - start_time, 4)
        final_mhc = current_mhc
        absolute_imp = round(initial_mhc - final_mhc, 4)
        percentage_imp = round((absolute_imp / initial_mhc * 100.0), 2) if initial_mhc > 0 else 0.0
        final_signature = generate_layout_signature(current_layout)

        trace = CRARAFT_trace = CRAFTExecutionTrace(
            algorithm_name=self.name,
            algorithm_version=self.version,
            initial_mhc=initial_mhc,
            final_mhc=final_mhc,
            absolute_improvement=absolute_imp,
            percentage_improvement=percentage_imp,
            total_iterations=len(trace_steps),
            total_swaps_accepted=len(accepted_swaps),
            termination_reason=termination_reason,
            steps=trace_steps,
            execution_time_seconds=exec_time,
        )

        unequal_adj = detect_unequal_adjacent_pairs(problem, current_layout, tolerance=config.numerical_tolerance)

        craft_result = CRAFTSolverResult(
            algorithm_name=self.name,
            algorithm_version=self.version,
            initial_layout_signature=initial_signature,
            final_layout_signature=final_signature,
            is_complete=True,
            is_feasible=True,
            termination_reason=termination_reason,
            iterations=len(trace_steps),
            accepted_swaps=accepted_swaps,
            initial_mhc=initial_mhc,
            final_mhc=final_mhc,
            absolute_improvement=absolute_imp,
            percentage_improvement=percentage_imp,
            trace=trace,
            final_layout=current_layout,
            metadata={
                "unequal_adjacent_pairs_count": len(unequal_adj),
                "unequal_adjacent_pairs": unequal_adj,
                "config": config.model_dump(),
            },
        )

        # Convert final ContinuousLayout to standard LayoutSolution
        solution = current_layout.to_layout_solution(
            problem_id=problem.id,
            algorithm_name=self.name,
            algorithm_version=self.version,
            objective_values={
                "material_handling_cost": final_mhc,
                "initial_mhc": initial_mhc,
                "absolute_improvement": absolute_imp,
                "percentage_improvement": percentage_imp,
            },
        )
        solution.is_complete = True
        solution.placed_department_count = len(current_layout.placements)
        solution.total_department_count = len(problem.departments)
        solution.unplaced_departments = []
        solution.termination_reason = termination_reason
        solution.execution_time_seconds = exec_time
        solution.metadata = {
            "craft_result": craft_result.model_dump(),
            "trace": trace.model_dump(),
        }

        return solution, craft_result


# Also register with the exact name alias
AlgorithmRegistry.register("craft_pairwise_rectangular_v1")(CRAFTAlgorithm)
