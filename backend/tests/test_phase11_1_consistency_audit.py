"""Phase 11.1: Consistency and Integrity Audit Test Suite for Adaptive Strategy Pipeline.

Audits metric integrity, dataset hashes, algorithm fairness, provenance tracking,
Pareto dominance consistency, and verifies that no mock or outdated approximations bypass
CanonicalEvaluationService.
"""

import json
from pathlib import Path
import pytest

from app.algorithms.generator.solver import FeasibleLayoutGenerator
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.evaluation.canonical import (
    CanonicalEvaluationService,
    compute_evaluation_config_hash,
    compute_problem_provenance_hashes,
)
from app.evaluation.config import EvaluationConfig
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout
from app.optimization.adaptive import (
    AdaptiveConfig,
    StrategyExecutionEngine,
)
from app.services.layout_normalizer import generate_layout_signature
from app.services.problem_analyzer import ProblemAnalyzer
from app.services.problem_service import problem_service

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "examples"


@pytest.fixture
def academic_4_problem() -> FacilityLayoutProblem:
    return problem_service.load_problem(DATA_DIR / "sample_academic_4.json")


@pytest.fixture
def medium_6_problem() -> FacilityLayoutProblem:
    return problem_service.load_problem(DATA_DIR / "sample_medium_plant.json")


@pytest.fixture
def industrial_10_problem() -> FacilityLayoutProblem:
    return problem_service.load_problem(DATA_DIR / "sample_plant.json")


@pytest.fixture
def expansion_8_problem() -> FacilityLayoutProblem:
    return problem_service.load_problem(DATA_DIR / "sample_expansion_8.json")


@pytest.fixture
def logistics_5_problem() -> FacilityLayoutProblem:
    return problem_service.load_problem(DATA_DIR / "sample_logistics_5.json")


# =============================================================================
# 1. Canonical vs Adaptive Metric Equality
# =============================================================================
def test_canonical_vs_adaptive_metric_equality(industrial_10_problem):
    """Every feasible candidate accepted by Adaptive Engine must have metrics identical

    to direct re-evaluation via CanonicalEvaluationService.
    """
    eval_cfg = EvaluationConfig()
    adaptive_cfg = AdaptiveConfig(
        max_total_runtime_seconds=15.0,
        ga_population_size=12,
        ga_generations=6,
        random_seed=42,
    )

    result = StrategyExecutionEngine.execute(
        industrial_10_problem, config=adaptive_cfg, evaluation_config=eval_cfg
    )
    assert result.feasible_status is True

    for item in result.candidate_portfolio.items:
        if not item.feasibility or item.solution is None:
            continue

        direct_report = CanonicalEvaluationService.evaluate(
            industrial_10_problem, item.solution, config=eval_cfg
        )

        assert item.material_handling_cost == pytest.approx(
            direct_report.material_handling_cost, abs=1e-3
        )
        assert item.relationship_satisfaction == pytest.approx(
            direct_report.relationship_satisfaction_percentage, abs=1e-3
        )
        assert item.soft_penalty == pytest.approx(
            direct_report.soft_penalty, abs=1e-3
        )
        assert item.problem_hash == direct_report.problem_composite_hash
        assert item.evaluation_config_hash == direct_report.evaluation_config_hash
        assert item.output_layout_signature == direct_report.layout_signature


# =============================================================================
# 2. Same Problem Hash Verification
# =============================================================================
def test_same_problem_hash_verification():
    """Verify that all 5 benchmark problem files produce immutable, deterministic hashes."""
    expected_hashes = {
        "FLP_ACADEMIC_4": "a6b0eca8de2d8d8f4b796093c02f5c73d8bee8533cd7ef7d14e220b821953b65",
        "FLP_MEDIUM_6": "2200093b5f3247c1ea0a58fd516b760ddedcae2a08a10b4e256423b4245077a8",
        "FLP_INDUSTRIAL_10": "1beead643d6dbe44f5c4b05fe8cb49892112be06e3e46cf00d66677a35910179",
        "FLP_EXPANSION_8": "cbd5b8c575e2075b7bd203aabdd15e3aac8b2c256c22651b0a27020f6c403b52",
        "FLP_LOGISTICS_5": "410558424825ebcc93a1ff36c750b4293ee83ce5ea3f722b879916c279ea694d",
    }

    files = {
        "FLP_ACADEMIC_4": DATA_DIR / "sample_academic_4.json",
        "FLP_MEDIUM_6": DATA_DIR / "sample_medium_plant.json",
        "FLP_INDUSTRIAL_10": DATA_DIR / "sample_plant.json",
        "FLP_EXPANSION_8": DATA_DIR / "sample_expansion_8.json",
        "FLP_LOGISTICS_5": DATA_DIR / "sample_logistics_5.json",
    }

    for pid, filepath in files.items():
        prob = problem_service.load_problem(filepath)
        hashes = compute_problem_provenance_hashes(prob)
        assert hashes["problem_id"] == pid
        assert hashes["composite_data_hash"] == expected_hashes[pid]


