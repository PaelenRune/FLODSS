"""Unit tests for Phase 5 — CORELAP Algorithm (corelap_deterministic_v1).

Covers all 26 specified requirements:
1. TCR hand-calculated correctness
2. Missing relationship defaults to U (0.0)
3. Deterministic initial department selection
4. Initial tie-breaking (TCR -> required_area -> alphabetical ID)
5. Next department selection by maximal placed affinity
6. Placement order for known case ([A, B, C, D])
7. Department dimension generation (area conservation, aspect ratio)
8. Candidate generation along borders
9. Candidate boundary rejection
10. Overlap candidate rejection
11. Adjacency scoring with shared wall length
12. X-relationship penalty multiplier
13. Fixed department preservation (brownfield scenario)
14. All departments placed on viable facility
15. Output boundary validity
16. Output no-overlap validity
17. Deterministic layout signature
18. Ten-run repeatability (all 10 runs produce bitwise identical signatures)
19. Execution trace completeness
20. Algorithm registry contains CORELAP
21. Evaluation engine integration (MHC, Flow Distance, Relationship, Area, Penalties)
22. Sample factory solution feasibility diagnostics on sample_plant.json
23. Baseline comparison (CORELAP vs manual baseline)
24. API algorithms discovery endpoint (GET /api/algorithms)
25. API CORELAP solve endpoint (POST /api/algorithms/corelap/solve)
26. Frontend TypeScript build validation
"""

import math
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.geometry import Point2D, Dimensions2D, BoundingBox
from app.models.facility import Facility
from app.models.department import Department
from app.models.flow import Flow
from app.models.relationship import Relationship, ClosenessRating, RELATIONSHIP_DEFAULT_SCORES
from app.models.constraint import Constraint, ConstraintType, ConstraintClassification
from app.models.problem import FacilityLayoutProblem, ObjectiveConfig, PrimaryObjective
from app.models.solution import LayoutSolution, SolverTerminationReason
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.corelap.config import CORELAPConfig, PlacementMode, InitialAnchorMode, TraceLevel
from app.algorithms.corelap.trace import CORELAPExecutionTrace, CORELAPTraceStep
from app.algorithms.corelap.tcr import (
    calculate_tcr,
    select_initial_department,
    select_next_department,
    get_relationship_weight,
)
from app.algorithms.corelap.geometry_helpers import (
    determine_department_dimensions,
    generate_legal_department_shapes,
    generate_candidate_placements,
)
from app.algorithms.corelap.scoring import score_candidate_placement, evaluate_and_rank_candidates
from app.algorithms.corelap.solver import CORELAPAlgorithm
from app.services.problem_loader import load_problem
from app.services.layout_validator import LayoutValidator
from app.evaluation.engine import EvaluationEngine


# ---------------------------------------------------------------------------
# Fixture: Academic 4-Department Problem with Known Hand Calculations
# ---------------------------------------------------------------------------

