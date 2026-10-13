"""Comprehensive test suite for Phase 9.2: Evaluation Integrity & Reproducibility Audit.

Covers:
1. Canonical evaluation configuration hashing and determinism
2. Component-level problem data provenance hashing on FLP_INDUSTRIAL_10
3. Mathematical hand-calculation verification of MHC and Flow-Distance on FLP_ACADEMIC_4
4. Mathematical verification of non-uniform flow costs proving Flow-Distance != MHC / 2
5. Canonical evaluation of saved Manual Baseline layout
6. Canonical evaluation of saved Guillotine Generated layout
7. Canonical evaluation of saved GA Best Solution layout
8. Geometric audit of CST_SOFT_VIBRATION_SEP across all 3 layouts
9. GA Seed 2024 exact bitwise reproducibility ($93,876.54)
10. Explicit proof that Flow-Distance is not MHC / 2
11. Statistical decomposition of initialization vs evolution (39.2% vs 40.9%)
12. 5-Seed ablation study summary integrity in evaluation_audit_summary.json
13. Evaluation report idempotency and hash consistency
14. CanonicalEvaluationReport Pydantic serialization roundtrip
"""

import json
import math
import os
from pathlib import Path
import pytest

from app.algorithms.ga.models import GAConfig
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.evaluation.canonical import (
    CanonicalEvaluationReport,
    CanonicalEvaluationService,
    compute_evaluation_config_hash,
    compute_problem_provenance_hashes,
)
from app.evaluation.config import EvaluationConfig
from app.models.constraint import (
    Constraint,
    ConstraintClassification,
    ConstraintType,
)
from app.models.department import Department
from app.models.facility import Facility
from app.models.flow import Flow
from app.models.problem import FacilityLayoutProblem
from app.models.relationship import Relationship, RelationshipType
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.services.geometry_engine import DistanceMetricType, GeometryEngine
from app.services.layout_normalizer import generate_layout_signature
from app.services.problem_service import problem_service


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "examples"
MANUAL_PATH = DATA_DIR / "sample_layout.json"
GUILLOTINE_PATH = DATA_DIR / "generated_industrial_10.json"
GA_BEST_PATH = DATA_DIR / "ga_optimized_industrial_10.json"
AUDIT_SUMMARY_PATH = DATA_DIR / "evaluation_audit_summary.json"


@pytest.fixture
def industrial_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_INDUSTRIAL_10")


@pytest.fixture
def academic_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_ACADEMIC_4")


def test_canonical_config_hash_consistency():
    """Verify that default EvaluationConfig produces a deterministic SHA-256 fingerprint."""
    cfg1 = EvaluationConfig()
    cfg2 = EvaluationConfig()
    h1 = compute_evaluation_config_hash(cfg1)
    h2 = compute_evaluation_config_hash(cfg2)
    assert h1 == h2
    assert len(h1) == 64
    assert h1 == "eb0c6a65de43d685de8a995638289a9189876cb4d43b40d175072d6409cf7811"


def test_problem_provenance_hashes_flp_industrial_10(industrial_problem):
    """Verify cryptographic provenance hashes for FLP_INDUSTRIAL_10."""
    hashes = compute_problem_provenance_hashes(industrial_problem)
    assert hashes["problem_id"] == "FLP_INDUSTRIAL_10"
    assert len(hashes["composite_data_hash"]) == 64
    assert len(hashes["department_geometry_hash"]) == 64
    assert len(hashes["flow_matrix_hash"]) == 64
    assert len(hashes["rel_matrix_hash"]) == 64
    assert len(hashes["constraint_definitions_hash"]) == 64

    # Hashes must remain deterministic across multiple invocations
    hashes_again = compute_problem_provenance_hashes(industrial_problem)
    assert hashes == hashes_again


def test_mathematical_hand_calculation_academic_4(academic_problem):
    """Independently hand-calculate MHC and Flow-Distance on FLP_ACADEMIC_4 and verify."""
    # Place 4 departments in a 2x2 grid:
    # DEP_A: (0, 0), 10x10 -> Centroid (5, 5)
    # DEP_B: (10, 0), 10x10 -> Centroid (15, 5)
    # DEP_C: (10, 10), 10x10 -> Centroid (15, 15)
    # DEP_D: (0, 10), 10x10 -> Centroid (5, 15)
    layout = ContinuousLayout(
        problem_id=academic_problem.id,
        facility_width=120.0,
        facility_height=120.0,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0, y=0, width=10, height=10),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10, y=0, width=10, height=10),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=10, y=10, width=10, height=10),
            "DEP_D": ContinuousPlacement(department_id="DEP_D", x=0, y=10, width=10, height=10),
        },
    )

    # In FLP_ACADEMIC_4:
    # Flows:
    # A->B: quantity 50.0, cost 1.0. D(A, B) = |5-15| + |5-5| = 10.0 -> Cost = 50*10*1 = 500, FD = 50*10 = 500
    # B->C: quantity 30.0, cost 1.0. D(B, C) = |15-15| + |5-15| = 10.0 -> Cost = 30*10*1 = 300, FD = 30*10 = 300
    # C->D: quantity 10.0, cost 1.0. D(C, D) = |15-5| + |15-15| = 10.0 -> Cost = 10*10*1 = 100, FD = 10*10 = 100
    # Expected MHC = 500 + 300 + 100 = 900.0
    # Expected Flow-Distance = 500 + 300 + 100 = 900.0

    report = CanonicalEvaluationService.evaluate(academic_problem, layout)
    assert report.material_handling_cost == 900.00
    assert report.flow_distance == 900.00
    assert report.is_feasible is True


