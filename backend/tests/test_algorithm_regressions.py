"""Regression tests for algorithm defects found during the November 2026 code audit.

1. CRAFT reported NO_IMPROVING_SWAP when it actually stopped because max_iterations ran out.
2. ALDEP rounded the grid size up, so the grid (and placements) could extend past the facility.
3. ALDEP's default strip-splitting mode produced overlapping continuous bounding boxes.
4. ALDEP's rectangular mode consumed the strip cursor on a misfit, leaving later departments unplaced,
   and ignored department shape limits when choosing the block span.
"""

import math
import random

import pytest

from app.algorithms.ga.decoder import BayChromosomeDecoder
from app.algorithms.ga.fitness import GAFitnessEvaluator
from app.algorithms.ga.initialization import initialize_population
from app.algorithms.ga.models import BayChromosome, GAConfig
from app.algorithms.ga.operators import mutate_chromosome
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.evaluation.engine import EvaluationEngine
from app.models.geometry import BoundingBox, Point2D
from app.models.department import Department
from app.models.facility import Facility
from app.models.flow import Flow
from app.models.problem import FacilityLayoutProblem
from app.models.relationship import ClosenessRating, Relationship
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.algorithms.aldep.config import ALDEPConfig
from app.algorithms.aldep.placement import create_strip_sweep_layout
from app.algorithms.aldep.solver import ALDEPAlgorithm
from app.algorithms.craft.models import CRAFTTerminationReason
from app.algorithms.craft.solver import CRAFTAlgorithm
from app.services.layout_validator import LayoutValidator

DEPT_IDS = ["DEP_A", "DEP_B", "DEP_C", "DEP_D"]


def _problem(width: float, height: float, area: float) -> FacilityLayoutProblem:
    return FacilityLayoutProblem(
        id="REGRESSION_4",
        name="Regression 4-department problem",
        facility=Facility(id="FAC", name="Plant", width=width, height=height, area=width * height),
        departments=[Department(id=d, name=d, required_area=area) for d in DEPT_IDS],
        relationships=[
            Relationship(department_a="DEP_A", department_b="DEP_B", relationship_type=ClosenessRating.A),
            Relationship(department_a="DEP_A", department_b="DEP_C", relationship_type=ClosenessRating.E),
            Relationship(department_a="DEP_B", department_b="DEP_C", relationship_type=ClosenessRating.I),
        ],
        flows=[
            Flow(source_department="DEP_A", target_department="DEP_B", quantity=50.0),
            Flow(source_department="DEP_B", target_department="DEP_C", quantity=30.0),
            Flow(source_department="DEP_C", target_department="DEP_D", quantity=10.0),
        ],
    )


def _row_layout(problem: FacilityLayoutProblem, order) -> ContinuousLayout:
    return ContinuousLayout(
        problem_id=problem.id,
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
        placements={
            d: ContinuousPlacement(department_id=d, x=10.0 * i, y=0.0, width=10.0, height=10.0)
            for i, d in enumerate(order)
        },
    )


# ---------------------------------------------------------------------------
# CRAFT
# ---------------------------------------------------------------------------

def test_craft_reports_max_iterations_when_budget_exhausted():
    problem = _problem(120.0, 120.0, 100.0)
    layout = _row_layout(problem, ["DEP_A", "DEP_C", "DEP_D", "DEP_B"])  # needs 2 swaps to converge

    _, full = CRAFTAlgorithm().solve_with_result(problem, layout, max_iterations=50)
    assert len(full.accepted_swaps) >= 2
    assert full.termination_reason == CRAFTTerminationReason.NO_IMPROVING_SWAP.value

    _, limited = CRAFTAlgorithm().solve_with_result(problem, layout, max_iterations=1)
    assert len(limited.accepted_swaps) == 1
    assert limited.final_mhc > full.final_mhc  # stopped early, better layouts still exist
    assert limited.termination_reason == CRAFTTerminationReason.MAX_ITERATIONS_REACHED.value


def test_craft_converged_run_within_budget_is_not_max_iterations():
    problem = _problem(120.0, 120.0, 100.0)
    layout = _row_layout(problem, ["DEP_A", "DEP_C", "DEP_D", "DEP_B"])
    # Exactly enough iterations for the 2 swaps plus the confirming non-improving pass
    _, res = CRAFTAlgorithm().solve_with_result(problem, layout, max_iterations=3)
    assert res.termination_reason == CRAFTTerminationReason.NO_IMPROVING_SWAP.value


