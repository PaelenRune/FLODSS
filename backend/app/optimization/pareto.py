"""Pareto Frontier, multi-objective dominance, and decision support service for FLODSS."""

from enum import Enum
import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field

from app.evaluation.canonical import (
    CanonicalEvaluationReport,
    CanonicalEvaluationService,
    compute_evaluation_config_hash,
    compute_problem_provenance_hashes,
)
from app.evaluation.config import EvaluationConfig
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout
from app.models.solution import LayoutSolution
from app.services.layout_normalizer import generate_layout_signature


class ObjectiveDirection(str, Enum):
    """Direction of optimization for an objective."""

    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class ObjectiveDefinition(BaseModel):
    """Formal specification of an optimization objective."""

    id: str = Field(..., description="Unique objective identifier")
    name: str = Field(..., description="Human-readable objective name")
    direction: ObjectiveDirection = Field(..., description="Optimization direction: minimize or maximize")
    unit: str = Field(..., description="Measurement unit (e.g., $, %, points)")
    description: str = Field(default="", description="Detailed engineering description")
    weight: float = Field(default=1.0, ge=0.0, description="Default decision weight")
    tolerance: float = Field(default=1e-4, ge=0.0, description="Floating-point comparison tolerance")


def get_default_pareto_objectives() -> List[ObjectiveDefinition]:
    """Return canonical 3-objective formulation for FLODSS.
    
    1. Material Handling Cost — MINIMIZE ($)
    2. Relationship Satisfaction — MAXIMIZE (%)
    3. Soft Constraint Penalty — MINIMIZE ($)
    
    Note: Flow-Distance is reported in auxiliary metrics but excluded from default
    Pareto objectives due to mathematical collinearity with MHC.
    """
    return [
        ObjectiveDefinition(
            id="material_handling_cost",
            name="Material Handling Cost (MHC)",
            direction=ObjectiveDirection.MINIMIZE,
            unit="USD",
            description="Total annualized handling cost: Sum(F_ij * D_ij * C_ij) in USD",
            weight=0.34,
            tolerance=1e-2,  # $0.01 tolerance
        ),
        ObjectiveDefinition(
            id="relationship_satisfaction",
            name="Relationship Satisfaction",
            direction=ObjectiveDirection.MAXIMIZE,
            unit="%",
            description="Normalized Muther SLP closeness satisfaction in [0.0, 100.0]%",
            weight=0.33,
            tolerance=1e-2,  # 0.01% tolerance
        ),
        ObjectiveDefinition(
            id="soft_penalty",
            name="Soft Constraint Penalty",
            direction=ObjectiveDirection.MINIMIZE,
            unit="USD",
            description="Total annualized engineering soft penalty costs in USD",
            weight=0.33,
            tolerance=1e-2,  # $0.01 tolerance
        ),
    ]


class ParetoCandidate(BaseModel):
    """Evaluated layout candidate ready for Pareto dominance analysis."""

    candidate_id: str
    algorithm_source: str = Field(default="unknown")
    layout_signature: str
    problem_id: str
    problem_composite_hash: str
    evaluation_config_hash: str

    # Core Objectives
    objective_values: Dict[str, float] = Field(
        ...,
        description="Key-value mapping of objective_id to numerical score",
    )

    # Auxiliary & Reporting Metrics
    auxiliary_metrics: Dict[str, Any] = Field(default_factory=dict)
    is_complete: bool = True
    is_feasible: bool = True
    hard_violations_count: int = 0
    soft_violations_count: int = 0

    # Pareto Ranking State
    pareto_rank: Optional[int] = Field(default=None, description="1 = Frontier, 2 = 2nd Layer, ...")
    is_non_dominated: bool = Field(default=False, description="True if pareto_rank == 1")
    dominated_by: List[str] = Field(default_factory=list, description="IDs of candidates that dominate this candidate")
    dominates: List[str] = Field(default_factory=list, description="IDs of candidates dominated by this candidate")

    # Decision Support
    normalized_utility: Optional[float] = Field(default=None, description="Multi-criteria utility in [0.0, 1.0]")
    placements: Optional[Dict[str, Any]] = Field(default=None, description="Placements dictionary for visual rendering")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExcludedCandidate(BaseModel):
    """Candidate excluded from Pareto frontier with explicit reason."""

    candidate_id: str
    algorithm_source: str
    layout_signature: Optional[str] = None
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)


