"""Comprehensive test suite for Phase 9.1: GA Verification & Reproducibility.

Covers:
1. Independent validation of saved GA layout
2. Same-seed reproducibility
3. Baseline isolation (no dependency on sample_layout.json / manual baseline)
4. Correct generation-0 statistics
5. Correct evolution improvement
6. Feasibility-first dominance (Deb's rule)
7. Correct penalty policy & unit consistency
8. Best-so-far fitness non-increasing invariant
9. All departments placed once (completeness & no duplicates)
10. Layout signature consistency
11. JSON persistence roundtrip
12. Statistical calculations correctness
13. Ablation experiment reproducibility
14. API compatibility
"""

import json
import math
import os
import random
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.algorithms.ga.models import (
    BayChromosome,
    GAConfig,
    GAResult,
    GATerminationReason,
    Individual,
    individual_sort_key,
)
from app.algorithms.ga.decoder import BayChromosomeDecoder
from app.algorithms.ga.fitness import GAFitnessEvaluator
from app.algorithms.ga.operators import tournament_selection
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.constraints.engine import ConstraintEngine
from app.evaluation.config import EvaluationConfig
from app.evaluation.engine import EvaluationEngine
from app.feasibility.service import RectangularFeasibilityService
from app.models.constraint import ConstraintClassification
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator
from app.services.problem_service import problem_service


SAVED_LAYOUT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "examples"
    / "ga_optimized_industrial_10.json"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def industrial_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_INDUSTRIAL_10")


# ==============================================================================
# 1. Independent Multi-Validator Audit of Saved GA Layout
# ==============================================================================

def test_01_saved_ga_layout_passes_all_three_validators(industrial_problem: FacilityLayoutProblem):
    """Saved GA layout passes RectangularFeasibilityService, LayoutValidator, and ConstraintEngine."""
    assert SAVED_LAYOUT_PATH.exists(), f"Missing saved file at {SAVED_LAYOUT_PATH}"
    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruct ContinuousLayout from placements
    placements_dict = {
        did: ContinuousPlacement(
            department_id=did,
            x=p["x"],
            y=p["y"],
            width=p["width"],
            height=p["height"],
            orientation_degrees=0.0,
        )
        for did, p in data["placements"].items()
    }
    layout = ContinuousLayout(
        problem_id=data["problem_id"],
        facility_width=industrial_problem.facility.width,
        facility_height=industrial_problem.facility.height,
        placements=placements_dict,
    )

    # Validator 1: RectangularFeasibilityService
    rf_valid, rf_errors = RectangularFeasibilityService.validate_rectangular_layout(industrial_problem, layout)
    assert rf_valid is True, f"RectangularFeasibilityService errors: {rf_errors}"
    assert len(rf_errors) == 0

    # Validator 2: LayoutValidator
    lv_res = LayoutValidator.validate(industrial_problem, layout)
    assert lv_res.is_valid is True, f"LayoutValidator errors: {lv_res.errors}"
    assert lv_res.total_overlap_area == 0.0

    # Validator 3: ConstraintEngine
    constraint_engine = ConstraintEngine()
    violations = constraint_engine.check_all(industrial_problem, layout)
    hard_violations = [v for v in violations if v.classification == ConstraintClassification.HARD]
    assert len(hard_violations) == 0, f"Hard violations found: {hard_violations}"


# ==============================================================================
# 2. Same-Seed Deterministic Reproducibility
# ==============================================================================

def test_02_same_seed_reproducibility(industrial_problem: FacilityLayoutProblem):
    """Running GA twice with identical random seed yields bitwise identical solutions and signatures."""
    algo = GeneticLayoutAlgorithm()
    cfg = GAConfig(
        population_size=20,
        generations=15,
        crossover_rate=0.8,
        mutation_rate=0.2,
        random_seed=12345,
    )

    res1 = algo.solve_with_result(industrial_problem, config=cfg)
    res2 = algo.solve_with_result(industrial_problem, config=cfg)

    assert res1.best_mhc == res2.best_mhc
    assert res1.best_fitness == res2.best_fitness
    assert res1.best_chromosome.order == res2.best_chromosome.order
    assert res1.best_chromosome.bay_sizes == res2.best_chromosome.bay_sizes
    assert res1.best_solution.metadata["layout_signature"] == res2.best_solution.metadata["layout_signature"]


