"""Comprehensive test suite and academic benchmarks for ALDEP (Automated Layout Design Program)."""

import math
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.geometry import Point2D, Dimensions2D, BoundingBox, ReservedZone
from app.models.facility import Facility
from app.models.department import Department
from app.models.flow import Flow
from app.models.relationship import Relationship, ClosenessRating, DEFAULT_RELATIONSHIP_SCORES
from app.models.problem import FacilityLayoutProblem, ObjectiveConfig, PrimaryObjective
from app.models.solution import LayoutSolution, SolverTerminationReason
from app.models.representation import ContinuousLayout, GridLayout
from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.aldep.config import (
    ALDEPConfig,
    SweepDirection,
    SelectionTieBreak,
    TraceLevel,
)
from app.algorithms.aldep.models import (
    ALDEPSelectionStep,
    ALDEPDepartmentShapeDiagnostic,
    ALDEPCandidateResult,
    ALDEPExecutionTrace,
    ALDEPSolverResult,
)
from app.algorithms.aldep.selection import (
    get_relationship_score,
    select_initial_department,
    select_next_department,
    generate_aldep_sequence,
)
from app.algorithms.aldep.placement import (
    create_strip_sweep_layout,
    _build_serpentine_cell_sequence,
)
from app.algorithms.aldep.solver import ALDEPAlgorithm
from app.services.problem_service import problem_service
from app.services.problem_loader import load_problem
from app.services.layout_validator import LayoutValidator
from app.evaluation.engine import EvaluationEngine


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def academic_4dept_problem() -> FacilityLayoutProblem:
    """Standard 4-department academic verification problem.
    
    Layout: 120m x 120m facility.
    4 departments of 100m² each: DEP_A, DEP_B, DEP_C, DEP_D.
    Relationships:
        (A, B) = A (16.0)
        (A, C) = E (8.0)
        (B, C) = I (4.0)
        (B, D) = O (2.0)
        (C, D) = X (-8.0)
        (A, D) = U (0.0 - omitted)
    Flows:
        A -> B: 50 loads
        B -> C: 30 loads
        C -> D: 10 loads
    """
    facility = Facility(id="FAC_ACADEMIC_4", name="Academic Plant", width=120.0, height=120.0, area=14400.0)
    departments = [
        Department(id="DEP_A", name="Milling", required_area=100.0, min_width=10.0, max_width=30.0),
        Department(id="DEP_B", name="Drilling", required_area=100.0, min_width=10.0, max_width=30.0),
        Department(id="DEP_C", name="Welding", required_area=100.0, min_width=10.0, max_width=30.0),
        Department(id="DEP_D", name="Storage", required_area=100.0, min_width=10.0, max_width=30.0),
    ]
    relationships = [
        Relationship(department_a="DEP_A", department_b="DEP_B", relationship_type=ClosenessRating.A, score=16.0),
        Relationship(department_a="DEP_A", department_b="DEP_C", relationship_type=ClosenessRating.E, score=8.0),
        Relationship(department_a="DEP_B", department_b="DEP_C", relationship_type=ClosenessRating.I, score=4.0),
        Relationship(department_a="DEP_B", department_b="DEP_D", relationship_type=ClosenessRating.O, score=2.0),
        Relationship(department_a="DEP_C", department_b="DEP_D", relationship_type=ClosenessRating.X, score=-8.0),
    ]
    flows = [
        Flow(source_department="DEP_A", target_department="DEP_B", quantity=50.0, cost_per_unit_distance=1.0),
        Flow(source_department="DEP_B", target_department="DEP_C", quantity=30.0, cost_per_unit_distance=1.0),
        Flow(source_department="DEP_C", target_department="DEP_D", quantity=10.0, cost_per_unit_distance=1.0),
    ]
    return FacilityLayoutProblem(
        id="FLP_ACADEMIC_4",
        name="Academic 4-Dept Verification",
        facility=facility,
        departments=departments,
        relationships=relationships,
        flows=flows,
        objective_config=ObjectiveConfig(primary_objective=PrimaryObjective.MINIMIZE_FLOW_DISTANCE),
    )


# ---------------------------------------------------------------------------
# 1. Muther REL Relationship Lookup
# ---------------------------------------------------------------------------

