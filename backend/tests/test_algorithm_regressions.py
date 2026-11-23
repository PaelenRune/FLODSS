"""Regression tests for algorithm defects found during the November 2026 code audit.

1. CRAFT reported NO_IMPROVING_SWAP when it actually stopped because max_iterations ran out.
2. ALDEP rounded the grid size up, so the grid (and placements) could extend past the facility.
3. ALDEP's default strip-splitting mode produced overlapping continuous bounding boxes.
"""

import pytest

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


def test_aldep_auto_mode_falls_back_to_splitting_when_rectangular_cannot_fit():
    # 4 x 600 m² in a 60 x 40 m plant = 100% utilization; rectangular strips waste space and leave
    # departments unplaced, so AUTO must fall back to classical splitting and place everything.
    problem = _problem(60.0, 40.0, 600.0)
    rect = create_strip_sweep_layout(problem, DEPT_IDS, ALDEPConfig(allow_strip_splitting=False))
    auto = create_strip_sweep_layout(problem, DEPT_IDS, ALDEPConfig())
    assert rect[3], "precondition: rectangular mode should leave departments unplaced here"
    assert auto[3] == []
    assert len(auto[1].placements) == 4


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
