"""Phase 14.6 Scientific Validation, Feasibility Consistency, and Regression Test Suite."""

import json
import math
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.algorithms.corelap.solver import CORELAPAlgorithm
from app.constraints.engine import ConstraintEngine
from app.evaluation.canonical import (
    CanonicalEvaluationReport,
    CanonicalEvaluationService,
    compute_evaluation_config_hash,
    compute_problem_provenance_hashes,
)
from app.evaluation.config import EvaluationConfig
from app.evaluation.engine import EvaluationEngine
from app.models.geometry import BoundingBox, Point2D, ReservedZone
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.optimization.adaptive import (
    AdaptiveConfig,
    StrategyExecutionEngine,
)
from app.optimization.pareto import ParetoCandidate, ParetoFrontierService
from app.services.layout_validator import LayoutValidator
from app.services.problem_service import problem_service


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Aspect Ratio Violation Marks Layout Infeasible Across All Engines
# ---------------------------------------------------------------------------

def test_aspect_ratio_violation_marks_layout_infeasible():
    """Verify that a 5x20m placement (AR=4.0) on a department with max_aspect_ratio=3.0
    is strictly rejected by LayoutValidator, ConstraintEngine, EvaluationEngine, and CanonicalEvaluationService.
    """
    base_problem = problem_service.get_example_problem("FLP_ACADEMIC_4")
    problem = base_problem.model_copy(deep=True)
    for d in problem.departments:
        d.min_aspect_ratio = 1.0
        d.max_aspect_ratio = 3.0

    # Place DEP_D as 5 x 20 m -> Area = 100 m², Aspect Ratio = 20 / 5 = 4.0 > 3.0
    infeasible_layout = ContinuousLayout(
        problem_id=problem.id,
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10.0, y=0.0, width=10.0, height=10.0),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=0.0, y=10.0, width=10.0, height=10.0),
            "DEP_D": ContinuousPlacement(department_id="DEP_D", x=20.0, y=0.0, width=5.0, height=20.0),
        },
    )

    assert math.isclose(infeasible_layout.placements["DEP_D"].aspect_ratio, 4.0, abs_tol=1e-6)

    # 1. LayoutValidator check
    val_res = LayoutValidator.validate(problem, infeasible_layout)
    assert val_res.is_valid is False
    assert any("aspect ratio" in err.lower() and "dep_d" in err.lower() for err in val_res.errors)

    # 2. ConstraintEngine check
    violations = ConstraintEngine().check_all(problem, infeasible_layout)
    hard_violations = [v for v in violations if v.classification.value == "hard"]
    assert len(hard_violations) >= 1
    assert any("DEP_D" in v.involved_departments and "aspect ratio" in (v.description or "").lower() for v in hard_violations)

    # 3. EvaluationEngine check
    eval_report = EvaluationEngine().evaluate(problem, infeasible_layout)
    assert eval_report.complete_layout is True
    assert eval_report.is_feasible is False
    assert eval_report.hard_violation_count >= 1

    # 4. CanonicalEvaluationService check
    canon_report = CanonicalEvaluationService.evaluate(problem, infeasible_layout)
    assert canon_report.is_complete is True
    assert canon_report.is_feasible is False
    assert canon_report.hard_violations_count >= 1


# ---------------------------------------------------------------------------
# 2. CORELAP Respects max_aspect_ratio Or Fails Closed
# ---------------------------------------------------------------------------