def test_01_muther_rel_score_lookup(academic_4dept_problem: FacilityLayoutProblem):
    """Test 1: Verify Muther REL score retrieval and symmetric bidirectional matching."""
    # Direct match (A, B) -> 16.0
    assert get_relationship_score(academic_4dept_problem, "DEP_A", "DEP_B") == 16.0
    # Reverse match (B, A) -> 16.0
    assert get_relationship_score(academic_4dept_problem, "DEP_B", "DEP_A") == 16.0
    # Match (A, C) -> 8.0
    assert get_relationship_score(academic_4dept_problem, "DEP_A", "DEP_C") == 8.0
    # Negative match (C, D) -> -8.0
    assert get_relationship_score(academic_4dept_problem, "DEP_C", "DEP_D") == -8.0
    # Self-relation -> 0.0
    assert get_relationship_score(academic_4dept_problem, "DEP_A", "DEP_A") == 0.0
    # Omitted relation (A, D) -> defaults to 0.0 (rating U)
    assert get_relationship_score(academic_4dept_problem, "DEP_A", "DEP_D") == 0.0


# ---------------------------------------------------------------------------
# 2. Initial Department Selection & Seed Reproducibility
# ---------------------------------------------------------------------------

def test_02_initial_selection_random_and_seed_reproducibility():
    """Test 2: Initial department is selected randomly and is deterministic with seeded RNG."""
    import random
    unplaced = ["DEP_A", "DEP_B", "DEP_C", "DEP_D"]

    rng1 = random.Random(42)
    sel1, step1 = select_initial_department(unplaced, 8.0, rng1)

    rng2 = random.Random(42)
    sel2, step2 = select_initial_department(unplaced, 8.0, rng2)

    assert sel1 == sel2
    assert step1.selection_mode == "INITIAL_RANDOM"
    assert step1.selected_department in unplaced

    # Diversity across seeds
    different_selections = set()
    for s in range(50):
        rng = random.Random(s)
        sel, _ = select_initial_department(unplaced, 8.0, rng)
        different_selections.add(sel)
    assert len(different_selections) >= 3, "Initial selection should explore multiple departments across seeds"


# ---------------------------------------------------------------------------
# 3. Subsequent Department Selection: Highest Rating Priority
# ---------------------------------------------------------------------------

def test_03_selection_logic_highest_rating_priority(academic_4dept_problem: FacilityLayoutProblem):
    """Test 3: From DEP_A, candidates with score >= 8.0 are B(16) and C(8); B must be chosen (A > E)."""
    import random
    rng = random.Random(123)
    config = ALDEPConfig(selection_threshold=8.0, tie_breaker=SelectionTieBreak.RANDOM_AMONG_MAX)

    unplaced = ["DEP_B", "DEP_C", "DEP_D"]
    selected, step = select_next_department(
        last_dept_id="DEP_A",
        unplaced=unplaced,
        problem=academic_4dept_problem,
        config=config,
        rng=rng,
        step_number=2,
    )

    assert selected == "DEP_B"
    assert step.selection_mode == "AFFINITY_MAX"
    assert "DEP_B" in step.eligible_candidates
    assert "DEP_C" in step.eligible_candidates
    assert "DEP_D" not in step.eligible_candidates
    assert step.candidate_scores["DEP_B"] == 16.0
    assert step.candidate_scores["DEP_C"] == 8.0
    assert step.candidate_scores["DEP_D"] == 0.0


# ---------------------------------------------------------------------------
# 4. Selection Logic: Threshold Cutoff
# ---------------------------------------------------------------------------

def test_04_selection_logic_threshold_cutoff(academic_4dept_problem: FacilityLayoutProblem):
    """Test 4: High threshold cutoff (T=10.0) excludes rating E (score 8.0)."""
    import random
    rng = random.Random(42)
    config = ALDEPConfig(selection_threshold=10.0)

    unplaced = ["DEP_B", "DEP_C", "DEP_D"]
    selected, step = select_next_department(
        last_dept_id="DEP_A",
        unplaced=unplaced,
        problem=academic_4dept_problem,
        config=config,
        rng=rng,
        step_number=2,
    )

    assert selected == "DEP_B"
    assert step.eligible_candidates == ["DEP_B"]


