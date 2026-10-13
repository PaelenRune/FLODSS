"""ALDEP (Automated Layout Design Program) construction heuristic solver implementation."""

import random
import time
from typing import Any, Dict, List, Optional, Tuple

from app.algorithms.base import (
    BaseLayoutAlgorithm,
    AlgorithmCategory,
    ValidationResult,
)
from app.algorithms.registry import register_algorithm
from app.algorithms.aldep.config import ALDEPConfig, TraceLevel
from app.algorithms.aldep.models import (
    ALDEPCandidateResult,
    ALDEPExecutionTrace,
    ALDEPSolverResult,
)
from app.algorithms.aldep.selection import generate_aldep_sequence
from app.algorithms.aldep.placement import create_strip_sweep_layout
from app.models.geometry import Dimensions2D, Point2D
from app.models.problem import FacilityLayoutProblem, PrimaryObjective
from app.models.representation import ContinuousLayout
from app.models.solution import LayoutSolution, SolverTerminationReason
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator
from app.evaluation.engine import EvaluationEngine


@register_algorithm("aldep")
class ALDEPAlgorithm(BaseLayoutAlgorithm):
    """ALDEP (Automated Layout Design Program) stochastic construction heuristic.
    
    Academic Reference:
        - Seevers, J. A., & Ihm, P. (1967). ALDEP - Automated Layout Design Program.
          Proceedings of the SHARE-ACM-IEEE Design Automation Workshop.
        - Buffa, E. S., Armour, G. C., & Vollmann, T. E. (1964). Allocating Facilities with CRAFT.
        - Tompkins, J. A., et al. (2010). Facilities Planning (4th ed.). John Wiley & Sons.
    """

    @property
    def name(self) -> str:
        return "aldep"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AlgorithmCategory:
        return AlgorithmCategory.CONSTRUCTION

    @property
    def default_parameters(self) -> Dict[str, Any]:
        return ALDEPConfig().model_dump()

    @property
    def supported_problem_types(self) -> List[str]:
        return [
            "unequal_areas",
            "discrete_grid",
            "qualitative_relationships",
            "stochastic_multi_candidate",
            "fixed_positions",
            "reserved_zones",
        ]

    @property
    def metadata(self) -> Dict[str, Any]:
        meta = super().metadata
        meta.update({
            "display_name": "ALDEP (Automated Layout Design Program)",
            "stochastic": True,
            "complexity": "O(K * N^2) where K=candidates, N=departments",
            "reference": "Seevers & Ihm (1967) / Buffa, Armour & Vollmann (1964)",
        })
        return meta

    def validate(self, problem: FacilityLayoutProblem) -> ValidationResult:
        """Validate problem preconditions for ALDEP."""
        res = super().validate(problem)
        errors = list(res.errors)
        warnings = list(res.warnings)

        if not problem.departments:
            errors.append("ALDEP requires at least one department in the problem definition.")

        if not problem.relationships:
            warnings.append(
                "Problem contains no qualitative relationships (REL chart). "
                "ALDEP will operate purely using random sequence generation."
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def solve(self, problem: FacilityLayoutProblem, **kwargs) -> LayoutSolution:
        """Execute ALDEP heuristic and return top-ranked LayoutSolution."""
        solution, _ = self.solve_with_result(problem, **kwargs)
        return solution

    def solve_with_result(
        self,
        problem: FacilityLayoutProblem,
        **kwargs,
    ) -> Tuple[LayoutSolution, ALDEPSolverResult]:
        """Execute ALDEP and return both primary LayoutSolution and detailed ALDEPSolverResult."""
        start_time = time.perf_counter()

        # 1. Parameter configuration
        cfg_dict = self.parameters.copy()
        cfg_dict.update(kwargs)
        config = ALDEPConfig.model_validate(cfg_dict)

        base_seed = config.random_seed if config.random_seed is not None else 42
        num_candidates = config.number_of_candidates
        total_dept_count = len(problem.departments)

        eval_engine = EvaluationEngine()
        candidates: List[ALDEPCandidateResult] = []
        seen_signatures: Dict[str, int] = {}  # signature -> candidate_index

        # 2. Multi-candidate generation loop
        for c_idx in range(num_candidates):
            cand_seed = base_seed + c_idx
            rng = random.Random(cand_seed)

            # Sequence generation via Muther REL affinity and seeded random tie-break
            dept_order, steps = generate_aldep_sequence(problem, config, rng)

            # Strip-sweep spatial placement
            grid_layout, cont_layout, shape_diag, unplaced = create_strip_sweep_layout(
                problem=problem,
                department_order=dept_order,
                config=config,
            )

            signature = generate_layout_signature(cont_layout)
            placed_count = len(cont_layout.placements)
            is_complete = (len(unplaced) == 0 and placed_count == total_dept_count)

            # Geometric validation
            val_res = LayoutValidator.validate(problem, cont_layout)
            is_feasible = is_complete and val_res.is_valid

            # Termination status
            if is_feasible:
                term_reason = SolverTerminationReason.SUCCESS_COMPLETE.value
            elif is_complete:
                term_reason = "COMPLETE_WITH_GEOMETRIC_WARNINGS"
            else:
                term_reason = SolverTerminationReason.FAILED_NO_FEASIBLE_CANDIDATE.value

            # Independent evaluation
            eval_report = eval_engine.evaluate(problem, cont_layout)
            mhc = eval_report.objective_values.get("material_handling_cost")
            flow_dist = eval_report.objective_values.get("flow_distance")
            rel_score = eval_report.objective_values.get("relationship_score")
            area_util = eval_report.objective_values.get("area_utilization")

            # Duplicate check
            is_dup = signature in seen_signatures
            dup_of = seen_signatures.get(signature) if is_dup else None
            if not is_dup:
                seen_signatures[signature] = c_idx

            cand_result = ALDEPCandidateResult(
                candidate_index=c_idx,
                seed=cand_seed,
                department_order=dept_order,
                layout_signature=signature,
                is_complete=is_complete,
                is_feasible=is_feasible,
                is_duplicate=is_dup,
                duplicate_of_index=dup_of,
                placed_department_count=placed_count,
                total_department_count=total_dept_count,
                unplaced_departments=unplaced,
                termination_reason=term_reason,
                material_handling_cost=mhc,
                flow_distance=flow_dist,
                relationship_score=rel_score,
                area_utilization=area_util,
                shape_diagnostics=shape_diag,
                continuous_layout=cont_layout,
                grid_layout=grid_layout,
                selection_steps=steps if config.trace_level == TraceLevel.DETAILED else steps[:1],
            )
            candidates.append(cand_result)

        # 3. Ranking candidates
        primary_obj = (
            problem.objective_config.primary_objective
            if problem.objective_config
            else PrimaryObjective.MINIMIZE_FLOW_DISTANCE
        )

        def ranking_key(c: ALDEPCandidateResult) -> Tuple[int, int, float, float]:
            # Feasible & complete first (priority 2), complete second (priority 1), partial last (0)
            status_priority = 2 if c.is_feasible else (1 if c.is_complete else 0)
            placed_prio = c.placed_department_count
            mhc_val = c.material_handling_cost if c.material_handling_cost is not None else float("inf")
            rel_val = c.relationship_score if c.relationship_score is not None else -float("inf")

            is_rel_obj = (
                primary_obj == PrimaryObjective.MAXIMIZE_RELATIONSHIPS
                or getattr(primary_obj, "value", primary_obj) == "maximize_relationships"
            )
            if is_rel_obj:
                return (-status_priority, -placed_prio, -rel_val, mhc_val)
            else:
                return (-status_priority, -placed_prio, mhc_val, -rel_val)

        ranked_candidates = sorted(candidates, key=ranking_key)
        best_cand = ranked_candidates[0]

        exec_time = time.perf_counter() - start_time

        # 4. Construct execution trace
        trace = ALDEPExecutionTrace(
            algorithm_name=self.name,
            algorithm_version=self.version,
            number_of_candidates=num_candidates,
            unique_candidate_count=len(seen_signatures),
            feasible_candidate_count=sum(1 for c in candidates if c.is_feasible),
            complete_candidate_count=sum(1 for c in candidates if c.is_complete),
            best_candidate_index=best_cand.candidate_index,
            best_candidate_seed=best_cand.seed,
            execution_time_seconds=round(exec_time, 4),
            best_selection_steps=best_cand.selection_steps,
        )

        solver_result = ALDEPSolverResult(
            algorithm_name=self.name,
            algorithm_version=self.version,
            best_candidate=best_cand,
            candidates=candidates,
            trace=trace,
        )

        # 5. Assemble standard LayoutSolution
        placements_dict = {
            k: v.to_department_placement() for k, v in best_cand.continuous_layout.placements.items()
        }
        dept_positions = {k: v.centroid for k, v in best_cand.continuous_layout.placements.items()}
        dept_dims = {
            k: Dimensions2D(width=v.width, height=v.height)
            for k, v in best_cand.continuous_layout.placements.items()
        }

        objectives: Dict[str, float] = {}
        if best_cand.material_handling_cost is not None:
            objectives["material_handling_cost"] = best_cand.material_handling_cost
        if best_cand.flow_distance is not None:
            objectives["total_flow_distance"] = best_cand.flow_distance
        if best_cand.relationship_score is not None:
            objectives["relationship_score"] = best_cand.relationship_score
        if best_cand.area_utilization is not None:
            objectives["area_utilization"] = best_cand.area_utilization

        layout_solution = LayoutSolution(
            problem_id=problem.id,
            algorithm_name=self.name,
            algorithm_version=self.version,
            placements=placements_dict,
            department_positions=dept_positions,
            department_dimensions=dept_dims,
            objective_values=objectives,
            feasibility_status=best_cand.is_feasible,
            execution_time_seconds=round(exec_time, 4),
            is_complete=best_cand.is_complete,
            placed_department_count=best_cand.placed_department_count,
            total_department_count=best_cand.total_department_count,
            unplaced_departments=best_cand.unplaced_departments,
            termination_reason=best_cand.termination_reason,
            metadata={
                "layout_signature": best_cand.layout_signature,
                "best_candidate_index": best_cand.candidate_index,
                "best_candidate_seed": best_cand.seed,
                "total_candidates": num_candidates,
                "unique_candidates": len(seen_signatures),
                "department_order": best_cand.department_order,
                "shape_diagnostics": {
                    k: v.model_dump() for k, v in best_cand.shape_diagnostics.items()
                },
                "trace": trace.model_dump(),
            },
        )

        return layout_solution, solver_result