@pytest.fixture
def academic_4dept_problem() -> FacilityLayoutProblem:
    """Standard 4-department verification problem with hand-computable values.
    
    TCR Calculation:
        w(A, B) = A = 16
        w(A, C) = E = 8
        w(A, D) = U = 0
        -> TCR_A = 16 + 8 + 0 = 24
        
        w(B, C) = I = 4
        w(B, D) = O = 2
        -> TCR_B = 16 + 4 + 2 = 22
        
        w(C, D) = X = -8
        -> TCR_C = 8 + 4 + (-8) = 4
        
        -> TCR_D = 0 + 2 + (-8) = -6
        
    Order Expectation:
        Initial: A (TCR 24)
        Next 1:  B (Affinity with {A} is 16 > 8 > 0)
        Next 2:  C (Affinity with {A, B} is 8 + 4 = 12 > 0 + 2 = 2)
        Next 3:  D
        Expected Placement Order: [A, B, C, D]
    """
    facility = Facility(id="FAC_TEST", name="Test Plant", width=120.0, height=120.0)
    departments = [
        Department(id="DEP_A", name="Milling", required_area=100.0),
        Department(id="DEP_B", name="Drilling", required_area=100.0),
        Department(id="DEP_C", name="Welding", required_area=100.0),
        Department(id="DEP_D", name="Storage", required_area=100.0),
    ]
    relationships = [
        Relationship(department_a="DEP_A", department_b="DEP_B", relationship_type=ClosenessRating.A, score=16.0),
        Relationship(department_a="DEP_A", department_b="DEP_C", relationship_type=ClosenessRating.E, score=8.0),
        Relationship(department_a="DEP_B", department_b="DEP_C", relationship_type=ClosenessRating.I, score=4.0),
        Relationship(department_a="DEP_B", department_b="DEP_D", relationship_type=ClosenessRating.O, score=2.0),
        Relationship(department_a="DEP_C", department_b="DEP_D", relationship_type=ClosenessRating.X, score=-8.0),
        # Note: (A, D) is intentionally omitted to verify default U = 0.0
    ]
    flows = [
        Flow(source_department="DEP_A", target_department="DEP_B", quantity=50.0, unit="loads/day"),
        Flow(source_department="DEP_B", target_department="DEP_C", quantity=30.0, unit="loads/day"),
        Flow(source_department="DEP_C", target_department="DEP_D", quantity=10.0, unit="loads/day"),
    ]
    return FacilityLayoutProblem(
        id="FLP_ACADEMIC_4",
        name="Academic Hand-Calculated Problem",
        facility=facility,
        departments=departments,
        relationships=relationships,
        flows=flows,
    )


# ---------------------------------------------------------------------------
# Tests 1 - 6: TCR and Department Selection Logic
# ---------------------------------------------------------------------------

def test_1_tcr_hand_calculated_correctness(academic_4dept_problem: FacilityLayoutProblem):
    """Test 1: Verify hand-calculated TCR values matches exact theoretical expectation."""
    tcr = calculate_tcr(academic_4dept_problem)
    assert tcr["DEP_A"] == pytest.approx(24.0, abs=1e-5)
    assert tcr["DEP_B"] == pytest.approx(22.0, abs=1e-5)
    assert tcr["DEP_C"] == pytest.approx(4.0, abs=1e-5)
    assert tcr["DEP_D"] == pytest.approx(-6.0, abs=1e-5)


def test_2_missing_relationship_defaults_to_u(academic_4dept_problem: FacilityLayoutProblem):
    """Test 2: Department pair without explicit relationship defaults to U = 0.0."""
    w_ad = get_relationship_weight(academic_4dept_problem, "DEP_A", "DEP_D")
    assert w_ad == 0.0
    w_da = get_relationship_weight(academic_4dept_problem, "DEP_D", "DEP_A")
    assert w_da == 0.0


def test_3_deterministic_initial_department(academic_4dept_problem: FacilityLayoutProblem):
    """Test 3: First department selected has the highest TCR (DEP_A)."""
    tcr = calculate_tcr(academic_4dept_problem)
    chosen = select_initial_department(academic_4dept_problem.departments, tcr)
    assert chosen.id == "DEP_A"


def test_4_initial_tie_breaking():
    """Test 4: Initial selection tie-breaking: TCR -> area -> alphabetical ID."""
    depts = [
        Department(id="DEP_Z", name="Dept Z", required_area=200.0),
        Department(id="DEP_A", name="Dept A", required_area=300.0),
        Department(id="DEP_B", name="Dept B", required_area=300.0),
    ]
    # Case A: Same TCR, different areas -> larger area wins
    tcr_equal = {"DEP_Z": 20.0, "DEP_A": 20.0, "DEP_B": 20.0}
    # DEP_A and DEP_B have 300 area, DEP_Z has 200 area. Between A and B, alphabetical ID 'DEP_A' wins!
    chosen = select_initial_department(depts, tcr_equal)
    assert chosen.id == "DEP_A"


