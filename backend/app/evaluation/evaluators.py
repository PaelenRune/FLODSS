"""Standardized, decoupled industrial metric evaluators."""

import math
from typing import Any, Dict, List, Optional, Union
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.models.representation import ContinuousLayout
from app.models.relationship import RELATIONSHIP_DEFAULT_SCORES
from app.evaluation.base import BaseMetricEvaluator
from app.evaluation.metrics import (
    MetricType,
    MetricDirection,
    EvaluationMetricResult,
)
from app.evaluation.config import EvaluationConfig
from app.evaluation.matrices import (
    DistanceMatrixService,
    DistanceMatrixResult,
    FlowMatrixService,
    RelationshipMatrixService,
)
from app.constraints.engine import ConstraintEngine
from app.services.geometry_engine import DistanceMetricType, GeometryEngine


def _to_continuous_layout(
    problem: FacilityLayoutProblem,
    solution: Union[LayoutSolution, ContinuousLayout],
) -> ContinuousLayout:
    """Normalize solution or continuous layout."""
    if isinstance(solution, ContinuousLayout):
        return solution
    return ContinuousLayout.from_layout_solution(
        solution,
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
    )


class FlowDistanceEvaluator(BaseMetricEvaluator):
    """Calculates total rectilinear or euclidean flow-distance across directed flows: FD = Sum(F_ij * D_ij)."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or EvaluationConfig()

    @property
    def metric_name(self) -> str:
        return MetricType.TOTAL_FLOW_DISTANCE.value

    @property
    def display_name(self) -> str:
        return "Total Flow Distance"

    @property
    def unit(self) -> str:
        return "m-moves"

    @property
    def direction(self) -> MetricDirection:
        return MetricDirection.MINIMIZE

    def evaluate(
        self,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
        distance_matrix: Optional[DistanceMatrixResult] = None,
    ) -> EvaluationMetricResult:
        layout = _to_continuous_layout(problem, solution)
        d_matrix = distance_matrix or DistanceMatrixService.compute(layout, metric=self.config.distance_metric)

        total_fd = 0.0
        contributors: List[Dict[str, Any]] = []

        for flow in problem.flows:
            try:
                dist = d_matrix.get_distance(flow.source_department, flow.target_department)
            except KeyError:
                continue

            contribution = flow.quantity * dist
            total_fd += contribution

            if flow.quantity > 0:
                contributors.append({
                    "source": flow.source_department,
                    "target": flow.target_department,
                    "flow": flow.quantity,
                    "distance": round(dist, 2),
                    "contribution": round(contribution, 2),
                    "product_or_process_id": flow.product_or_process_id,
                })

        # Sort contributors descending
        contributors.sort(key=lambda x: x["contribution"], reverse=True)
        for c in contributors:
            c["percentage"] = round((c["contribution"] / total_fd * 100.0), 2) if total_fd > 0 else 0.0

        return EvaluationMetricResult(
            metric_name=self.metric_name,
            display_name=self.display_name,
            value=round(total_fd, 2),
            unit=self.unit,
            direction=self.direction,
            details={
                "metric_type": self.config.distance_metric.value,
                "flow_count": len(problem.flows),
                "top_contributors": contributors[: self.config.max_top_contributors],
            },
        )


class MaterialHandlingCostEvaluator(BaseMetricEvaluator):
    """Calculates total material handling cost: MHC = Sum(F_ij * D_ij * C_ij)."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or EvaluationConfig()

    @property
    def metric_name(self) -> str:
        return MetricType.MATERIAL_HANDLING_COST.value

    @property
    def display_name(self) -> str:
        return "Material Handling Cost"

    @property
    def unit(self) -> str:
        return "$"

    @property
    def direction(self) -> MetricDirection:
        return MetricDirection.MINIMIZE

    def evaluate(
        self,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
        distance_matrix: Optional[DistanceMatrixResult] = None,
    ) -> EvaluationMetricResult:
        layout = _to_continuous_layout(problem, solution)
        d_matrix = distance_matrix or DistanceMatrixService.compute(layout, metric=self.config.distance_metric)

        total_mhc = 0.0
        contributors: List[Dict[str, Any]] = []

        for flow in problem.flows:
            try:
                dist = d_matrix.get_distance(flow.source_department, flow.target_department)
            except KeyError:
                continue

            cost_per_unit = (
                flow.cost_per_unit_distance
                if flow.cost_per_unit_distance is not None
                else self.config.default_cost_per_unit_distance
            )

            cost = flow.quantity * dist * cost_per_unit
            total_mhc += cost

            if flow.quantity > 0:
                contributors.append({
                    "source": flow.source_department,
                    "target": flow.target_department,
                    "flow": flow.quantity,
                    "distance": round(dist, 2),
                    "cost_per_unit_distance": cost_per_unit,
                    "cost": round(cost, 2),
                    "product_or_process_id": flow.product_or_process_id,
                })

        contributors.sort(key=lambda x: x["cost"], reverse=True)
        for c in contributors:
            c["percentage"] = round((c["cost"] / total_mhc * 100.0), 2) if total_mhc > 0 else 0.0

        return EvaluationMetricResult(
            metric_name=self.metric_name,
            display_name=self.display_name,
            value=round(total_mhc, 2),
            unit=self.unit,
            direction=self.direction,
            details={
                "metric_type": self.config.distance_metric.value,
                "default_cost_per_unit_distance": self.config.default_cost_per_unit_distance,
                "top_contributors": contributors[: self.config.max_top_contributors],
            },
        )