def test_corelap_respects_max_aspect_ratio_or_fails_closed():
    """Verify CORELAP never generates 5x20m (AR=4.0) when max_aspect_ratio=3.0 (or default 3.0),
    and fails closed if a department's aspect ratio constraint cannot be satisfied.
    """
    base_problem = problem_service.get_example_problem("FLP_ACADEMIC_4")
    problem = base_problem.model_copy(deep=True)
    for d in problem.departments:
        d.min_aspect_ratio = 1.0
        d.max_aspect_ratio = 3.0

    solver = CORELAPAlgorithm()
    sol = solver.solve(problem)
    cont = ContinuousLayout.from_layout_solution(sol, problem.facility.width, problem.facility.height)

    for did, p in cont.placements.items():
        assert p.aspect_ratio <= 3.0 + 1e-6, f"Department {did} violated max_aspect_ratio=3.0 with AR={p.aspect_ratio}"

    val_res = LayoutValidator.validate(problem, cont)
    assert val_res.is_valid is True
    assert sol.feasibility_status is True
    assert sol.metadata["is_feasible"] is True
    assert sol.metadata["validation_status"] == "FEASIBLE"

    # Now test fail-closed behavior when contradictory constraints make legal placement impossible
    impossible_problem = base_problem.model_copy(deep=True)
    # Require width >= 25m on a 100 m² department (so height <= 4m -> AR >= 6.25) while max_aspect_ratio = 1.2
    impossible_problem.departments[0].min_width = 25.0
    impossible_problem.departments[0].max_aspect_ratio = 1.2
    sol_imp = solver.solve(impossible_problem)
    assert sol_imp.feasibility_status is False
    assert sol_imp.metadata["is_feasible"] is False
    assert sol_imp.metadata["validation_status"] == "INFEASIBLE"


# ---------------------------------------------------------------------------
# 3. Adaptive Engine Never Returns Infeasible With COMPLETED_SUCCESSFULLY
# ---------------------------------------------------------------------------

def test_adaptive_never_returns_infeasible_with_completed_successfully():
    """Verify AdaptiveStrategyEngine separates execution_status, validation_status, is_feasible,
    termination_reason, and failure_reason, and never uses COMPLETED_SUCCESSFULLY as a failure reason.
    """
    # A. Feasible execution on FLP_ACADEMIC_4
    problem = problem_service.get_example_problem("FLP_ACADEMIC_4")
    res_ok = StrategyExecutionEngine.execute(
        problem,
        config=AdaptiveConfig(
            max_total_runtime_seconds=5.0,
            ga_population_size=10,
            ga_generations=5,
        ),
    )
    assert res_ok.execution_status == "COMPLETED"
    assert res_ok.is_feasible is True
    assert res_ok.validation_status == "FEASIBLE"
    assert res_ok.termination_reason == "COMPLETED_SUCCESSFULLY"
    assert res_ok.failure_reason is None
    assert res_ok.best_continuous_layout is not None
    assert res_ok.best_validation is not None
    val_valid = res_ok.best_validation.is_valid if hasattr(res_ok.best_validation, "is_valid") else res_ok.best_validation.get("is_valid")
    assert val_valid is True
    assert res_ok.best_evaluation is not None
    eval_feas = res_ok.best_evaluation.is_feasible if hasattr(res_ok.best_evaluation, "is_feasible") else res_ok.best_evaluation.get("is_feasible")
    assert eval_feas is True

    # B. Infeasible problem where no solver can satisfy contradictory constraints
    impossible_problem = problem.model_copy(deep=True)
    for d in impossible_problem.departments:
        d.min_width = 30.0  # Area=100 -> h=3.33 -> AR=9.0
        d.max_aspect_ratio = 1.1  # Contradicts min_width=30.0 for 100 m²
    res_fail = StrategyExecutionEngine.execute(
        impossible_problem,
        config=AdaptiveConfig(
            max_total_runtime_seconds=3.0,
            ga_population_size=8,
            ga_generations=3,
        ),
    )
    assert res_fail.is_feasible is False
    assert res_fail.validation_status == "INFEASIBLE"
    assert res_fail.termination_reason != "COMPLETED_SUCCESSFULLY"
    assert res_fail.failure_reason is not None
    assert "COMPLETED_SUCCESSFULLY" not in res_fail.failure_reason


# ---------------------------------------------------------------------------
# 4. Adaptive Fallback Chain Records Exact Failure Reason
# ---------------------------------------------------------------------------