# ---------------------------------------------------------------------------
# ALDEP
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("width,height,cell", [(48.0, 48.0, 5.0), (47.0, 33.0, 5.0), (50.0, 50.0, 5.0)])
def test_aldep_grid_never_exceeds_facility(width, height, cell):
    problem = _problem(width, height, 150.0)
    config = ALDEPConfig(cell_size=cell)
    grid, layout, _, _ = create_strip_sweep_layout(problem, DEPT_IDS, config)

    assert grid.columns * cell <= width + 1e-9
    assert grid.rows * cell <= height + 1e-9
    for p in layout.placements.values():
        assert p.x + p.width <= width + 1e-6
        assert p.y + p.height <= height + 1e-6


def test_aldep_exact_multiple_keeps_full_grid():
    problem = _problem(50.0, 50.0, 100.0)
    grid, _, _, _ = create_strip_sweep_layout(problem, DEPT_IDS, ALDEPConfig(cell_size=5.0))
    assert grid.columns == 10 and grid.rows == 10


def test_aldep_default_auto_mode_prefers_rectangular_and_overlap_free():
    assert ALDEPConfig().allow_strip_splitting is None  # AUTO

    # 75 m² = 3 cells of 5 m; with a 2-cell strip the classical mode produces overlapping boxes.
    problem = _problem(120.0, 120.0, 75.0)
    _, result = ALDEPAlgorithm().solve_with_result(problem, number_of_candidates=5)
    best = result.best_candidate

    validation = LayoutValidator.validate(problem, best.continuous_layout)
    assert validation.is_valid, validation.errors
    assert best.is_feasible
    assert not best.unplaced_departments


def test_aldep_rectangular_mode_packs_full_utilization_without_overlap():
    # 4 x 600 m² in a 60 x 40 m plant = 100% utilization. The old strip cursor wasted space and left
    # departments unplaced; multi-strip first-fit blocks now place all four as clean rectangles.
    problem = _problem(60.0, 40.0, 600.0)
    _, layout, _, unplaced = create_strip_sweep_layout(
        problem, DEPT_IDS, ALDEPConfig(allow_strip_splitting=False)
    )
    assert unplaced == []
    assert len(layout.placements) == 4
    validation = LayoutValidator.validate(problem, layout)
    assert validation.is_valid, validation.errors


def test_aldep_rectangular_mode_does_not_skip_later_departments_after_a_misfit():
    # One department is too big for the plant: it must be reported unplaced, but the cursor must not
    # be consumed, so every department after it is still placed.
    problem = _problem(60.0, 40.0, 300.0)
    problem.departments[1].required_area = 5000.0  # DEP_B cannot fit anywhere
    _, layout, _, unplaced = create_strip_sweep_layout(
        problem, DEPT_IDS, ALDEPConfig(allow_strip_splitting=False)
    )
    assert unplaced == ["DEP_B"]
    assert set(layout.placements) == {"DEP_A", "DEP_C", "DEP_D"}


def test_aldep_rectangular_blocks_prefer_spans_that_respect_shape_limits():
    # A 600 m² department limited to aspect ratio 2 must not become a 1-strip ribbon (60 x 10 m).
    problem = _problem(60.0, 40.0, 300.0)
    problem.departments[0].required_area = 600.0
    problem.departments[0].max_aspect_ratio = 2.0
    _, layout, _, unplaced = create_strip_sweep_layout(
        problem, DEPT_IDS, ALDEPConfig(allow_strip_splitting=False)
    )
    assert unplaced == []
    p = layout.placements["DEP_A"]
    assert max(p.width, p.height) / min(p.width, p.height) <= 2.0 + 1e-6


def test_aldep_fixed_department_respects_width_limits():
    problem = _problem(60.0, 40.0, 300.0)
    problem.departments[0].fixed_position = Point2D(x=0.0, y=0.0)
    problem.departments[0].max_width = 10.0
    _, layout, _, _ = create_strip_sweep_layout(problem, DEPT_IDS, ALDEPConfig(allow_strip_splitting=False))
    assert layout.placements["DEP_A"].width <= 10.0 + 1e-6


# ---------------------------------------------------------------------------
# GA
# ---------------------------------------------------------------------------

def _square_problem() -> FacilityLayoutProblem:
    return _problem(20.0, 20.0, 100.0)