# ---------------------------------------------------------------------------
# 5. Selection Logic: Tie-Break Among Tied Maximal Candidates
# ---------------------------------------------------------------------------

def test_05_selection_logic_tie_break_random():
    """Test 5: When multiple candidates tie for maximum rating, random tie-breaking resolves."""
    import random
    facility = Facility(id="F", name="F", width=100.0, height=100.0)
    departments = [
        Department(id="D1", name="D1", required_area=100.0),
        Department(id="D2", name="D2", required_area=100.0),
        Department(id="D3", name="D3", required_area=100.0),
    ]
    # D1 has rating A with both D2 and D3
    relationships = [
        Relationship(department_a="D1", department_b="D2", relationship_type=ClosenessRating.A, score=16.0),
        Relationship(department_a="D1", department_b="D3", relationship_type=ClosenessRating.A, score=16.0),
    ]
    prob = FacilityLayoutProblem(id="P", name="P", facility=facility, departments=departments, relationships=relationships)

    config = ALDEPConfig(selection_threshold=8.0, tie_breaker=SelectionTieBreak.RANDOM_AMONG_MAX)

    picks = set()
    for s in range(20):
        rng = random.Random(s)
        sel, _ = select_next_department("D1", ["D2", "D3"], prob, config, rng, step_number=2)
        picks.add(sel)

    assert picks == {"D2", "D3"}, "Tie-breaking must allow both tied candidates to be selected across seeds"


# ---------------------------------------------------------------------------
# 6. Selection Logic: Fallback to Random Choice When No Candidate Meets Threshold
# ---------------------------------------------------------------------------

def test_06_selection_logic_fallback_when_no_candidate_meets_threshold(academic_4dept_problem: FacilityLayoutProblem):
    """Test 6: From DEP_B, unplaced are C(4.0) and D(2.0); with T=8.0, neither qualifies -> fallback."""
    import random
    rng = random.Random(42)
    config = ALDEPConfig(selection_threshold=8.0)

    unplaced = ["DEP_C", "DEP_D"]
    selected, step = select_next_department(
        last_dept_id="DEP_B",
        unplaced=unplaced,
        problem=academic_4dept_problem,
        config=config,
        rng=rng,
        step_number=3,
    )

    assert step.selection_mode == "RANDOM_FALLBACK"
    assert step.eligible_candidates == []
    assert selected in ["DEP_C", "DEP_D"]


# ---------------------------------------------------------------------------
# 7. Complete Sequence Generation on Academic Problem
# ---------------------------------------------------------------------------

def test_07_complete_sequence_generation(academic_4dept_problem: FacilityLayoutProblem):
    """Test 7: Full ALDEP sequence generation creates an exact 4-department permutation."""
    import random
    rng = random.Random(42)
    config = ALDEPConfig(selection_threshold=8.0)

    order, steps = generate_aldep_sequence(academic_4dept_problem, config, rng)
    assert len(order) == 4
    assert set(order) == {"DEP_A", "DEP_B", "DEP_C", "DEP_D"}
    assert len(steps) == 4
    assert steps[0].selection_mode == "INITIAL_RANDOM"


# ---------------------------------------------------------------------------
# 8. Serpentine Strip-Sweep Cell Sequence Generation
# ---------------------------------------------------------------------------