def test_adaptive_fallback_chain_records_exact_failure_reason():
    """Verify that when a primary stage fails or produces an infeasible layout,
    the fallback chain records the exact failure reason and transitions to the fallback algorithm.
    """
    problem = problem_service.get_example_problem("FLP_INDUSTRIAL_10")
    res = StrategyExecutionEngine.execute(
        problem,
        config=AdaptiveConfig(
            max_total_runtime_seconds=6.0,
            ga_population_size=12,
            ga_generations=5,
            random_seed=42,
        ),
    )
    assert len(res.execution_trace) >= 1
    for trace_item in res.execution_trace:
        assert trace_item.step_index >= 1
        assert bool(trace_item.selected_algorithm)
        if not trace_item.is_feasible:
            assert trace_item.failure_reason is not None
            assert trace_item.failure_reason != "COMPLETED_SUCCESSFULLY"

    # Also test a problem where primary fails and fallback is triggered
    impossible_problem = problem_service.get_example_problem("FLP_ACADEMIC_4").model_copy(deep=True)
    for d in impossible_problem.departments:
        d.min_width = 30.0
        d.max_aspect_ratio = 1.1
    res_fb = StrategyExecutionEngine.execute(
        impossible_problem,
        config=AdaptiveConfig(max_total_runtime_seconds=3.0, fallback_enabled=True),
    )
    assert len(res_fb.fallback_trace) >= 1
    assert all(st.was_fallback for st in res_fb.fallback_trace)
    assert all(st.failure_reason and st.failure_reason != "COMPLETED_SUCCESSFULLY" for st in res_fb.execution_trace if not st.is_feasible)


# ---------------------------------------------------------------------------
# 5. Problem Switch Invalidates Stale Solution State (Cross-Problem Rejection)
# ---------------------------------------------------------------------------

def test_problem_switch_invalidates_stale_solution_state():
    """Verify that a layout generated for FLP_ACADEMIC_4 is strictly rejected when evaluated
    or included in Pareto analysis for FLP_INDUSTRIAL_10.
    """
    prob_4 = problem_service.get_example_problem("FLP_ACADEMIC_4")
    prob_10 = problem_service.get_example_problem("FLP_INDUSTRIAL_10")

    sol_4 = CORELAPAlgorithm().solve(prob_4)
    cont_4 = ContinuousLayout.from_layout_solution(sol_4, prob_4.facility.width, prob_4.facility.height)

    # Validate cont_4 against prob_10 -> must be invalid (missing departments / cross-problem)
    val_cross = LayoutValidator.validate(prob_10, cont_4)
    assert val_cross.is_valid is False

    # Pareto analysis on prob_10 with cont_4 candidate -> cont_4 must be excluded
    pareto_res = ParetoFrontierService.analyze(
        problem=prob_10,
        raw_candidates=[
            {
                "id": "STALE_ACADEMIC_4_LAYOUT",
                "algorithm_name": "CORELAP",
                "problem_id": prob_4.id,
                "placements": {
                    did: {"x": p.x, "y": p.y, "width": p.width, "height": p.height}
                    for did, p in cont_4.placements.items()
                },
            }
        ],
    )
    assert pareto_res.valid_candidates_count == 0
    assert pareto_res.excluded_candidates_count == 1
    assert "Cross-problem mismatch" in pareto_res.excluded[0].reason


# ---------------------------------------------------------------------------
# 6. Pareto Rejects Candidates With Mismatched Problem Composite Hash
# ---------------------------------------------------------------------------