class TradeOffComparison(BaseModel):
    """Pairwise trade-off analysis between two Pareto candidates."""

    candidate_a_id: str
    candidate_b_id: str
    objective_deltas: Dict[str, float] = Field(
        ...,
        description="A - B value difference for each objective",
    )
    analysis_text: str = Field(..., description="Human-readable trade-off explanation")


class DecisionSupportRecommendation(BaseModel):
    """Weighted multi-criteria decision recommendation."""

    profile_name: str
    recommended_candidate_id: str
    utility_score: float
    is_on_pareto_frontier: bool
    priority_weights: Dict[str, float]
    rationale: str


class ParetoAnalysisResult(BaseModel):
    """Comprehensive output of Pareto Frontier and Decision Support Analysis."""

    problem_id: str
    problem_composite_hash: str
    evaluation_config_hash: str
    total_candidates_evaluated: int
    valid_candidates_count: int
    excluded_candidates_count: int
    frontier_count: int
    frontier_candidate_ids: List[str]
    ranks: Dict[int, List[str]] = Field(default_factory=dict, description="Mapping from rank (1, 2, ...) to candidate IDs")
    candidates: List[ParetoCandidate]
    excluded: List[ExcludedCandidate]
    objectives: List[ObjectiveDefinition]
    recommendations: Dict[str, DecisionSupportRecommendation] = Field(default_factory=dict)


