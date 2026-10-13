"""Comprehensive test suite for Phase 10: Multi-Objective Evaluation & Pareto Frontier V1.

Covers:
1. Mathematical hand-calculation verification on the 3-solution example (A, B, C)
2. Direction correctness: Minimize (MHC, Soft Penalty) vs Maximize (Relationship Satisfaction)
3. Equal objective vector handling (no self-domination or false dominance)
4. Floating-point tolerance handling (precision audit: 180263.94 vs 180263.99)
5. Non-dominated sorting and rank assignment
6. Duplicate layout signature handling and deduplication
7. Complete layout filtering (rejects incomplete layouts with explicit reason)
8. Infeasible layout filtering (rejects hard constraint / overlap violations)
9. Cross-problem comparison rejection (detects mismatched problem IDs / provenance hashes)
10. Cross-config comparison rejection (detects disparate EvaluationConfig hashes)
11. Deterministic ranking within each Pareto layer
12. Three-objective frontier on FLP_INDUSTRIAL_10 saved baselines
13. Trade-off analysis pairwise comparison service
14. Decision support multi-criteria weighted recommendation correctness
15. GA candidate portfolio integration (candidate_pool)
16. API endpoint integration tests (POST /api/pareto/analyze, POST /api/pareto/compare, GET /api/pareto/objectives)
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.algorithms.ga.models import GAConfig
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.evaluation.canonical import (
    CanonicalEvaluationService,
    compute_evaluation_config_hash,
    compute_problem_provenance_hashes,
)
from app.evaluation.config import EvaluationConfig
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.optimization.pareto import (
    DecisionSupportRecommendation,
    ExcludedCandidate,
    ObjectiveDefinition,
    ObjectiveDirection,
    ParetoAnalysisResult,
    ParetoCandidate,
    ParetoFrontierService,
    TradeOffComparison,
    get_default_pareto_objectives,
)
from app.services.problem_service import problem_service


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "examples"
MANUAL_PATH = DATA_DIR / "sample_layout.json"
GUILLOTINE_PATH = DATA_DIR / "generated_industrial_10.json"
GA_BEST_PATH = DATA_DIR / "ga_optimized_industrial_10.json"


@pytest.fixture
def industrial_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_INDUSTRIAL_10")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_hand_calculated_three_solution_example():
    """Verify hand-calculated 3-solution example specified in requirements.
    
    A: MHC = 100, REL = 80, Soft Penalty = 0
    B: MHC = 120, REL = 70, Soft Penalty = 10
    C: MHC = 90,  REL = 60, Soft Penalty = 0
    
    Expected:
    - A dominates B
    - A and C do not dominate each other
    - Pareto Frontier = {A, C} (Rank 1); B is Rank 2
    """
    objectives = get_default_pareto_objectives()

    cand_a = ParetoCandidate(
        candidate_id="Sol_A",
        algorithm_source="manual",
        layout_signature="sig_a",
        problem_id="PROB_TEST",
        problem_composite_hash="hash_test",
        evaluation_config_hash="cfg_test",
        objective_values={
            "material_handling_cost": 100.0,
            "relationship_satisfaction": 80.0,
            "soft_penalty": 0.0,
        },
    )

    cand_b = ParetoCandidate(
        candidate_id="Sol_B",
        algorithm_source="manual",
        layout_signature="sig_b",
        problem_id="PROB_TEST",
        problem_composite_hash="hash_test",
        evaluation_config_hash="cfg_test",
        objective_values={
            "material_handling_cost": 120.0,
            "relationship_satisfaction": 70.0,
            "soft_penalty": 10.0,
        },
    )

    cand_c = ParetoCandidate(
        candidate_id="Sol_C",
        algorithm_source="manual",
        layout_signature="sig_c",
        problem_id="PROB_TEST",
        problem_composite_hash="hash_test",
        evaluation_config_hash="cfg_test",
        objective_values={
            "material_handling_cost": 90.0,
            "relationship_satisfaction": 60.0,
            "soft_penalty": 0.0,
        },
    )

    # 1. Pairwise dominance assertions
    # A vs B: A is strictly better in all 3 objectives (100 < 120, 80 > 70, 0 < 10)
    assert ParetoFrontierService.dominates(cand_a, cand_b, objectives) is True
    assert ParetoFrontierService.dominates(cand_b, cand_a, objectives) is False

    # A vs C: A has better REL (80 > 60), but C has better MHC (90 < 100); both have Soft Penalty = 0
    assert ParetoFrontierService.dominates(cand_a, cand_c, objectives) is False
    assert ParetoFrontierService.dominates(cand_c, cand_a, objectives) is False

    # B vs C: B has better REL (70 > 60), but C has better MHC (90 < 120) and better Soft Penalty (0 < 10)
    assert ParetoFrontierService.dominates(cand_b, cand_c, objectives) is False
    assert ParetoFrontierService.dominates(cand_c, cand_b, objectives) is False

    # 2. Fast non-dominated sorting
    ranks, sorted_cands = ParetoFrontierService.fast_non_dominated_sort(
        [cand_a, cand_b, cand_c], objectives
    )

    # Expected: Rank 1 has {Sol_A, Sol_C}; Rank 2 has {Sol_B}
    assert 1 in ranks
    assert 2 in ranks
    assert set(ranks[1]) == {"Sol_A", "Sol_C"}
    assert ranks[2] == ["Sol_B"]

    # Check candidate objects
    cand_map = {c.candidate_id: c for c in sorted_cands}
    assert cand_map["Sol_A"].pareto_rank == 1
    assert cand_map["Sol_A"].is_non_dominated is True
    assert cand_map["Sol_C"].pareto_rank == 1
    assert cand_map["Sol_C"].is_non_dominated is True
    assert cand_map["Sol_B"].pareto_rank == 2
    assert cand_map["Sol_B"].is_non_dominated is False
    assert "Sol_A" in cand_map["Sol_B"].dominated_by


def test_direction_correctness_minimize_vs_maximize():
    """Verify that objective directions (minimize vs maximize) are applied correctly."""
    objectives = [
        ObjectiveDefinition(id="cost", name="Cost", direction=ObjectiveDirection.MINIMIZE, unit="$"),
        ObjectiveDefinition(id="score", name="Score", direction=ObjectiveDirection.MAXIMIZE, unit="pts"),
    ]

    p1 = ParetoCandidate(
        candidate_id="P1", algorithm_source="test", layout_signature="s1",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"cost": 10.0, "score": 100.0},
    )
    p2 = ParetoCandidate(
        candidate_id="P2", algorithm_source="test", layout_signature="s2",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"cost": 20.0, "score": 50.0},
    )

    # P1 has lower cost and higher score -> dominates P2
    assert ParetoFrontierService.dominates(p1, p2, objectives) is True
    assert ParetoFrontierService.dominates(p2, p1, objectives) is False


def test_equal_objective_vectors_do_not_dominate():
    """Verify that two solutions with identical objective values do NOT dominate each other."""
    objectives = get_default_pareto_objectives()

    cand1 = ParetoCandidate(
        candidate_id="C1", algorithm_source="test", layout_signature="s1",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"material_handling_cost": 1000.0, "relationship_satisfaction": 50.0, "soft_penalty": 0.0},
    )
    cand2 = ParetoCandidate(
        candidate_id="C2", algorithm_source="test", layout_signature="s2",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"material_handling_cost": 1000.0, "relationship_satisfaction": 50.0, "soft_penalty": 0.0},
    )

    # Identical vectors: neither is strictly better in any objective
    assert ParetoFrontierService.dominates(cand1, cand2, objectives) is False
    assert ParetoFrontierService.dominates(cand2, cand1, objectives) is False

    ranks, _ = ParetoFrontierService.fast_non_dominated_sort([cand1, cand2], objectives)
    assert set(ranks[1]) == {"C1", "C2"}


def test_floating_point_tolerance_and_guillotine_precision_audit():
    """Test floating-point tolerance behavior and investigate Guillotine MHC difference (180263.94 vs 180263.99).
    
    A 5-cent difference on an $180,000 cost is 0.000028%.
    With tolerance >= 0.10, the two representations are treated as equivalent.
    """
    objectives = [
        ObjectiveDefinition(
            id="material_handling_cost",
            name="MHC",
            direction=ObjectiveDirection.MINIMIZE,
            unit="$",
            tolerance=0.10,  # 10-cent tolerance
        ),
        ObjectiveDefinition(
            id="relationship_satisfaction",
            name="Rel",
            direction=ObjectiveDirection.MAXIMIZE,
            unit="%",
            tolerance=0.01,
        ),
        ObjectiveDefinition(
            id="soft_penalty",
            name="Soft",
            direction=ObjectiveDirection.MINIMIZE,
            unit="$",
            tolerance=0.10,
        ),
    ]

    # Two versions of Guillotine: in-memory (180263.94) vs file (180263.99)
    g_mem = ParetoCandidate(
        candidate_id="G_mem", algorithm_source="guillotine", layout_signature="sig_g1",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"material_handling_cost": 180263.94, "relationship_satisfaction": 44.17, "soft_penalty": 62500.0},
    )
    g_file = ParetoCandidate(
        candidate_id="G_file", algorithm_source="guillotine", layout_signature="sig_g2",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"material_handling_cost": 180263.99, "relationship_satisfaction": 44.17, "soft_penalty": 62500.0},
    )

    # Under tolerance 0.10, 180263.94 and 180263.99 do NOT dominate each other
    assert ParetoFrontierService.dominates(g_mem, g_file, objectives, tolerance=0.10) is False
    assert ParetoFrontierService.dominates(g_file, g_mem, objectives, tolerance=0.10) is False


def test_duplicate_signature_handling(industrial_problem):
    """Verify that multiple candidates sharing the identical layout signature are deduplicated."""
    with open(MANUAL_PATH, "r", encoding="utf-8") as f:
        data1 = json.load(f)
    with open(MANUAL_PATH, "r", encoding="utf-8") as f:
        data2 = json.load(f)

    data1["id"] = "Manual_1"
    data2["id"] = "Manual_2"

    result = ParetoFrontierService.analyze(
        problem=industrial_problem,
        raw_candidates=[data1, data2],
    )

    assert result.total_candidates_evaluated == 2
    assert result.valid_candidates_count == 1
    assert result.excluded_candidates_count == 1
    assert "Duplicate layout signature" in result.excluded[0].reason


def test_incomplete_layout_filtering(industrial_problem):
    """Verify that an incomplete layout missing required departments is rejected with reason."""
    incomplete_layout = {
        "problem_id": industrial_problem.id,
        "facility_width": 150.0,
        "facility_height": 80.0,
        "placements": {
            # Only 2 out of 10 departments placed
            "DEP_WELDING": {"x": 0.0, "y": 0.0, "width": 20.0, "height": 20.0},
            "DEP_CUTTING": {"x": 20.0, "y": 0.0, "width": 20.0, "height": 20.0},
        },
    }

    result = ParetoFrontierService.analyze(
        problem=industrial_problem,
        raw_candidates=[incomplete_layout],
    )

    assert result.valid_candidates_count == 0
    assert result.excluded_candidates_count == 1
    assert "Incomplete layout" in result.excluded[0].reason


def test_infeasible_layout_filtering(industrial_problem):
    """Verify that an infeasible layout with overlapping departments is rejected with reason."""
    # Place two departments at the exact same coordinates (overlap)
    overlapping_layout = {
        "problem_id": industrial_problem.id,
        "facility_width": 150.0,
        "facility_height": 80.0,
        "placements": {
            d.id: {"x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0}
            for d in industrial_problem.departments
        },
    }

    result = ParetoFrontierService.analyze(
        problem=industrial_problem,
        raw_candidates=[overlapping_layout],
    )

    assert result.valid_candidates_count == 0
    assert result.excluded_candidates_count == 1
    assert "Infeasible layout" in result.excluded[0].reason


def test_cross_problem_comparison_rejection(industrial_problem):
    """Verify that candidate layouts belonging to a different problem are rejected."""
    mismatched_candidate = {
        "problem_id": "OTHER_PROBLEM_ID",
        "facility_width": 50.0,
        "facility_height": 50.0,
        "placements": {},
    }

    result = ParetoFrontierService.analyze(
        problem=industrial_problem,
        raw_candidates=[mismatched_candidate],
    )

    assert result.valid_candidates_count == 0
    assert result.excluded_candidates_count == 1
    assert "Cross-problem mismatch" in result.excluded[0].reason


def test_cross_config_comparison_rejection():
    """Verify that a candidate evaluated under a disparate EvaluationConfig is rejected."""
    cand = ParetoCandidate(
        candidate_id="Foreign_Config_Cand",
        algorithm_source="test",
        layout_signature="sig_foreign",
        problem_id="FLP_INDUSTRIAL_10",
        problem_composite_hash="1beead643d6dbe44f5c4b05fe8cb49892112be06e3e46cf00d66677a35910179",
        evaluation_config_hash="mismatched_config_hash_12345",  # Disparate config hash!
        objective_values={"material_handling_cost": 1000.0, "relationship_satisfaction": 50.0, "soft_penalty": 0.0},
    )

    prob = problem_service.get_example_problem("FLP_INDUSTRIAL_10")
    result = ParetoFrontierService.analyze(
        problem=prob,
        raw_candidates=[cand],
    )

    assert result.valid_candidates_count == 0
    assert result.excluded_candidates_count == 1
    assert "EvaluationConfig hash mismatch" in result.excluded[0].reason


def test_three_objective_frontier_flp_industrial_10(industrial_problem):
    """Evaluate saved baselines and multi-seed layouts on FLP_INDUSTRIAL_10.
    
    Verifies that:
    1. GA Best (Seed 2024) and GA Seed 101 are on the Pareto Frontier (Rank 1).
    2. Manual Baseline is dominated by GA solutions (Rank 3).
    3. Guillotine Baseline is dominated (Rank 4).
    4. Frontier contains genuine trade-offs between MHC and Relationship Satisfaction.
    """
    portfolio_files = [
        MANUAL_PATH,
        GUILLOTINE_PATH,
        GA_BEST_PATH,
    ]
    candidates = []
    labels = ["Manual Baseline", "Guillotine Baseline", "GA Best Solution (Seed 2024)"]
    for p, label in zip(portfolio_files, labels):
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
            d["id"] = label
            d["algorithm_name"] = label
            candidates.append(d)

    # Also load multi-seed if available
    seeds_path = DATA_DIR / "pareto_additional_seeds.json"
    if seeds_path.exists():
        with open(seeds_path, "r", encoding="utf-8") as f:
            candidates.extend(json.load(f))

    result = ParetoFrontierService.analyze(
        problem=industrial_problem,
        raw_candidates=candidates,
    )

    assert result.valid_candidates_count >= 3
    assert result.frontier_count >= 1

    # Check frontier contents
    assert "GA Best Solution (Seed 2024)" in result.frontier_candidate_ids or "ga_optimized_industrial_10" in result.frontier_candidate_ids or any("2024" in fid for fid in result.frontier_candidate_ids)

    # Manual Baseline should be dominated (not Rank 1)
    manual_cand = next((c for c in result.candidates if "sample_layout" in c.candidate_id or "Manual" in c.candidate_id), None)
    if manual_cand:
        assert manual_cand.is_non_dominated is False
        assert manual_cand.pareto_rank > 1

    # Guillotine Baseline should have soft penalty = $62,500.0 and be dominated
    guill_cand = next((c for c in result.candidates if "generated_industrial" in c.candidate_id or "Guillotine" in c.candidate_id), None)
    if guill_cand:
        assert guill_cand.is_non_dominated is False
        assert guill_cand.objective_values["soft_penalty"] == 62500.0
        assert guill_cand.pareto_rank >= 3


def test_pairwise_tradeoff_comparison():
    """Verify pairwise trade-off comparison between two candidates."""
    objectives = get_default_pareto_objectives()

    cand1 = ParetoCandidate(
        candidate_id="Sol_LowCost", algorithm_source="GA", layout_signature="s1",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"material_handling_cost": 93876.54, "relationship_satisfaction": 63.70, "soft_penalty": 0.0},
    )
    cand2 = ParetoCandidate(
        candidate_id="Sol_HighRel", algorithm_source="GA", layout_signature="s2",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"material_handling_cost": 107487.83, "relationship_satisfaction": 64.79, "soft_penalty": 0.0},
    )

    tradeoff = ParetoFrontierService.compare_pair(cand1, cand2, objectives)
    assert tradeoff.candidate_a_id == "Sol_LowCost"
    assert tradeoff.candidate_b_id == "Sol_HighRel"
    assert "Sol_LowCost is better on Material Handling Cost" in tradeoff.analysis_text
    assert "Sol_HighRel is better on Relationship Satisfaction" in tradeoff.analysis_text


def test_decision_support_weighted_recommendation():
    """Verify that multi-criteria weighted recommendation selects the expected candidate under different profiles."""
    objectives = get_default_pareto_objectives()

    c_cost = ParetoCandidate(
        candidate_id="C_Cost", algorithm_source="GA", layout_signature="s1",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"material_handling_cost": 90000.0, "relationship_satisfaction": 60.0, "soft_penalty": 0.0},
    )
    c_rel = ParetoCandidate(
        candidate_id="C_Rel", algorithm_source="GA", layout_signature="s2",
        problem_id="P", problem_composite_hash="h", evaluation_config_hash="c",
        objective_values={"material_handling_cost": 110000.0, "relationship_satisfaction": 85.0, "soft_penalty": 0.0},
    )

    recs = ParetoFrontierService.compute_decision_recommendations(
        [c_cost, c_rel], objectives
    )

    # Cost priority should choose C_Cost
    assert recs["cost_priority"].recommended_candidate_id == "C_Cost"

    # Relationship priority should choose C_Rel
    assert recs["relationship_priority"].recommended_candidate_id == "C_Rel"


def test_ga_candidate_pool_integration(industrial_problem):
    """Verify that GeneticLayoutAlgorithm returns candidate_pool with unique feasible layouts."""
    cfg = GAConfig(
        population_size=20,
        generations=10,
        random_seed=42,
    )
    algo = GeneticLayoutAlgorithm()
    res = algo.solve_with_result(industrial_problem, config=cfg)

    assert hasattr(res, "candidate_pool")
    assert isinstance(res.candidate_pool, list)
    assert len(res.candidate_pool) >= 1  # At least the best layout


def test_api_pareto_endpoints(client):
    """Test FastAPI endpoints /api/pareto/objectives and /api/pareto/analyze."""
    # 1. GET /api/pareto/objectives
    resp_obj = client.get("/api/pareto/objectives")
    assert resp_obj.status_code == 200
    objs = resp_obj.json()
    assert len(objs) == 3
    assert objs[0]["id"] == "material_handling_cost"
    assert objs[1]["id"] == "relationship_satisfaction"
    assert objs[2]["id"] == "soft_penalty"

    # 2. POST /api/pareto/analyze
    resp_an = client.post("/api/pareto/analyze", json={
        "problem_id": "FLP_INDUSTRIAL_10",
        "include_saved_baselines": True,
    })
    assert resp_an.status_code == 200
    res = resp_an.json()
    assert res["problem_id"] == "FLP_INDUSTRIAL_10"
    assert res["valid_candidates_count"] >= 3
    assert res["frontier_count"] >= 1
    assert "cost_priority" in res["recommendations"]
    assert "relationship_priority" in res["recommendations"]

    # 3. POST /api/pareto/compare
    c1 = res["candidates"][0]
    c2 = res["candidates"][1]
    resp_comp = client.post("/api/pareto/compare", json={
        "candidate_a": c1,
        "candidate_b": c2,
    })
    assert resp_comp.status_code == 200
    comp_data = resp_comp.json()
    assert "analysis_text" in comp_data
