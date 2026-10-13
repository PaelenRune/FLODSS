"""Decoupled Evaluation Engine for multi-criteria assessment of layout solutions."""

from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.models.representation import ContinuousLayout
from app.models.constraint import ConstraintViolation, ConstraintClassification
from app.evaluation.base import BaseMetricEvaluator
from app.evaluation.metrics import EvaluationMetricResult, MetricType, MetricDirection
from app.evaluation.config import EvaluationConfig
from app.evaluation.evaluators import (
    FlowDistanceEvaluator,
    MaterialHandlingCostEvaluator,
    RelationshipSatisfactionEvaluator,
    AreaUtilizationEvaluator,
    ConstraintPenaltyEvaluator,
)
from app.evaluation.matrices import DistanceMatrixService, DistanceMatrixResult
from app.constraints.engine import ConstraintEngine
from app.services.layout_normalizer import generate_layout_signature


class EvaluationReport(BaseModel):
    """Consolidated multi-criteria evaluation report for a single layout solution."""

    problem_id: str = Field(..., description="Target facility problem identifier")
    algorithm_name: str = Field(default="unknown_algorithm", description="Producing algorithm or baseline name")
    layout_signature: Optional[str] = Field(default=None, description="Deterministic SHA-256 geometric invariant fingerprint")
    is_feasible: bool = Field(default=True, description="Strict feasibility status (False if any hard constraint violated)")

    # Layout completeness and benchmark integrity (Phase 5.1)
    complete_layout: bool = Field(
        default=True,
        description="True if all problem departments are positioned; False if partial construction",
    )
    is_comparable: bool = Field(
        default=True,
        description="True if layout is complete and eligible for apples-to-apples baseline comparison and ranking",
    )
    unplaced_departments: List[str] = Field(
        default_factory=list,
        description="List of department IDs omitted from this layout",
    )
    diagnostic_partial_values: Optional[Dict[str, float]] = Field(
        default=None,
        description="Diagnostic scores for partial layouts; cannot be compared to complete layouts",
    )

    # Standardized objective values
    objective_values: Dict[str, float] = Field(
        default_factory=dict,
        description="Raw computed scores for standard objectives (material_handling_cost, flow_distance, relationship_score, etc.)",
    )
    normalized_values: Optional[Dict[str, float]] = Field(
        default=None,
        description="Normalized [0.0, 1.0] objective scores across a multi-layout comparison set",
    )
    composite_score: Optional[float] = Field(
        default=None,
        description="Multi-objective weighted composite quality score",
    )
    rank: Optional[int] = Field(
        default=None,
        description="Ordinal rank within comparison set (1 = best)",
    )

    # Constraints breakdown
    constraint_violations: List[ConstraintViolation] = Field(default_factory=list)
    hard_violation_count: int = Field(default=0, ge=0)
    soft_violation_count: int = Field(default=0, ge=0)
    total_constraint_penalty: float = Field(default=0.0, ge=0)

    # Detailed metric diagnostics
    metrics: Dict[str, EvaluationMetricResult] = Field(default_factory=dict)
    summary_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Legacy flat score view for backwards compatibility",
    )
    top_contributors: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Top contributing flow and relationship pairs for AI explanation",
    )
    evaluation_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parameters and metric configuration used during assessment",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComparisonReport(BaseModel):
    """Comparative evaluation across multiple candidate layout solutions."""

    problem_id: str
    solution_count: int
    reports: List[EvaluationReport] = Field(default_factory=list)
    ranking: List[str] = Field(
        default_factory=list,
        description="Ranked list of algorithm names or solution IDs based on multi-criteria weighting",
    )
    weights_used: Dict[str, float] = Field(
        default_factory=dict,
        description="Objective weights utilized during composite ranking",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationEngine:
    """Coordinates independent evaluators to assess layout solutions without coupling to algorithms."""

    def __init__(
        self,
        evaluators: Optional[List[BaseMetricEvaluator]] = None,
        constraint_engine: Optional[ConstraintEngine] = None,
        config: Optional[EvaluationConfig] = None,
    ):
        """Initialize engine with either custom or default industrial metric evaluators."""
        self.config = config or EvaluationConfig()
        self.constraint_engine = constraint_engine or ConstraintEngine()
        self._evaluators: Dict[str, BaseMetricEvaluator] = {}

        if evaluators is not None:
            for ev in evaluators:
                self.register_evaluator(ev)
        else:
            # Register standard evaluation suite
            self.register_evaluator(MaterialHandlingCostEvaluator(self.config))
            self.register_evaluator(FlowDistanceEvaluator(self.config))
            self.register_evaluator(RelationshipSatisfactionEvaluator(self.config))
            self.register_evaluator(AreaUtilizationEvaluator(self.config))
            self.register_evaluator(ConstraintPenaltyEvaluator(self.constraint_engine, self.config))

    def register_evaluator(self, evaluator: BaseMetricEvaluator) -> None:
        """Register an evaluator into the engine."""
        self._evaluators[evaluator.metric_name] = evaluator

    def unregister_evaluator(self, metric_name: str) -> None:
        """Remove an evaluator by its metric name."""
        self._evaluators.pop(metric_name, None)

    @property
    def registered_metrics(self) -> List[str]:
        """List all currently registered metric names."""
        return list(self._evaluators.keys())

    def evaluate(
        self,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout, Dict[str, Any]],
        config: Optional[EvaluationConfig] = None,
        metrics_subset: Optional[List[str]] = None,
    ) -> EvaluationReport:
        """Run all registered evaluators on a layout solution.
        
        Args:
            problem: Facility problem specification.
            solution: Candidate layout solution or continuous layout.
            config: Optional evaluation configuration overrides.
            metrics_subset: Optional filter of specific metric names to compute.
            
        Returns:
            Comprehensive EvaluationReport.
        """
        eff_config = config or self.config

        # 1. Normalize layout
        if isinstance(solution, ContinuousLayout):
            cont_layout = solution
            algo_name = (
                (solution.metadata.get("algorithm_name") if solution.metadata else None)
                or solution.name
                or solution.id
                or "continuous_layout"
            )
            sol_feasible = True
            existing_violations: List[ConstraintViolation] = []
        elif isinstance(solution, LayoutSolution):
            cont_layout = ContinuousLayout.from_layout_solution(
                solution,
                facility_width=problem.facility.width,
                facility_height=problem.facility.height,
            )
            algo_name = solution.algorithm_name or "layout_solution"
            sol_feasible = solution.feasibility_status
            existing_violations = list(solution.constraint_violations)
        elif isinstance(solution, dict):
            cont_layout = ContinuousLayout.model_validate(solution)
            meta = solution.get("metadata") or {}
            algo_name = (
                (meta.get("algorithm_name") if isinstance(meta, dict) else None)
                or solution.get("name")
                or solution.get("id")
                or "dict_layout"
            )
            sol_feasible = True
            existing_violations = []
        else:
            raise TypeError(f"Unsupported solution type for evaluation: {type(solution)}")

        # 2. Geometric signature
        signature = generate_layout_signature(cont_layout)

        # 3. Precompute distance matrix once for all spatial evaluators
        distance_matrix: DistanceMatrixResult = DistanceMatrixService.compute(
            cont_layout,
            metric=eff_config.distance_metric,
        )

        # 4. Check constraints via ConstraintEngine
        constraint_violations = self.constraint_engine.check_all(problem, cont_layout)
        # Merge any pre-attached violations
        all_violations = existing_violations + constraint_violations
        hard_count = self.constraint_engine.count_hard_violations(all_violations)
        soft_count = self.constraint_engine.count_soft_violations(all_violations)
        total_penalty = self.constraint_engine.calculate_total_penalty(all_violations)

        # Check completeness against required problem departments
        problem_dept_ids = {d.id for d in problem.departments}
        placed_dept_ids = set(cont_layout.placements.keys())
        missing_depts = sorted(list(problem_dept_ids - placed_dept_ids))
        is_complete_layout = (len(missing_depts) == 0)
        is_comparable = is_complete_layout

        is_feasible = sol_feasible and (hard_count == 0) and is_complete_layout

        # 5. Evaluate all registered metrics
        metric_results: Dict[str, EvaluationMetricResult] = {}
        summary_scores: Dict[str, float] = {}
        top_contributors: Dict[str, List[Dict[str, Any]]] = {}

        for name, evaluator in self._evaluators.items():
            if metrics_subset and name not in metrics_subset:
                continue
            try:
                # Pass precomputed distance matrix if accepted
                if isinstance(evaluator, (FlowDistanceEvaluator, MaterialHandlingCostEvaluator, RelationshipSatisfactionEvaluator)):
                    res = evaluator.evaluate(problem, cont_layout, distance_matrix=distance_matrix)
                else:
                    res = evaluator.evaluate(problem, cont_layout)

                metric_results[name] = res
                summary_scores[name] = res.value

                # Extract top contributors if available
                if "top_contributors" in res.details:
                    top_contributors[name] = res.details["top_contributors"]
            except Exception as e:
                metric_results[name] = EvaluationMetricResult(
                    metric_name=name,
                    display_name=evaluator.display_name,
                    value=float("nan"),
                    details={"error": str(e)},
                )

        # 6. Map standard objective values
        mhc_val = summary_scores.get(MetricType.MATERIAL_HANDLING_COST.value, 0.0)
        fd_val = summary_scores.get(MetricType.TOTAL_FLOW_DISTANCE.value, 0.0)
        
        # For relationship satisfaction, retrieve raw score if present in details, else percentage
        rel_metric = metric_results.get(MetricType.RELATIONSHIP_SATISFACTION.value)
        if rel_metric and "relationship_raw_score" in rel_metric.details:
            rel_val = float(rel_metric.details["relationship_raw_score"])
        else:
            rel_val = summary_scores.get(MetricType.RELATIONSHIP_SATISFACTION.value, 0.0)

        util_val = summary_scores.get(MetricType.AREA_UTILIZATION.value, 0.0)

        if not is_complete_layout:
            diagnostic_partial_values = {
                "partial_material_handling_cost": round(mhc_val, 2),
                "partial_flow_distance": round(fd_val, 2),
                "partial_relationship_score": round(rel_val, 2),
                "partial_area_utilization": round(util_val, 2),
                "partial_constraint_penalty": round(total_penalty, 2),
            }
            objective_values: Dict[str, float] = {
                "material_handling_cost": round(mhc_val, 2),
                "flow_distance": round(fd_val, 2),
                "relationship_score": round(rel_val, 2),
                "area_utilization": round(util_val, 2),
                "constraint_penalty": round(total_penalty, 2),
                **diagnostic_partial_values,
            }
        else:
            diagnostic_partial_values = None
            objective_values = {
                "material_handling_cost": round(mhc_val, 2),
                "flow_distance": round(fd_val, 2),
                "relationship_score": round(rel_val, 2),
                "area_utilization": round(util_val, 2),
                "constraint_penalty": round(total_penalty, 2),
            }

        return EvaluationReport(
            problem_id=problem.id,
            algorithm_name=algo_name,
            layout_signature=signature,
            is_feasible=is_feasible,
            complete_layout=is_complete_layout,
            is_comparable=is_comparable,
            unplaced_departments=missing_depts,
            diagnostic_partial_values=diagnostic_partial_values,
            objective_values=objective_values,
            constraint_violations=all_violations,
            hard_violation_count=hard_count,
            soft_violation_count=soft_count,
            total_constraint_penalty=total_penalty,
            metrics=metric_results,
            summary_scores=summary_scores,
            top_contributors=top_contributors,
            evaluation_config=eff_config.model_dump(),
        )

    def evaluate_many(
        self,
        problem: FacilityLayoutProblem,
        solutions: List[Union[LayoutSolution, ContinuousLayout, Dict[str, Any]]],
        config: Optional[EvaluationConfig] = None,
    ) -> ComparisonReport:
        """Evaluate a set of candidate solutions with multi-layout normalization and feasibility-first ranking."""
        eff_config = config or self.config

        # 1. Independent evaluation of each solution
        reports = [self.evaluate(problem, sol, config=eff_config) for sol in solutions]
        if not reports:
            return ComparisonReport(
                problem_id=problem.id,
                solution_count=0,
                reports=[],
                ranking=[],
            )

        complete_reports = [r for r in reports if r.complete_layout]
        incomplete_reports = [r for r in reports if not r.complete_layout]

        # Isolate incomplete reports from composite ranking and normalization
        for ir in incomplete_reports:
            ir.normalized_values = None
            ir.composite_score = None
            ir.rank = None
            ir.is_comparable = False

        # 2. Extract objective weights (from problem configuration or defaults)
        weights: Dict[str, float] = {
            "material_handling_cost": 1.0,
            "flow_distance": 0.8,
            "relationship_score": 0.6,
            "area_utilization": 0.3,
            "constraint_penalty": 1.0,
        }
        if problem.objectives:
            for obj_name, obj_cfg in problem.objectives.items():
                if obj_cfg.enabled and obj_cfg.weight is not None:
                    weights[obj_name] = obj_cfg.weight

        # Apply config overrides
        weights.update(eff_config.objective_weights)

        obj_keys = ["material_handling_cost", "flow_distance", "relationship_score", "area_utilization", "constraint_penalty"]

        # Directions: MHC (MIN), FD (MIN), Rel (MAX), Area (MAX), Penalty (MIN)
        is_minimization = {
            "material_handling_cost": True,
            "flow_distance": True,
            "relationship_score": False,
            "area_utilization": False,
            "constraint_penalty": True,
        }

        total_weight = sum(weights.get(k, 1.0) for k in obj_keys)
        if total_weight <= 0:
            total_weight = 1.0

        if complete_reports:
            # 3. Min-Max normalization strictly across COMPLETE solution set
            min_vals: Dict[str, float] = {}
            max_vals: Dict[str, float] = {}

            for k in obj_keys:
                vals = [r.objective_values.get(k, 0.0) for r in complete_reports]
                min_vals[k] = min(vals)
                max_vals[k] = max(vals)

            for r in complete_reports:
                r.normalized_values = {}
                weighted_sum = 0.0

                for k in obj_keys:
                    val = r.objective_values.get(k, 0.0)
                    v_min = min_vals[k]
                    v_max = max_vals[k]

                    if abs(v_max - v_min) < 1e-9:
                        norm = 1.0
                    elif is_minimization[k]:
                        norm = (v_max - val) / (v_max - v_min)
                    else:
                        norm = (val - v_min) / (v_max - v_min)

                    norm = max(0.0, min(1.0, norm))
                    r.normalized_values[k] = round(norm, 4)
                    weighted_sum += weights.get(k, 1.0) * norm

                r.composite_score = round(weighted_sum / total_weight, 4)

            # 4. Feasibility-First Sorting & Ranking among complete layouts
            def rank_sort_key(r: EvaluationReport) -> Tuple[int, int, float, float]:
                if r.is_feasible:
                    return (0, 0, 0.0, -r.composite_score if r.composite_score is not None else 0.0)
                else:
                    return (
                        1,
                        r.hard_violation_count,
                        r.total_constraint_penalty,
                        -r.composite_score if r.composite_score is not None else 0.0,
                    )

            ranked_complete = sorted(complete_reports, key=rank_sort_key)
            for i, r in enumerate(ranked_complete):
                r.rank = i + 1

            all_reports = ranked_complete + incomplete_reports
            ranking = [r.algorithm_name for r in ranked_complete]
        else:
            all_reports = incomplete_reports
            ranking = []

        return ComparisonReport(
            problem_id=problem.id,
            solution_count=len(solutions),
            reports=all_reports,
            ranking=ranking,
            weights_used=weights,
            metadata={"normalization_method": eff_config.normalization_method},
        )

    def compare(
        self,
        problem: FacilityLayoutProblem,
        solutions: List[Union[LayoutSolution, ContinuousLayout, Dict[str, Any]]],
    ) -> ComparisonReport:
        """Alias for evaluate_many to preserve backwards compatibility."""
        return self.evaluate_many(problem, solutions)