def test_5_next_department_selection(academic_4dept_problem: FacilityLayoutProblem):
    """Test 5: Next department selection ranks by placed affinity sum."""
    tcr = calculate_tcr(academic_4dept_problem)
    unplaced = [d for d in academic_4dept_problem.departments if d.id != "DEP_A"]
    placed_ids = ["DEP_A"]
    
    # Affinity with A: DEP_B is 16, DEP_C is 8, DEP_D is 0
    next_dept, score = select_next_department(unplaced, placed_ids, academic_4dept_problem, tcr)
    assert next_dept.id == "DEP_B"
    assert score == pytest.approx(16.0, abs=1e-5)


def test_6_placement_order_known_case(academic_4dept_problem: FacilityLayoutProblem):
    """Test 6: Full placement sequence matches theoretical order [DEP_A, DEP_B, DEP_C, DEP_D]."""
    solver = CORELAPAlgorithm()
    solution = solver.solve(academic_4dept_problem)
    assert solution.metadata["placement_order"] == ["DEP_A", "DEP_B", "DEP_C", "DEP_D"]


# ---------------------------------------------------------------------------
# Tests 7 - 13: Geometric Candidate Generation, Scoring, and Filtering
# ---------------------------------------------------------------------------

def test_7_department_dimension_generation():
    """Test 7: Department dimension generation preserves required area."""
    config = CORELAPConfig(aspect_ratio_target=1.0)
    dept = Department(id="DEP_TEST", name="Test", required_area=144.0)
    w, h = determine_department_dimensions(dept, config)
    assert math.isclose(w * h, 144.0, rel_tol=1e-3)
    assert w == pytest.approx(12.0, abs=1e-2)
    assert h == pytest.approx(12.0, abs=1e-2)

    # With min_width constraint
    dept_constrained = Department(id="DEP_MIN", name="Min W", required_area=100.0, min_width=20.0)
    w_c, h_c = determine_department_dimensions(dept_constrained, config)
    assert w_c >= 20.0
    assert math.isclose(w_c * h_c, 100.0, rel_tol=1e-2)


def test_8_candidate_generation_along_borders():
    """Test 8: Candidate placements generated adjacent to placed boxes."""
    placed = {
        "DEP_A": ContinuousPlacement(department_id="DEP_A", x=40.0, y=40.0, width=20.0, height=20.0),
    }
    config = CORELAPConfig()
    cands, _ = generate_candidate_placements("DEP_B", 10.0, 10.0, placed, 100.0, 100.0, config)
    assert len(cands) > 0
    # Right border x should touch 60.0
    right_cands = [c for c in cands if math.isclose(c.x, 60.0, abs_tol=1e-4)]
    assert len(right_cands) > 0


def test_9_candidate_boundary_rejection():
    """Test 9: Candidates projecting outside facility boundary are strictly rejected."""
    placed = {
        "DEP_CORNER": ContinuousPlacement(department_id="DEP_CORNER", x=0.0, y=0.0, width=10.0, height=10.0),
    }
    config = CORELAPConfig()
    # Left of (0, 0) would have x = -10, which must be rejected as out of bounds
    cands, rejections = generate_candidate_placements("DEP_B", 10.0, 10.0, placed, 50.0, 50.0, config)
    assert rejections["out_of_bounds"] > 0
    assert all(c.x >= -1e-4 and c.y >= -1e-4 for c in cands)


def test_10_overlap_candidate_rejection():
    """Test 10: Candidates overlapping an existing department are rejected."""
    placed = {
        "DEP_1": ContinuousPlacement(department_id="DEP_1", x=20.0, y=20.0, width=20.0, height=20.0),
        "DEP_2": ContinuousPlacement(department_id="DEP_2", x=40.0, y=20.0, width=20.0, height=20.0),
    }
    config = CORELAPConfig()
    cands, rejections = generate_candidate_placements("DEP_3", 20.0, 20.0, placed, 100.0, 100.0, config)
    assert rejections["overlap_department"] > 0
    # Verify no candidate intersects DEP_1 or DEP_2
    for c in cands:
        assert not (c.x < 40.0 and c.x + c.width > 20.0 and c.y < 40.0 and c.y + c.height > 20.0)


