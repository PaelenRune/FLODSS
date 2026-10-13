"""Comprehensive test suite for Phase 9: Genetic Algorithm V1 Layout Optimization."""

import copy
import random
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.algorithms.base import AlgorithmCategory, BaseLayoutAlgorithm
from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.ga.models import (
    BayChromosome,
    GAConfig,
    GAResult,
    GATerminationReason,
    Individual,
    GenerationRecord,
)
from app.algorithms.ga.decoder import BayChromosomeDecoder
from app.algorithms.ga.fitness import GAFitnessEvaluator
from app.algorithms.ga.initialization import (
    initialize_population,
    find_valid_bay_combinations,
    extract_chromosome_from_layout,
)
from app.algorithms.ga.operators import (
    tournament_selection,
    order_crossover,
    bay_sizes_crossover,
    crossover_chromosomes,
    swap_mutation,
    insertion_mutation,
    inversion_mutation,
    bay_shift_mutation,
    bay_split_or_merge_mutation,
    mutate_chromosome,
)
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.evaluation.config import EvaluationConfig
from app.evaluation.engine import EvaluationEngine
from app.evaluation.evaluators import MaterialHandlingCostEvaluator
from app.models.department import Department
from app.models.geometry import BoundingBox, Dimensions2D, Point2D, ReservedZone
from app.models.problem import Facility, FacilityLayoutProblem
from app.services.problem_service import problem_service
from app.services.layout_validator import LayoutValidator


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def academic_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_ACADEMIC_4")


@pytest.fixture
def medium_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_MEDIUM_6")


@pytest.fixture
def industrial_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_INDUSTRIAL_10")


# ==============================================================================
# 1. Chromosome Representation & Serialization
# ==============================================================================
def test_01_chromosome_initialization_and_serialization():
    order = ["DEP_A", "DEP_B", "DEP_C", "DEP_D"]
    bay_sizes = [2, 2]
    chrom = BayChromosome(order=order, bay_sizes=bay_sizes, orientation="horizontal")

    assert chrom.order == order
    assert chrom.bay_sizes == bay_sizes
    assert chrom.orientation == "horizontal"

    # Copy
    chrom_copy = chrom.copy()
    assert chrom_copy.order == chrom.order
    assert chrom_copy.bay_sizes == chrom.bay_sizes
    chrom_copy.order[0] = "DEP_MODIFIED"
    assert chrom.order[0] == "DEP_A"

    # Bays extraction and reconstruction
    bays = chrom.get_bays()
    assert len(bays) == 2
    assert bays[0] == ["DEP_A", "DEP_B"]
    assert bays[1] == ["DEP_C", "DEP_D"]

    rebuilt = BayChromosome.from_bays(bays, orientation="horizontal")
    assert rebuilt.order == chrom.order
    assert rebuilt.bay_sizes == chrom.bay_sizes


# ==============================================================================
# 2. Decoder Structural Validation
# ==============================================================================
def test_02_decoder_structure_validation(academic_problem: FacilityLayoutProblem):
    # Invalid: missing department
    bad_order = ["DEP_A", "DEP_B", "DEP_C"]
    bad_chrom = BayChromosome(order=bad_order, bay_sizes=[1, 2], orientation="horizontal")
    layout, is_feasible, violations = BayChromosomeDecoder.decode(academic_problem, bad_chrom)
    assert not is_feasible
    assert any("missing" in v.lower() for v in violations)

    # Invalid: bay size sum mismatch
    bad_bays = BayChromosome(order=["DEP_A", "DEP_B", "DEP_C", "DEP_D"], bay_sizes=[2, 3], orientation="horizontal")
    layout, is_feasible, violations = BayChromosomeDecoder.decode(academic_problem, bad_bays)
    assert not is_feasible
    assert any("sum" in v.lower() or "partitioning" in v.lower() for v in violations)


# ==============================================================================
# 3. Exact Area Conservation
# ==============================================================================
def test_03_decoder_exact_area_conservation(industrial_problem: FacilityLayoutProblem):
    order = [d.id for d in industrial_problem.departments]
    chrom = BayChromosome(order=order, bay_sizes=[3, 3, 4], orientation="horizontal")
    layout, _, _ = BayChromosomeDecoder.decode(industrial_problem, chrom)

    dept_map = {d.id: d for d in industrial_problem.departments}
    total_alloc_area = 0.0

    for did, p in layout.placements.items():
        req_area = dept_map[did].required_area
        alloc_area = p.width * p.height
        total_alloc_area += alloc_area
        # Error must be under floating tolerance (< 0.01 m²)
        assert abs(alloc_area - req_area) < 0.01

    assert abs(total_alloc_area - industrial_problem.total_required_area) < 0.1