class RelationshipSatisfactionEvaluator(BaseMetricEvaluator):
    """Evaluates Muther SLP relationship satisfaction.
    
    Mathematical Formulation:
    - Facility maximum diagonal span D_max = sqrt(W^2 + H^2).
    - Proximity ratio P_ij = max(0.0, 1.0 - (D_ij / D_max)).
    - Positive relationships (A, E, I, O: S_ij > 0) earn a proximity reward:
      Reward_ij = S_ij * P_ij  (Max potential = S_ij when touching/zero distance).
    - Undesirable relationships (X = -8: S_ij < 0) incur a proximity penalty when too close:
      Penalty_ij = |S_ij| * P_ij  (Decreases towards zero as departments move apart).
    - Net Raw Score = Sum(Reward_ij) - Sum(Penalty_ij).
    - Satisfaction Ratio = max(0.0, min(1.0, Net Score / Sum(S_ij for S_ij > 0))).
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or EvaluationConfig()

    @property
    def metric_name(self) -> str:
        return MetricType.RELATIONSHIP_SATISFACTION.value

    @property
    def display_name(self) -> str:
        return "Relationship Satisfaction"

    @property
    def unit(self) -> str:
        return "%"

    @property
    def direction(self) -> MetricDirection:
        return MetricDirection.MAXIMIZE

    def evaluate(
        self,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
        distance_matrix: Optional[DistanceMatrixResult] = None,
    ) -> EvaluationMetricResult:
        layout = _to_continuous_layout(problem, solution)
        fac_w = problem.facility.width
        fac_h = problem.facility.height
        max_dist = math.hypot(fac_w, fac_h)
        if max_dist <= 0:
            max_dist = 1.0

        d_matrix = distance_matrix or DistanceMatrixService.compute(layout, metric=self.config.distance_metric)

        total_reward = 0.0
        total_penalty = 0.0
        max_possible_reward = 0.0
        pair_details: List[Dict[str, Any]] = []

        for rel in problem.relationships:
            try:
                dist = d_matrix.get_distance(rel.department_a, rel.department_b)
            except KeyError:
                continue

            score = rel.score
            if score == 0.0 and rel.relationship_type.value != "U":
                score = RELATIONSHIP_DEFAULT_SCORES.get(rel.relationship_type, 0.0)

            # Proximity factor P in [0.0, 1.0]
            prox = max(0.0, 1.0 - (dist / max_dist))

            if score > 0:
                reward = score * prox
                total_reward += reward
                max_possible_reward += score
                pair_details.append({
                    "department_a": rel.department_a,
                    "department_b": rel.department_b,
                    "rating": rel.relationship_type.value,
                    "score": score,
                    "distance": round(dist, 2),
                    "proximity": round(prox, 3),
                    "contribution": round(reward, 2),
                    "type": "reward",
                })
            elif score < 0:
                # X penalty
                pen = abs(score) * prox
                total_penalty += pen
                pair_details.append({
                    "department_a": rel.department_a,
                    "department_b": rel.department_b,
                    "rating": rel.relationship_type.value,
                    "score": score,
                    "distance": round(dist, 2),
                    "proximity": round(prox, 3),
                    "penalty": round(pen, 2),
                    "type": "penalty",
                })

        net_raw_score = total_reward - total_penalty

        if max_possible_reward > 0:
            satisfaction_ratio = max(0.0, min(1.0, net_raw_score / max_possible_reward))
        else:
            satisfaction_ratio = 1.0

        satisfaction_pct = round(satisfaction_ratio * 100.0, 2)

        return EvaluationMetricResult(
            metric_name=self.metric_name,
            display_name=self.display_name,
            value=satisfaction_pct,
            unit=self.unit,
            direction=self.direction,
            details={
                "relationship_raw_score": round(net_raw_score, 2),
                "relationship_satisfaction_ratio": round(satisfaction_ratio, 4),
                "satisfaction_percentage": satisfaction_pct,
                "positive_proximity_reward": round(total_reward, 2),
                "negative_proximity_penalty": round(total_penalty, 2),
                "max_possible_reward": round(max_possible_reward, 2),
                "evaluated_relationships_count": len(problem.relationships),
                "details": pair_details,
            },
        )


class AreaUtilizationEvaluator(BaseMetricEvaluator):
    """Calculates floor area utilization: occupied department area vs usable facility area."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or EvaluationConfig()

    @property
    def metric_name(self) -> str:
        return MetricType.AREA_UTILIZATION.value

    @property
    def display_name(self) -> str:
        return "Floor Area Utilization"

    @property
    def unit(self) -> str:
        return "%"

    @property
    def direction(self) -> MetricDirection:
        return MetricDirection.MAXIMIZE

    def evaluate(
        self,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> EvaluationMetricResult:
        layout = _to_continuous_layout(problem, solution)
        fac_w = problem.facility.width
        fac_h = problem.facility.height
        facility_area = fac_w * fac_h

        # Compute reserved zones area without double counting
        reserved_area = sum(z.bounding_box.area for z in layout.reserved_zones)
        usable_area = max(0.0, facility_area - reserved_area)

        occupied_area = sum(p.area for p in layout.placements.values())
        free_area = max(0.0, usable_area - occupied_area)

        utilization_ratio = occupied_area / usable_area if usable_area > 0 else 0.0
        utilization_pct = round(utilization_ratio * 100.0, 2)

        return EvaluationMetricResult(
            metric_name=self.metric_name,
            display_name=self.display_name,
            value=utilization_pct,
            unit=self.unit,
            direction=self.direction,
            details={
                "facility_area": round(facility_area, 2),
                "reserved_area": round(reserved_area, 2),
                "usable_area": round(usable_area, 2),
                "occupied_area": round(occupied_area, 2),
                "free_area": round(free_area, 2),
                "utilization_ratio": round(utilization_ratio, 4),
            },
        )


class ConstraintPenaltyEvaluator(BaseMetricEvaluator):
    """Evaluates constraints via ConstraintEngine, reporting total penalty and violation diagnostics."""

    def __init__(self, engine: Optional[ConstraintEngine] = None, config: Optional[EvaluationConfig] = None):
        self.engine = engine or ConstraintEngine()
        self.config = config or EvaluationConfig()

    @property
    def metric_name(self) -> str:
        return MetricType.CONSTRAINT_VIOLATIONS.value

    @property
    def display_name(self) -> str:
        return "Constraint Penalty"

    @property
    def unit(self) -> str:
        return "$"

    @property
    def direction(self) -> MetricDirection:
        return MetricDirection.MINIMIZE

    def evaluate(
        self,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> EvaluationMetricResult:
        violations = self.engine.check_all(problem, solution)
        total_penalty = self.engine.calculate_total_penalty(violations)
        hard_count = self.engine.count_hard_violations(violations)
        soft_count = self.engine.count_soft_violations(violations)

        return EvaluationMetricResult(
            metric_name=self.metric_name,
            display_name=self.display_name,
            value=round(total_penalty, 2),
            unit=self.unit,
            direction=self.direction,
            details={
                "total_constraint_penalty": round(total_penalty, 2),
                "hard_violation_count": hard_count,
                "soft_violation_count": soft_count,
                "is_feasible": hard_count == 0,
                "violations": [v.model_dump() for v in violations],
            },
        )