class ParetoFrontierService:
    """Centralized service for Multi-Objective Evaluation, Pareto Dominance, and Decision Support."""

    @classmethod
    def dominates(
        cls,
        cand_a: ParetoCandidate,
        cand_b: ParetoCandidate,
        objectives: List[ObjectiveDefinition],
        tolerance: float = 1e-4,
    ) -> bool:
        """Check if candidate A Pareto-dominates candidate B.
        
        Definition:
        A dominates B iff:
        1. A is no worse than B in all objectives (considering minimization/maximization and tolerance).
        2. A is strictly better than B in at least one objective (beyond tolerance).
        """
        at_least_one_strictly_better = False

        for obj in objectives:
            val_a = cand_a.objective_values.get(obj.id)
            val_b = cand_b.objective_values.get(obj.id)
            if val_a is None or val_b is None:
                continue

            eff_tol = max(tolerance, obj.tolerance)

            if obj.direction == ObjectiveDirection.MINIMIZE:
                # To be no worse, val_a must be <= val_b + tol
                if val_a > val_b + eff_tol:
                    return False  # A is worse than B in this objective
                # Check if strictly better
                if val_a < val_b - eff_tol:
                    at_least_one_strictly_better = True

            elif obj.direction == ObjectiveDirection.MAXIMIZE:
                # To be no worse, val_a must be >= val_b - tol
                if val_a < val_b - eff_tol:
                    return False  # A is worse than B in this objective
                # Check if strictly better
                if val_a > val_b + eff_tol:
                    at_least_one_strictly_better = True

        return at_least_one_strictly_better

    @classmethod
    def fast_non_dominated_sort(
        cls,
        candidates: List[ParetoCandidate],
        objectives: List[ObjectiveDefinition],
        tolerance: float = 1e-4,
    ) -> Tuple[Dict[int, List[str]], List[ParetoCandidate]]:
        """Execute O(K^2 * M) non-dominated sorting to assign Pareto ranks and identify frontier.
        
        Returns:
            ranks: Dict mapping rank_int (1, 2, ...) to List of candidate IDs
            updated_candidates: Candidates with updated pareto_rank, dominated_by, dominates fields
        """
        if not candidates:
            return {}, []

        # Data structures for non-dominated sort
        domination_sets: Dict[str, List[str]] = {c.candidate_id: [] for c in candidates}
        domination_counts: Dict[str, int] = {c.candidate_id: 0 for c in candidates}
        ranks: Dict[int, List[str]] = {1: []}
        cand_map: Dict[str, ParetoCandidate] = {c.candidate_id: c for c in candidates}

        n = len(candidates)
        for i in range(n):
            p = candidates[i]
            for j in range(i + 1, n):
                q = candidates[j]

                p_dom_q = cls.dominates(p, q, objectives, tolerance=tolerance)
                q_dom_p = cls.dominates(q, p, objectives, tolerance=tolerance)

                if p_dom_q:
                    domination_sets[p.candidate_id].append(q.candidate_id)
                    domination_counts[q.candidate_id] += 1
                elif q_dom_p:
                    domination_sets[q.candidate_id].append(p.candidate_id)
                    domination_counts[p.candidate_id] += 1

            if domination_counts[p.candidate_id] == 0:
                ranks[1].append(p.candidate_id)

        current_rank = 1
        while current_rank in ranks and ranks[current_rank]:
            next_rank_candidates: List[str] = []
            for p_id in ranks[current_rank]:
                for q_id in domination_sets[p_id]:
                    domination_counts[q_id] -= 1
                    if domination_counts[q_id] == 0:
                        next_rank_candidates.append(q_id)

            current_rank += 1
            if next_rank_candidates:
                ranks[current_rank] = next_rank_candidates

        # Clean empty ranks
        ranks = {r: ids for r, ids in ranks.items() if ids}

        # Assign ranks and dominance relationships to candidate objects
        # Deterministic sorting within each rank: by primary objective (material_handling_cost) ascending, then candidate_id
        for rank_num, c_ids in ranks.items():
            c_ids.sort(
                key=lambda cid: (
                    cand_map[cid].objective_values.get("material_handling_cost", 0.0),
                    cand_map[cid].objective_values.get("relationship_satisfaction", 0.0) * -1,
                    cid,
                )
            )
            for cid in c_ids:
                cand = cand_map[cid]
                cand.pareto_rank = rank_num
                cand.is_non_dominated = (rank_num == 1)
                cand.dominates = domination_sets[cid]
                # Populate dominated_by
                cand.dominated_by = [
                    other_id
                    for other_id, d_set in domination_sets.items()
                    if cid in d_set
                ]

        sorted_candidates = [cand_map[cid] for rank in sorted(ranks.keys()) for cid in ranks[rank]]
        return ranks, sorted_candidates

    @classmethod
    def compute_decision_recommendations(
        cls,
        candidates: List[ParetoCandidate],
        objectives: List[ObjectiveDefinition],
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, DecisionSupportRecommendation]:
        """Compute multi-criteria utility recommendations using Min-Max normalization."""
        if not candidates:
            return {}

        # 1. Calculate min and max for each objective across valid candidates
        obj_bounds: Dict[str, Tuple[float, float]] = {}
        for obj in objectives:
            vals = [c.objective_values.get(obj.id, 0.0) for c in candidates if obj.id in c.objective_values]
            if vals:
                obj_bounds[obj.id] = (min(vals), max(vals))
            else:
                obj_bounds[obj.id] = (0.0, 1.0)

        # 2. Normalize and compute utility for each candidate under given weights
        def calculate_utility(cand: ParetoCandidate, weights: Dict[str, float]) -> float:
            total_weight = sum(weights.values()) or 1.0
            utility_sum = 0.0

            for obj in objectives:
                w = weights.get(obj.id, 0.0)
                if w <= 0.0:
                    continue
                v = cand.objective_values.get(obj.id, 0.0)
                mn, mx = obj_bounds[obj.id]
                val_range = mx - mn

                if val_range <= 1e-9:
                    norm = 1.0  # All solutions equal on this objective
                elif obj.direction == ObjectiveDirection.MINIMIZE:
                    norm = (mx - v) / val_range  # Lower cost -> higher utility (in [0, 1])
                else:
                    norm = (v - mn) / val_range  # Higher satisfaction -> higher utility (in [0, 1])

                utility_sum += w * norm

            return utility_sum / total_weight

        # Standard preference profiles
        profiles = {
            "cost_priority": {
                "material_handling_cost": 0.70,
                "relationship_satisfaction": 0.15,
                "soft_penalty": 0.15,
            },
            "relationship_priority": {
                "material_handling_cost": 0.15,
                "relationship_satisfaction": 0.70,
                "soft_penalty": 0.15,
            },
            "soft_constraint_priority": {
                "material_handling_cost": 0.15,
                "relationship_satisfaction": 0.15,
                "soft_penalty": 0.70,
            },
            "balanced": {
                "material_handling_cost": 0.34,
                "relationship_satisfaction": 0.33,
                "soft_penalty": 0.33,
            },
        }

        if custom_weights:
            profiles["custom"] = custom_weights

        recommendations: Dict[str, DecisionSupportRecommendation] = {}

        for prof_name, w_dict in profiles.items():
            best_cand: Optional[ParetoCandidate] = None
            best_util = -1.0

            for cand in candidates:
                u = calculate_utility(cand, w_dict)
                if u > best_util:
                    best_util = u
                    best_cand = cand

            if best_cand:
                # Update candidate's default balanced utility
                if prof_name == "balanced":
                    best_cand.normalized_utility = round(best_util, 4)

                rationale = (
                    f"Candidate '{best_cand.candidate_id}' ({best_cand.algorithm_source}) achieves the highest "
                    f"utility ({best_util:.4f}) under {prof_name.replace('_', ' ')} weighting "
                    f"(MHC: ${best_cand.objective_values.get('material_handling_cost', 0):,.2f}, "
                    f"Rel: {best_cand.objective_values.get('relationship_satisfaction', 0):.2f}%, "
                    f"Soft Penalty: ${best_cand.objective_values.get('soft_penalty', 0):,.2f})."
                )

                if not best_cand.is_non_dominated:
                    rationale += (
                        f" WARNING: This solution is Pareto-dominated (Rank {best_cand.pareto_rank}) by "
                        f"{', '.join(best_cand.dominated_by[:3])}. A frontier alternative exists with superior trade-offs."
                    )

                recommendations[prof_name] = DecisionSupportRecommendation(
                    profile_name=prof_name,
                    recommended_candidate_id=best_cand.candidate_id,
                    utility_score=round(best_util, 4),
                    is_on_pareto_frontier=best_cand.is_non_dominated,
                    priority_weights=w_dict,
                    rationale=rationale,
                )

        return recommendations

    @classmethod
    def compare_pair(
        cls,
        cand_a: ParetoCandidate,
        cand_b: ParetoCandidate,
        objectives: List[ObjectiveDefinition],
    ) -> TradeOffComparison:
        """Compute explicit pairwise trade-off analysis between two candidates."""
        deltas = {}
        tradeoff_parts = []

        for obj in objectives:
            va = cand_a.objective_values.get(obj.id, 0.0)
            vb = cand_b.objective_values.get(obj.id, 0.0)
            diff = va - vb
            deltas[obj.id] = round(diff, 2)

            if abs(diff) < obj.tolerance:
                tradeoff_parts.append(f"equivalent on {obj.name}")
            elif (obj.direction == ObjectiveDirection.MINIMIZE and diff < 0) or (obj.direction == ObjectiveDirection.MAXIMIZE and diff > 0):
                tradeoff_parts.append(f"{cand_a.candidate_id} is better on {obj.name} by {abs(diff):,.2f} {obj.unit}")
            else:
                tradeoff_parts.append(f"{cand_b.candidate_id} is better on {obj.name} by {abs(diff):,.2f} {obj.unit}")

        text = f"Trade-off between {cand_a.candidate_id} and {cand_b.candidate_id}: " + "; ".join(tradeoff_parts) + "."
        return TradeOffComparison(
            candidate_a_id=cand_a.candidate_id,
            candidate_b_id=cand_b.candidate_id,
            objective_deltas=deltas,
            analysis_text=text,
        )

    @classmethod
    def analyze(
        cls,
        problem: FacilityLayoutProblem,
        raw_candidates: List[Union[Dict[str, Any], ContinuousLayout, LayoutSolution, ParetoCandidate, CanonicalEvaluationReport]],
        objectives: Optional[List[ObjectiveDefinition]] = None,
        config: Optional[EvaluationConfig] = None,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> ParetoAnalysisResult:
        """Evaluate, validate, filter, and compute the Pareto Frontier for a candidate portfolio."""
        eff_config = config or EvaluationConfig()
        eff_objectives = objectives or get_default_pareto_objectives()

        prob_hashes = compute_problem_provenance_hashes(problem)
        expected_prob_id = problem.id
        expected_prob_hash = prob_hashes["composite_data_hash"]
        expected_cfg_hash = compute_evaluation_config_hash(eff_config)

        valid_candidates: List[ParetoCandidate] = []
        excluded_candidates: List[ExcludedCandidate] = []
        seen_signatures: Dict[str, str] = {}  # signature -> first candidate_id

        for idx, item in enumerate(raw_candidates):
            cand_id = f"cand_{idx + 1}"
            algo_source = "unknown"

            # Early cross-problem detection
            declared_prob_id = None
            if isinstance(item, dict):
                cand_id = str(item.get("id") or f"cand_{idx + 1}")
                algo_source = str(item.get("algorithm_name") or "unknown")
                declared_prob_id = item.get("problem_id")
            elif hasattr(item, "problem_id"):
                cand_id = str(getattr(item, "id", None) or getattr(item, "candidate_id", None) or f"cand_{idx + 1}")
                algo_source = str(getattr(item, "algorithm_name", None) or getattr(item, "algorithm_source", None) or "unknown")
                declared_prob_id = getattr(item, "problem_id", None)

            if declared_prob_id and declared_prob_id != expected_prob_id:
                excluded_candidates.append(ExcludedCandidate(
                    candidate_id=cand_id,
                    algorithm_source=algo_source,
                    reason=f"Cross-problem mismatch: candidate problem_id '{declared_prob_id}' != expected '{expected_prob_id}'",
                ))
                continue

            # 1. Normalize and Evaluate to CanonicalEvaluationReport
            report: Optional[CanonicalEvaluationReport] = None
            placements_dict: Optional[Dict[str, Any]] = None
            metadata: Dict[str, Any] = {}

            try:
                if isinstance(item, ParetoCandidate):
                    # Already evaluated ParetoCandidate
                    cand = item
                    cand_id = cand.candidate_id
                    algo_source = cand.algorithm_source
                    placements_dict = cand.placements
                    metadata = cand.metadata

                    # Consistency validation
                    if cand.problem_id != expected_prob_id:
                        excluded_candidates.append(ExcludedCandidate(
                            candidate_id=cand_id,
                            algorithm_source=algo_source,
                            layout_signature=cand.layout_signature,
                            reason=f"Cross-problem mismatch: candidate problem_id '{cand.problem_id}' != expected '{expected_prob_id}'",
                        ))
                        continue

                    if cand.problem_composite_hash and cand.problem_composite_hash != expected_prob_hash:
                        excluded_candidates.append(ExcludedCandidate(
                            candidate_id=cand_id,
                            algorithm_source=algo_source,
                            layout_signature=cand.layout_signature,
                            reason=f"Problem hash mismatch: candidate composite hash != expected problem hash",
                        ))
                        continue

                    if cand.evaluation_config_hash and cand.evaluation_config_hash != expected_cfg_hash:
                        excluded_candidates.append(ExcludedCandidate(
                            candidate_id=cand_id,
                            algorithm_source=algo_source,
                            layout_signature=cand.layout_signature,
                            reason=f"EvaluationConfig hash mismatch: candidate evaluated under disparate config",
                        ))
                        continue

                    if not cand.is_complete:
                        excluded_candidates.append(ExcludedCandidate(
                            candidate_id=cand_id,
                            algorithm_source=algo_source,
                            layout_signature=cand.layout_signature,
                            reason="Incomplete layout: missing required departments",
                        ))
                        continue

                    if not cand.is_feasible:
                        excluded_candidates.append(ExcludedCandidate(
                            candidate_id=cand_id,
                            algorithm_source=algo_source,
                            layout_signature=cand.layout_signature,
                            reason="Infeasible layout: hard constraint or boundary/overlap violations",
                            details={"hard_violations": cand.hard_violations_count},
                        ))
                        continue

                    # Duplicate signature check
                    if cand.layout_signature in seen_signatures:
                        first_id = seen_signatures[cand.layout_signature]
                        excluded_candidates.append(ExcludedCandidate(
                            candidate_id=cand_id,
                            algorithm_source=algo_source,
                            layout_signature=cand.layout_signature,
                            reason=f"Duplicate layout signature: identical geometric placement to candidate '{first_id}'",
                        ))
                        continue

                    seen_signatures[cand.layout_signature] = cand_id
                    valid_candidates.append(cand)
                    continue

                elif isinstance(item, CanonicalEvaluationReport):
                    report = item
                    cand_id = f"eval_{idx + 1}"
                    algo_source = "canonical_evaluation"

                elif isinstance(item, dict) and "problem_composite_hash" in item and "material_handling_cost" in item:
                    # Serialized CanonicalEvaluationReport
                    report = CanonicalEvaluationReport.model_validate(item)
                    cand_id = item.get("candidate_id", f"cand_{idx + 1}")
                    algo_source = item.get("algorithm_source", "canonical_evaluation")
                    placements_dict = item.get("placements")
                    metadata = item.get("metadata", {})

                else:
                    # Raw Layout / Solution / Dict that needs evaluation
                    cand_id = str(getattr(item, "id", None) or (item.get("id") if isinstance(item, dict) else None) or f"cand_{idx + 1}")
                    algo_source = str(getattr(item, "algorithm_name", None) or (item.get("algorithm_name") if isinstance(item, dict) else None) or "unknown")

                    if isinstance(item, dict):
                        placements_dict = item.get("placements")
                        metadata = item.get("metadata", {})
                    elif isinstance(item, ContinuousLayout):
                        placements_dict = {
                            did: {"x": p.x, "y": p.y, "width": p.width, "height": p.height}
                            for did, p in item.placements.items()
                        }
                    elif isinstance(item, LayoutSolution):
                        placements_dict = {
                            did: {"x": p.origin.x, "y": p.origin.y, "width": p.dimensions.width, "height": p.dimensions.height}
                            for did, p in item.placements.items()
                        }

                    report = CanonicalEvaluationService.evaluate(problem, item, config=eff_config)

            except Exception as ex:
                excluded_candidates.append(ExcludedCandidate(
                    candidate_id=cand_id,
                    algorithm_source=algo_source,
                    reason=f"Evaluation failed: {str(ex)}",
                ))
                continue

            # Check report eligibility
            if report.problem_id != expected_prob_id:
                excluded_candidates.append(ExcludedCandidate(
                    candidate_id=cand_id,
                    algorithm_source=algo_source,
                    layout_signature=report.layout_signature,
                    reason=f"Cross-problem mismatch: candidate problem_id '{report.problem_id}' != expected '{expected_prob_id}'",
                ))
                continue

            if report.problem_composite_hash != expected_prob_hash:
                excluded_candidates.append(ExcludedCandidate(
                    candidate_id=cand_id,
                    algorithm_source=algo_source,
                    layout_signature=report.layout_signature,
                    reason=f"Problem hash mismatch: candidate composite hash != expected problem hash",
                ))
                continue

            if report.evaluation_config_hash != expected_cfg_hash:
                excluded_candidates.append(ExcludedCandidate(
                    candidate_id=cand_id,
                    algorithm_source=algo_source,
                    layout_signature=report.layout_signature,
                    reason=f"EvaluationConfig hash mismatch: candidate evaluated under disparate config",
                ))
                continue

            if not report.is_complete:
                excluded_candidates.append(ExcludedCandidate(
                    candidate_id=cand_id,
                    algorithm_source=algo_source,
                    layout_signature=report.layout_signature,
                    reason="Incomplete layout: missing required departments",
                ))
                continue

            if not report.is_feasible:
                excluded_candidates.append(ExcludedCandidate(
                    candidate_id=cand_id,
                    algorithm_source=algo_source,
                    layout_signature=report.layout_signature,
                    reason="Infeasible layout: hard constraint violations",
                    details={"hard_violations": report.hard_violations_count, "violations": report.violations},
                ))
                continue

            # Duplicate signature check
            if report.layout_signature in seen_signatures:
                first_id = seen_signatures[report.layout_signature]
                excluded_candidates.append(ExcludedCandidate(
                    candidate_id=cand_id,
                    algorithm_source=algo_source,
                    layout_signature=report.layout_signature,
                    reason=f"Duplicate layout signature: identical geometric placement to candidate '{first_id}'",
                ))
                continue

            seen_signatures[report.layout_signature] = cand_id

            # Assemble valid ParetoCandidate
            obj_vals = {
                "material_handling_cost": report.material_handling_cost,
                "relationship_satisfaction": report.relationship_satisfaction_percentage,
                "soft_penalty": report.soft_penalty,
            }

            aux_metrics = {
                "flow_distance": report.flow_distance,
                "relationship_raw_score": report.relationship_raw_score,
                "area_utilization": report.area_utilization,
            }

            valid_cand = ParetoCandidate(
                candidate_id=cand_id,
                algorithm_source=algo_source,
                layout_signature=report.layout_signature,
                problem_id=report.problem_id,
                problem_composite_hash=report.problem_composite_hash,
                evaluation_config_hash=report.evaluation_config_hash,
                objective_values=obj_vals,
                auxiliary_metrics=aux_metrics,
                is_complete=report.is_complete,
                is_feasible=report.is_feasible,
                hard_violations_count=report.hard_violations_count,
                soft_violations_count=report.soft_violations_count,
                placements=placements_dict,
                metadata=metadata,
            )
            valid_candidates.append(valid_cand)

        # 2. Run Non-Dominated Sorting
        ranks, ranked_candidates = cls.fast_non_dominated_sort(
            valid_candidates, eff_objectives, tolerance=1e-4
        )

        frontier_ids = ranks.get(1, [])

        # 3. Compute Multi-Criteria Decision Recommendations
        recs = cls.compute_decision_recommendations(
            ranked_candidates, eff_objectives, custom_weights=custom_weights
        )

        return ParetoAnalysisResult(
            problem_id=expected_prob_id,
            problem_composite_hash=expected_prob_hash,
            evaluation_config_hash=expected_cfg_hash,
            total_candidates_evaluated=len(raw_candidates),
            valid_candidates_count=len(ranked_candidates),
            excluded_candidates_count=len(excluded_candidates),
            frontier_count=len(frontier_ids),
            frontier_candidate_ids=frontier_ids,
            ranks=ranks,
            candidates=ranked_candidates,
            excluded=excluded_candidates,
            objectives=eff_objectives,
            recommendations=recs,
        )