def test_08_serpentine_sweep_cells_sequence():
    """Test 8: Vertical and horizontal serpentine cell orders reverse direction on alternating strips."""
    config_vert = ALDEPConfig(
        cell_size=10.0,
        strip_width_cells=2,
        sweep_direction=SweepDirection.VERTICAL,
        serpentine_sweep=True,
    )
    # Grid: 4 rows x 4 cols = 16 cells. 2 strips of width 2 cols.
    seq_vert = _build_serpentine_cell_sequence(rows=4, cols=4, config=config_vert, reserved_cells=set(), preoccupied_cells=set())
    assert len(seq_vert) == 16
    # Strip 0 (cols 0, 1): rows 0, 1, 2, 3 (ascending)
    assert seq_vert[0] == (0, 0)
    assert seq_vert[1] == (0, 1)
    assert seq_vert[6] == (3, 0)
    assert seq_vert[7] == (3, 1)
    # Strip 1 (cols 2, 3): rows 3, 2, 1, 0 (descending)
    assert seq_vert[8] == (3, 2)
    assert seq_vert[9] == (3, 3)
    assert seq_vert[14] == (0, 2)
    assert seq_vert[15] == (0, 3)

    # Test HORIZONTAL
    config_horiz = ALDEPConfig(
        cell_size=10.0,
        strip_width_cells=2,
        sweep_direction=SweepDirection.HORIZONTAL,
        serpentine_sweep=True,
    )
    seq_horiz = _build_serpentine_cell_sequence(rows=4, cols=4, config=config_horiz, reserved_cells=set(), preoccupied_cells=set())
    assert len(seq_horiz) == 16
    # Strip 0 (rows 0, 1): cols 0, 1, 2, 3 (left to right)
    assert seq_horiz[0] == (0, 0)
    assert seq_horiz[1] == (1, 0)
    # Strip 1 (rows 2, 3): cols 3, 2, 1, 0 (right to left)
    assert seq_horiz[8] == (2, 3)


# ---------------------------------------------------------------------------
# 9. Discretization Area and Error Diagnostics
# ---------------------------------------------------------------------------

def test_09_discretization_area_and_error_diagnostics(academic_4dept_problem: FacilityLayoutProblem):
    """Test 9: Department required area is converted to cell count, reporting exact area errors."""
    config = ALDEPConfig(cell_size=5.0, strip_width_cells=2)
    # Area 100m² / (5m)^2 = 4 cells exactly.
    grid, cont, diags, unplaced = create_strip_sweep_layout(
        academic_4dept_problem, ["DEP_A", "DEP_B", "DEP_C", "DEP_D"], config
    )
    assert len(unplaced) == 0
    for d_id in ["DEP_A", "DEP_B", "DEP_C", "DEP_D"]:
        diag = diags[d_id]
        assert diag.required_area == 100.0
        assert diag.allocated_cells == 4
        assert diag.allocated_area == 100.0
        assert diag.area_error == 0.0
        assert diag.area_error_pct == 0.0


# ---------------------------------------------------------------------------
# 10. Classical Strip-Sweep Splitting Behavior
# ---------------------------------------------------------------------------

def test_10_classical_strip_sweep_splitting_behavior(academic_4dept_problem: FacilityLayoutProblem):
    """Test 10: Classical strip sweep wraps across strips and generates continuous bounding boxes."""
    # Strip of width 1 col, 2 rows high facility (20m x 20m)
    fac_small = Facility(id="FS", name="FS", width=20.0, height=20.0)
    # Dept of 300m² needs 3 cells of 10x10. Each col has 2 cells, so it wraps to col 1!
    dept1 = Department(id="D1", name="D1", required_area=300.0)
    dept2 = Department(id="D2", name="D2", required_area=100.0)
    prob = FacilityLayoutProblem(id="PS", name="PS", facility=fac_small, departments=[dept1, dept2])

    config = ALDEPConfig(cell_size=10.0, strip_width_cells=1, allow_strip_splitting=True)
    grid, cont, diags, unplaced = create_strip_sweep_layout(prob, ["D1", "D2"], config)

    assert len(unplaced) == 0
    assert diags["D1"].allocated_cells == 3
    # In discrete grid: 0 overlap
    assert grid.get_cell(0, 0) == "D1"
    assert grid.get_cell(1, 0) == "D1"
    assert grid.get_cell(1, 1) == "D1"
    assert grid.get_cell(0, 1) == "D2"
    # D1 wrapped across columns, so it is non-rectangular
    assert diags["D1"].is_rectangular is False


# ---------------------------------------------------------------------------
# 11. Rectangular Strip-Sweep Adaptation
# ---------------------------------------------------------------------------

def test_11_rectangular_strip_sweep_adaptation():
    """Test 11: FLODSS rectangular adaptation (allow_strip_splitting=False) creates solid rectangular blocks."""
    plant_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_medium_plant.json"
    problem = load_problem(plant_path)

    # With strip_width=4 cells (20m) and allow_strip_splitting=False
    config = ALDEPConfig(cell_size=5.0, strip_width_cells=4, allow_strip_splitting=False)
    solver = ALDEPAlgorithm(parameters=config.model_dump())
    solution, result = solver.solve_with_result(problem)

    assert solution.is_complete is True
    assert solution.placed_department_count == 6
    assert solution.feasibility_status is True

    # Check that every department is strictly rectangular
    for d_id, diag in result.best_candidate.shape_diagnostics.items():
        assert diag.is_rectangular is True, f"Department {d_id} should be rectangular in no-split mode"


