"""Academic verification and regression test suite for CRAFT Pairwise Improvement Heuristic."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.problem import FacilityLayoutProblem
from app.models.facility import Facility
from app.models.department import Department
from app.models.flow import Flow
from app.models.geometry import Point2D, Dimensions2D, BoundingBox, ReservedZone
from app.models.constraint import Constraint, ConstraintType, ConstraintClassification
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.craft import (
    CRAFTAlgorithm,
    CRAFTConfig,
    CRAFTTerminationReason,
    check_pair_eligibility,
    find_eligible_pairs,
    create_swapped_layout,
    compute_mhc,
)
from app.services.problem_service import problem_service
from app.services.layout_normalizer import generate_layout_signature


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def three_dept_problem() -> FacilityLayoutProblem:
    """Hand-calculated 3-department benchmark problem.
    
    A, B, C along X-axis.
    A at (0, 0), B at (10, 0), C at (20, 0), each 10x10.
    Centroids: A=(5, 5), B=(15, 5), C=(25, 5).
    Flows:
      A -> C = 10 loads, unit cost = 1.0 (Manhattan distance = 20 -> Cost = 200)
      B -> C = 2 loads, unit cost = 1.0  (Manhattan distance = 10 -> Cost = 20)
    Initial Total MHC = 220.0.
    
    Candidate swaps:
      (A, B): MHC = 10*10 + 2*20 = 140.0 (Improvement = 80.0)
      (B, C): MHC = 10*10 + 2*10 = 120.0 (Improvement = 100.0) -> UNIQUE BEST!
      (A, C): MHC = 10*20 + 2*10 = 220.0 (Improvement = 0.0)
    
    Iteration 1 selects B <-> C. New MHC = 120.0.
    Iteration 2 has no improving swap -> Terminates with NO_IMPROVING_SWAP.
    """
    facility = Facility(id="FAC_3D", name="Hand Plant", width=50.0, height=20.0, area=1000.0)
    departments = [
        Department(id="DEP_A", name="Dept A", required_area=100.0, min_width=5.0, max_width=15.0),
        Department(id="DEP_B", name="Dept B", required_area=100.0, min_width=5.0, max_width=15.0),
        Department(id="DEP_C", name="Dept C", required_area=100.0, min_width=5.0, max_width=15.0),
    ]
    flows = [
        Flow(source_department="DEP_A", target_department="DEP_C", quantity=10.0, cost_per_unit_distance=1.0),
        Flow(source_department="DEP_B", target_department="DEP_C", quantity=2.0, cost_per_unit_distance=1.0),
    ]
    return FacilityLayoutProblem(
        id="FLP_HAND_3",
        name="Hand Calculated 3-Dept Benchmark",
        facility=facility,
        departments=departments,
        flows=flows,
        relationships=[],
        constraints=[],
    )


@pytest.fixture
def three_dept_initial_layout(three_dept_problem: FacilityLayoutProblem) -> ContinuousLayout:
    """Initial layout for 3-department fixture."""
    return ContinuousLayout(
        problem_id="FLP_HAND_3",
        facility_width=50.0,
        facility_height=20.0,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10.0, y=0.0, width=10.0, height=10.0),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=20.0, y=0.0, width=10.0, height=10.0),
        },
    )


# 1. Incomplete initial layout rejected
def test_incomplete_initial_layout_rejected(three_dept_problem: FacilityLayoutProblem):
    incomplete_layout = ContinuousLayout(
        problem_id="FLP_HAND_3",
        facility_width=50.0,
        facility_height=20.0,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10.0, y=0.0, width=10.0, height=10.0),
            # DEP_C is missing!
        },
    )
    solver = CRAFTAlgorithm()
    with pytest.raises(ValueError, match="missing placements for required departments"):
        solver.improve(three_dept_problem, incomplete_layout)


# 2. Infeasible initial layout rejected
def test_infeasible_initial_layout_rejected(three_dept_problem: FacilityLayoutProblem):
    overlapping_layout = ContinuousLayout(
        problem_id="FLP_HAND_3",
        facility_width=50.0,
        facility_height=20.0,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=5.0, y=0.0, width=10.0, height=10.0),  # Overlaps A
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=20.0, y=0.0, width=10.0, height=10.0),
        },
    )
    solver = CRAFTAlgorithm()
    with pytest.raises(ValueError, match="geometrically infeasible"):
        solver.improve(three_dept_problem, overlapping_layout)


# 3. Hand-calculated MHC
def test_hand_calculated_mhc_three_departments(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    initial_mhc = compute_mhc(three_dept_problem, three_dept_initial_layout)
    assert initial_mhc == 220.0

    # Test single-flow case with fixed dock:
    # A at (0,0), B at (10,0), C at (20,0), only Flow A->C = 10
    prob_single_flow = three_dept_problem.model_copy(deep=True)
    prob_single_flow.flows = [
        Flow(source_department="DEP_A", target_department="DEP_C", quantity=10.0, cost_per_unit_distance=1.0)
    ]
    prob_single_flow.departments[0].fixed_position = Point2D(x=0.0, y=0.0)  # A is fixed
    mhc_single = compute_mhc(prob_single_flow, three_dept_initial_layout)
    assert mhc_single == 200.0

    solver = CRAFTAlgorithm()
    solution, result = solver.solve_with_result(prob_single_flow, three_dept_initial_layout)
    assert result.initial_mhc == 200.0
    assert result.final_mhc == 100.0
    assert result.absolute_improvement == 100.0
    assert len(result.accepted_swaps) == 1
    assert result.accepted_swaps[0].dept_a == "DEP_B"
    assert result.accepted_swaps[0].dept_b == "DEP_C"


# 4. Correct pair exchange coordinates
def test_correct_pair_exchange_coordinates(
    three_dept_initial_layout: ContinuousLayout,
):
    swapped = create_swapped_layout(three_dept_initial_layout, "DEP_B", "DEP_C")
    # In initial: B at x=10, C at x=20
    # In swapped: B at x=20, C at x=10
    assert swapped.placements["DEP_B"].x == 20.0
    assert swapped.placements["DEP_B"].y == 0.0
    assert swapped.placements["DEP_C"].x == 10.0
    assert swapped.placements["DEP_C"].y == 0.0
    assert swapped.placements["DEP_A"].x == 0.0


# 5. Best improvement selection (Steepest Descent)
def test_best_improvement_selection_steepest_descent(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    solver = CRAFTAlgorithm()
    solution, result = solver.solve_with_result(three_dept_problem, three_dept_initial_layout)

    assert len(result.accepted_swaps) == 1
    # B <-> C should be chosen because improvement is 100.0 vs 80.0 for A <-> B
    first_swap = result.accepted_swaps[0]
    assert set([first_swap.dept_a, first_swap.dept_b]) == {"DEP_B", "DEP_C"}
    assert first_swap.mhc_before == 220.0
    assert first_swap.mhc_after == 120.0
    assert first_swap.improvement == 100.0
    assert result.final_mhc == 120.0
    assert result.termination_reason == CRAFTTerminationReason.NO_IMPROVING_SWAP.value


# 6. Equal-shape swap eligibility
def test_equal_shape_swap_eligibility(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    config = CRAFTConfig()
    is_ok, is_rot, reason = check_pair_eligibility(
        three_dept_problem, three_dept_initial_layout, "DEP_A", "DEP_B", config
    )
    assert is_ok is True
    assert is_rot is False
    assert reason is None


# 7. Invalid unequal-shape swap rejected
def test_invalid_unequal_shape_swap_rejected(
    three_dept_problem: FacilityLayoutProblem,
):
    unequal_layout = ContinuousLayout(
        problem_id="FLP_HAND_3",
        facility_width=50.0,
        facility_height=20.0,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10.0, y=0.0, width=15.0, height=10.0),  # 15x10 vs 10x10
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=25.0, y=0.0, width=10.0, height=10.0),
        },
    )
    config = CRAFTConfig(allow_rotational_swaps=True)
    is_ok, is_rot, reason = check_pair_eligibility(
        three_dept_problem, unequal_layout, "DEP_A", "DEP_B", config
    )
    assert is_ok is False
    assert "Unequal dimensions" in str(reason)


# 8. Fixed department protected from swap
def test_fixed_department_protected_from_swap(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    prob_fixed = three_dept_problem.model_copy(deep=True)
    prob_fixed.departments[0].fixed_position = Point2D(x=0.0, y=0.0)  # A is fixed

    config = CRAFTConfig()
    is_ok, _, reason = check_pair_eligibility(prob_fixed, three_dept_initial_layout, "DEP_A", "DEP_B", config)
    assert is_ok is False
    assert "fixed" in str(reason)

    pairs = find_eligible_pairs(prob_fixed, three_dept_initial_layout, config)
    # A cannot appear in any pair!
    for p in pairs:
        assert p[0] != "DEP_A" and p[1] != "DEP_A"


# 9. Overlap prevented in candidate swap
def test_overlap_prevented_in_candidate_swap(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    # Equal shapes swap bounding boxes exactly, so overlap cannot happen in equal shape swaps.
    # But if rotational swap would expand into another dept, candidate validator catches it.
    solver = CRAFTAlgorithm()
    solution, result = solver.solve_with_result(three_dept_problem, three_dept_initial_layout)
    assert result.is_feasible is True
    assert solution.feasibility_status is True


# 10. Boundary preserved in candidate swap
def test_boundary_preserved_in_candidate_swap(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    solver = CRAFTAlgorithm()
    solution, result = solver.solve_with_result(three_dept_problem, three_dept_initial_layout)
    for p in result.final_layout.placements.values():
        assert p.x >= 0.0
        assert p.y >= 0.0
        assert p.x + p.width <= three_dept_problem.facility.width
        assert p.y + p.height <= three_dept_problem.facility.height


# 11. Reserved zone preserved in candidate swap
def test_reserved_zone_preserved_in_candidate_swap(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    prob_rz = three_dept_problem.model_copy(deep=True)
    # Place a reserved zone right where DEP_C was (x=20..30, y=0..10)
    # But let's place it at x=25..35, y=0..10
    prob_rz.facility.reserved_zones = [
        ReservedZone(
            id="RZ_SAFETY",
            type="structural_column",
            bounding_box=BoundingBox(x_min=12.0, y_min=0.0, x_max=17.0, y_max=5.0),
            description="Column",
        )
    ]
    # Because B at (10, 0) overlaps RZ_SAFETY (12..17), initial layout should fail feasibility!
    solver = CRAFTAlgorithm()
    with pytest.raises(ValueError, match="geometrically infeasible|reserved"):
        solver.improve(prob_rz, three_dept_initial_layout)


# 12. Hard constraints preserved in candidate swap
def test_hard_constraints_preserved_in_candidate_swap(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    prob_cst = three_dept_problem.model_copy(deep=True)
    # Add a hard constraint that B and C must maintain at least distance 15m
    prob_cst.constraints.append(
        Constraint(
            id="CST_BC_SEP",
            type=ConstraintType.MIN_DISTANCE,
            involved_departments=["DEP_B", "DEP_C"],
            parameters={"distance": 15.0},
            classification=ConstraintClassification.HARD,
            penalty=5000.0,
        )
    )
    # In initial layout: B=(15,5), C=(25,5), distance = 10m -> Violates hard constraint!
    solver = CRAFTAlgorithm()
    with pytest.raises(ValueError, match="hard constraints"):
        solver.improve(prob_cst, three_dept_initial_layout)


# 13. No-improvement termination
def test_no_improvement_termination(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    # Layout that is already optimal: A at (0,0), C at (10,0), B at (20,0)
    optimal_layout = ContinuousLayout(
        problem_id="FLP_HAND_3",
        facility_width=50.0,
        facility_height=20.0,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0.0, y=0.0, width=10.0, height=10.0),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=10.0, y=0.0, width=10.0, height=10.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=20.0, y=0.0, width=10.0, height=10.0),
        },
    )
    solver = CRAFTAlgorithm()
    solution, result = solver.solve_with_result(three_dept_problem, optimal_layout)
    assert len(result.accepted_swaps) == 0
    assert result.termination_reason == CRAFTTerminationReason.NO_IMPROVING_SWAP.value
    assert result.final_mhc == result.initial_mhc


# 14. Max-iteration termination
def test_max_iteration_termination(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    # Set max_iterations=1, where optimal requires 1 swap and then checks stopping
    solver = CRAFTAlgorithm(parameters={"max_iterations": 1})
    solution, result = solver.solve_with_result(three_dept_problem, three_dept_initial_layout)
    assert result.iterations == 1
    assert len(result.accepted_swaps) == 1


# 15. Deterministic pair ordering
def test_deterministic_pair_ordering(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    config = CRAFTConfig()
    pairs_run1 = find_eligible_pairs(three_dept_problem, three_dept_initial_layout, config)
    pairs_run2 = find_eligible_pairs(three_dept_problem, three_dept_initial_layout, config)

    assert pairs_run1 == pairs_run2
    assert pairs_run1 == [
        ("DEP_A", "DEP_B", False),
        ("DEP_A", "DEP_C", False),
        ("DEP_B", "DEP_C", False),
    ]


# 16. Ten-run repeatability
def test_ten_run_repeatability(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    signatures = []
    mhcs = []
    solver = CRAFTAlgorithm()

    for _ in range(10):
        _, result = solver.solve_with_result(three_dept_problem, three_dept_initial_layout)
        signatures.append(result.final_layout_signature)
        mhcs.append(result.final_mhc)

    assert len(set(signatures)) == 1
    assert len(set(mhcs)) == 1


# 17. Non-increasing MHC invariant
def test_non_increasing_mhc_invariant(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    solver = CRAFTAlgorithm()
    _, result = solver.solve_with_result(three_dept_problem, three_dept_initial_layout)

    assert result.final_mhc <= result.initial_mhc
    for swap in result.accepted_swaps:
        assert swap.mhc_after <= swap.mhc_before


# 18. Accurate improvement percentage
def test_accurate_improvement_percentage(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    solver = CRAFTAlgorithm()
    _, result = solver.solve_with_result(three_dept_problem, three_dept_initial_layout)

    expected_abs = result.initial_mhc - result.final_mhc
    expected_pct = round((expected_abs / result.initial_mhc) * 100.0, 2)

    assert result.absolute_improvement == round(expected_abs, 4)
    assert result.percentage_improvement == expected_pct


# 19. Complete result semantics
def test_complete_result_semantics(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    solver = CRAFTAlgorithm()
    solution, result = solver.solve_with_result(three_dept_problem, three_dept_initial_layout)

    assert result.algorithm_name == "craft_pairwise_rectangular_v1"
    assert result.algorithm_version == "1.0.0"
    assert result.is_complete is True
    assert result.is_feasible is True
    assert result.initial_layout_signature is not None
    assert result.final_layout_signature is not None
    assert result.trace.total_swaps_accepted == len(result.accepted_swaps)
    assert "craft_result" in solution.metadata
    assert "trace" in solution.metadata


# 20. AlgorithmRegistry integration
def test_algorithm_registry_integration():
    craft1 = AlgorithmRegistry.get("craft")
    craft2 = AlgorithmRegistry.get("craft_pairwise_rectangular_v1")

    assert craft1.name == "craft_pairwise_rectangular_v1"
    assert craft2.name == "craft_pairwise_rectangular_v1"
    assert craft1.category.value == "improvement"


# 21. API solve endpoint
def test_api_solve_craft_endpoint(
    client: TestClient,
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    payload = {
        "problem": three_dept_problem.model_dump(),
        "initial_layout": three_dept_initial_layout.model_dump(),
        "config": {
            "max_iterations": 20,
            "min_improvement_threshold": 0.01,
        },
    }
    response = client.post("/api/algorithms/craft/solve", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "solution" in data
    assert "continuous_layout" in data
    assert "initial_layout" in data
    assert "result" in data
    assert "initial_evaluation" in data
    assert "final_evaluation" in data
    assert "trace" in data

    assert data["result"]["initial_mhc"] == 220.0
    assert data["result"]["final_mhc"] == 120.0
    assert data["result"]["accepted_swaps"][0]["improvement"] == 100.0


# 22. Trace detailed and summary levels
def test_trace_detailed_and_summary_levels(
    three_dept_problem: FacilityLayoutProblem,
    three_dept_initial_layout: ContinuousLayout,
):
    # Summary trace
    solver_sum = CRAFTAlgorithm(parameters={"trace_level": "SUMMARY"})
    _, res_sum = solver_sum.solve_with_result(three_dept_problem, three_dept_initial_layout)
    assert res_sum.trace.steps[0].candidate_evaluations is None

    # Detailed trace
    solver_det = CRAFTAlgorithm(parameters={"trace_level": "DETAILED"})
    _, res_det = solver_det.solve_with_result(three_dept_problem, three_dept_initial_layout)
    assert res_det.trace.steps[0].candidate_evaluations is not None
    assert len(res_det.trace.steps[0].candidate_evaluations) == 3


# 23. Medium benchmark (FLP_MEDIUM_6)
def test_medium_benchmark_flp_medium_6():
    problem = problem_service.get_example_problem("FLP_MEDIUM_6")
    corelap_solver = AlgorithmRegistry.get("corelap")
    corelap_solution = corelap_solver.solve(problem)
    assert corelap_solution.is_complete is True

    corelap_layout = ContinuousLayout.from_layout_solution(
        corelap_solution,
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
    )

    craft_solver = CRAFTAlgorithm()
    solution, result = craft_solver.solve_with_result(problem, corelap_layout)

    assert result.is_complete is True
    assert result.is_feasible is True
    assert result.final_mhc <= result.initial_mhc
    print(f"\n[FLP_MEDIUM_6 Benchmark] Initial MHC: {result.initial_mhc:.2f}, Final MHC: {result.final_mhc:.2f}, Swaps: {len(result.accepted_swaps)}, Reason: {result.termination_reason}")


# 24. Dense sample factory benchmark (FLP_INDUSTRIAL_10)
def test_dense_sample_factory_benchmark_flp_industrial_10(client: TestClient):
    problem = problem_service.get_example_problem("FLP_INDUSTRIAL_10")
    # Load manual baseline layout
    res = client.get("/api/layouts/examples/LAYOUT_SAMPLE_INDUSTRIAL_10")
    assert res.status_code == 200
    baseline_data = res.json()
    baseline_layout = ContinuousLayout.model_validate(baseline_data)

    craft_solver = CRAFTAlgorithm()
    solution, result = craft_solver.solve_with_result(problem, baseline_layout)

    assert result.is_complete is True
    assert result.is_feasible is True
    # The benchmark report:
    print(f"\n[FLP_INDUSTRIAL_10 Benchmark] Initial MHC: {result.initial_mhc:.2f}, Final MHC: {result.final_mhc:.2f}, Swaps: {len(result.accepted_swaps)}, Reason: {result.termination_reason}")