def test_mathematical_hand_calculation_non_uniform_costs():
    """Construct a minimal problem with non-uniform unit costs to mathematically prove FD != MHC / 2."""
    facility = Facility(id="FAC_TEST", name="Test", width=50.0, height=50.0, area=2500.0)
    departments = [
        Department(id="D1", name="D1", required_area=100.0, min_width=5.0, max_width=20.0, min_height=5.0, max_height=20.0),
        Department(id="D2", name="D2", required_area=100.0, min_width=5.0, max_width=20.0, min_height=5.0, max_height=20.0),
    ]
    flows = [
        Flow(source_department="D1", target_department="D2", quantity=20.0, cost_per_unit_distance=1.75),
    ]
    problem = FacilityLayoutProblem(
        id="FLP_TEST_NON_UNIFORM",
        name="Non-Uniform Cost Test",
        facility=facility,
        departments=departments,
        flows=flows,
        relationships=[],
        constraints=[],
    )

    # Place D1 at (0, 0), 10x10 -> Centroid (5, 5)
    # Place D2 at (20, 0), 10x10 -> Centroid (25, 5)
    # Distance = |5 - 25| + |5 - 5| = 20.0m
    # Hand calculation:
    # Flow-Distance = Quantity * Distance = 20.0 * 20.0 = 400.00 m-moves
    # MHC = Quantity * Distance * Cost = 20.0 * 20.0 * 1.75 = $700.00
    # Notice: MHC / 2 = 350.0 != Flow-Distance (400.0)

    layout = ContinuousLayout(
        problem_id=problem.id,
        facility_width=50.0,
        facility_height=50.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=0, y=0, width=10, height=10),
            "D2": ContinuousPlacement(department_id="D2", x=20, y=0, width=10, height=10),
        },
    )

    report = CanonicalEvaluationService.evaluate(problem, layout)
    assert report.flow_distance == 400.00
    assert report.material_handling_cost == 700.00
    assert report.flow_distance != report.material_handling_cost / 2.0