# ---------------------------------------------------------------------------
# 12. Reserved Zone and Fixed Position Avoidance
# ---------------------------------------------------------------------------

def test_12_reserved_zone_and_fixed_position_avoidance():
    """Test 12: Grid sweep respects reserved zones and places around fixed departments."""
    fac = Facility(
        id="FAC_RES",
        name="FAC_RES",
        width=50.0,
        height=50.0,
        reserved_zones=[ReservedZone(id="Z1", type="restricted", bounding_box=BoundingBox(x_min=0.0, y_min=0.0, x_max=10.0, y_max=10.0))],
    )
    d_fixed = Department(id="D_FIX", name="D_FIX", required_area=100.0, fixed_position=Point2D(x=20.0, y=20.0))
    d_free = Department(id="D_FREE", name="D_FREE", required_area=200.0)
    prob = FacilityLayoutProblem(id="P_RES", name="P_RES", facility=fac, departments=[d_fixed, d_free])

    config = ALDEPConfig(cell_size=5.0, strip_width_cells=2)
    grid, cont, diags, unplaced = create_strip_sweep_layout(prob, ["D_FREE"], config)

    assert len(unplaced) == 0
    # Reserved zone at bottom-left [0..10, 0..10] must have no department
    for r in range(2):
        for c in range(2):
            assert grid.get_cell(r, c) is None or grid.get_cell(r, c) == "RESERVED"


# ---------------------------------------------------------------------------
# 13. Multi-Candidate Generation and Diversity
# ---------------------------------------------------------------------------

def test_13_multi_candidate_generation_and_diversity(academic_4dept_problem: FacilityLayoutProblem):
    """Test 13: ALDEP generates K candidates with diversity in sequences and layouts."""
    config = ALDEPConfig(number_of_candidates=10, random_seed=42)
    solver = ALDEPAlgorithm(parameters=config.model_dump())
    solution, result = solver.solve_with_result(academic_4dept_problem)

    assert len(result.candidates) == 10
    assert result.trace.number_of_candidates == 10
    assert result.trace.unique_candidate_count >= 2, "10 candidates should yield multiple distinct layouts"


# ---------------------------------------------------------------------------
# 14. Deterministic Seed Reproducibility
# ---------------------------------------------------------------------------

def test_14_deterministic_seed_reproducibility(academic_4dept_problem: FacilityLayoutProblem):
    """Test 14: Executing ALDEP with identical seed produces bitwise identical candidates and signatures."""
    config = ALDEPConfig(number_of_candidates=5, random_seed=100)
    solver1 = ALDEPAlgorithm(parameters=config.model_dump())
    _, res1 = solver1.solve_with_result(academic_4dept_problem)

    solver2 = ALDEPAlgorithm(parameters=config.model_dump())
    _, res2 = solver2.solve_with_result(academic_4dept_problem)

    for i in range(5):
        assert res1.candidates[i].layout_signature == res2.candidates[i].layout_signature
        assert res1.candidates[i].department_order == res2.candidates[i].department_order
        assert res1.candidates[i].material_handling_cost == res2.candidates[i].material_handling_cost


# ---------------------------------------------------------------------------
# 15. Duplicate Candidate Detection
# ---------------------------------------------------------------------------

def test_15_duplicate_candidate_detection(academic_4dept_problem: FacilityLayoutProblem):
    """Test 15: Duplicate layouts across multiple seeds are flagged with duplicate_of_index."""
    # When number_of_candidates is high on a small 4-dept problem, duplicates naturally occur
    config = ALDEPConfig(number_of_candidates=20, random_seed=1)
    solver = ALDEPAlgorithm(parameters=config.model_dump())
    _, res = solver.solve_with_result(academic_4dept_problem)

    duplicates = [c for c in res.candidates if c.is_duplicate]
    assert len(duplicates) > 0, "Duplicate candidates must be identified"
    for d in duplicates:
        assert d.duplicate_of_index is not None
        assert d.duplicate_of_index < d.candidate_index


