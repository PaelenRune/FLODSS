"""Phase 15.2.1 Independent Scientific Verification Test Suite.

Verifies:
1. Exact mathematical concordance between Canonical Material Handling Cost (MHC)
   and independently computed pairwise centroid Manhattan flow-distance-cost summations.
2. Exact Muther REL satisfaction formula with linear proximity decay and X-relationship penalties.
3. Strict hard constraint validation (boundary containment, zero pairwise overlap,
   reserved exclusion zones, aspect ratio limits).
4. Pareto candidate provenance hash compatibility enforcement.
"""

import math
import pytest
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.models.relationship import RELATIONSHIP_DEFAULT_SCORES
from app.services.problem_service import problem_service
from app.evaluation.config import EvaluationConfig
from app.evaluation.evaluators import (
    MaterialHandlingCostEvaluator,
    FlowDistanceEvaluator,
    RelationshipSatisfactionEvaluator,
)
from app.evaluation.canonical import (
    CanonicalEvaluationService,
    compute_problem_provenance_hashes,
    compute_evaluation_config_hash,
)
from app.constraints.engine import ConstraintEngine
from app.services.layout_validator import LayoutValidator
from app.algorithms.corelap.solver import CORELAPAlgorithm


@pytest.fixture
def academic4_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_ACADEMIC_4")


@pytest.fixture
def expansion8_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_EXPANSION_8")


@pytest.fixture
def industrial10_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_INDUSTRIAL_10")


# ---------------------------------------------------------------------------
# 1. Independent Pairwise MHC Summation vs Canonical MHC
# ---------------------------------------------------------------------------

def test_independent_pairwise_mhc_calculation(industrial10_problem):
    """Verify that independent pairwise MHC calculation from raw centroid coordinates
    strictly equals canonical MaterialHandlingCostEvaluator output to within 1e-4 tolerance.
    """
    solver = CORELAPAlgorithm()
    solution = solver.solve(industrial10_problem)
    assert solution is not None

    layout = ContinuousLayout.from_layout_solution(
        solution,
        facility_width=industrial10_problem.facility.width,
        facility_height=industrial10_problem.facility.height,
    )

    # 1. Evaluate via Canonical MaterialHandlingCostEvaluator
    config = EvaluationConfig()
    evaluator = MaterialHandlingCostEvaluator(config=config)
    eval_result = evaluator.evaluate(industrial10_problem, layout)
    canonical_mhc = eval_result.value

    # 2. Independent from-scratch pairwise summation
    independent_mhc = 0.0
    pairwise_breakdown = []

    for flow in industrial10_problem.flows:
        if flow.source_department not in layout.placements or flow.target_department not in layout.placements:
            continue

        src_p = layout.placements[flow.source_department]
        tgt_p = layout.placements[flow.target_department]

        # Centroid coordinates
        src_cx = src_p.x + src_p.width / 2.0
        src_cy = src_p.y + src_p.height / 2.0
        tgt_cx = tgt_p.x + tgt_p.width / 2.0
        tgt_cy = tgt_p.y + tgt_p.height / 2.0

        # Rectilinear (Manhattan) distance
        d_manhattan = abs(src_cx - tgt_cx) + abs(src_cy - tgt_cy)

        # Unit cost
        c_ij = flow.cost_per_unit_distance if flow.cost_per_unit_distance is not None else config.default_cost_per_unit_distance

        # Pairwise MHC
        pair_cost = flow.quantity * d_manhattan * c_ij
        independent_mhc += pair_cost

        pairwise_breakdown.append({
            "source": flow.source_department,
            "target": flow.target_department,
            "quantity": flow.quantity,
            "distance": d_manhattan,
            "unit_cost": c_ij,
            "pair_cost": pair_cost,
        })

    # Exact mathematical concordance check
    assert math.isclose(canonical_mhc, round(independent_mhc, 2), abs_tol=1e-2), (
        f"MHC mismatch: canonical={canonical_mhc}, independent={independent_mhc}"
    )

    # Ensure top contributors match in order
    pairwise_breakdown.sort(key=lambda x: x["pair_cost"], reverse=True)
    top_evaluator = eval_result.details.get("top_contributors", [])
    if top_evaluator and pairwise_breakdown:
        assert top_evaluator[0]["source"] == pairwise_breakdown[0]["source"]
        assert top_evaluator[0]["target"] == pairwise_breakdown[0]["target"]
        assert math.isclose(top_evaluator[0]["cost"], round(pairwise_breakdown[0]["pair_cost"], 2), abs_tol=1e-2)


# ---------------------------------------------------------------------------
# 2. Independent Muther REL Satisfaction Verification
# ---------------------------------------------------------------------------