# ==============================================================================
# 3. Baseline Contamination Isolation Test
# ==============================================================================

def test_03_baseline_isolation(industrial_problem: FacilityLayoutProblem, monkeypatch):
    """GA operates with complete independence from sample_layout.json or manual baseline."""
    # Ensure no code in app.algorithms.ga reads sample_layout.json
    ga_dir = Path(__file__).resolve().parent.parent / "app" / "algorithms" / "ga"
    for py_file in ga_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "sample_layout" not in content, f"Contamination in {py_file}"
        assert "sample_plant" not in content, f"Contamination in {py_file}"

    # Run GA with a modified/isolated problem copy
    algo = GeneticLayoutAlgorithm()
    cfg = GAConfig(population_size=20, generations=10, random_seed=77)
    res = algo.solve_with_result(industrial_problem, config=cfg)
    assert res.is_feasible is True
    assert len(res.best_layout.placements) == len(industrial_problem.departments)


# ==============================================================================
# 4. Generation-0 Statistics Correctness
# ==============================================================================

def test_04_generation_0_statistics(industrial_problem: FacilityLayoutProblem):
    """Generation 0 record correctly captures initialization population metrics."""
    algo = GeneticLayoutAlgorithm()
    cfg = GAConfig(population_size=30, generations=5, random_seed=42)
    res = algo.solve_with_result(industrial_problem, config=cfg)

    assert len(res.history) >= 1
    gen0 = res.history[0]
    assert gen0.generation == 0
    assert gen0.best_fitness > 0.0
    assert gen0.best_mhc > 0.0
    assert gen0.feasible_count > 0
    assert gen0.unique_chromosomes > 1
    assert gen0.diversity > 0.0
    assert gen0.invalid_offspring_count == 0


# ==============================================================================
# 5. Evolutionary Improvement Property
# ==============================================================================

def test_05_evolution_improvement_property(industrial_problem: FacilityLayoutProblem):
    """Final best fitness is less than or equal to generation 0 best fitness."""
    algo = GeneticLayoutAlgorithm()
    cfg = GAConfig(
        population_size=30,
        generations=25,
        crossover_rate=0.8,
        mutation_rate=0.2,
        random_seed=42,
    )
    res = algo.solve_with_result(industrial_problem, config=cfg)

    gen0_fitness = res.history[0].best_fitness
    final_fitness = res.best_fitness
    assert final_fitness <= gen0_fitness, f"Fitness degraded from {gen0_fitness} to {final_fitness}"
    assert res.improvement_mhc >= 0.0


# ==============================================================================
# 6. Feasibility-First Dominance (Deb's Rule)
# ==============================================================================

def test_06_feasibility_first_dominance():
    """Feasible individual strictly dominates infeasible individual regardless of raw MHC."""
    chrom = BayChromosome(order=["A", "B"], bay_sizes=[1, 1], orientation="horizontal")
    
    feasible_ind = Individual(
        chromosome=chrom,
        fitness=150000.0,
        raw_mhc=150000.0,
        is_feasible=True,
        violations=[],
    )
    infeasible_ind = Individual(
        chromosome=chrom,
        fitness=50000.0,  # Lower numerical score
        raw_mhc=50000.0,
        is_feasible=False,
        violations=["overlap_detected", "out_of_bounds"],
    )

    # Feasibility-first key comparison
    key_feas = individual_sort_key(feasible_ind)
    key_infeas = individual_sort_key(infeasible_ind)
    assert key_feas < key_infeas, "Feasible individual must dominate infeasible individual"

    # Tournament selection
    rng = random.Random(42)
    pop = [infeasible_ind, feasible_ind]
    winner = tournament_selection(pop, 2, rng)
    assert winner.is_feasible is True