# ---------------------------------------------------------------------------
# 16. Candidate Ranking via EvaluationEngine
# ---------------------------------------------------------------------------

def test_16_candidate_ranking_via_evaluation_engine(academic_4dept_problem: FacilityLayoutProblem):
    """Test 16: Candidates are evaluated and ranked; best candidate is set as primary solution."""
    config = ALDEPConfig(number_of_candidates=10, random_seed=42)
    solver = ALDEPAlgorithm(parameters=config.model_dump())
    solution, result = solver.solve_with_result(academic_4dept_problem)

    best = result.best_candidate
    assert best.material_handling_cost is not None
    # Best candidate must have lower or equal MHC than other complete feasible candidates
    for c in result.candidates:
        if c.is_feasible and c.material_handling_cost is not None:
            assert best.material_handling_cost <= c.material_handling_cost + 1e-4

    assert solution.placements["DEP_A"].origin.x == best.continuous_layout.placements["DEP_A"].x


# ---------------------------------------------------------------------------
# 17. Academic 4-Department Benchmark Verification
# ---------------------------------------------------------------------------

def test_17_academic_4dept_hand_calculated_benchmark(academic_4dept_problem: FacilityLayoutProblem):
    """Test 17: Hand-calculated benchmark verification (120x120m, 10x10m cells, 1 strip).
    
    Order: [A, B, C, D] placed in strip 0 at rows 0, 1, 2, 3:
    Centroids: A=(5, 5), B=(5, 15), C=(5, 25), D=(5, 35).
    Flow A->B = 50 * 10 = 500
    Flow B->C = 30 * 10 = 300
    Flow C->D = 10 * 10 = 100
    Total MHC = 900.0.
    """
    config = ALDEPConfig(
        cell_size=10.0,
        strip_width_cells=1,
        number_of_candidates=1,
        random_seed=42,
    )
    # Manually run strip sweep with order [DEP_A, DEP_B, DEP_C, DEP_D]
    grid, cont, diags, unplaced = create_strip_sweep_layout(
        academic_4dept_problem,
        ["DEP_A", "DEP_B", "DEP_C", "DEP_D"],
        config,
    )
    assert len(unplaced) == 0
    val = LayoutValidator.validate(academic_4dept_problem, cont)
    assert val.is_valid is True

    engine = EvaluationEngine()
    report = engine.evaluate(academic_4dept_problem, cont)
    assert report.is_feasible is True
    assert report.objective_values["material_handling_cost"] == pytest.approx(900.0, abs=1e-2)
    assert report.objective_values["flow_distance"] == pytest.approx(900.0, abs=1e-2)


# ---------------------------------------------------------------------------
# 18. Benchmark: Medium Plant (FLP_MEDIUM_6)
# ---------------------------------------------------------------------------

def test_18_benchmark_medium_plant_flp_medium_6():
    """Test 18: ALDEP completely solves FLP_MEDIUM_6 (6 departments, 4100m²)."""
    plant_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_medium_plant.json"
    problem = load_problem(plant_path)

    config = ALDEPConfig(cell_size=5.0, strip_width_cells=2, number_of_candidates=5, random_seed=42)
    solver = ALDEPAlgorithm(parameters=config.model_dump())
    solution = solver.solve(problem)

    assert solution.is_complete is True
    assert solution.placed_department_count == 6
    assert solution.total_department_count == 6
    assert solution.unplaced_departments == []
    assert len(solution.placements) == 6
    assert solution.objective_values.get("material_handling_cost") is not None


# ---------------------------------------------------------------------------
# 19. Benchmark: Industrial Plant (FLP_INDUSTRIAL_10)
# ---------------------------------------------------------------------------

def test_19_benchmark_industrial_plant_flp_industrial_10():
    """Test 19: ALDEP places all 10 departments of FLP_INDUSTRIAL_10 on the discrete grid."""
    plant_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_plant.json"
    problem = load_problem(plant_path)

    config = ALDEPConfig(cell_size=5.0, strip_width_cells=3, number_of_candidates=3, random_seed=42)
    solver = ALDEPAlgorithm(parameters=config.model_dump())
    solution, result = solver.solve_with_result(problem)

    assert solution.is_complete is True
    assert solution.placed_department_count == 10
    assert solution.total_department_count == 10
    assert solution.unplaced_departments == []
    assert len(result.best_candidate.shape_diagnostics) == 10