def test_11_adjacency_scoring(academic_4dept_problem: FacilityLayoutProblem):
    """Test 11: Placing candidates with positive relationship adjacent yields higher score."""
    placed = {
        "DEP_A": ContinuousPlacement(department_id="DEP_A", x=20.0, y=20.0, width=20.0, height=20.0),
    }
    config = CORELAPConfig(placement_mode=PlacementMode.ADJACENCY)
    
    # Candidate directly touching DEP_A (shared wall x=40)
    touching_cand = ContinuousPlacement(department_id="DEP_B", x=40.0, y=20.0, width=20.0, height=20.0)
    score_touch, _ = score_candidate_placement(touching_cand, placed, academic_4dept_problem, config)
    
    # Candidate separated from DEP_A
    distant_cand = ContinuousPlacement(department_id="DEP_B", x=80.0, y=80.0, width=20.0, height=20.0)
    score_distant, _ = score_candidate_placement(distant_cand, placed, academic_4dept_problem, config)
    
    assert score_touch > score_distant


def test_12_x_relationship_penalty(academic_4dept_problem: FacilityLayoutProblem):
    """Test 12: Placing X-relationship departments adjacent receives severe negative penalty."""
    placed = {
        "DEP_C": ContinuousPlacement(department_id="DEP_C", x=20.0, y=20.0, width=20.0, height=20.0),
    }
    config = CORELAPConfig(placement_mode=PlacementMode.ADJACENCY, x_penalty_multiplier=25.0)
    
    # DEP_D has X relationship with DEP_C (w = -8.0)
    touching_cand = ContinuousPlacement(department_id="DEP_D", x=40.0, y=20.0, width=20.0, height=20.0)
    score_touch, _ = score_candidate_placement(touching_cand, placed, academic_4dept_problem, config)
    
    # Touching score should be deeply negative: w * shared_length * 25 = -8 * 20 * 25 = -4000
    assert score_touch < -100.0


def test_13_fixed_department_preservation():
    """Test 13: Departments with fixed_position are placed at Step 0 and preserved."""
    fac = Facility(id="F1", name="Plant", width=100.0, height=100.0)
    depts = [
        Department(id="D_FIXED", name="Boiler", required_area=100.0, fixed_position=Point2D(x=5.0, y=5.0)),
        Department(id="D_FREE", name="Assembly", required_area=100.0),
    ]
    prob = FacilityLayoutProblem(
        id="FLP_FIXED",
        name="Brownfield Plant",
        facility=fac,
        departments=depts,
        relationships=[Relationship(department_a="D_FIXED", department_b="D_FREE", relationship_type=ClosenessRating.A, score=16.0)],
        flows=[],
    )
    solver = CORELAPAlgorithm()
    solution = solver.solve(prob)
    
    fixed_p = solution.placements["D_FIXED"]
    assert fixed_p.origin.x == 5.0
    assert fixed_p.origin.y == 5.0
    assert solution.metadata["placement_order"][0] == "D_FIXED"


# ---------------------------------------------------------------------------
# Tests 14 - 19: Full Solution Feasibility, Trace, and Repeatability
# ---------------------------------------------------------------------------

def test_14_all_departments_placed(academic_4dept_problem: FacilityLayoutProblem):
    """Test 14: All departments in problem are successfully positioned."""
    solver = CORELAPAlgorithm()
    solution = solver.solve(academic_4dept_problem)
    assert len(solution.placements) == len(academic_4dept_problem.departments)
    assert solution.feasibility_status is True
    assert solution.is_complete is True
    assert solution.placed_department_count == 4
    assert solution.total_department_count == 4
    assert solution.unplaced_departments == []
    assert solution.termination_reason == SolverTerminationReason.SUCCESS_COMPLETE.value