def test_pareto_rejects_candidates_with_mismatched_problem_hash():
    """Verify that modifying a department's area or aspect ratio constraint alters
    problem_composite_hash and causes ParetoFrontierService to reject stale candidates.
    """
    prob_orig = problem_service.get_example_problem("FLP_ACADEMIC_4")
    sol_orig = CORELAPAlgorithm().solve(prob_orig)
    cont_orig = ContinuousLayout.from_layout_solution(sol_orig, prob_orig.facility.width, prob_orig.facility.height)
    report_orig = CanonicalEvaluationService.evaluate(prob_orig, cont_orig)

    stale_cand = ParetoCandidate(
        candidate_id="CAND_STALE_HASH",
        algorithm_source="CORELAP",
        layout_signature=report_orig.layout_signature,
        problem_id=prob_orig.id,
        problem_composite_hash=report_orig.problem_composite_hash,
        evaluation_config_hash=report_orig.evaluation_config_hash,
        objective_values={
            "material_handling_cost": report_orig.material_handling_cost,
            "relationship_satisfaction": report_orig.relationship_satisfaction_percentage,
            "soft_penalty": report_orig.soft_penalty,
        },
        is_complete=True,
        is_feasible=True,
    )

    # Modify department constraint on problem
    prob_modified = prob_orig.model_copy(deep=True)
    prob_modified.departments[0].max_aspect_ratio = 2.5
    new_hashes = compute_problem_provenance_hashes(prob_modified)
    assert new_hashes["composite_data_hash"] != report_orig.problem_composite_hash

    pareto_res = ParetoFrontierService.analyze(
        problem=prob_modified,
        raw_candidates=[stale_cand],
    )
    assert pareto_res.valid_candidates_count == 0
    assert pareto_res.excluded_candidates_count == 1
    assert "hash mismatch" in pareto_res.excluded[0].reason.lower()


# ---------------------------------------------------------------------------
# 7. Pareto Table And Canvas Share Same Feasibility Verdict
# ---------------------------------------------------------------------------