# ---------------------------------------------------------------------------
# 20. Insufficient Grid Capacity Partial Handling
# ---------------------------------------------------------------------------

def test_20_insufficient_grid_capacity_partial_handling():
    """Test 20: ALDEP handles small facility capacity gracefully, reporting unplaced departments."""
    # Facility physical boundary is 20x20m (400m² = 16 cells of 5x5m)
    tiny_fac = Facility(id="TINY", name="TINY", width=20.0, height=20.0, area=600.0)
    # Departments requiring 200m² each (8 cells each -> 24 cells needed, but only 16 available in grid)
    departments = [
        Department(id="D1", name="D1", required_area=200.0),
        Department(id="D2", name="D2", required_area=200.0),
        Department(id="D3", name="D3", required_area=200.0),
    ]
    prob = FacilityLayoutProblem(id="P_TINY", name="P_TINY", facility=tiny_fac, departments=departments)

    config = ALDEPConfig(cell_size=5.0, strip_width_cells=2, number_of_candidates=1)
    solver = ALDEPAlgorithm(parameters=config.model_dump())
    solution = solver.solve(prob)

    assert solution.is_complete is False
    assert solution.placed_department_count == 2
    assert solution.total_department_count == 3
    assert len(solution.unplaced_departments) == 1
    assert solution.unplaced_departments[0] in ["D1", "D2", "D3"]
    assert solution.termination_reason == SolverTerminationReason.FAILED_NO_FEASIBLE_CANDIDATE.value


# ---------------------------------------------------------------------------
# 21. Algorithm Registry Contains ALDEP
# ---------------------------------------------------------------------------

def test_21_algorithm_registry_contains_aldep():
    """Test 21: ALDEP is registered in AlgorithmRegistry with correct metadata."""
    registered = AlgorithmRegistry.list_available()
    names = [a["name"] for a in registered]
    assert "aldep" in names

    instance = AlgorithmRegistry.get("aldep")
    assert instance.name == "aldep"
    assert instance.version == "1.0.0"
    assert instance.category.value == "construction"
    assert instance.metadata["stochastic"] is True


# ---------------------------------------------------------------------------
# 22. API Endpoint: POST /api/algorithms/aldep/solve
# ---------------------------------------------------------------------------

def test_22_api_solve_aldep_endpoint(client: TestClient, academic_4dept_problem: FacilityLayoutProblem):
    """Test 22: POST /api/algorithms/aldep/solve executes ALDEP and returns complete response payload."""
    payload = {
        "problem": academic_4dept_problem.model_dump(),
        "config": {
            "number_of_candidates": 3,
            "random_seed": 42,
            "cell_size": 10.0,
            "strip_width_cells": 1,
        },
    }
    resp = client.post("/api/algorithms/aldep/solve", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "solution" in data
    assert "continuous_layout" in data
    assert "best_candidate" in data
    assert "candidates" in data
    assert len(data["candidates"]) == 3
    assert "trace" in data
    assert "validation" in data
    assert "evaluation" in data
    assert data["solution"]["placed_department_count"] == 4
    assert data["solution"]["is_complete"] is True


# ---------------------------------------------------------------------------
# 23. API Endpoint: Solve Medium Plant
# ---------------------------------------------------------------------------

def test_23_api_solve_aldep_medium_plant(client: TestClient):
    """Test 23: POST /api/algorithms/aldep/solve on FLP_MEDIUM_6 resolves problem_id and executes cleanly."""
    payload = {
        "problem_id": "FLP_MEDIUM_6",
        "config": {
            "number_of_candidates": 4,
            "random_seed": 42,
            "cell_size": 5.0,
            "strip_width_cells": 4,
            "allow_strip_splitting": False,
        },
    }
    resp = client.post("/api/algorithms/aldep/solve", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["solution"]["is_complete"] is True
    assert data["solution"]["placed_department_count"] == 6
    assert len(data["candidates"]) == 4
    assert data["validation"]["is_valid"] is True