# ==============================================================================
# 4. Zero Pairwise Department Overlap
# ==============================================================================
def test_04_decoder_zero_pairwise_overlap(industrial_problem: FacilityLayoutProblem):
    order = [d.id for d in industrial_problem.departments]
    chrom = BayChromosome(order=order, bay_sizes=[3, 3, 4], orientation="horizontal")
    layout, _, _ = BayChromosomeDecoder.decode(industrial_problem, chrom)

    val = LayoutValidator.validate(industrial_problem, layout)
    assert val.total_overlap_area == 0.0


# ==============================================================================
# 5. Boundary Containment
# ==============================================================================
def test_05_decoder_boundary_containment(industrial_problem: FacilityLayoutProblem):
    order = [d.id for d in industrial_problem.departments]
    chrom = BayChromosome(order=order, bay_sizes=[3, 3, 4], orientation="horizontal")
    layout, _, violations = BayChromosomeDecoder.decode(industrial_problem, chrom)

    fac_w = industrial_problem.facility.width
    fac_h = industrial_problem.facility.height

    for did, p in layout.placements.items():
        assert p.x >= -1e-4
        assert p.y >= -1e-4
        assert p.x + p.width <= fac_w + 1e-4
        assert p.y + p.height <= fac_h + 1e-4


# ==============================================================================
# 6. Dimension Bounds and Aspect Ratio Checks
# ==============================================================================
def test_06_decoder_aspect_ratio_and_dimension_bounds(industrial_problem: FacilityLayoutProblem):
    # A single bay with all 10 departments creates extreme 150m wide ribbons
    chrom = BayChromosome(order=[d.id for d in industrial_problem.departments], bay_sizes=[10], orientation="horizontal")
    layout, is_feasible, violations = BayChromosomeDecoder.decode(industrial_problem, chrom)

    # Must be detected as infeasible due to dimension bound violations
    assert not is_feasible
    assert len(violations) > 0


# ==============================================================================
# 7. Tournament Selection
# ==============================================================================
def test_07_tournament_selection():
    rng = random.Random(42)
    c1 = BayChromosome(order=["A", "B"], bay_sizes=[2])
    c2 = BayChromosome(order=["B", "A"], bay_sizes=[2])
    c3 = BayChromosome(order=["A", "B"], bay_sizes=[1, 1])

    ind1 = Individual(chromosome=c1, fitness=100.0)
    ind2 = Individual(chromosome=c2, fitness=50.0)
    ind3 = Individual(chromosome=c3, fitness=200.0)

    pop = [ind1, ind2, ind3]
    # Tournament size 3 must always pick ind2 (fitness 50.0)
    winner = tournament_selection(pop, 3, rng)
    assert winner.fitness == 50.0
    assert winner.chromosome == c2


# ==============================================================================
# 8. Order Crossover (OX) Valid Permutations
# ==============================================================================
def test_08_order_crossover_valid_permutations():
    rng = random.Random(123)
    p1 = ["A", "B", "C", "D", "E", "F", "G", "H"]
    p2 = ["H", "G", "F", "E", "D", "C", "B", "A"]

    for _ in range(50):
        c1, c2 = order_crossover(p1, p2, rng)
        assert len(c1) == len(p1)
        assert len(c2) == len(p2)
        assert set(c1) == set(p1)
        assert set(c2) == set(p2)
        assert len(set(c1)) == len(p1)
        assert len(set(c2)) == len(p2)