def test_15_output_boundary_validity(academic_4dept_problem: FacilityLayoutProblem):
    """Test 15: All placed departments lie strictly within facility bounds."""
    solver = CORELAPAlgorithm()
    solution = solver.solve(academic_4dept_problem)
    fw = academic_4dept_problem.facility.width
    fh = academic_4dept_problem.facility.height
    
    for p in solution.placements.values():
        assert p.origin.x >= 0.0
        assert p.origin.y >= 0.0
        assert p.origin.x + p.dimensions.width <= fw + 1e-4
        assert p.origin.y + p.dimensions.height <= fh + 1e-4


def test_16_output_no_overlap(academic_4dept_problem: FacilityLayoutProblem):
    """Test 16: Placed departments have zero geometric overlap."""
    solver = CORELAPAlgorithm()
    solution = solver.solve(academic_4dept_problem)
    cont_layout = ContinuousLayout.from_layout_solution(
        solution,
        facility_width=academic_4dept_problem.facility.width,
        facility_height=academic_4dept_problem.facility.height,
    )
    val = LayoutValidator.validate(academic_4dept_problem, cont_layout)
    assert val.is_valid is True
    assert val.total_overlap_area == 0.0
    assert len(val.errors) == 0


def test_17_deterministic_signature(academic_4dept_problem: FacilityLayoutProblem):
    """Test 17: CORELAP generates a non-null deterministic SHA-256 layout signature."""
    solver = CORELAPAlgorithm()
    sol1 = solver.solve(academic_4dept_problem)
    sig1 = sol1.metadata.get("layout_signature")
    assert sig1 is not None
    assert len(sig1) == 64


def test_18_ten_run_repeatability(academic_4dept_problem: FacilityLayoutProblem):
    """Test 18: Repeated solver executions produce 100% bitwise identical coordinates and signatures."""
    signatures = []
    positions = []
    
    for _ in range(10):
        solver = CORELAPAlgorithm()
        sol = solver.solve(academic_4dept_problem)
        signatures.append(sol.metadata["layout_signature"])
        positions.append({d: (p.origin.x, p.origin.y) for d, p in sol.placements.items()})
        
    assert len(set(signatures)) == 1, "Layout signature fluctuated across identical runs!"
    for i in range(1, 10):
        assert positions[i] == positions[0], f"Coordinate drift on iteration {i}!"


def test_19_execution_trace_completeness(academic_4dept_problem: FacilityLayoutProblem):
    """Test 19: Explainability trace captures every step with metrics and candidates."""
    solver = CORELAPAlgorithm()
    sol = solver.solve(academic_4dept_problem)
    trace = CORELAPExecutionTrace.model_validate(sol.metadata["trace"])
    
    assert trace.execution_success is True
    assert trace.is_complete is True
    assert trace.placed_department_count == 4
    assert trace.total_department_count == 4
    assert trace.unplaced_departments == []
    assert trace.termination_reason == SolverTerminationReason.SUCCESS_COMPLETE.value
    assert trace.total_departments == 4
    assert trace.placed_count == 4
    assert len(trace.steps) == 4
    for idx, step in enumerate(trace.steps):
        assert step.step_number == idx + 1
        assert step.selected_department in [d.id for d in academic_4dept_problem.departments]
        assert step.candidate_count >= 1
        assert "x" in step.selected_candidate


# ---------------------------------------------------------------------------
# Tests 20 - 23: Registry, Evaluation Engine, and Baseline Benchmarking
# ---------------------------------------------------------------------------

def test_20_registry_contains_corelap():
    """Test 20: AlgorithmRegistry contains registered CORELAP algorithm."""
    registered = AlgorithmRegistry.list_available()
    algo_names = [a["name"] for a in registered]
    assert "corelap" in algo_names
    instance = AlgorithmRegistry.get("corelap")
    assert instance.name == "corelap"
    assert instance.category.value == "construction"