def test_canonical_evaluation_manual_baseline(industrial_problem):
    """Verify saved Manual Baseline layout under canonical contract."""
    with open(MANUAL_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    report = CanonicalEvaluationService.evaluate(industrial_problem, data)
    assert report.material_handling_cost == 139498.75
    assert report.flow_distance == 117893.75
    assert report.relationship_satisfaction_percentage == 55.47
    assert report.hard_violations_count == 0
    assert report.soft_violations_count == 0
    assert report.soft_penalty == 0.0
    assert report.is_feasible is True
    assert report.is_complete is True


def test_canonical_evaluation_guillotine_baseline(industrial_problem):
    """Verify saved Guillotine Generated layout under canonical contract."""
    with open(GUILLOTINE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    report = CanonicalEvaluationService.evaluate(industrial_problem, data)
    assert abs(report.material_handling_cost - 180263.99) < 0.1
    assert abs(report.flow_distance - 153551.19) < 0.1
    assert report.relationship_satisfaction_percentage == 44.17
    assert report.hard_violations_count == 0
    assert report.soft_violations_count == 1
    assert report.soft_penalty == 62500.0
    assert report.is_feasible is True
    assert report.is_complete is True

    # Check the violation detail
    v = report.violations[0]
    assert v["constraint_id"] == "CST_SOFT_VIBRATION_SEP"
    assert v["classification"] == "soft"
    assert v["magnitude"] == 25.0
    assert v["penalty_cost"] == 62500.0


def test_canonical_evaluation_ga_best_solution(industrial_problem):
    """Verify saved GA Best Solution layout under canonical contract."""
    with open(GA_BEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    report = CanonicalEvaluationService.evaluate(industrial_problem, data)
    assert report.material_handling_cost == 93876.54
    assert report.flow_distance == 78675.22
    assert report.relationship_satisfaction_percentage == 63.70
    assert report.hard_violations_count == 0
    assert report.soft_violations_count == 0
    assert report.soft_penalty == 0.0
    assert report.is_feasible is True
    assert report.is_complete is True


def test_vibration_separation_geometric_deficit():
    """Verify edge-to-edge distance calculation for CST_SOFT_VIBRATION_SEP across all 3 layouts."""
    # 1. Guillotine
    with open(GUILLOTINE_PATH, "r", encoding="utf-8") as f:
        g_data = json.load(f)
    pm_g = g_data["placements"]["DEP_MACHINING"]
    pq_g = g_data["placements"]["DEP_QUALITY"]
    bb_m_g = ContinuousPlacement(department_id="DEP_MACHINING", x=pm_g["x"], y=pm_g["y"], width=pm_g["width"], height=pm_g["height"]).bounding_box
    bb_q_g = ContinuousPlacement(department_id="DEP_QUALITY", x=pq_g["x"], y=pq_g["y"], width=pq_g["width"], height=pq_g["height"]).bounding_box
    dist_g = GeometryEngine.edge_to_edge_distance(bb_m_g, bb_q_g)
    assert dist_g == 0.0  # Touching at x = 130.0
    deficit_g = max(0.0, 25.0 - dist_g)
    assert deficit_g == 25.0
    assert deficit_g * 2500.0 == 62500.0

    # 2. Manual
    with open(MANUAL_PATH, "r", encoding="utf-8") as f:
        m_data = json.load(f)
    pm_m = m_data["placements"]["DEP_MACHINING"]
    pq_m = m_data["placements"]["DEP_QUALITY"]
    x_m = pm_m.get("x", pm_m.get("origin", {}).get("x"))
    y_m = pm_m.get("y", pm_m.get("origin", {}).get("y"))
    w_m = pm_m.get("width", pm_m.get("dimensions", {}).get("width"))
    h_m = pm_m.get("height", pm_m.get("dimensions", {}).get("height"))

    x_q = pq_m.get("x", pq_m.get("origin", {}).get("x"))
    y_q = pq_m.get("y", pq_m.get("origin", {}).get("y"))
    w_q = pq_m.get("width", pq_m.get("dimensions", {}).get("width"))
    h_q = pq_m.get("height", pq_m.get("dimensions", {}).get("height"))

    bb_m_m = ContinuousPlacement(department_id="DEP_MACHINING", x=x_m, y=y_m, width=w_m, height=h_m).bounding_box
    bb_q_m = ContinuousPlacement(department_id="DEP_QUALITY", x=x_q, y=y_q, width=w_q, height=h_q).bounding_box
    dist_m = GeometryEngine.edge_to_edge_distance(bb_m_m, bb_q_m)
    assert dist_m == 42.5  # Clear buffer > 25.0
    assert max(0.0, 25.0 - dist_m) == 0.0

    # 3. GA Best
    with open(GA_BEST_PATH, "r", encoding="utf-8") as f:
        ga_data = json.load(f)
    pm_ga = ga_data["placements"]["DEP_MACHINING"]
    pq_ga = ga_data["placements"]["DEP_QUALITY"]
    bb_m_ga = ContinuousPlacement(department_id="DEP_MACHINING", x=pm_ga["x"], y=pm_ga["y"], width=pm_ga["width"], height=pm_ga["height"]).bounding_box
    bb_q_ga = ContinuousPlacement(department_id="DEP_QUALITY", x=pq_ga["x"], y=pq_ga["y"], width=pq_ga["width"], height=pq_ga["height"]).bounding_box
    dist_ga = round(GeometryEngine.edge_to_edge_distance(bb_m_ga, bb_q_ga), 2)
    assert dist_ga == 50.71  # Clear buffer > 25.0
    assert max(0.0, 25.0 - dist_ga) == 0.0


def test_ga_seed_2024_exact_reproducibility(industrial_problem):
    """Confirm exact reproduction of Seed 2024 producing MHC = $93,876.54 and matching signature."""
    cfg = GAConfig(
        population_size=40,
        generations=100,
        crossover_rate=0.8,
        mutation_rate=0.2,
        stagnation_limit=100,
        random_seed=2024,
    )
    algo = GeneticLayoutAlgorithm()
    res = algo.solve_with_result(industrial_problem, config=cfg)

    assert abs(res.best_mhc - 93876.54) < 0.01
    assert res.is_feasible is True

    sig = generate_layout_signature(res.best_layout)
    assert sig == "fa36b29c4fa43e85984c1b8885a93ed9bf8f3d98e38ecdf6d0cc0104fd58ed60"


def test_flow_distance_not_half_mhc(industrial_problem):
    """Verify that for all 3 layouts, Flow-Distance is mathematically distinct from MHC / 2."""
    for path in [MANUAL_PATH, GUILLOTINE_PATH, GA_BEST_PATH]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        report = CanonicalEvaluationService.evaluate(industrial_problem, data)
        half_mhc = round(report.material_handling_cost / 2.0, 2)
        assert abs(report.flow_distance - half_mhc) > 1000.0, (
            f"Flow-Distance ({report.flow_distance}) must not equal MHC/2 ({half_mhc}) for {path.name}"
        )


def test_statistical_decomposition_ratios():
    """Verify the mathematical arithmetic of both statistical contribution methods."""
    # Data from the 5-seed benchmark:
    A = 180263.94  # Guillotine baseline
    seeds_data = [
        {"seed": 42, "initial_mhc": 141969.58, "final_mhc": 121190.46},
        {"seed": 101, "initial_mhc": 159771.10, "final_mhc": 107487.83},
        {"seed": 2024, "initial_mhc": 159771.10, "final_mhc": 93876.54},
        {"seed": 777, "initial_mhc": 148614.48, "final_mhc": 107922.59},
        {"seed": 999, "initial_mhc": 151531.95, "final_mhc": 114717.87},
    ]

    # Method 1: Macro-average of ratios
    init_pcts = []
    evol_pcts = []
    for s in seeds_data:
        init_gain = A - s["initial_mhc"]
        evol_gain = s["initial_mhc"] - s["final_mhc"]
        total_gain = A - s["final_mhc"]
        init_pcts.append((init_gain / total_gain) * 100.0)
        evol_pcts.append((evol_gain / total_gain) * 100.0)

    mean_init_pct = round(sum(init_pcts) / len(init_pcts), 1)
    mean_evol_pct = round(sum(evol_pcts) / len(evol_pcts), 1)
    assert mean_init_pct == 40.9
    assert mean_evol_pct == 59.1
    assert round(mean_init_pct + mean_evol_pct, 1) == 100.0

    # Method 2: Ratio of aggregate means
    mean_initial = sum(s["initial_mhc"] for s in seeds_data) / len(seeds_data)
    mean_final = sum(s["final_mhc"] for s in seeds_data) / len(seeds_data)
    agg_init_gain = A - mean_initial
    agg_evol_gain = mean_initial - mean_final
    agg_total_gain = A - mean_final

    agg_init_pct = round((agg_init_gain / agg_total_gain) * 100.0, 1)
    agg_evol_pct = round((agg_evol_gain / agg_total_gain) * 100.0, 1)
    assert agg_init_pct == 39.2
    assert agg_evol_pct == 60.8
    assert round(agg_init_pct + agg_evol_pct, 1) == 100.0


def test_ablation_5seed_summary_integrity():
    """Verify that evaluation_audit_summary.json exists and confirms Full GA superiority."""
    assert AUDIT_SUMMARY_PATH.exists()
    with open(AUDIT_SUMMARY_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)

    ablation = audit["ablation_5seed"]
    assert "A_Init_Only" in ablation
    assert "B_Mutation_Only" in ablation
    assert "C_Crossover_Only" in ablation
    assert "D_Full_GA" in ablation

    # Full GA should have the lowest mean MHC across all 5 seeds
    mean_init = ablation["A_Init_Only"]["mean_mhc"]
    mean_mut = ablation["B_Mutation_Only"]["mean_mhc"]
    mean_cx = ablation["C_Crossover_Only"]["mean_mhc"]
    mean_full = ablation["D_Full_GA"]["mean_mhc"]

    assert mean_full < mean_init
    assert mean_full < mean_mut
    assert mean_full < mean_cx
    assert mean_full == 109039.06


def test_canonical_report_model_serialization(industrial_problem):
    """Test that CanonicalEvaluationReport serializes to dict and JSON without error."""
    with open(GA_BEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    rep = CanonicalEvaluationService.evaluate(industrial_problem, data)

    # Dump to JSON
    json_str = rep.model_dump_json()
    assert isinstance(json_str, str)

    # Reconstitute from JSON
    rep2 = CanonicalEvaluationReport.model_validate_json(json_str)
    assert rep2.material_handling_cost == rep.material_handling_cost
    assert rep2.flow_distance == rep.flow_distance
    assert rep2.layout_signature == rep.layout_signature
    assert rep2.problem_composite_hash == rep.problem_composite_hash


def test_evaluation_hash_and_metric_idempotency(industrial_problem):
    """Verify that multiple consecutive canonical evaluations produce bitwise identical results."""
    with open(GA_BEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    rep1 = CanonicalEvaluationService.evaluate(industrial_problem, data)
    rep2 = CanonicalEvaluationService.evaluate(industrial_problem, data)

    assert rep1.model_dump() == rep2.model_dump()
    assert rep1.problem_composite_hash == rep2.problem_composite_hash
    assert rep1.evaluation_config_hash == rep2.evaluation_config_hash
    assert rep1.layout_signature == rep2.layout_signature