def test_pareto_table_and_canvas_share_same_feasibility_verdict(client):
    """Verify that every candidate included in ParetoAnalysisResult has normalized flat placements
    that pass LayoutValidator.validate(problem, layout) with is_valid=True, and infeasible candidates
    (e.g. aspect ratio 4 > 3) are excluded.
    """
    base_prob = problem_service.get_example_problem("FLP_ACADEMIC_4")
    problem = base_prob.model_copy(deep=True)
    for d in problem.departments:
        d.max_aspect_ratio = 3.0

    # Candidate 1: Feasible 10x10 layout (AR = 1.0 <= 3.0)
    feasible_cand = {
        "id": "FEASIBLE_10x10",
        "algorithm_name": "CORELAP",
        "problem_id": problem.id,
        "placements": {
            "DEP_A": {"department_id": "DEP_A", "x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0},
            "DEP_B": {"department_id": "DEP_B", "x": 10.0, "y": 0.0, "width": 10.0, "height": 10.0},
            "DEP_C": {"department_id": "DEP_C", "x": 0.0, "y": 10.0, "width": 10.0, "height": 10.0},
            "DEP_D": {"department_id": "DEP_D", "x": 10.0, "y": 10.0, "width": 10.0, "height": 10.0},
        },
    }

    # Candidate 2: Infeasible 5x20 layout for DEP_D (AR = 4.0 > 3.0)
    infeasible_cand = {
        "id": "INFEASIBLE_5x20",
        "algorithm_name": "BROKEN_HEURISTIC",
        "problem_id": problem.id,
        "placements": {
            "DEP_A": {"department_id": "DEP_A", "x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0},
            "DEP_B": {"department_id": "DEP_B", "x": 10.0, "y": 0.0, "width": 10.0, "height": 10.0},
            "DEP_C": {"department_id": "DEP_C", "x": 0.0, "y": 10.0, "width": 10.0, "height": 10.0},
            "DEP_D": {"department_id": "DEP_D", "x": 20.0, "y": 0.0, "width": 5.0, "height": 20.0},
        },
    }

    res = ParetoFrontierService.analyze(
        problem=problem,
        raw_candidates=[feasible_cand, infeasible_cand],
    )
    assert res.valid_candidates_count == 1
    assert res.excluded_candidates_count == 1
    assert res.candidates[0].candidate_id == "FEASIBLE_10x10"
    assert res.candidates[0].is_feasible is True
    assert res.excluded[0].candidate_id == "INFEASIBLE_5x20"

    # Reconstruct ContinuousLayout from candidate placements (exact UI canvas flow)
    cand = res.candidates[0]
    assert cand.placements is not None
    reconstructed = ContinuousLayout(
        problem_id=problem.id,
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
        placements={
            did: ContinuousPlacement(
                department_id=did,
                x=p["x"],
                y=p["y"],
                width=p["width"],
                height=p["height"],
                orientation_degrees=p.get("orientation_degrees", 0.0),
            )
            for did, p in cand.placements.items()
        },
    )
    canvas_val = LayoutValidator.validate(problem, reconstructed)
    assert canvas_val.is_valid is True
    assert len(canvas_val.errors) == 0


# ---------------------------------------------------------------------------
# 8 & 9. Export Center Active Layout Signature & JSON Roundtrip Verification
# ---------------------------------------------------------------------------

def test_export_center_reads_active_layout_and_canonical_metrics():
    """Verify that ContinuousLayout preserves layout_signature from solver through validation
    and canonical evaluation so ExportCenterCard always receives the active layout and signature.
    """
    problem = problem_service.get_example_problem("FLP_ACADEMIC_4")
    sol = CORELAPAlgorithm().solve(problem)
    assert sol.layout_signature is not None

    cont = ContinuousLayout.from_layout_solution(sol, problem.facility.width, problem.facility.height)
    assert cont.layout_signature == sol.layout_signature
    assert cont.metadata.get("layout_signature") == sol.layout_signature

    val = LayoutValidator.validate(problem, cont)
    assert val.is_valid is True
    assert val.signature == sol.layout_signature

    canon = CanonicalEvaluationService.evaluate(problem, cont)
    assert canon.layout_signature == sol.layout_signature
    assert canon.is_feasible is True


def test_exported_json_roundtrip_reproduces_identical_metrics_and_hashes():
    """Verify that exporting an active layout + provenance bundle to JSON and re-importing
    reproduces identical layout_signature, problem_composite_hash, evaluation_config_hash, and metrics.
    """
    problem = problem_service.get_example_problem("FLP_INDUSTRIAL_10")
    res = StrategyExecutionEngine.execute(
        problem,
        config=AdaptiveConfig(max_total_runtime_seconds=5.0, ga_population_size=12, ga_generations=5, random_seed=42),
    )
    assert res.best_continuous_layout is not None
    orig_layout = ContinuousLayout.model_validate(res.best_continuous_layout)
    orig_eval = CanonicalEvaluationService.evaluate(problem, orig_layout)

    # Simulate Export Center JSON bundle
    exported_payload = orig_layout.model_dump()
    exported_payload["layout_signature"] = orig_eval.layout_signature
    exported_payload["provenance"] = {
        "problem_id": problem.id,
        "problem_composite_hash": orig_eval.problem_composite_hash,
        "evaluation_config_hash": orig_eval.evaluation_config_hash,
        "layout_signature": orig_eval.layout_signature,
    }
    json_str = json.dumps(exported_payload, indent=2)

    # Roundtrip reload
    reloaded_dict = json.loads(json_str)
    reloaded_layout = ContinuousLayout.model_validate(reloaded_dict)
    reloaded_val = LayoutValidator.validate(problem, reloaded_layout)
    reloaded_eval = CanonicalEvaluationService.evaluate(problem, reloaded_layout)

    assert reloaded_val.is_valid == orig_eval.is_feasible
    assert reloaded_eval.layout_signature == orig_eval.layout_signature
    assert reloaded_eval.problem_composite_hash == orig_eval.problem_composite_hash
    assert reloaded_eval.evaluation_config_hash == orig_eval.evaluation_config_hash
    assert reloaded_eval.material_handling_cost == orig_eval.material_handling_cost
    assert reloaded_eval.flow_distance == orig_eval.flow_distance
    assert reloaded_eval.relationship_satisfaction_percentage == orig_eval.relationship_satisfaction_percentage
    assert reloaded_eval.area_utilization == orig_eval.area_utilization
    assert reloaded_eval.soft_penalty == orig_eval.soft_penalty


# ---------------------------------------------------------------------------
# 10. Exact Hand Calculation Verification on FLP_ACADEMIC_4
# ---------------------------------------------------------------------------

def test_mhc_hand_calculation_academic_4():
    """Verify exact mathematical hand calculation of centroids, rectilinear distances,
    Flow Distance, and Material Handling Cost (MHC) on FLP_ACADEMIC_4.
    """
    problem = problem_service.get_example_problem("FLP_ACADEMIC_4")
    # Place 4 departments of 10x10m in a 2x2 grid:
    # DEP_A: (0,0) -> centroid (5,5)
    # DEP_B: (10,0) -> centroid (15,5)
    # DEP_C: (0,10) -> centroid (5,15)
    # DEP_D: (10,10) -> centroid (15,15)
    layout = ContinuousLayout(
        problem_id=problem.id,
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10.0, y=0.0, width=10.0, height=10.0),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=0.0, y=10.0, width=10.0, height=10.0),
            "DEP_D": ContinuousPlacement(department_id="DEP_D", x=10.0, y=10.0, width=10.0, height=10.0),
        },
    )

    centroids = {
        "DEP_A": (5.0, 5.0),
        "DEP_B": (15.0, 5.0),
        "DEP_C": (5.0, 15.0),
        "DEP_D": (15.0, 15.0),
    }

    expected_flow_distance = 0.0
    expected_mhc = 0.0
    for f in problem.flows:
        cx1, cy1 = centroids[f.source_department]
        cx2, cy2 = centroids[f.target_department]
        d_ij = abs(cx1 - cx2) + abs(cy1 - cy2)
        expected_flow_distance += f.quantity * d_ij
        expected_mhc += f.quantity * d_ij * f.cost_per_unit_distance

    canon = CanonicalEvaluationService.evaluate(problem, layout)
    assert math.isclose(canon.flow_distance, expected_flow_distance, abs_tol=1e-6)
    assert math.isclose(canon.material_handling_cost, expected_mhc, abs_tol=1e-6)
    # Verify exact hand-calculated values on FLP_ACADEMIC_4:
    # A->B: d=|5-15|+|5-5|=10, q=50, c=1.0 => FD=500, MHC=500
    # B->C: d=|15-5|+|5-15|=20, q=30, c=1.0 => FD=600, MHC=600
    # C->D: d=|5-15|+|15-15|=10, q=10, c=1.0 => FD=100, MHC=100
    # Total FD = 1200.0, Total MHC = 1200.0
    assert canon.flow_distance == 1200.0
    assert canon.material_handling_cost == 1200.0