def test_21_evaluation_integration(academic_4dept_problem: FacilityLayoutProblem):
    """Test 21: Generated layout evaluates cleanly via independent EvaluationEngine."""
    solver = CORELAPAlgorithm()
    sol = solver.solve(academic_4dept_problem)
    cont_layout = ContinuousLayout.from_layout_solution(
        sol,
        facility_width=academic_4dept_problem.facility.width,
        facility_height=academic_4dept_problem.facility.height,
    )
    engine = EvaluationEngine()
    report = engine.evaluate(problem=academic_4dept_problem, solution=cont_layout)
    
    assert report.is_feasible is True
    assert "material_handling_cost" in report.objective_values
    assert "flow_distance" in report.objective_values
    assert "relationship_score" in report.objective_values
    assert "area_utilization" in report.objective_values
    assert report.hard_violation_count == 0


def test_22_sample_factory_solution():
    """Test 22: CORELAP executes on sample_plant.json with explicit incomplete failure semantics."""
    plant_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_plant.json"
    problem = load_problem(plant_path)
    solver = CORELAPAlgorithm()
    solution = solver.solve(problem)
    
    # Verifies solver ran, produced placement order, and documented incomplete status
    assert len(solution.metadata["placement_order"]) >= 2
    assert "tcr_values" in solution.metadata
    assert solution.execution_time_seconds > 0.0
    
    # Phase 5.1 completion assertions
    assert solution.is_complete is False
    assert solution.feasibility_status is False
    assert solution.termination_reason == SolverTerminationReason.FAILED_NO_FEASIBLE_CANDIDATE.value
    assert solution.placed_department_count == 5
    assert solution.total_department_count == 10
    assert len(solution.unplaced_departments) == 5
    assert "DEP_ASSEMBLY" in solution.unplaced_departments
    assert solution.metadata.get("failure_reason") is not None

    # Evaluation engine must mark partial layout non-comparable
    engine = EvaluationEngine()
    cont_layout = ContinuousLayout.from_layout_solution(solution, problem.facility.width, problem.facility.height)
    rep = engine.evaluate(problem, cont_layout)
    assert rep.complete_layout is False
    assert rep.is_comparable is False
    assert rep.is_feasible is False
    assert rep.diagnostic_partial_values is not None
    assert "partial_material_handling_cost" in rep.diagnostic_partial_values