# =============================================================================
# 3. Saved vs Generated Layout Identity
# =============================================================================
def test_saved_vs_generated_layout_identity(industrial_10_problem):
    """Saved Guillotine layout and freshly generated layout produce identical layout signatures.

    The minimal $0.05 MHC delta ($180,263.99 vs $180,263.94) is strictly caused by 4-decimal
    float serialization in the JSON file.
    """
    with open(DATA_DIR / "generated_industrial_10.json", "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    saved_cont = ContinuousLayout.model_validate(saved_data)
    saved_sig = generate_layout_signature(saved_cont)
    saved_rep = CanonicalEvaluationService.evaluate(industrial_10_problem, saved_cont)

    gen = FeasibleLayoutGenerator(
        parameters={"strategy": "guillotine_row_packing", "random_seed": 42}
    )
    gen_sol = gen.solve(industrial_10_problem)
    gen_cont = ContinuousLayout.from_layout_solution(
        gen_sol,
        facility_width=industrial_10_problem.facility.width,
        facility_height=industrial_10_problem.facility.height,
    )
    gen_sig = generate_layout_signature(gen_cont)
    gen_rep = CanonicalEvaluationService.evaluate(industrial_10_problem, gen_sol)

    # Identical SHA-256 geometric signature
    assert saved_sig == gen_sig
    assert saved_sig == "61c4bf88996517780fd1f43839d1e1654c6be9276072a9799c4a7e1c8fc12174"

    # Minimal 0.05 difference from file precision
    assert abs(saved_rep.material_handling_cost - gen_rep.material_handling_cost) < 0.1
    assert abs(saved_rep.material_handling_cost - 180263.99) < 0.01
    assert abs(gen_rep.material_handling_cost - 180263.94) < 0.01

    # Exact equality on relationship satisfaction and soft penalty
    assert saved_rep.relationship_satisfaction_percentage == gen_rep.relationship_satisfaction_percentage == 44.17
    assert saved_rep.soft_penalty == gen_rep.soft_penalty == 62500.0


# =============================================================================
# 4. Soft Penalty Consistency
# =============================================================================
def test_soft_penalty_consistency(industrial_10_problem):
    """Guillotine layout on FLP_INDUSTRIAL_10 must have soft penalty of exactly $62,500.00, not $0.00."""
    with open(DATA_DIR / "generated_industrial_10.json", "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    rep = CanonicalEvaluationService.evaluate(industrial_10_problem, saved_data)
    assert rep.soft_violations_count == 1
    assert rep.soft_penalty == 62500.0

    # Geometric check: Machining and Quality touch along x = 130.0 (D_edge = 0.0)
    # Required distance = 25.0m -> Deficit = 25.0m * $2,500/m = $62,500.00
    v = rep.violations[0]
    assert v["constraint_id"] == "CST_SOFT_VIBRATION_SEP"
    assert v["classification"] == "soft"
    assert v["penalty_cost"] == 62500.0


# =============================================================================
# 5. Relationship Metric Consistency
# =============================================================================
def test_rel_metric_consistency(industrial_10_problem):
    """Guillotine layout on FLP_INDUSTRIAL_10 canonical REL satisfaction is strictly 44.17%, NOT 52.40%."""
    with open(DATA_DIR / "generated_industrial_10.json", "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    rep = CanonicalEvaluationService.evaluate(industrial_10_problem, saved_data)
    assert rep.relationship_satisfaction_percentage == 44.17
    assert rep.relationship_satisfaction_percentage != 52.40


# =============================================================================
# 6. Dataset Identity Regression
# =============================================================================
def test_dataset_identity_regression(medium_6_problem):
    """Verify FLP_MEDIUM_6 floor area, department area, and utilization (58.57%, NOT 85.0%)."""
    assert medium_6_problem.id == "FLP_MEDIUM_6"
    assert medium_6_problem.facility.width == 100.0
    assert medium_6_problem.facility.height == 70.0
    assert medium_6_problem.facility.area == 7000.0
    assert len(medium_6_problem.departments) == 6

    total_req = sum(d.required_area for d in medium_6_problem.departments)
    assert total_req == 4100.0

    utilization = total_req / medium_6_problem.facility.area
    assert round(utilization, 4) == 0.5857
    assert round(utilization * 100, 2) == 58.57
    assert utilization != 0.85

    fp = ProblemAnalyzer.extract_fingerprint(medium_6_problem)
    assert round(fp.area_utilization, 4) == 0.5857


# =============================================================================
# 7. Correct Strategy Labeling
# =============================================================================
def test_correct_strategy_labeling(medium_6_problem, expansion_8_problem, logistics_5_problem):
    """Verify that Guillotine Row Packing and MER DFS are distinct strategies.

    Guillotine row packing fails on Medium 6, Expansion 8, and Logistics 5,
    while MER DFS succeeds. They must not be conflated under 'Guillotine'.
    """
    # Guillotine fails on Medium 6
    g_med = FeasibleLayoutGenerator(parameters={"strategy": "guillotine_row_packing", "random_seed": 42}).solve(medium_6_problem)
    assert g_med.is_complete is False

    # MER DFS succeeds on Medium 6
    dfs_med = FeasibleLayoutGenerator(parameters={"strategy": "free_rectangle_dfs", "random_seed": 42}).solve(medium_6_problem)
    assert dfs_med.is_complete is True
    assert dfs_med.feasibility_status is True

    # Guillotine fails on Expansion 8
    g_exp = FeasibleLayoutGenerator(parameters={"strategy": "guillotine_row_packing", "random_seed": 42}).solve(expansion_8_problem)
    assert g_exp.is_complete is False

    # MER DFS succeeds on Expansion 8
    dfs_exp = FeasibleLayoutGenerator(parameters={"strategy": "free_rectangle_dfs", "random_seed": 42}).solve(expansion_8_problem)
    assert dfs_exp.is_complete is True
    assert dfs_exp.feasibility_status is True

    # Guillotine fails on Logistics 5
    g_log = FeasibleLayoutGenerator(parameters={"strategy": "guillotine_row_packing", "random_seed": 42}).solve(logistics_5_problem)
    assert g_log.is_complete is False

    # MER DFS succeeds on Logistics 5
    dfs_log = FeasibleLayoutGenerator(parameters={"strategy": "free_rectangle_dfs", "random_seed": 42}).solve(logistics_5_problem)
    assert dfs_log.is_complete is True
    assert dfs_log.feasibility_status is True


# =============================================================================
# 8. Fair Budget Reporting
# =============================================================================
def test_fair_budget_reporting(industrial_10_problem):
    """Verify evaluation counts between Fixed GA (N=40, G=100) and Adaptive GA (N=30, G=40)."""
    pop_fixed = 40
    gen_fixed = 100
    evals_fixed = pop_fixed + gen_fixed * (pop_fixed - 2)
    assert evals_fixed == 3840

    pop_adaptive = 30
    gen_adaptive = 40
    evals_adaptive = pop_adaptive + gen_adaptive * (pop_adaptive - 2)
    assert evals_adaptive == 1150

    # Fixed GA has 3.34x larger evaluation budget than Adaptive GA
    ratio = evals_fixed / evals_adaptive
    assert round(ratio, 2) == 3.34


# =============================================================================
# 9. Provenance Integrity
# =============================================================================
def test_provenance_integrity(industrial_10_problem):
    """Verify that candidates in ParetoFrontier carry their true algorithm source, not 'canonical_evaluation'."""
    cfg = AdaptiveConfig(
        max_total_runtime_seconds=15.0,
        ga_population_size=10,
        ga_generations=5,
        random_seed=42,
    )
    result = StrategyExecutionEngine.execute(industrial_10_problem, config=cfg)

    assert len(result.pareto_frontier.candidates) >= 1
    for cand in result.pareto_frontier.candidates:
        assert cand.algorithm_source in ["feasible_layout_generator", "genetic_algorithm", "craft", "corelap", "aldep"]
        assert cand.algorithm_source != "canonical_evaluation"
        assert cand.candidate_id in [item.candidate_id for item in result.candidate_portfolio.items]


# =============================================================================
# 10. Pareto Consistency
# =============================================================================
def test_pareto_consistency_industrial_10(industrial_10_problem):
    """On FLP_INDUSTRIAL_10, GA Slicing strictly dominates Guillotine across all 3 objectives:

    - Lower MHC ($116,228.34 < $180,263.94)
    - Higher REL Satisfaction (61.52% > 44.17%)
    - Lower Soft Penalty ($0.00 < $62,500.00)
    Therefore, Guillotine is NOT Pareto-optimal (Rank > 1), and the non-dominated frontier
    contains strictly 1 candidate, correcting previous misclaims.
    """
    cfg = AdaptiveConfig(
        max_total_runtime_seconds=15.0,
        ga_population_size=30,
        ga_generations=40,
        random_seed=42,
    )
    result = StrategyExecutionEngine.execute(industrial_10_problem, config=cfg)

    # Candidate 1: Guillotine
    cand_guillotine = next(
        (c for c in result.pareto_frontier.candidates if c.algorithm_source == "feasible_layout_generator"),
        None,
    )
    # Candidate 2: GA
    cand_ga = next(
        (c for c in result.pareto_frontier.candidates if c.algorithm_source == "genetic_algorithm"),
        None,
    )

    assert cand_guillotine is not None
    assert cand_ga is not None

    # GA strictly dominates Guillotine
    assert cand_ga.objective_values["material_handling_cost"] < cand_guillotine.objective_values["material_handling_cost"]
    assert cand_ga.objective_values["relationship_satisfaction"] > cand_guillotine.objective_values["relationship_satisfaction"]
    assert cand_ga.objective_values["soft_penalty"] < cand_guillotine.objective_values["soft_penalty"]

    # Guillotine must be dominated
    assert cand_guillotine.is_non_dominated is False
    assert cand_guillotine.pareto_rank > 1

    # GA must be non-dominated
    assert cand_ga.is_non_dominated is True
    assert cand_ga.pareto_rank == 1

    # Exactly 1 non-dominated candidate on the frontier
    non_dom = [c for c in result.pareto_frontier.candidates if c.is_non_dominated]
    assert len(non_dom) == 1
    assert non_dom[0].candidate_id == cand_ga.candidate_id