# ---------------------------------------------------------------------------
# 11. Flow Distance Is Independent of Unit Cost (Not MHC / 2)
# ---------------------------------------------------------------------------

def test_flow_distance_not_mhc_divided_by_two():
    """Prove that Flow Distance = Sum(F_ij * D_ij) and Material Handling Cost = Sum(F_ij * D_ij * C_ij)
    are computed independently and Flow Distance is never hardcoded as MHC / 2.
    """
    base_prob = problem_service.get_example_problem("FLP_ACADEMIC_4")
    problem = base_prob.model_copy(deep=True)
    # Assign heterogeneous unit costs C_ij
    custom_costs = [1.25, 3.50, 0.80]
    for idx, f in enumerate(problem.flows):
        f.cost_per_unit_distance = custom_costs[idx % len(custom_costs)]

    layout = ContinuousLayout(
        problem_id=problem.id,
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10.0, y=0.0, width=10.0, height=10.0),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=0.0, y=10.0, width=10.0, height=10.0),
            "DEP_D": ContinuousPlacement(department_id="DEP_D", x=10.0, y=10.0, width=10.0, height=10.0),
        },
    )

    canon = CanonicalEvaluationService.evaluate(problem, layout)
    # Flow distance must still be 1200.0 (since F_ij and D_ij are unchanged)
    assert canon.flow_distance == 1200.0
    # MHC = 500*1.25 + 600*3.50 + 100*0.80 = 625 + 2100 + 80 = 2805.0
    assert canon.material_handling_cost == 2805.0
    assert canon.flow_distance != canon.material_handling_cost / 2.0


# ---------------------------------------------------------------------------
# 12. Overlap, Boundary, Reserved Zone & Fixed Department Hard Constraints
# ---------------------------------------------------------------------------