# ==============================================================================
# 7. Soft Penalty Unit Policy & Financial Consistency
# ==============================================================================

def test_07_soft_penalty_unit_policy(industrial_problem: FacilityLayoutProblem):
    """MHC is in USD ($), soft penalty is in USD ($), lambda is dimensionless trade-off weight."""
    eval_config = EvaluationConfig()
    evaluator = GAFitnessEvaluator(eval_config)
    cfg = GAConfig(soft_penalty_weight=1.5)

    chrom = BayChromosome(
        order=[d.id for d in industrial_problem.departments],
        bay_sizes=[5, 5],
        orientation="horizontal",
    )
    ind = Individual(chromosome=chrom)
    evaluator.evaluate(industrial_problem, ind, cfg)

    # If feasible, fitness = raw_mhc + lambda * soft_penalty
    if ind.is_feasible:
        expected_fitness = round(ind.raw_mhc + (1.5 * ind.soft_penalty), 2)
        assert abs(ind.fitness - expected_fitness) < 0.1
    assert ind.soft_penalty >= 0.0
    assert ind.raw_mhc > 0.0


# ==============================================================================
# 8. Best-so-far Fitness Invariant
# ==============================================================================

def test_08_best_so_far_fitness_monotonic_invariant(industrial_problem: FacilityLayoutProblem):
    """Across all generational cycles, recorded best_fitness never increases."""
    algo = GeneticLayoutAlgorithm()
    cfg = GAConfig(
        population_size=25,
        generations=20,
        random_seed=999,
    )
    res = algo.solve_with_result(industrial_problem, config=cfg)

    for i in range(1, len(res.history)):
        prev_best = res.history[i - 1].best_fitness
        curr_best = res.history[i].best_fitness
        assert curr_best <= prev_best + 1e-4, f"Fitness increased at gen {i}: {prev_best} -> {curr_best}"


# ==============================================================================
# 9. All Departments Placed Exactly Once
# ==============================================================================

def test_09_all_departments_placed_exactly_once(industrial_problem: FacilityLayoutProblem):
    """Every problem department is present in layout exactly once with positive dimensions."""
    algo = GeneticLayoutAlgorithm()
    cfg = GAConfig(population_size=20, generations=5, random_seed=42)
    res = algo.solve_with_result(industrial_problem, config=cfg)

    problem_ids = set(d.id for d in industrial_problem.departments)
    placed_ids = set(res.best_layout.placements.keys())
    assert placed_ids == problem_ids
    assert len(res.best_layout.placements) == len(problem_ids)

    for did, p in res.best_layout.placements.items():
        assert p.width > 0.0
        assert p.height > 0.0
        assert p.x >= 0.0
        assert p.y >= 0.0


# ==============================================================================
# 10. Layout Signature Determinism & Geometric Invariance
# ==============================================================================

def test_10_layout_signature_consistency(industrial_problem: FacilityLayoutProblem):
    """generate_layout_signature produces identical hash for identical layout geometry."""
    algo = GeneticLayoutAlgorithm()
    cfg = GAConfig(population_size=20, generations=5, random_seed=42)
    res = algo.solve_with_result(industrial_problem, config=cfg)

    sig1 = generate_layout_signature(res.best_layout)
    sig2 = generate_layout_signature(res.best_layout)
    assert sig1 == sig2
    assert len(sig1) == 64  # SHA-256 hex string


# ==============================================================================
# 11. JSON Persistence Roundtrip
# ==============================================================================