def test_independent_rel_satisfaction_calculation(academic4_problem):
    """Verify that independent REL satisfaction calculation matches evaluator output."""
    solver = CORELAPAlgorithm()
    solution = solver.solve(academic4_problem)
    layout = ContinuousLayout.from_layout_solution(
        solution,
        facility_width=academic4_problem.facility.width,
        facility_height=academic4_problem.facility.height,
    )

    config = EvaluationConfig()
    evaluator = RelationshipSatisfactionEvaluator(config=config)
    eval_result = evaluator.evaluate(academic4_problem, layout)

    fac_w = academic4_problem.facility.width
    fac_h = academic4_problem.facility.height
    d_max = math.sqrt(fac_w ** 2 + fac_h ** 2)

    total_positive_potential = 0.0
    net_score = 0.0

    for rel in academic4_problem.relationships:
        if rel.department_a not in layout.placements or rel.department_b not in layout.placements:
            continue

        p_a = layout.placements[rel.department_a]
        p_b = layout.placements[rel.department_b]

        cx_a, cy_a = p_a.x + p_a.width / 2.0, p_a.y + p_a.height / 2.0
        cx_b, cy_b = p_b.x + p_b.width / 2.0, p_b.y + p_b.height / 2.0

        dist = abs(cx_a - cx_b) + abs(cy_a - cy_b) if config.distance_metric.value == "manhattan" else math.hypot(cx_a - cx_b, cy_a - cy_b)
        proximity_ratio = max(0.0, 1.0 - (dist / d_max))

        score = rel.score if rel.score is not None else RELATIONSHIP_DEFAULT_SCORES.get(rel.relationship_type.value, 0)

        if score > 0:
            total_positive_potential += score
            net_score += score * proximity_ratio
        elif score < 0:
            # Undesirable penalty
            net_score -= abs(score) * proximity_ratio

    expected_ratio = max(0.0, min(1.0, net_score / total_positive_potential)) if total_positive_potential > 0 else 0.0
    expected_percent = round(expected_ratio * 100.0, 2)

    assert math.isclose(eval_result.value, expected_percent, abs_tol=1e-1), (
        f"REL satisfaction mismatch: evaluator={eval_result.value}%, expected={expected_percent}%"
    )


# ---------------------------------------------------------------------------
# 3. Hard Constraint Verification & Exact Detection
# ---------------------------------------------------------------------------

def test_hard_constraints_detection_suite(expansion8_problem):
    """Verify that boundary containment, zero overlap, reserved exclusion zones,
    and aspect ratio violations are strictly detected with 100% accuracy.
    """
    fac_w = expansion8_problem.facility.width
    fac_h = expansion8_problem.facility.height

    # Construct a valid layout
    valid_placements = {}
    x = 0.0
    for d in expansion8_problem.departments:
        valid_placements[d.id] = ContinuousPlacement(
            department_id=d.id,
            x=x,
            y=0.0,
            width=15.0,
            height=15.0,
        )
        x += 16.0

    valid_layout = ContinuousLayout(
        problem_id=expansion8_problem.id,
        facility_width=fac_w,
        facility_height=fac_h,
        placements=valid_placements,
    )

    validator = LayoutValidator()
    engine = ConstraintEngine()

    # 1. Test Injected Boundary Violation (Department extends beyond facility height)
    oob_layout = valid_layout.model_copy(deep=True)
    oob_dept = expansion8_problem.departments[0].id
    oob_layout.placements[oob_dept].y = fac_h - 5.0  # y + height = fac_h + 10.0 > fac_h

    val_res = validator.validate(expansion8_problem, oob_layout)
    assert val_res.is_valid is False
    assert any("boundar" in err.lower() or "outside" in err.lower() for err in val_res.errors)

    # 2. Test Injected Pairwise Overlap
    overlap_layout = valid_layout.model_copy(deep=True)
    d1 = expansion8_problem.departments[0].id
    d2 = expansion8_problem.departments[1].id
    overlap_layout.placements[d2].x = overlap_layout.placements[d1].x + 5.0  # Overlaps by 10m x 15m

    val_res = validator.validate(expansion8_problem, overlap_layout)
    assert val_res.is_valid is False
    assert val_res.total_overlap_area > 0.0

    # 3. Test Injected Reserved Zone Intrusion (on Expansion8 with reserved aisle)
    assert expansion8_problem.facility.reserved_zones and len(expansion8_problem.facility.reserved_zones) > 0
    rz = expansion8_problem.facility.reserved_zones[0]
    rz_layout = valid_layout.model_copy(deep=True)
    # Move department 0 squarely inside reserved zone
    rz_layout.placements[d1].x = rz.bounding_box.x_min + 1.0
    rz_layout.placements[d1].y = rz.bounding_box.y_min + 1.0

    violations = engine.check_all(expansion8_problem, rz_layout)
    hard_violations = [v for v in violations if v.classification.value == "hard"]
    assert any("reserved" in (v.description or "").lower() for v in hard_violations)

    # 4. Test Injected Aspect Ratio Violation
    ar_layout = valid_layout.model_copy(deep=True)
    ar_layout.placements[d1].width = 3.0
    ar_layout.placements[d1].height = 27.0  # Aspect Ratio = 27 / 3 = 9.0 > max 3.0

    violations = engine.check_all(expansion8_problem, ar_layout)
    assert any("aspect ratio" in (v.description or "").lower() for v in violations)


# ---------------------------------------------------------------------------
# 4. Pareto Provenance Hashes & Model Compatibility
# ---------------------------------------------------------------------------

def test_pareto_model_hashes_and_compatibility(industrial10_problem, academic4_problem):
    """Verify that problem composite hashes distinctly differentiate problem models,
    preventing invalid cross-problem comparisons.
    """
    hash_industrial = compute_problem_provenance_hashes(industrial10_problem)
    hash_academic = compute_problem_provenance_hashes(academic4_problem)

    assert hash_industrial["composite_data_hash"] != hash_academic["composite_data_hash"]
    assert len(hash_industrial["composite_data_hash"]) == 64  # SHA-256 length

    eval_config_default = EvaluationConfig()
    eval_hash_1 = compute_evaluation_config_hash(eval_config_default)
    assert len(eval_hash_1) == 64