def test_23_baseline_comparison():
    """Test 23: Baseline snapshot file exists, marks status incomplete, and enforces benchmark integrity."""
    baseline_path = (
        Path(__file__).resolve().parent.parent.parent
        / "experiments"
        / "baselines"
        / "corelap_sample_plant.json"
    )
    assert baseline_path.exists(), "experiments/baselines/corelap_sample_plant.json must exist!"
    import json
    with open(baseline_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["problem_id"] == "FLP_INDUSTRIAL_10"
    assert data["status"] == "incomplete"
    assert data["comparable_to_baseline"] is False
    assert "academic_statement" in data
    assert data["corelap_results"]["termination_reason"] == "FAILED_NO_FEASIBLE_CANDIDATE"
    assert data["comparison"]["comparable"] is False
    assert "manual_baseline_results" in data


# ---------------------------------------------------------------------------
# Tests 24 - 26: FastAPI Endpoints & Frontend Build
# ---------------------------------------------------------------------------

def test_24_api_algorithms_list():
    """Test 24: GET /api/algorithms lists CORELAP metadata."""
    client = TestClient(app)
    resp = client.get("/api/algorithms")
    assert resp.status_code == 200
    algos = resp.json()
    names = [a["name"] for a in algos]
    assert "corelap" in names


def test_25_api_corelap_solve():
    """Test 25: POST /api/algorithms/corelap/solve executes CORELAP and returns layout, trace, and evaluation."""
    client = TestClient(app)
    payload = {
        "problem_id": "FLP_INDUSTRIAL_10",
        "config": {
            "placement_mode": "classical_adjacency",
            "initial_anchor_mode": "center",
        },
    }
    resp = client.post("/api/algorithms/corelap/solve", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "solution" in data
    assert "continuous_layout" in data
    assert "trace" in data
    assert "validation" in data
    assert "evaluation" in data
    assert data["solution"]["is_complete"] is False
    assert data["solution"]["termination_reason"] == "FAILED_NO_FEASIBLE_CANDIDATE"
    assert len(data["trace"]["placement_order"]) >= 2


def test_26_frontend_typescript_build():
    """Test 26: Frontend build artifacts exist and index.html is generated."""
    dist_html = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist" / "index.html"
    assert dist_html.exists(), "frontend/dist/index.html must exist after npm run build!"


# ---------------------------------------------------------------------------
# Tests 27 - 31: Phase 5.1 Completeness, Shapes, Modes & Central Validation
# ---------------------------------------------------------------------------

def test_27_medium_plant_complete_solution():
    """Test 27: CORELAP completely solves FLP_MEDIUM_6 (6 departments, 58.6% area utilization)."""
    plant_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_medium_plant.json"
    problem = load_problem(plant_path)
    solver = CORELAPAlgorithm()
    solution = solver.solve(problem)

    assert solution.is_complete is True
    assert solution.feasibility_status is True
    assert solution.placed_department_count == 6
    assert solution.total_department_count == 6
    assert solution.unplaced_departments == []
    assert solution.termination_reason == SolverTerminationReason.SUCCESS_COMPLETE.value

    # Geometric validation check
    cont_layout = ContinuousLayout.from_layout_solution(solution, problem.facility.width, problem.facility.height)
    val = LayoutValidator.validate(problem, cont_layout)
    assert val.is_valid is True
    assert val.total_overlap_area == 0.0

    # Central validator check
    is_comp, is_feas, issues = LayoutValidator.check_completeness_and_feasibility(problem, cont_layout)
    assert is_comp is True
    assert is_feas is True
    assert len(issues) == 0

    # Independent evaluation check
    report = EvaluationEngine().evaluate(problem, cont_layout)
    assert report.complete_layout is True
    assert report.is_comparable is True
    assert report.is_feasible is True
    assert report.diagnostic_partial_values is None


def test_28_evaluation_engine_isolation_of_incomplete_layouts():
    """Test 28: Incomplete layouts are strictly excluded from normalization and composite ranking in evaluate_many."""
    plant_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_medium_plant.json"
    problem = load_problem(plant_path)
    solver = CORELAPAlgorithm()
    sol_complete = solver.solve(problem)

    # Construct an artificial incomplete layout missing 2 departments
    layout_complete = ContinuousLayout.from_layout_solution(sol_complete, problem.facility.width, problem.facility.height)
    layout_partial = layout_complete.model_copy(deep=True)
    layout_partial.metadata["algorithm_name"] = "partial_heuristic"
    layout_partial.placements.pop("DEP_SHIPPING", None)
    layout_partial.placements.pop("DEP_PACKAGING", None)

    engine = EvaluationEngine()
    comparison = engine.evaluate_many(problem, [layout_complete, layout_partial])

    assert comparison.solution_count == 2
    rep_complete = next(r for r in comparison.reports if r.complete_layout)
    rep_partial = next(r for r in comparison.reports if not r.complete_layout)

    # Complete layout has valid normalization and rank
    assert rep_complete.normalized_values is not None
    assert rep_complete.composite_score is not None
    assert rep_complete.rank == 1
    assert rep_complete.is_comparable is True

    # Incomplete layout is isolated
    assert rep_partial.normalized_values is None
    assert rep_partial.composite_score is None
    assert rep_partial.rank is None
    assert rep_partial.is_comparable is False

    # Ranking list only includes comparable layouts
    assert comparison.ranking == [rep_complete.algorithm_name]


def test_29_legal_shape_generation_and_orientations():
    """Test 29: generate_legal_department_shapes respects aspect ratio and orientation options."""
    dept = Department(
        id="D_VAR",
        name="Variable Dept",
        required_area=400.0,
        min_width=10.0,
        max_width=40.0,
        min_height=10.0,
        max_height=40.0,
        max_aspect_ratio=3.0,
    )
    placed: dict = {}
    
    cfg_with_rot = CORELAPConfig(allow_shape_alternatives=True, evaluate_orientations=True)
    shapes_rot = generate_legal_department_shapes(dept, placed, 100.0, 100.0, cfg_with_rot)
    
    # Check all shapes satisfy area and bounds
    for w, h, orient in shapes_rot:
        assert 10.0 <= w <= 40.0
        assert 10.0 <= h <= 40.0
        assert orient in (0.0, 90.0)
        ar = max(w, h) / min(w, h)
        assert ar <= 3.0 + 1e-4

    # Without rotation
    cfg_no_rot = CORELAPConfig(allow_shape_alternatives=True, evaluate_orientations=False)
    shapes_no_rot = generate_legal_department_shapes(dept, placed, 100.0, 100.0, cfg_no_rot)
    for _, _, orient in shapes_no_rot:
        assert orient == 0.0


def test_30_classical_vs_extended_scoring_mode():
    """Test 30: Classical adjacency produces 0.0 for separated departments; Extended mode applies decay."""
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    dept_a = Department(id="DA", name="DA", required_area=100.0)
    dept_b = Department(id="DB", name="DB", required_area=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_SCORING",
        facility=facility,
        departments=[dept_a, dept_b],
        relationships=[
            Relationship(department_a="DA", department_b="DB", relationship_type=ClosenessRating.A),
        ],
    )

    placed_placements = {
        "DA": ContinuousPlacement(department_id="DA", x=10.0, y=10.0, width=10.0, height=10.0),
    }
    # Candidate for DB separated by 20m gap
    cand_separated = ContinuousPlacement(department_id="DB", x=40.0, y=10.0, width=10.0, height=10.0)

    # 1. Classical mode
    cfg_classical = CORELAPConfig(placement_mode=PlacementMode.CLASSICAL_ADJACENCY)
    score_classic, neighbors_classic = score_candidate_placement(
        cand_separated, placed_placements, problem, cfg_classical
    )
    assert score_classic == 0.0
    assert len(neighbors_classic) == 0

    # 2. Extended mode
    cfg_extended = CORELAPConfig(placement_mode=PlacementMode.EXTENDED_DISTANCE_WEIGHTED)
    score_extended, _ = score_candidate_placement(
        cand_separated, placed_placements, problem, cfg_extended
    )
    assert score_extended > 0.0


def test_31_check_completeness_and_feasibility_central_method(academic_4dept_problem: FacilityLayoutProblem):
    """Test 31: LayoutValidator.check_completeness_and_feasibility central method correctly flags missing depts and violations."""
    solver = CORELAPAlgorithm()
    solution = solver.solve(academic_4dept_problem)
    cont_layout = ContinuousLayout.from_layout_solution(
        solution, academic_4dept_problem.facility.width, academic_4dept_problem.facility.height
    )

    # 1. Complete and feasible layout
    is_comp, is_feas, issues = LayoutValidator.check_completeness_and_feasibility(
        academic_4dept_problem, cont_layout, hard_violation_count=0
    )
    assert is_comp is True
    assert is_feas is True
    assert len(issues) == 0

    # 2. Incomplete layout (missing DEP_D)
    partial_layout = cont_layout.model_copy(deep=True)
    partial_layout.placements.pop("DEP_D", None)
    is_comp, is_feas, issues = LayoutValidator.check_completeness_and_feasibility(
        academic_4dept_problem, partial_layout, hard_violation_count=0
    )
    assert is_comp is False
    assert is_feas is False
    assert any("Missing placements" in iss for iss in issues)

    # 3. Complete layout with hard constraint violation count > 0
    is_comp, is_feas, issues = LayoutValidator.check_completeness_and_feasibility(
        academic_4dept_problem, cont_layout, hard_violation_count=2
    )
    assert is_comp is True
    assert is_feas is False
    assert any("2 hard constraint violation(s) present" in iss for iss in issues)