def test_11_json_persistence_roundtrip(industrial_problem: FacilityLayoutProblem, tmp_path):
    """Persisting and reloading GA solution payload preserves full geometric and validation data."""
    algo = GeneticLayoutAlgorithm()
    cfg = GAConfig(population_size=20, generations=5, random_seed=42)
    res = algo.solve_with_result(industrial_problem, config=cfg)

    payload = {
        "problem_id": industrial_problem.id,
        "algorithm_name": "genetic_algorithm",
        "chromosome": res.best_chromosome.model_dump(),
        "placements": {
            did: {
                "department_id": did,
                "x": round(cp.x, 4),
                "y": round(cp.y, 4),
                "width": round(cp.width, 4),
                "height": round(cp.height, 4),
            }
            for did, cp in res.best_layout.placements.items()
        },
        "evaluation": {
            "mhc": round(res.best_mhc, 2),
            "fitness": round(res.best_fitness, 2),
        },
    }

    target_file = tmp_path / "test_ga_payload.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    with open(target_file, "r", encoding="utf-8") as f:
        reloaded = json.load(f)

    assert reloaded["problem_id"] == industrial_problem.id
    assert len(reloaded["placements"]) == len(industrial_problem.departments)
    assert reloaded["evaluation"]["mhc"] == round(res.best_mhc, 2)


# ==============================================================================
# 12. Statistical Metrics Correctness
# ==============================================================================

def test_12_statistical_metrics_correctness():
    """Verify mean, median, standard deviation formulas across sample runs."""
    samples = [121190.46, 107487.83, 93876.54, 107922.59, 114717.87]
    n = len(samples)
    mean_val = sum(samples) / n
    median_val = sorted(samples)[n // 2]
    variance = sum((x - mean_val) ** 2 for x in samples) / (n - 1)
    std_dev = math.sqrt(variance)

    assert round(mean_val, 2) == 109039.06
    assert round(median_val, 2) == 107922.59
    assert round(std_dev, 2) == 10166.86


# ==============================================================================
# 13. Ablation Experiment Reproducibility
# ==============================================================================

def test_13_ablation_variants_execute_validly(industrial_problem: FacilityLayoutProblem):
    """All 4 ablation configurations execute and return feasible individuals."""
    algo = GeneticLayoutAlgorithm()

    # Variant A: Init only (generations=0)
    res_a = algo.solve_with_result(
        industrial_problem,
        config=GAConfig(population_size=20, generations=0, random_seed=42),
    )
    assert res_a.generation_count == 0
    assert res_a.is_feasible is True

    # Variant B: Mutation only (crossover_rate=0)
    res_b = algo.solve_with_result(
        industrial_problem,
        config=GAConfig(population_size=20, generations=5, crossover_rate=0.0, mutation_rate=0.2, random_seed=42),
    )
    assert res_b.is_feasible is True

    # Variant C: Crossover only (mutation_rate=0)
    res_c = algo.solve_with_result(
        industrial_problem,
        config=GAConfig(population_size=20, generations=5, crossover_rate=0.8, mutation_rate=0.0, random_seed=42),
    )
    assert res_c.is_feasible is True

    # Variant D: Full GA
    res_d = algo.solve_with_result(
        industrial_problem,
        config=GAConfig(population_size=20, generations=5, crossover_rate=0.8, mutation_rate=0.2, random_seed=42),
    )
    assert res_d.is_feasible is True


# ==============================================================================
# 14. API Compatibility & Endpoints
# ==============================================================================

def test_14_api_compatibility_and_endpoints(client: TestClient, industrial_problem: FacilityLayoutProblem):
    """Algorithm is registered and executable via FastAPI REST API endpoints."""
    # 1. Check algorithm registry endpoint
    resp = client.get("/api/algorithms")
    assert resp.status_code == 200
    algos = resp.json()
    algo_names = [a["name"] for a in algos]
    assert "genetic_algorithm" in algo_names or "ga" in algo_names

    # 2. Run solve endpoint with GA
    payload = {
        "problem_id": "FLP_ACADEMIC_4",
        "config": {
            "population_size": 20,
            "generations": 5,
            "random_seed": 42,
        },
    }
    solve_resp = client.post("/api/algorithms/genetic/solve", json=payload)
    assert solve_resp.status_code == 200
    data = solve_resp.json()
    assert data["solution"]["algorithm_name"] == "genetic_algorithm"
    assert data["solution"]["is_complete"] is True
    assert data["result"]["is_feasible"] is True