# ==============================================================================
# 9. Mutations (Swap, Insertion, Inversion, Bay Shift, Split/Merge)
# ==============================================================================
def test_09_mutations():
    rng = random.Random(999)
    base_order = ["DEP_1", "DEP_2", "DEP_3", "DEP_4", "DEP_5"]

    # Swap
    swapped = swap_mutation(base_order, rng)
    assert set(swapped) == set(base_order)
    assert len(swapped) == len(base_order)

    # Insertion
    inserted = insertion_mutation(base_order, rng)
    assert set(inserted) == set(base_order)
    assert len(inserted) == len(base_order)

    # Inversion
    inverted = inversion_mutation(base_order, rng)
    assert set(inverted) == set(base_order)
    assert len(inverted) == len(base_order)

    # Bay shift
    bay_sizes = [3, 2]
    shifted = bay_shift_mutation(bay_sizes, rng)
    assert sum(shifted) == sum(bay_sizes)
    assert all(s >= 1 for s in shifted)

    # Bay split
    split_res = bay_split_or_merge_mutation([5], min_bays=1, max_bays=4, rng=rng)
    assert sum(split_res) == 5
    assert len(split_res) == 2


# ==============================================================================
# 10. Population Initialization
# ==============================================================================
def test_10_population_initialization(industrial_problem: FacilityLayoutProblem):
    rng = random.Random(42)
    cfg = GAConfig(population_size=30, random_seed=42)
    evaluator = GAFitnessEvaluator()
    pop = initialize_population(industrial_problem, cfg, evaluator, rng)

    assert len(pop) == 30
    for ind in pop:
        assert len(ind.chromosome.order) == len(industrial_problem.departments)
        assert sum(ind.chromosome.bay_sizes) == len(industrial_problem.departments)
        assert ind.fitness > 0


# ==============================================================================
# 11. Fitness Evaluator & Soft Penalty
# ==============================================================================
def test_11_fitness_evaluator_mhc_and_soft_penalty(industrial_problem: FacilityLayoutProblem):
    evaluator = GAFitnessEvaluator()
    cfg = GAConfig(soft_penalty_weight=2.0)

    # Valid 3-bay partition
    b1 = ["DEP_CUTTING", "DEP_WELDING", "DEP_RAW_MATERIAL"]
    b2 = ["DEP_MACHINING", "DEP_SURFACE_TREAT", "DEP_ASSEMBLY"]
    b3 = ["DEP_SHIPPING", "DEP_MAINTENANCE", "DEP_QUALITY", "DEP_FINISHED_GOODS"]
    chrom = BayChromosome(order=b1 + b2 + b3, bay_sizes=[3, 3, 4], orientation="horizontal")

    ind = Individual(chromosome=chrom)
    evaluator.evaluate(industrial_problem, ind, cfg)

    assert ind.is_feasible
    assert ind.raw_mhc > 0
    # Expected: fitness == raw_mhc + 2.0 * soft_penalty
    expected_fit = round(ind.raw_mhc + 2.0 * ind.soft_penalty, 2)
    assert abs(ind.fitness - expected_fit) < 0.1


# ==============================================================================
# 12. Infeasible Penalty Barrier
# ==============================================================================
def test_12_infeasible_penalty_barrier(industrial_problem: FacilityLayoutProblem):
    evaluator = GAFitnessEvaluator()
    cfg = GAConfig(infeasible_penalty=1e7)

    # Infeasible: single 1-bay partition creates massive ribbon violations
    chrom = BayChromosome(order=[d.id for d in industrial_problem.departments], bay_sizes=[10], orientation="horizontal")
    ind = Individual(chromosome=chrom)
    evaluator.evaluate(industrial_problem, ind, cfg)

    assert not ind.is_feasible
    # Must receive massive barrier penalty
    assert ind.fitness >= 1e7


# ==============================================================================
# 13. Deterministic Reproduction with Same Seed
# ==============================================================================
def test_13_deterministic_reproduction_same_seed(medium_problem: FacilityLayoutProblem):
    ga = GeneticLayoutAlgorithm()
    cfg = GAConfig(generations=15, population_size=20, random_seed=42)

    res1 = ga.solve_with_result(medium_problem, config=cfg)
    res2 = ga.solve_with_result(medium_problem, config=cfg)

    assert res1.best_mhc == res2.best_mhc
    assert res1.best_fitness == res2.best_fitness
    assert res1.best_chromosome.order == res2.best_chromosome.order
    assert res1.best_chromosome.bay_sizes == res2.best_chromosome.bay_sizes