def test_ga_decoder_mirrors_layout_to_reach_fixed_corner():
    # DEP_A is fixed at the top-right corner; the bay structure grows from bottom-left, so only a
    # mirrored decode can satisfy it.
    problem = _square_problem()
    problem.departments[0].fixed_position = Point2D(x=10.0, y=10.0)
    layout, feasible, violations = BayChromosomeDecoder.decode(
        problem, BayChromosome(order=DEPT_IDS, bay_sizes=[2, 2]), tolerance=1e-3
    )
    a = layout.placements["DEP_A"]
    assert (round(a.x, 3), round(a.y, 3)) == (10.0, 10.0)
    assert feasible, violations
    assert LayoutValidator.validate(problem, layout).is_valid


def test_ga_auto_orientation_seeds_both_orientations_and_can_mutate():
    problem = _square_problem()
    config = GAConfig(orientation="auto", population_size=20, random_seed=1)
    pop = initialize_population(problem, config, GAFitnessEvaluator(), random.Random(1))
    assert {ind.chromosome.orientation for ind in pop} == {"horizontal", "vertical"}

    rng = random.Random(3)
    chrom = BayChromosome(order=DEPT_IDS, bay_sizes=[2, 2], orientation="horizontal")
    flipped = {mutate_chromosome(chrom, 1.0, config, rng).orientation for _ in range(200)}
    assert flipped == {"horizontal", "vertical"}

    fixed_cfg = GAConfig(orientation="horizontal")
    assert {mutate_chromosome(chrom, 1.0, fixed_cfg, rng).orientation for _ in range(200)} == {"horizontal"}


def test_ga_result_values_are_always_finite():
    problem = _square_problem()
    result = GeneticLayoutAlgorithm().solve_with_result(
        problem, population_size=10, generations=3, random_seed=7, max_runtime_seconds=5.0
    )
    for key, value in result.best_solution.objective_values.items():
        assert math.isfinite(value), key
    assert math.isfinite(result.initial_mhc) and math.isfinite(result.improvement_percentage)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def test_explicit_zero_relationship_score_is_respected():
    problem = _square_problem()
    problem.relationships[0].score = 0.0  # A-B rated 'A' but deliberately weighted 0
    layout = _row_layout(problem, DEPT_IDS)
    report = EvaluationEngine().evaluate(problem, layout)
    baseline = _square_problem()
    assert report.objective_values["relationship_score"] < EvaluationEngine().evaluate(
        baseline, _row_layout(baseline, DEPT_IDS)
    ).objective_values["relationship_score"]


def test_overlapping_reserved_zones_are_not_double_counted():
    from app.evaluation.evaluators import _union_area_in_facility
    boxes = [BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10), BoundingBox(x_min=5, y_min=0, x_max=15, y_max=10),
             BoundingBox(x_min=-5, y_min=15, x_max=5, y_max=25)]
    # union of first two = 150; third clipped to the 20 x 20 facility = 5 x 5 = 25
    assert _union_area_in_facility(boxes, 20.0, 20.0) == pytest.approx(175.0)


def test_pre_feasibility_subtracts_reserved_zones():
    from app.algorithms.generator.pre_feasibility import PreFeasibilityAnalyzer
    from app.models.geometry import ReservedZone
    # 4 x 100 m² = 400 m² fits a 20 x 20 plant, but not once a 10 x 20 m keep-out zone is removed.
    problem = _square_problem()
    assert PreFeasibilityAnalyzer.analyze(problem).is_feasible
    problem.facility.reserved_zones = [
        ReservedZone(id="RZ", name="Aisle", bounding_box=BoundingBox(x_min=0, y_min=0, x_max=10, y_max=20))
    ]
    report = PreFeasibilityAnalyzer.analyze(problem)
    assert not report.is_feasible
    assert report.facility_available_area == pytest.approx(200.0)


def test_aldep_classical_mode_still_available_and_flagged():
    problem = _problem(120.0, 120.0, 75.0)
    _, result = ALDEPAlgorithm().solve_with_result(
        problem, number_of_candidates=1, allow_strip_splitting=True
    )
    cand = result.best_candidate
    # Classical serpentine blocks are non-rectangular; their bounding boxes overlap and are reported.
    assert cand.is_complete
    assert not cand.is_feasible
    assert cand.termination_reason == "COMPLETE_WITH_GEOMETRIC_WARNINGS"