def test_overlap_boundary_reserved_zone_fixed_department_hard_constraints():
    """Verify that pairwise department overlap, facility boundary overflow, reserved zone collision,
    and fixed department position violation each independently force is_valid=False and is_feasible=False
    across LayoutValidator, EvaluationEngine, and CanonicalEvaluationService.
    """
    base_prob = problem_service.get_example_problem("FLP_ACADEMIC_4")

    # (a) Pairwise Overlap Violation (DEP_A and DEP_B overlap by 5x10 = 50 m²)
    overlap_layout = ContinuousLayout(
        problem_id=base_prob.id,
        facility_width=base_prob.facility.width,
        facility_height=base_prob.facility.height,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=5.0, y=0.0, width=10.0, height=10.0),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=0.0, y=10.0, width=10.0, height=10.0),
            "DEP_D": ContinuousPlacement(department_id="DEP_D", x=10.0, y=10.0, width=10.0, height=10.0),
        },
    )
    assert LayoutValidator.validate(base_prob, overlap_layout).is_valid is False
    assert EvaluationEngine().evaluate(base_prob, overlap_layout).is_feasible is False
    assert CanonicalEvaluationService.evaluate(base_prob, overlap_layout).is_feasible is False

    # (b) Facility Boundary Overflow (DEP_D placed at x=115..125 outside 120m facility width)
    boundary_layout = ContinuousLayout(
        problem_id=base_prob.id,
        facility_width=base_prob.facility.width,
        facility_height=base_prob.facility.height,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10.0, y=0.0, width=10.0, height=10.0),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=0.0, y=10.0, width=10.0, height=10.0),
            "DEP_D": ContinuousPlacement(department_id="DEP_D", x=115.0, y=10.0, width=10.0, height=10.0),
        },
    )
    assert LayoutValidator.validate(base_prob, boundary_layout).is_valid is False
    assert EvaluationEngine().evaluate(base_prob, boundary_layout).is_feasible is False
    assert CanonicalEvaluationService.evaluate(base_prob, boundary_layout).is_feasible is False

    # (c) Reserved Zone Collision
    rz_prob = base_prob.model_copy(deep=True)
    rz_prob.facility.reserved_zones = [
        ReservedZone(
            id="RZ_KEEP_OUT",
            type="pillar",
            bounding_box=BoundingBox(x_min=12.0, y_min=12.0, x_max=18.0, y_max=18.0),
            strict=True,
        )
    ]
    rz_layout = ContinuousLayout(
        problem_id=rz_prob.id,
        facility_width=rz_prob.facility.width,
        facility_height=rz_prob.facility.height,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10.0, y=0.0, width=10.0, height=10.0),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=0.0, y=10.0, width=10.0, height=10.0),
            "DEP_D": ContinuousPlacement(department_id="DEP_D", x=10.0, y=10.0, width=10.0, height=10.0),
        },
    )
    assert LayoutValidator.validate(rz_prob, rz_layout).is_valid is False
    assert EvaluationEngine().evaluate(rz_prob, rz_layout).is_feasible is False
    assert CanonicalEvaluationService.evaluate(rz_prob, rz_layout).is_feasible is False

    # (d) Fixed Department Position Violation
    fixed_prob = base_prob.model_copy(deep=True)
    fixed_prob.departments[0].fixed_position = Point2D(x=20.0, y=10.0)
    fixed_layout = ContinuousLayout(
        problem_id=fixed_prob.id,
        facility_width=fixed_prob.facility.width,
        facility_height=fixed_prob.facility.height,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10.0, y=0.0, width=10.0, height=10.0),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=0.0, y=10.0, width=10.0, height=10.0),
            "DEP_D": ContinuousPlacement(department_id="DEP_D", x=10.0, y=10.0, width=10.0, height=10.0),
        },
    )
    assert LayoutValidator.validate(fixed_prob, fixed_layout).is_valid is False
    assert EvaluationEngine().evaluate(fixed_prob, fixed_layout).is_feasible is False
    assert CanonicalEvaluationService.evaluate(fixed_prob, fixed_layout).is_feasible is False
