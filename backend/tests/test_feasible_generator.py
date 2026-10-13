"""Unit, integration, and benchmark tests for Phase 8: Feasible Rectangular Layout Generator."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.geometry import Point2D, Dimensions2D, BoundingBox, ReservedZone
from app.models.facility import Facility
from app.models.department import Department
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution, SolverTerminationReason
from app.feasibility.representations import SlicingCutType, SlicingNode, SlicingTree
from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.generator.models import (
    GeneratorConfig,
    GeneratorResult,
    GeneratorStrategy,
    DepartmentOrderingStrategy,
    GeneratorTerminationReason,
)
from app.algorithms.generator.pre_feasibility import PreFeasibilityAnalyzer
from app.algorithms.generator.slicing_decoder import AreaPreservingSlicingDecoder
from app.algorithms.generator.search_free_rectangle import FreeRectangleSearchEngine
from app.algorithms.generator.search_guillotine_packing import GuillotineRowPackingEngine
from app.algorithms.generator.solver import FeasibleLayoutGenerator
from app.services.problem_service import problem_service
from app.services.layout_validator import LayoutValidator
from app.evaluation.engine import EvaluationEngine


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def academic_4_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_ACADEMIC_4")


@pytest.fixture
def medium_6_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_MEDIUM_6")


@pytest.fixture
def industrial_10_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_INDUSTRIAL_10")


# ---------------------------------------------------------------------------
# 1. Pre-Feasibility Analysis Tests
# ---------------------------------------------------------------------------

def test_pre_feasibility_valid_problem(academic_4_problem: FacilityLayoutProblem):
    """Pre-feasibility analysis approves a standard valid layout problem."""
    report = PreFeasibilityAnalyzer.analyze(academic_4_problem)
    assert report.is_feasible is True
    assert len(report.errors) == 0
    assert report.facility_available_area >= report.total_required_area


def test_pre_feasibility_exceeded_facility_area():
    """Problem construction itself enforces total area capacity and raises ValidationError."""
    facility = Facility(id="FAC_SMALL", name="Small Plant", width=50.0, height=50.0)
    depts = [
        Department(id="D1", name="D1", required_area=2000.0),
        Department(id="D2", name="D2", required_area=1000.0),
    ]
    with pytest.raises(ValidationError) as exc_info:
        FacilityLayoutProblem(
            id="FLP_OVERFLOW",
            name="Overflow Problem",
            facility=facility,
            departments=depts,
        )
    assert "exceeds facility area" in str(exc_info.value)


def test_pre_feasibility_department_dimension_unfit():
    """Pre-feasibility detects departments that cannot physically fit inside the facility."""
    facility = Facility(id="FAC_NARROW", name="Narrow Plant", width=10.0, height=50.0)
    depts = [
        Department(id="D1", name="D1", required_area=200.0, min_width=15.0),  # min_width > facility width!
    ]
    prob = FacilityLayoutProblem(
        id="FLP_UNFIT",
        name="Unfit Dimension",
        facility=facility,
        departments=depts,
    )
    report = PreFeasibilityAnalyzer.analyze(prob)
    assert report.is_feasible is False
    assert any("NO legal rectangular dimensions" in err for err in report.errors)


def test_pre_feasibility_out_of_bounds_fixed_department():
    """Pre-feasibility flags fixed departments placed outside facility boundaries."""
    facility = Facility(id="FAC_TEST", name="Plant", width=100.0, height=100.0)
    depts = [
        Department(
            id="D1",
            name="D1",
            required_area=100.0,
            fixed_position=Point2D(x=150.0, y=50.0),  # x > width!
        ),
    ]
    prob = FacilityLayoutProblem(
        id="FLP_OUT_OF_BOUNDS",
        name="Out of bounds fixed",
        facility=facility,
        departments=depts,
    )
    report = PreFeasibilityAnalyzer.analyze(prob)
    assert report.is_feasible is False
    assert any("outside facility boundaries" in err for err in report.errors)


# ---------------------------------------------------------------------------
# 2. Slicing Tree Decoder Tests
# ---------------------------------------------------------------------------

def test_slicing_tree_decoder_area_preservation():
    """AreaPreservingSlicingDecoder partitions space with exact area ratios."""
    facility = Facility(id="FAC_20x20", name="Square Facility", width=20.0, height=20.0)
    depts = [
        Department(id="D1", name="D1", required_area=100.0, min_width=5.0, max_width=15.0, max_aspect_ratio=2.0),
        Department(id="D2", name="D2", required_area=100.0, min_width=5.0, max_width=15.0, max_aspect_ratio=2.0),
        Department(id="D3", name="D3", required_area=100.0, min_width=5.0, max_width=15.0, max_aspect_ratio=2.0),
        Department(id="D4", name="D4", required_area=100.0, min_width=5.0, max_width=15.0, max_aspect_ratio=2.0),
    ]
    prob = FacilityLayoutProblem(
        id="FLP_SQUARE_4",
        name="Square 4 Problem",
        facility=facility,
        departments=depts,
    )

    tree = SlicingTree(
        root=SlicingNode(
            cut_type=SlicingCutType.HORIZONTAL,
            cut_ratio=0.5,
            left=SlicingNode(
                cut_type=SlicingCutType.VERTICAL,
                cut_ratio=0.5,
                left=SlicingNode(department_id="D1"),
                right=SlicingNode(department_id="D2"),
            ),
            right=SlicingNode(
                cut_type=SlicingCutType.VERTICAL,
                cut_ratio=0.5,
                left=SlicingNode(department_id="D3"),
                right=SlicingNode(department_id="D4"),
            ),
        )
    )

    layout, is_valid, violations = AreaPreservingSlicingDecoder.decode(tree, prob)

    assert is_valid is True
    assert len(violations) == 0
    assert len(layout.placements) == 4
    for p in layout.placements.values():
        assert abs(p.width * p.height - 100.0) < 1e-2


def test_slicing_tree_decoder_detects_aspect_ratio_violation():
    """Slicing tree decoder rejects placements that violate department aspect ratio bounds."""
    # 100m wide by 4m high facility (400 m² total)
    facility = Facility(id="FAC_STRIP", name="Strip Facility", width=100.0, height=4.0)
    depts = [
        Department(id="D1", name="D1", required_area=100.0, max_aspect_ratio=2.0),
        Department(id="D2", name="D2", required_area=100.0, max_aspect_ratio=2.0),
        Department(id="D3", name="D3", required_area=100.0, max_aspect_ratio=2.0),
        Department(id="D4", name="D4", required_area=100.0, max_aspect_ratio=2.0),
    ]
    prob = FacilityLayoutProblem(
        id="FLP_STRIP_4",
        name="Strip 4 Problem",
        facility=facility,
        departments=depts,
    )

    # 4 vertical slices: each will be 25m wide by 4m high -> aspect ratio 25/4 = 6.25 > 2.0 max!
    tree = SlicingTree(
        root=SlicingNode(
            cut_type=SlicingCutType.VERTICAL,
            cut_ratio=0.5,
            left=SlicingNode(
                cut_type=SlicingCutType.VERTICAL,
                cut_ratio=0.5,
                left=SlicingNode(department_id="D1"),
                right=SlicingNode(department_id="D2"),
            ),
            right=SlicingNode(
                cut_type=SlicingCutType.VERTICAL,
                cut_ratio=0.5,
                left=SlicingNode(department_id="D3"),
                right=SlicingNode(department_id="D4"),
            ),
        )
    )

    layout, is_valid, violations = AreaPreservingSlicingDecoder.decode(tree, prob)
    assert is_valid is False
    assert any("aspect ratio" in v.lower() for v in violations)


# ---------------------------------------------------------------------------
# 3. Free Rectangle Search Engine Tests
# ---------------------------------------------------------------------------

def test_free_rectangle_search_academic_4(academic_4_problem: FacilityLayoutProblem):
    """Free rectangle search successfully finds a feasible layout for Academic 4 problem."""
    config = GeneratorConfig(
        strategy=GeneratorStrategy.FREE_RECTANGLE_DFS,
        max_nodes=1000,
        max_backtracks=500,
    )
    result = FreeRectangleSearchEngine.search(academic_4_problem, config)

    assert result.success is True
    assert result.complete is True
    assert result.placed_department_count == 4
    assert result.termination_reason == GeneratorTerminationReason.SUCCESS_FEASIBLE_FOUND
    assert result.layout is not None

    # Validate geometric legality
    val = LayoutValidator.validate(academic_4_problem, result.layout)
    assert val.is_valid is True
    assert len(val.errors) == 0
    assert val.total_overlap_area == 0.0


def test_free_rectangle_search_medium_6(medium_6_problem: FacilityLayoutProblem):
    """Free rectangle search successfully finds 100% feasible layout for Medium 6 problem."""
    config = GeneratorConfig(
        strategy=GeneratorStrategy.FREE_RECTANGLE_DFS,
        max_nodes=5000,
        max_backtracks=2000,
    )
    result = FreeRectangleSearchEngine.search(medium_6_problem, config)

    assert result.success is True
    assert result.complete is True
    assert result.placed_department_count == 6
    assert result.termination_reason == GeneratorTerminationReason.SUCCESS_FEASIBLE_FOUND

    val = LayoutValidator.validate(medium_6_problem, result.layout)
    assert val.is_valid is True
    assert len(val.errors) == 0
    assert val.total_overlap_area == 0.0


def test_free_rectangle_search_budget_exhaustion(industrial_10_problem: FacilityLayoutProblem):
    """Free rectangle search cleanly terminates with SEARCH_BUDGET_EXHAUSTED when budget is tiny."""
    config = GeneratorConfig(
        strategy=GeneratorStrategy.FREE_RECTANGLE_DFS,
        max_nodes=10,  # minimum valid budget
        max_backtracks=0,
    )
    result = FreeRectangleSearchEngine.search(industrial_10_problem, config)

    assert result.success is False
    assert result.complete is False
    assert result.termination_reason == GeneratorTerminationReason.SEARCH_BUDGET_EXHAUSTED


# ---------------------------------------------------------------------------
# 4. Guillotine Row Packing Engine Tests
# ---------------------------------------------------------------------------

def test_guillotine_packing_academic_4(academic_4_problem: FacilityLayoutProblem):
    """Guillotine row packing produces 100% complete and valid layout for Academic 4."""
    config = GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)
    result = GuillotineRowPackingEngine.search(academic_4_problem, config)

    assert result.success is True
    assert result.complete is True
    assert result.placed_department_count == 4
    assert result.layout is not None

    val = LayoutValidator.validate(academic_4_problem, result.layout)
    assert val.is_valid is True
    assert len(val.errors) == 0


def test_guillotine_packing_industrial_10_feasibility(industrial_10_problem: FacilityLayoutProblem):
    """Guillotine row packing solves FLP_INDUSTRIAL_10 with 10/10 depts, 0 overlaps, 0 hard violations."""
    config = GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)
    result = GuillotineRowPackingEngine.search(industrial_10_problem, config)

    assert result.success is True, f"Failed with reason: {result.termination_reason}"
    assert result.complete is True
    assert result.placed_department_count == 10
    assert result.termination_reason == GeneratorTerminationReason.SUCCESS_FEASIBLE_FOUND
    assert result.layout is not None

    # Strict engineering validation
    val = LayoutValidator.validate(industrial_10_problem, result.layout)
    assert val.is_valid is True
    assert len(val.errors) == 0
    assert val.total_overlap_area == 0.0


# ---------------------------------------------------------------------------
# 5. Solver & Algorithm Registry Integration Tests
# ---------------------------------------------------------------------------

def test_algorithm_registry_contains_feasible_generator():
    """FeasibleLayoutGenerator is properly registered in AlgorithmRegistry under standard keys."""
    algo1 = AlgorithmRegistry.get("feasible_layout_generator")
    assert isinstance(algo1, FeasibleLayoutGenerator)

    algo2 = AlgorithmRegistry.get("feasible_generator")
    assert isinstance(algo2, FeasibleLayoutGenerator)


def test_feasible_layout_generator_solve_interface(academic_4_problem: FacilityLayoutProblem):
    """FeasibleLayoutGenerator implements the standard BaseLayoutAlgorithm interface."""
    solver = FeasibleLayoutGenerator()
    solution = solver.solve(academic_4_problem)

    assert isinstance(solution, LayoutSolution)
    assert solution.feasibility_status is True
    assert solution.is_complete is True
    assert len(solution.placements) == 4


def test_feasible_layout_generator_solve_with_result(industrial_10_problem: FacilityLayoutProblem):
    """solve_with_result returns both standard LayoutSolution and rich GeneratorResult."""
    solver = FeasibleLayoutGenerator()
    config = GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)
    solution, result = solver.solve_with_result(industrial_10_problem, config=config)

    assert solution.feasibility_status is True
    assert result.success is True
    assert result.placed_department_count == 10
    assert result.runtime_seconds < 1.0  # Must be fast and efficient (<1s)


# ---------------------------------------------------------------------------
# 6. Geometric Constraints Compliance Tests
# ---------------------------------------------------------------------------

def test_geometric_compliance_dimensions_and_aspect_ratio(industrial_10_problem: FacilityLayoutProblem):
    """All placed departments strictly satisfy area, min/max dimension, and aspect ratio bounds."""
    solver = FeasibleLayoutGenerator()
    config = GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)
    _, result = solver.solve_with_result(industrial_10_problem, config=config)

    layout = result.layout
    assert layout is not None
    depts_map = {d.id: d for d in industrial_10_problem.departments}

    for p in layout.placements.values():
        dept = depts_map[p.department_id]
        # Area tolerance 5%
        assert abs(p.width * p.height - dept.required_area) / dept.required_area < 0.05
        # Min/max dimension constraints
        if dept.min_width:
            assert p.width >= dept.min_width - 1e-4
        if dept.max_width:
            assert p.width <= dept.max_width + 1e-4
        if dept.min_height:
            assert p.height >= dept.min_height - 1e-4
        if dept.max_height:
            assert p.height <= dept.max_height + 1e-4
        # Aspect ratio constraint
        aspect_ratio = max(p.width / p.height, p.height / p.width)
        max_ar = dept.max_aspect_ratio or 3.0
        assert aspect_ratio <= max_ar + 1e-3


def test_geometric_compliance_non_overlapping(industrial_10_problem: FacilityLayoutProblem):
    """Pairwise bounding box overlap between any two departments is zero."""
    solver = FeasibleLayoutGenerator()
    config = GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)
    _, result = solver.solve_with_result(industrial_10_problem, config=config)

    placements = list(result.layout.placements.values())
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            d1, d2 = placements[i], placements[j]
            # Check overlap on x and y
            x_overlap = max(0.0, min(d1.right, d2.right) - max(d1.left, d2.left))
            y_overlap = max(0.0, min(d1.top, d2.top) - max(d1.bottom, d2.bottom))
            overlap_area = x_overlap * y_overlap
            assert overlap_area < 1e-3, f"Overlap between {d1.department_id} and {d2.department_id}: {overlap_area}"


def test_geometric_compliance_facility_boundary(industrial_10_problem: FacilityLayoutProblem):
    """All placed departments reside strictly within the facility boundary."""
    solver = FeasibleLayoutGenerator()
    config = GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)
    _, result = solver.solve_with_result(industrial_10_problem, config=config)

    fac_w = industrial_10_problem.facility.width
    fac_h = industrial_10_problem.facility.height

    for p in result.layout.placements.values():
        assert p.left >= -1e-4
        assert p.bottom >= -1e-4
        assert p.right <= fac_w + 1e-4
        assert p.top <= fac_h + 1e-4


# ---------------------------------------------------------------------------
# 7. Baseline Independence & Determinism Tests
# ---------------------------------------------------------------------------

def test_deterministic_reproducibility(industrial_10_problem: FacilityLayoutProblem):
    """Running FeasibleLayoutGenerator with identical config yields bitwise identical layouts."""
    solver = FeasibleLayoutGenerator()
    config = GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)

    _, res1 = solver.solve_with_result(industrial_10_problem, config=config)
    _, res2 = solver.solve_with_result(industrial_10_problem, config=config)

    assert len(res1.layout.placements) == len(res2.layout.placements)
    for k in res1.layout.placements:
        p1 = res1.layout.placements[k]
        p2 = res2.layout.placements[k]
        assert p1.department_id == p2.department_id
        assert abs(p1.x - p2.x) < 1e-9
        assert abs(p1.y - p2.y) < 1e-9
        assert abs(p1.width - p2.width) < 1e-9
        assert abs(p1.height - p2.height) < 1e-9


def test_baseline_independence(industrial_10_problem: FacilityLayoutProblem):
    """The generator does not read, reference, or duplicate sample_layout.json baseline coordinates."""
    solver = FeasibleLayoutGenerator()
    config = GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)
    _, result = solver.solve_with_result(industrial_10_problem, config=config)

    baseline_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_layout.json"
    assert baseline_path.exists(), "sample_layout.json should exist for comparison"

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)
    baseline_coords = {
        k: (v["x"], v["y"])
        for k, v in baseline_data.get("placements", {}).items()
    }
    generated_coords = {
        d.department_id: (d.x, d.y)
        for d in result.layout.placements.values()
    }
    differences = [
        abs(generated_coords[k][0] - baseline_coords[k][0]) > 0.1 or
        abs(generated_coords[k][1] - baseline_coords[k][1]) > 0.1
        for k in baseline_coords if k in generated_coords
    ]
    assert len(differences) > 0, "Departments should match problem IDs"
    assert any(differences), "Generated layout must not be an identical copy of the manual baseline!"


# ---------------------------------------------------------------------------
# 8. Multi-Criteria Evaluation Verification
# ---------------------------------------------------------------------------

def test_evaluation_engine_metrics_on_generated_layout(industrial_10_problem: FacilityLayoutProblem):
    """The generated layout can be fully evaluated with EvaluationEngine without errors."""
    solver = FeasibleLayoutGenerator()
    config = GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)
    _, result = solver.solve_with_result(industrial_10_problem, config=config)

    eval_engine = EvaluationEngine()
    report = eval_engine.evaluate(industrial_10_problem, result.layout)

    assert report.objective_values.get("material_handling_cost", 0.0) > 0.0
    assert report.objective_values.get("flow_distance", 0.0) > 0.0
    assert report.hard_violation_count == 0


# ---------------------------------------------------------------------------
# 9. API Endpoint Integration Tests
# ---------------------------------------------------------------------------

def test_api_feasible_generator_solve_academic_4(client: TestClient):
    """API endpoint returns 200 OK and feasible solution for FLP_ACADEMIC_4."""
    payload = {
        "problem_id": "FLP_ACADEMIC_4",
        "config": {
            "strategy": "guillotine_row_packing",
            "max_nodes": 500,
        },
    }
    response = client.post("/api/algorithms/feasible-generator/solve", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["result"]["success"] is True
    assert data["result"]["complete"] is True
    assert data["result"]["placed_department_count"] == 4
    assert data["validation"]["is_valid"] is True
    assert len(data["validation"]["errors"]) == 0
    assert data["evaluation"] is not None


def test_api_feasible_generator_solve_industrial_10(client: TestClient):
    """API endpoint returns 200 OK and feasible solution for FLP_INDUSTRIAL_10."""
    payload = {
        "problem_id": "FLP_INDUSTRIAL_10",
        "config": {
            "strategy": "guillotine_row_packing",
        },
    }
    response = client.post("/api/algorithms/feasible-generator/solve", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["result"]["success"] is True
    assert data["result"]["complete"] is True
    assert data["result"]["placed_department_count"] == 10
    assert data["validation"]["is_valid"] is True
    assert len(data["validation"]["errors"]) == 0
    assert data["evaluation"]["objective_values"]["material_handling_cost"] > 0


def test_api_feasible_generator_problem_not_found(client: TestClient):
    """API endpoint returns 404 when requested problem ID does not exist."""
    payload = {
        "problem_id": "NON_EXISTENT_PROBLEM_123",
    }
    response = client.post("/api/algorithms/feasible-generator/solve", json=payload)
    assert response.status_code == 404