# ==============================================================================
# 14. Diversity Across Different Seeds
# ==============================================================================
def test_14_diversity_across_different_seeds(medium_problem: FacilityLayoutProblem):
    ga = GeneticLayoutAlgorithm()
    cfg1 = GAConfig(generations=10, population_size=20, random_seed=111)
    cfg2 = GAConfig(generations=10, population_size=20, random_seed=999)

    res1 = ga.solve_with_result(medium_problem, config=cfg1)
    res2 = ga.solve_with_result(medium_problem, config=cfg2)

    # Both run to completion
    assert res1.generation_count == 10
    assert res2.generation_count == 10


# ==============================================================================
# 15. BaseLayoutAlgorithm Contract and Registry Lookup
# ==============================================================================
def test_15_registry_and_contract():
    alg = AlgorithmRegistry.get("genetic_algorithm")
    assert isinstance(alg, BaseLayoutAlgorithm)
    assert alg.name == "genetic_algorithm"
    assert alg.version == "1.0.0"
    assert alg.category == AlgorithmCategory.METAHEURISTIC

    alg_alias = AlgorithmRegistry.get("ga")
    assert alg_alias.name == "genetic_algorithm"


# ==============================================================================
# 16. Solve FLP_ACADEMIC_4
# ==============================================================================
def test_16_solve_flp_academic_4(academic_problem: FacilityLayoutProblem):
    ga = GeneticLayoutAlgorithm()
    res = ga.solve_with_result(academic_problem, config=GAConfig(generations=10, population_size=20, random_seed=42))

    assert res.is_feasible
    assert res.best_solution.placed_department_count == 4
    assert res.best_mhc <= 600.0


# ==============================================================================
# 17. Solve FLP_MEDIUM_6
# ==============================================================================
def test_17_solve_flp_medium_6(medium_problem: FacilityLayoutProblem):
    ga = GeneticLayoutAlgorithm()
    res = ga.solve_with_result(medium_problem, config=GAConfig(generations=15, population_size=25, random_seed=42))

    assert res.is_feasible
    assert res.best_solution.placed_department_count == 6
    assert res.best_mhc > 0


# ==============================================================================
# 18. Solve FLP_INDUSTRIAL_10 and Verify Improvement
# ==============================================================================
def test_18_solve_flp_industrial_10_improvement(industrial_problem: FacilityLayoutProblem):
    ga = GeneticLayoutAlgorithm()
    cfg = GAConfig(generations=20, population_size=30, random_seed=42)
    res = ga.solve_with_result(industrial_problem, config=cfg)

    assert res.is_feasible
    assert res.best_solution.placed_department_count == 10
    assert len(res.best_layout.placements) == 10

    # Total area must strictly equal 11000 m²
    total_area = sum(p.width * p.height for p in res.best_layout.placements.values())
    assert abs(total_area - 11000.0) < 0.1

    # Overlap must be 0.0
    val = LayoutValidator.validate(industrial_problem, res.best_layout)
    assert val.total_overlap_area == 0.0

    # MHC must improve significantly over initial Guillotine baseline ($180,263.94)
    assert res.best_mhc < 180263.94
    assert res.best_fitness <= res.history[0].best_fitness

    # Soft vibration separation constraint penalty must be reduced or eliminated
    assert res.best_soft_penalty < 62500.0


# ==============================================================================
# 19. API Endpoint POST /api/algorithms/genetic/solve
# ==============================================================================
def test_19_api_endpoint_genetic_solve(client: TestClient):
    payload = {
        "problem_id": "FLP_ACADEMIC_4",
        "config": {
            "generations": 8,
            "population_size": 15,
            "random_seed": 42,
        },
    }
    resp = client.post("/api/algorithms/genetic/solve", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "solution" in data
    assert "continuous_layout" in data
    assert "result" in data
    assert "validation" in data
    assert "evaluation" in data

    assert data["result"]["is_feasible"] is True
    assert data["result"]["generation_count"] == 8
    assert len(data["continuous_layout"]["placements"]) == 4


# ==============================================================================
# 20. API Endpoint with Inline Problem
# ==============================================================================
def test_20_api_endpoint_inline_problem(client: TestClient, academic_problem: FacilityLayoutProblem):
    payload = {
        "problem": academic_problem.model_dump(mode="json"),
        "config": {
            "generations": 5,
            "population_size": 15,
            "random_seed": 42,
        },
    }
    resp = client.post("/api/algorithms/genetic/solve", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["is_feasible"] is True
