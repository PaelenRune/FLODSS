"""CORELAP: Computerized Relationship Layout Planning algorithm implementation."""

import time
from typing import Any, Dict, List, Optional, Set
from app.algorithms.base import (
    BaseLayoutAlgorithm,
    AlgorithmCategory,
    ValidationResult,
)
from app.algorithms.registry import register_algorithm
from app.models.problem import FacilityLayoutProblem
from app.models.department import Department
from app.models.solution import LayoutSolution, SolverTerminationReason
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.services.layout_normalizer import generate_layout_signature
from app.algorithms.corelap.config import CORELAPConfig, TraceLevel
from app.algorithms.corelap.trace import CORELAPTraceStep, CORELAPExecutionTrace
from app.algorithms.corelap.tcr import (
    calculate_tcr,
    select_initial_department,
    select_next_department,
)
from app.algorithms.corelap.geometry_helpers import (
    determine_department_dimensions,
    generate_legal_department_shapes,
    generate_candidate_placements,
)
from app.algorithms.corelap.scoring import evaluate_and_rank_candidates


@register_algorithm("corelap")
class CORELAPAlgorithm(BaseLayoutAlgorithm):
    """Deterministic CORELAP v1.0 layout construction heuristic.
    
    References:
        - Lee, R. C., & Moore, J. M. (1967). CORELAP—COmputerized RElationship LAyout Planning.
          Journal of Industrial Engineering, 18(3), 195-200.
        - Muther, R. (1973). Systematic Layout Planning (SLP).
    """

    @property
    def name(self) -> str:
        return "corelap"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AlgorithmCategory:
        return AlgorithmCategory.CONSTRUCTION

    @property
    def default_parameters(self) -> Dict[str, Any]:
        return CORELAPConfig().model_dump()

    @property
    def supported_problem_types(self) -> List[str]:
        return [
            "unequal_areas",
            "qualitative_relationships",
            "continuous_representation",
            "fixed_positions",
            "reserved_zones",
        ]

    @property
    def metadata(self) -> Dict[str, Any]:
        base_meta = super().metadata
        base_meta.update({
            "display_name": "CORELAP (Computerized Relationship Layout Planning)",
            "deterministic": True,
            "complexity": "O(N^2 * C) where N=departments, C=candidate positions",
            "reference": "Lee & Moore (1967) / Muther Systematic Layout Planning",
        })
        return base_meta

    def validate(self, problem: FacilityLayoutProblem) -> ValidationResult:
        """Validate whether the problem can be constructed via CORELAP."""
        res = super().validate(problem)
        errors = list(res.errors)
        warnings = list(res.warnings)

        if not problem.relationships:
            warnings.append(
                "Problem contains no qualitative relationships (REL chart). "
                "CORELAP will default to area-based tie-breaking."
            )

        if not problem.departments:
            errors.append("At least one department is required for CORELAP.")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def solve(self, problem: FacilityLayoutProblem, **kwargs) -> LayoutSolution:
        """Execute deterministic CORELAP layout construction.
        
        Lifecycle:
            1. Parse configuration and validate feasibility.
            2. Compute Total Closeness Ratings (TCR).
            3. Position pre-fixed departments (brownfield preservation).
            4. Greedily select and position departments by maximal affinity.
            5. Audit trace history and export standardized LayoutSolution with completion status.
        """
        start_time = time.perf_counter()

        # 1. Merge configuration parameters
        cfg_dict = self.parameters.copy()
        cfg_dict.update(kwargs)
        config = CORELAPConfig.model_validate(cfg_dict)

        total_dept_count = len(problem.departments)
        tcr_map = calculate_tcr(problem)
        unplaced_map: Dict[str, Department] = {d.id: d for d in problem.departments}
        placed_placements: Dict[str, ContinuousPlacement] = {}
        placement_order: List[str] = []
        trace_steps: List[CORELAPTraceStep] = []

        # 2. Pre-place fixed position departments
        fixed_depts = [d for d in problem.departments if d.fixed_position is not None]
        for fd in fixed_depts:
            w, h = determine_department_dimensions(fd, config)
            fx = fd.fixed_position.x
            fy = fd.fixed_position.y
            placed_placements[fd.id] = ContinuousPlacement(
                department_id=fd.id,
                x=fx,
                y=fy,
                width=w,
                height=h,
            )
            placement_order.append(fd.id)
            unplaced_map.pop(fd.id, None)

            trace_steps.append(
                CORELAPTraceStep(
                    step_number=len(trace_steps) + 1,
                    selected_department=fd.id,
                    tcr=tcr_map.get(fd.id, 0.0),
                    placed_relationship_score=0.0,
                    candidate_count=1,
                    selected_candidate={"x": fx, "y": fy, "width": w, "height": h},
                    candidate_score=1000.0,
                    neighbors=[],
                    rejected_candidates=0,
                    rejection_reasons={},
                )
            )

        step_idx = len(trace_steps) + 1
        failure_reason: Optional[str] = None

        # 3. Construction loop
        while unplaced_map:
            unplaced_list = list(unplaced_map.values())

            # Select department to place
            if not placed_placements:
                selected_dept = select_initial_department(unplaced_list, tcr_map)
                placed_score = 0.0
            else:
                selected_dept, placed_score = select_next_department(
                    unplaced_list, set(placed_placements.keys()), problem, tcr_map
                )

            base_w, base_h = determine_department_dimensions(selected_dept, config)

            # Generate legal shapes if alternatives permitted
            legal_shapes = generate_legal_department_shapes(
                dept=selected_dept,
                placed_placements=placed_placements,
                facility_width=problem.facility.width,
                facility_height=problem.facility.height,
                config=config,
            )

            # Generate valid candidate placements across legal shapes
            candidates, rejection_reasons = generate_candidate_placements(
                dept_id=selected_dept.id,
                width=base_w,
                height=base_h,
                placed_placements=placed_placements,
                facility_width=problem.facility.width,
                facility_height=problem.facility.height,
                config=config,
                reserved_zones=problem.facility.reserved_zones if hasattr(problem.facility, "reserved_zones") else [],
                shapes=legal_shapes,
            )

            if not candidates:
                # No feasible non-overlapping position within plant bounds
                failure_reason = (
                    f"No feasible candidate position found for department '{selected_dept.id}' "
                    f"within facility boundary [{problem.facility.width}x{problem.facility.height}]. "
                    f"Rejections: {rejection_reasons}"
                )
                break

            # Score and rank candidates deterministically
            ranked_cands = evaluate_and_rank_candidates(
                candidates=candidates,
                placed_placements=placed_placements,
                problem=problem,
                config=config,
            )

            chosen_placement, chosen_score, chosen_neighbors = ranked_cands[0]
            placed_placements[selected_dept.id] = chosen_placement
            placement_order.append(selected_dept.id)
            unplaced_map.pop(selected_dept.id, None)

            # Capture detailed diagnostics if requested
            candidate_diagnostics = None
            if config.trace_level == TraceLevel.DETAILED:
                candidate_diagnostics = [
                    {
                        "x": c.x,
                        "y": c.y,
                        "width": c.width,
                        "height": c.height,
                        "orientation_degrees": c.orientation_degrees,
                        "score": round(s, 2),
                        "neighbors": n,
                    }
                    for c, s, n in ranked_cands[:10]
                ]

            trace_steps.append(
                CORELAPTraceStep(
                    step_number=step_idx,
                    selected_department=selected_dept.id,
                    tcr=tcr_map.get(selected_dept.id, 0.0),
                    placed_relationship_score=placed_score,
                    candidate_count=len(candidates),
                    selected_candidate={
                        "x": chosen_placement.x,
                        "y": chosen_placement.y,
                        "width": chosen_placement.width,
                        "height": chosen_placement.height,
                    },
                    candidate_score=chosen_score,
                    neighbors=chosen_neighbors,
                    rejected_candidates=sum(rejection_reasons.values()),
                    rejection_reasons=rejection_reasons,
                    candidate_diagnostics=candidate_diagnostics,
                )
            )
            step_idx += 1

        elapsed_seconds = round(time.perf_counter() - start_time, 4)
        unplaced_dept_ids = sorted(list(unplaced_map.keys()))
        placed_dept_count = len(placed_placements)
        is_complete = (len(unplaced_dept_ids) == 0 and failure_reason is None)

        if is_complete:
            termination_reason = SolverTerminationReason.SUCCESS_COMPLETE.value
        elif failure_reason and "No feasible candidate position" in failure_reason:
            termination_reason = SolverTerminationReason.FAILED_NO_FEASIBLE_CANDIDATE.value
        else:
            termination_reason = SolverTerminationReason.PARTIAL_INCOMPLETE.value

        # 4. Assemble ContinuousLayout representation
        reserved = problem.facility.reserved_zones if hasattr(problem.facility, "reserved_zones") else []
        continuous_layout = ContinuousLayout(
            id=f"CORELAP_{problem.id}",
            name=f"CORELAP Layout ({problem.name})",
            problem_id=problem.id,
            facility_width=problem.facility.width,
            facility_height=problem.facility.height,
            placements=placed_placements,
            reserved_zones=reserved or [],
        )

        signature = generate_layout_signature(continuous_layout)
        continuous_layout.layout_signature = signature

        from app.services.layout_validator import LayoutValidator
        from app.constraints.engine import ConstraintEngine

        val_res = LayoutValidator.validate(problem, continuous_layout)
        const_violations = ConstraintEngine().check_all(problem, continuous_layout)
        hard_violation_count = ConstraintEngine.count_hard_violations(const_violations)
        is_feasible = bool(is_complete and val_res.is_valid and hard_violation_count == 0)

        trace = CORELAPExecutionTrace(
            algorithm_name="corelap_deterministic_v1",
            algorithm_version=self.version,
            total_departments=total_dept_count,
            placed_count=placed_dept_count,
            execution_success=is_complete,
            is_complete=is_complete,
            placed_department_count=placed_dept_count,
            total_department_count=total_dept_count,
            unplaced_departments=unplaced_dept_ids,
            termination_reason=termination_reason,
            placement_order=placement_order,
            tcr_values=tcr_map,
            steps=trace_steps,
            failure_reason=failure_reason or ("; ".join(val_res.errors) if not val_res.is_valid else None),
            execution_time_seconds=elapsed_seconds,
        )

        # 5. Convert to standard LayoutSolution
        solution = continuous_layout.to_layout_solution(
            problem_id=problem.id,
            algorithm_name=self.name,
            algorithm_version=self.version,
        )

        solution.is_complete = is_complete
        solution.placed_department_count = placed_dept_count
        solution.total_department_count = total_dept_count
        solution.unplaced_departments = unplaced_dept_ids
        solution.termination_reason = termination_reason
        solution.feasibility_status = is_feasible
        solution.constraint_violations = const_violations
        solution.execution_time_seconds = elapsed_seconds
        solution.metadata = {
            "algorithm_name": "corelap_deterministic_v1",
            "algorithm_version": self.version,
            "success": is_complete,
            "execution_status": "COMPLETED" if is_complete else "INCOMPLETE",
            "validation_status": "FEASIBLE" if is_feasible else "INFEASIBLE",
            "is_complete": is_complete,
            "is_feasible": is_feasible,
            "placed_department_count": placed_dept_count,
            "total_department_count": total_dept_count,
            "unplaced_departments": unplaced_dept_ids,
            "termination_reason": termination_reason,
            "failure_reason": failure_reason or ("; ".join(val_res.errors) if not val_res.is_valid else None),
            "validation_errors": val_res.errors,
            "config": config.model_dump(),
            "tcr_values": tcr_map,
            "placement_order": placement_order,
            "layout_signature": signature,
            "trace": trace.model_dump(),
        }

        return solution
