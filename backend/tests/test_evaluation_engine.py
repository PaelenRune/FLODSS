"""Comprehensive unit tests for the FLODSS Evaluation & Constraint Engine (Phase 4).

Covers:
- Directed Flow-Distance with exact hand calculations (Manhattan and Euclidean)
- Material Handling Cost with flow-specific costs and default fallbacks
- Asymmetric directed flows (A -> B != B -> A)
- Deterministic matrix precomputations (Distance, Flow, Relationship)
- Muther SLP relationship satisfaction (positive proximity reward, X proximity penalty)
- Floor area utilization (gross facility, reserved zones, net usable)
- Constraint Engine: Hard vs Soft classification, feasibility gating, penalty computations
- Specific checkers: NonOverlapping, Boundary, FixedPosition, MinDistance, MaxDistance, Adjacency, Separation
- Min-Max normalization, composite weighted ranking, and feasibility-first sorting
- Machine-readable top contributors breakdown
- EvaluationReport & ComparisonReport serialization
- Reproducibility and deterministic signature invariance
- FastAPI evaluation endpoints (/evaluate, /compare, /metrics)
- End-to-end integration on sample_plant.json and sample_layout.json
- Duplicate placement dictionary semantics and fixed orientation validation
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.geometry import Point2D, Dimensions2D, ReservedZone
from app.models.facility import Facility
from app.models.department import Department
from app.models.flow import Flow
from app.models.relationship import Relationship, ClosenessRating, RELATIONSHIP_DEFAULT_SCORES
from app.models.constraint import (
    Constraint,
    ConstraintType,
    ConstraintClassification,
    ConstraintViolation,
)
from app.models.problem import FacilityLayoutProblem, ObjectiveConfig, PrimaryObjective
from app.models.representation import (
    ContinuousLayout,
    ContinuousPlacement,
    LayoutRepresentationType,
)
from app.models.solution import LayoutSolution, DepartmentPlacement
from app.evaluation.config import EvaluationConfig, DistanceMetricType
from app.evaluation.matrices import (
    DistanceMatrixService,
    FlowMatrixService,
    RelationshipMatrixService,
)
from app.constraints.engine import ConstraintEngine
from app.constraints.checkers import (
    NonOverlappingChecker,
    BoundaryChecker,
    FixedPositionChecker,
    MinDistanceChecker,
    MaxDistanceChecker,
    AdjacencyChecker,
    SeparationChecker,
)
from app.evaluation.evaluators import (
    FlowDistanceEvaluator,
    MaterialHandlingCostEvaluator,
    RelationshipSatisfactionEvaluator,
    AreaUtilizationEvaluator,
    ConstraintPenaltyEvaluator,
)
from app.evaluation.engine import EvaluationEngine, EvaluationReport, ComparisonReport
from app.services.problem_loader import load_problem
from app.services.layout_normalizer import generate_layout_signature


# ---------------------------------------------------------------------------
# Test Fixtures for Exact Hand Calculations
# ---------------------------------------------------------------------------

@pytest.fixture
def exact_calc_setup():
    """Setup a 2-department problem with known hand-calculated distances and flows.
    
    Facility: 100 x 100
    Dept A: Origin (10, 10), Dimensions (20, 20) -> Centroid (20, 20)
    Dept B: Origin (40, 50), Dimensions (20, 20) -> Centroid (50, 60)
    
    Distance Vector (Centroid to Centroid):
      dx = |50 - 20| = 30
      dy = |60 - 20| = 40
      Manhattan = 30 + 40 = 70.0
      Euclidean = sqrt(30^2 + 40^2) = 50.0
      
    Flows:
      A -> B: quantity = 10, cost_per_unit_distance = 2.0
      B -> A: quantity = 5, cost_per_unit_distance = 3.0
      
    Hand Calculations:
      Manhattan Flow-Distance: 10 * 70 + 5 * 70 = 700 + 350 = 1050.0
      Manhattan MHC: (10 * 70 * 2.0) + (5 * 70 * 3.0) = 1400 + 1050 = 2450.0
      
      Euclidean Flow-Distance: 10 * 50 + 5 * 50 = 500 + 250 = 750.0
      Euclidean MHC: (10 * 50 * 2.0) + (5 * 50 * 3.0) = 1000 + 750 = 1750.0
    """
    facility = Facility(id="FAC_TEST", name="Test Plant", width=100.0, height=100.0)
    dept_a = Department(id="DEP_A", name="Dept A", required_area=400.0)
    dept_b = Department(id="DEP_B", name="Dept B", required_area=400.0)
    
    flows = [
        Flow(source_department="DEP_A", target_department="DEP_B", quantity=10.0, cost_per_unit_distance=2.0),
        Flow(source_department="DEP_B", target_department="DEP_A", quantity=5.0, cost_per_unit_distance=3.0),
    ]
    
    problem = FacilityLayoutProblem(
        id="PROB_EXACT",
        name="Exact Math Problem",
        facility=facility,
        departments=[dept_a, dept_b],
        flows=flows,
    )
    
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=10.0, y=10.0, width=20.0, height=20.0),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=40.0, y=50.0, width=20.0, height=20.0),
        },
    )
    
    return problem, layout


# ---------------------------------------------------------------------------
# 1. Flow-Distance and MHC Hand-Calculated Tests
# ---------------------------------------------------------------------------

def test_flow_distance_known_calculation(exact_calc_setup):
    """Test 1: Verify exact hand-calculated flow distance under Manhattan and Euclidean."""
    problem, layout = exact_calc_setup
    
    # Manhattan
    cfg_manhattan = EvaluationConfig(distance_metric=DistanceMetricType.MANHATTAN)
    eval_fd_man = FlowDistanceEvaluator(cfg_manhattan)
    res_man = eval_fd_man.evaluate(problem, layout)
    assert res_man.value == 1050.0
    
    # Euclidean
    cfg_euclidean = EvaluationConfig(distance_metric=DistanceMetricType.EUCLIDEAN)
    eval_fd_euc = FlowDistanceEvaluator(cfg_euclidean)
    res_euc = eval_fd_euc.evaluate(problem, layout)
    assert res_euc.value == 750.0


def test_mhc_known_calculation(exact_calc_setup):
    """Test 2: Verify exact hand-calculated Material Handling Cost under Manhattan and Euclidean."""
    problem, layout = exact_calc_setup
    
    # Manhattan MHC: 1400 + 1050 = 2450.0
    cfg_man = EvaluationConfig(distance_metric=DistanceMetricType.MANHATTAN)
    eval_mhc_man = MaterialHandlingCostEvaluator(cfg_man)
    res_man = eval_mhc_man.evaluate(problem, layout)
    assert res_man.value == 2450.0
    
    # Euclidean MHC: 1000 + 750 = 1750.0
    cfg_euc = EvaluationConfig(distance_metric=DistanceMetricType.EUCLIDEAN)
    eval_mhc_euc = MaterialHandlingCostEvaluator(cfg_euc)
    res_euc = eval_mhc_euc.evaluate(problem, layout)
    assert res_euc.value == 1750.0


def test_directed_flow_asymmetry(exact_calc_setup):
    """Test 3: Verify directed flow asymmetry (A -> B != B -> A)."""
    problem, layout = exact_calc_setup
    eval_mhc = MaterialHandlingCostEvaluator(EvaluationConfig(distance_metric=DistanceMetricType.MANHATTAN))
    res = eval_mhc.evaluate(problem, layout)
    
    top_contributors = res.details["top_contributors"]
    assert len(top_contributors) == 2
    
    # A -> B is 1400.0, B -> A is 1050.0
    contrib_a_b = next(c for c in top_contributors if c["source"] == "DEP_A" and c["target"] == "DEP_B")
    contrib_b_a = next(c for c in top_contributors if c["source"] == "DEP_B" and c["target"] == "DEP_A")
    
    assert contrib_a_b["cost"] == 1400.0
    assert contrib_b_a["cost"] == 1050.0
    assert contrib_a_b["cost"] != contrib_b_a["cost"]


def test_manhattan_vs_euclidean_difference(exact_calc_setup):
    """Test 4: Verify Manhattan distance is strictly greater than or equal to Euclidean."""
    problem, layout = exact_calc_setup
    engine_man = EvaluationEngine(config=EvaluationConfig(distance_metric=DistanceMetricType.MANHATTAN))
    engine_euc = EvaluationEngine(config=EvaluationConfig(distance_metric=DistanceMetricType.EUCLIDEAN))
    
    rep_man = engine_man.evaluate(problem, layout)
    rep_euc = engine_euc.evaluate(problem, layout)
    
    assert rep_man.objective_values["flow_distance"] > rep_euc.objective_values["flow_distance"]
    assert rep_man.objective_values["material_handling_cost"] > rep_euc.objective_values["material_handling_cost"]


# ---------------------------------------------------------------------------
# 2. Deterministic Matrix Services Tests
# ---------------------------------------------------------------------------

def test_distance_matrix_deterministic_ordering(exact_calc_setup):
    """Test 5: Verify distance matrix is deterministic and uses sorted department IDs."""
    _, layout = exact_calc_setup
    
    # Add third department
    layout.placements["DEP_C"] = ContinuousPlacement(
        department_id="DEP_C", x=70.0, y=70.0, width=10.0, height=10.0
    )
    
    dist_res = DistanceMatrixService.compute(layout, metric=DistanceMetricType.MANHATTAN)
    assert dist_res.department_order == ["DEP_A", "DEP_B", "DEP_C"]
    assert dist_res.numpy_matrix.shape == (3, 3)
    assert len(dist_res.matrix) == 3
    assert dist_res.get_distance("DEP_A", "DEP_B") == 70.0
    assert dist_res.get_distance("DEP_B", "DEP_A") == 70.0
    assert dist_res.get_distance("DEP_A", "DEP_A") == 0.0


def test_flow_matrix_correctness(exact_calc_setup):
    """Test 6: Verify flow matrix preserves exact directed values."""
    problem, _ = exact_calc_setup
    flow_res = FlowMatrixService.compute(problem)
    
    assert flow_res.department_order == ["DEP_A", "DEP_B"]
    assert flow_res.get_flow("DEP_A", "DEP_B") == 10.0
    assert flow_res.get_flow("DEP_B", "DEP_A") == 5.0
    assert flow_res.get_flow("DEP_A", "DEP_A") == 0.0


def test_relationship_matrix_correctness():
    """Test 7: Verify relationship matrix correctly maps ClosenessRating scores."""
    facility = Facility(id="FAC", name="Facility", width=50.0, height=50.0)
    problem = FacilityLayoutProblem(
        id="PROB_REL",
        facility=facility,
        departments=[
            Department(id="D1", name="D1", required_area=100.0),
            Department(id="D2", name="D2", required_area=100.0),
            Department(id="D3", name="D3", required_area=100.0),
        ],
        relationships=[
            Relationship(department_a="D1", department_b="D2", relationship_type=ClosenessRating.A),
            Relationship(department_a="D1", department_b="D3", relationship_type=ClosenessRating.X),
        ],
    )
    
    rel_res = RelationshipMatrixService.compute(problem)
    assert rel_res.get_weight("D1", "D2") == 16.0
    assert rel_res.get_weight("D2", "D1") == 16.0
    assert rel_res.get_weight("D1", "D3") == -8.0
    assert rel_res.get_weight("D3", "D1") == -8.0
    assert rel_res.get_weight("D2", "D3") == 0.0


# ---------------------------------------------------------------------------
# 3. Muther SLP Qualitative Relationship Satisfaction Tests
# ---------------------------------------------------------------------------

def test_positive_relationship_proximity_reward():
    """Test 8: Verify closer placement yields higher score for positive closeness ratings."""
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_REL_POS",
        facility=facility,
        departments=[
            Department(id="D1", name="D1", required_area=100.0),
            Department(id="D2", name="D2", required_area=100.0),
        ],
        relationships=[
            Relationship(department_a="D1", department_b="D2", relationship_type=ClosenessRating.A),
        ],
    )
    
    # Layout 1: Very close (distance = 10m)
    layout_close = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=10.0, y=10.0, width=10.0, height=10.0),
            "D2": ContinuousPlacement(department_id="D2", x=20.0, y=10.0, width=10.0, height=10.0),
        },
    )
    
    # Layout 2: Far apart (distance = 70m)
    layout_far = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=10.0, y=10.0, width=10.0, height=10.0),
            "D2": ContinuousPlacement(department_id="D2", x=80.0, y=10.0, width=10.0, height=10.0),
        },
    )
    
    eval_rel = RelationshipSatisfactionEvaluator(EvaluationConfig())
    res_close = eval_rel.evaluate(problem, layout_close)
    res_far = eval_rel.evaluate(problem, layout_far)
    
    assert res_close.value > res_far.value
    assert float(res_close.details["relationship_raw_score"]) > float(res_far.details["relationship_raw_score"])


def test_negative_x_relationship_proximity_penalty():
    """Test 9: Verify undesirable X relationship penalizes close proximity and rewards separation."""
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_REL_X",
        facility=facility,
        departments=[
            Department(id="D1", name="D1", required_area=100.0),
            Department(id="D2", name="D2", required_area=100.0),
        ],
        relationships=[
            Relationship(department_a="D1", department_b="D2", relationship_type=ClosenessRating.X),
        ],
    )
    
    # Close: Hazardous proximity
    layout_close = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=10.0, y=10.0, width=10.0, height=10.0),
            "D2": ContinuousPlacement(department_id="D2", x=20.0, y=10.0, width=10.0, height=10.0),
        },
    )
    
    # Far: Safe separation
    layout_far = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=0.0, y=0.0, width=10.0, height=10.0),
            "D2": ContinuousPlacement(department_id="D2", x=80.0, y=80.0, width=10.0, height=10.0),
        },
    )
    
    eval_rel = RelationshipSatisfactionEvaluator(EvaluationConfig())
    res_close = eval_rel.evaluate(problem, layout_close)
    res_far = eval_rel.evaluate(problem, layout_far)
    
    # Far placement reduces penalty (raw score is closer to 0, i.e. greater)
    raw_close = float(res_close.details["relationship_raw_score"])
    raw_far = float(res_far.details["relationship_raw_score"])
    assert raw_far > raw_close


# ---------------------------------------------------------------------------
# 4. Area Utilization with Reserved Zones Tests
# ---------------------------------------------------------------------------

def test_area_utilization_with_reserved_zones():
    """Test 10: Verify area utilization accurately deducts reserved zones without double-counting."""
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)  # Area = 10,000
    problem = FacilityLayoutProblem(
        id="PROB_AREA",
        facility=facility,
        departments=[
            Department(id="D1", name="D1", required_area=1000.0),
            Department(id="D2", name="D2", required_area=1000.0),
        ],
    )
    
    # 2 depts of 1000 each = 2000 total occupied
    # Reserved zone: 20 x 20 = 400
    # Usable area: 10000 - 400 = 9600
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=0.0, y=0.0, width=20.0, height=50.0),   # 1000
            "D2": ContinuousPlacement(department_id="D2", x=30.0, y=0.0, width=20.0, height=50.0),  # 1000
        },
        reserved_zones=[
            ReservedZone(
                id="RZ_PILLAR",
                type="restricted",
                bounding_box={"x_min": 60.0, "y_min": 0.0, "x_max": 80.0, "y_max": 20.0},
            )
        ],
    )
    
    eval_area = AreaUtilizationEvaluator(EvaluationConfig())
    res = eval_area.evaluate(problem, layout)
    
    assert res.details["facility_area"] == 10000.0
    assert res.details["occupied_area"] == 2000.0
    assert res.details["reserved_area"] == 400.0
    assert res.details["usable_area"] == 9600.0
    assert res.details["utilization_ratio"] == round(2000.0 / 9600.0, 4)
    assert res.value == round((2000.0 / 9600.0) * 100, 2)


# ---------------------------------------------------------------------------
# 5. Constraint Engine Checkers Tests
# ---------------------------------------------------------------------------

def test_non_overlapping_hard_constraint():
    """Test 11: NonOverlappingChecker detects overlap and flags hard violation."""
    checker = NonOverlappingChecker()
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_CST",
        facility=facility,
        departments=[
            Department(id="D1", name="D1", required_area=400.0),
            Department(id="D2", name="D2", required_area=400.0),
        ],
        constraints=[
            Constraint(id="CST_NO_OVERLAP", type=ConstraintType.NON_OVERLAPPING, classification=ConstraintClassification.HARD),
        ],
    )
    
    # Overlapping placements
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=10.0, y=10.0, width=20.0, height=20.0),
            "D2": ContinuousPlacement(department_id="D2", x=20.0, y=10.0, width=20.0, height=20.0),
        },
    )
    
    violations = checker.check(problem.constraints[0], problem, layout)
    assert len(violations) == 1
    assert violations[0].classification == ConstraintClassification.HARD
    assert violations[0].magnitude == 200.0  # 10m x 20m overlap area


def test_boundary_hard_constraint():
    """Test 12: BoundaryChecker detects protrusion beyond facility wall."""
    checker = BoundaryChecker()
    facility = Facility(id="FAC", name="Facility", width=50.0, height=50.0)
    problem = FacilityLayoutProblem(
        id="PROB_BOUND",
        facility=facility,
        departments=[Department(id="D1", name="D1", required_area=400.0)],
        constraints=[
            Constraint(id="CST_BOUND", type=ConstraintType.BOUNDARY, classification=ConstraintClassification.HARD),
        ],
    )
    
    # Department exceeds right boundary: x=40, width=20 -> x_max=60 > 50
    layout = ContinuousLayout(
        facility_width=50.0,
        facility_height=50.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=40.0, y=10.0, width=20.0, height=20.0),
        },
    )
    
    violations = checker.check(problem.constraints[0], problem, layout)
    assert len(violations) == 1
    assert violations[0].classification == ConstraintClassification.HARD
    assert violations[0].magnitude == 10.0


def test_fixed_position_hard_constraint():
    """Test 13: FixedPositionChecker verifies anchored department coordinates."""
    checker = FixedPositionChecker()
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_FIX",
        facility=facility,
        departments=[Department(id="DOCK", name="Shipping Dock", required_area=200.0)],
        constraints=[
            Constraint(
                id="CST_FIXED",
                type=ConstraintType.FIXED_POSITION,
                involved_departments=["DOCK"],
                parameters={"fixed_x": 0.0, "fixed_y": 0.0},
                classification=ConstraintClassification.HARD,
            ),
        ],
    )
    
    # Placed at (10, 10) instead of (0, 0)
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "DOCK": ContinuousPlacement(department_id="DOCK", x=10.0, y=10.0, width=20.0, height=10.0),
        },
    )
    
    violations = checker.check(problem.constraints[0], problem, layout)
    assert len(violations) == 1
    assert violations[0].classification == ConstraintClassification.HARD


def test_min_distance_constraint():
    """Test 14: MinDistanceChecker flags distance below required threshold."""
    checker = MinDistanceChecker()
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_MIN_DIST",
        facility=facility,
        departments=[
            Department(id="HAZARD", name="Chemical", required_area=100.0),
            Department(id="OFFICE", name="Admin", required_area=100.0),
        ],
        constraints=[
            Constraint(
                id="CST_MIN_DIST",
                type=ConstraintType.MIN_DISTANCE,
                involved_departments=["HAZARD", "OFFICE"],
                parameters={"min_distance": 30.0, "use_centroid": True},
                classification=ConstraintClassification.SOFT,
                penalty=50.0,
            ),
        ],
    )
    
    # Distance between centroids: (15, 15) to (25, 15) = 10m < 30m
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "HAZARD": ContinuousPlacement(department_id="HAZARD", x=10.0, y=10.0, width=10.0, height=10.0),
            "OFFICE": ContinuousPlacement(department_id="OFFICE", x=20.0, y=10.0, width=10.0, height=10.0),
        },
    )
    
    violations = checker.check(problem.constraints[0], problem, layout)
    assert len(violations) == 1
    assert violations[0].classification == ConstraintClassification.SOFT
    assert violations[0].magnitude == 20.0  # 30 - 10 = 20m violation
    assert violations[0].penalty_cost == 1000.0  # 20m * $50/m = $1000


def test_max_distance_constraint():
    """Test 15: MaxDistanceChecker flags separation exceeding threshold."""
    checker = MaxDistanceChecker()
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_MAX_DIST",
        facility=facility,
        departments=[
            Department(id="LINE1", name="Line 1", required_area=100.0),
            Department(id="LINE2", name="Line 2", required_area=100.0),
        ],
        constraints=[
            Constraint(
                id="CST_MAX_DIST",
                type=ConstraintType.MAX_DISTANCE,
                involved_departments=["LINE1", "LINE2"],
                parameters={"max_distance": 20.0, "use_centroid": True},
                classification=ConstraintClassification.SOFT,
                penalty=10.0,
            ),
        ],
    )
    
    # Centroids: (15, 15) and (65, 15) -> dist = 50m > 20m
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "LINE1": ContinuousPlacement(department_id="LINE1", x=10.0, y=10.0, width=10.0, height=10.0),
            "LINE2": ContinuousPlacement(department_id="LINE2", x=60.0, y=10.0, width=10.0, height=10.0),
        },
    )
    
    violations = checker.check(problem.constraints[0], problem, layout)
    assert len(violations) == 1
    assert violations[0].magnitude == 30.0  # 50 - 20 = 30m


def test_adjacency_constraint():
    """Test 16: AdjacencyChecker flags non-touching departments requiring shared wall."""
    checker = AdjacencyChecker()
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_ADJ",
        facility=facility,
        departments=[
            Department(id="STAMPING", name="Stamping", required_area=100.0),
            Department(id="WELDING", name="Welding", required_area=100.0),
        ],
        constraints=[
            Constraint(
                id="CST_ADJ",
                type=ConstraintType.ADJACENCY,
                involved_departments=["STAMPING", "WELDING"],
                classification=ConstraintClassification.SOFT,
                penalty=250.0,
            ),
        ],
    )
    
    # Separated by a 5m gap (x=10..20 and x=25..35)
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "STAMPING": ContinuousPlacement(department_id="STAMPING", x=10.0, y=10.0, width=10.0, height=10.0),
            "WELDING": ContinuousPlacement(department_id="WELDING", x=25.0, y=10.0, width=10.0, height=10.0),
        },
    )
    
    violations = checker.check(problem.constraints[0], problem, layout)
    assert len(violations) == 1
    assert violations[0].penalty_cost == 250.0


def test_separation_constraint():
    """Test 17: SeparationChecker enforces minimum clearance boundary."""
    checker = SeparationChecker()
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_SEP",
        facility=facility,
        departments=[
            Department(id="FURNACE", name="Furnace", required_area=100.0),
            Department(id="PAINT", name="Paint Booth", required_area=100.0),
        ],
        constraints=[
            Constraint(
                id="CST_SEP",
                type=ConstraintType.SEPARATION,
                involved_departments=["FURNACE", "PAINT"],
                parameters={"min_separation": 15.0},
                classification=ConstraintClassification.HARD,
            ),
        ],
    )
    
    # Gap is only 5m (x=10..20 and x=25..35) -> 10m violation
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "FURNACE": ContinuousPlacement(department_id="FURNACE", x=10.0, y=10.0, width=10.0, height=10.0),
            "PAINT": ContinuousPlacement(department_id="PAINT", x=25.0, y=10.0, width=10.0, height=10.0),
        },
    )
    
    violations = checker.check(problem.constraints[0], problem, layout)
    assert len(violations) == 1
    assert violations[0].magnitude == 10.0


# ---------------------------------------------------------------------------
# 6. Hard vs Soft Constraint Feasibility & Penalty Tests
# ---------------------------------------------------------------------------

def test_hard_violation_renders_layout_infeasible():
    """Test 18: Hard constraint violation strictly sets is_feasible = False."""
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_HARD",
        facility=facility,
        departments=[
            Department(id="D1", name="D1", required_area=100.0),
            Department(id="D2", name="D2", required_area=100.0),
        ],
        constraints=[
            Constraint(id="CST_NO_OVERLAP", type=ConstraintType.NON_OVERLAPPING, classification=ConstraintClassification.HARD),
        ],
    )
    
    # Completely overlapping
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=10.0, y=10.0, width=10.0, height=10.0),
            "D2": ContinuousPlacement(department_id="D2", x=10.0, y=10.0, width=10.0, height=10.0),
        },
    )
    
    engine = EvaluationEngine()
    report = engine.evaluate(problem, layout)
    
    assert report.is_feasible is False
    assert report.hard_violation_count >= 1


def test_soft_violation_preserves_feasibility():
    """Test 19: Soft constraint violation produces penalty cost but keeps is_feasible = True."""
    facility = Facility(id="FAC", name="Facility", width=100.0, height=100.0)
    problem = FacilityLayoutProblem(
        id="PROB_SOFT",
        facility=facility,
        departments=[
            Department(id="D1", name="D1", required_area=100.0),
            Department(id="D2", name="D2", required_area=100.0),
        ],
        constraints=[
            Constraint(
                id="CST_MAX_DIST",
                type=ConstraintType.MAX_DISTANCE,
                involved_departments=["D1", "D2"],
                parameters={"max_distance": 10.0},
                classification=ConstraintClassification.SOFT,
                penalty=5.0,
            ),
        ],
    )
    
    # Non-overlapping, within facility, but 50m apart
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements={
            "D1": ContinuousPlacement(department_id="D1", x=0.0, y=0.0, width=10.0, height=10.0),
            "D2": ContinuousPlacement(department_id="D2", x=50.0, y=0.0, width=10.0, height=10.0),
        },
    )
    
    engine = EvaluationEngine()
    report = engine.evaluate(problem, layout)
    
    assert report.is_feasible is True
    assert report.hard_violation_count == 0
    assert report.soft_violation_count == 1
    assert report.total_constraint_penalty > 0.0
    assert report.objective_values["constraint_penalty"] > 0.0


def test_soft_constraint_penalty_computation():
    """Test 20: Constraint penalty evaluator correctly tallies unit penalty x magnitude."""
    engine = ConstraintEngine()
    violations = [
        ConstraintViolation(
            constraint_id="C1",
            constraint_type=ConstraintType.MAX_DISTANCE,
            classification=ConstraintClassification.SOFT,
            involved_departments=["A", "B"],
            magnitude=10.0,
            penalty_cost=50.0,  # magnitude (10) * unit_penalty (5) = 50.0
        ),
        ConstraintViolation(
            constraint_id="C2",
            constraint_type=ConstraintType.ADJACENCY,
            classification=ConstraintClassification.SOFT,
            involved_departments=["B", "C"],
            magnitude=1.0,
            penalty_cost=100.0,
        ),
    ]
    
    total = engine.calculate_total_penalty(violations)
    assert total == 150.0


# ---------------------------------------------------------------------------
# 7. Evaluation Engine & Serialization Tests
# ---------------------------------------------------------------------------

def test_evaluation_report_serialization(exact_calc_setup):
    """Test 21: EvaluationReport serializes cleanly to dict and JSON."""
    problem, layout = exact_calc_setup
    engine = EvaluationEngine()
    report = engine.evaluate(problem, layout)
    
    dumped = report.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["problem_id"] == "PROB_EXACT"
    assert "material_handling_cost" in dumped["objective_values"]
    assert "flow_distance" in dumped["objective_values"]
    
    # JSON round-trip
    json_str = json.dumps(dumped)
    assert isinstance(json_str, str)
    reloaded = json.loads(json_str)
    assert reloaded["problem_id"] == "PROB_EXACT"


def test_evaluate_single_layout(exact_calc_setup):
    """Test 22: Complete single layout evaluation returns all standard metric fields."""
    problem, layout = exact_calc_setup
    engine = EvaluationEngine()
    report = engine.evaluate(problem, layout)
    
    assert isinstance(report, EvaluationReport)
    assert report.is_feasible is True
    assert report.objective_values["material_handling_cost"] == 2450.0
    assert report.objective_values["flow_distance"] == 1050.0
    assert "relationship_score" in report.objective_values
    assert "area_utilization" in report.objective_values
    assert "constraint_penalty" in report.objective_values
    assert report.layout_signature is not None


# ---------------------------------------------------------------------------
# 8. Multi-Layout Normalization and Feasibility-First Ranking Tests
# ---------------------------------------------------------------------------

def test_min_max_normalization(exact_calc_setup):
    """Test 23: Min-max normalization scales multi-objective values into [0.0, 1.0]."""
    problem, layout1 = exact_calc_setup
    
    # Layout 2 with greater distances
    layout2 = layout1.model_copy(deep=True)
    layout2.metadata["algorithm_name"] = "layout_expensive"
    layout2.placements["DEP_B"].x = 70.0
    layout2.placements["DEP_B"].y = 70.0
    
    engine = EvaluationEngine()
    comparison = engine.evaluate_many(problem, [layout1, layout2])
    
    assert comparison.solution_count == 2
    r1 = comparison.reports[0]
    r2 = comparison.reports[1]
    
    # Both normalized dictionaries must be populated
    assert r1.normalized_values is not None
    assert r2.normalized_values is not None
    for k, v in r1.normalized_values.items():
        assert 0.0 <= v <= 1.0
    for k, v in r2.normalized_values.items():
        assert 0.0 <= v <= 1.0


def test_feasibility_first_ranking(exact_calc_setup):
    """Test 24: Feasible layouts must strictly rank ahead of infeasible ones regardless of cost."""
    problem, layout_good = exact_calc_setup
    
    # Add boundary constraint
    problem.constraints.append(
        Constraint(id="CST_BOUND", type=ConstraintType.BOUNDARY, classification=ConstraintClassification.HARD)
    )
    
    # Infeasible layout placed outside boundary (x=95, width=20 -> x_max=115 > 100)
    layout_infeasible = layout_good.model_copy(deep=True)
    layout_infeasible.metadata["algorithm_name"] = "infeasible_solver"
    layout_infeasible.placements["DEP_A"].x = 95.0
    
    # Feasible layout placed further apart (higher cost, but feasible)
    layout_feasible_expensive = layout_good.model_copy(deep=True)
    layout_feasible_expensive.metadata["algorithm_name"] = "feasible_expensive_solver"
    layout_feasible_expensive.placements["DEP_B"].x = 60.0
    layout_feasible_expensive.placements["DEP_B"].y = 60.0
    
    engine = EvaluationEngine()
    comp = engine.evaluate_many(problem, [layout_infeasible, layout_feasible_expensive])
    
    assert comp.solution_count == 2
    # First ranked solution MUST be the feasible one
    assert comp.reports[0].is_feasible is True
    assert comp.reports[0].algorithm_name == "feasible_expensive_solver"
    assert comp.reports[1].is_feasible is False
    assert comp.reports[1].algorithm_name == "infeasible_solver"
    assert comp.ranking[0] == "feasible_expensive_solver"


def test_weighted_composite_ranking(exact_calc_setup):
    """Test 25: User-defined objective weights influence composite score and rank."""
    problem, layout_a = exact_calc_setup
    
    layout_b = layout_a.model_copy(deep=True)
    layout_b.metadata["algorithm_name"] = "alt_layout_b"
    layout_b.placements["DEP_B"].x = 50.0
    
    config = EvaluationConfig(
        objective_weights={
            "material_handling_cost": 5.0,
            "flow_distance": 0.1,
            "relationship_score": 0.1,
            "area_utilization": 0.1,
            "constraint_penalty": 0.1,
        }
    )
    
    engine = EvaluationEngine(config=config)
    comp = engine.evaluate_many(problem, [layout_a, layout_b])
    
    assert comp.solution_count == 2
    assert comp.reports[0].composite_score >= comp.reports[1].composite_score


def test_evaluation_determinism_and_reproducibility(exact_calc_setup):
    """Test 26: Evaluating identical layout twice yields identical metrics and signature."""
    problem, layout = exact_calc_setup
    engine = EvaluationEngine()
    
    r1 = engine.evaluate(problem, layout)
    r2 = engine.evaluate(problem, layout)
    
    assert r1.layout_signature == r2.layout_signature
    assert r1.objective_values == r2.objective_values
    assert r1.is_feasible == r2.is_feasible
    assert r1.hard_violation_count == r2.hard_violation_count


# ---------------------------------------------------------------------------
# 9. FastAPI Endpoints Tests
# ---------------------------------------------------------------------------

client = TestClient(app)

def test_api_metrics_endpoint():
    """Test 27: GET /api/evaluation/metrics returns available metrics catalog."""
    response = client.get("/api/evaluation/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["count"] >= 4
    metric_names = [m["name"] for m in data["metrics"]]
    assert "material_handling_cost" in metric_names
    assert "total_flow_distance" in metric_names


def test_api_evaluate_and_compare_endpoints(exact_calc_setup):
    """Test 28: POST /api/evaluation/evaluate and /api/evaluation/compare endpoints work via API."""
    problem, layout = exact_calc_setup
    
    # 1. Single evaluation
    eval_payload = {
        "problem": problem.model_dump(),
        "layout": layout.model_dump(),
        "config": {"distance_metric": "manhattan"},
    }
    resp_eval = client.post("/api/evaluation/evaluate", json=eval_payload)
    assert resp_eval.status_code == 200
    rep_data = resp_eval.json()
    assert rep_data["is_feasible"] is True
    assert rep_data["objective_values"]["material_handling_cost"] == 2450.0
    
    # 2. Comparison endpoint
    layout_alt = layout.model_copy(deep=True)
    layout_alt.metadata["algorithm_name"] = "layout_variant_alt"
    
    comp_payload = {
        "problem": problem.model_dump(),
        "layouts": [layout.model_dump(), layout_alt.model_dump()],
    }
    resp_comp = client.post("/api/evaluation/compare", json=comp_payload)
    assert resp_comp.status_code == 200
    comp_data = resp_comp.json()
    assert comp_data["solution_count"] == 2
    assert len(comp_data["ranking"]) == 2


# ---------------------------------------------------------------------------
# 10. Sample File End-to-End Integration Tests
# ---------------------------------------------------------------------------

def test_sample_layout_evaluation_integration():
    """Test 29: Evaluate real sample_layout.json against sample_plant.json."""
    plant_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_plant.json"
    layout_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_layout.json"
    
    assert plant_path.exists()
    assert layout_path.exists()
    
    problem = load_problem(plant_path)
    with open(layout_path, "r", encoding="utf-8") as f:
        layout_dict = json.load(f)
    
    engine = EvaluationEngine()
    report = engine.evaluate(problem, layout_dict)
    
    assert report.is_feasible is True
    assert report.objective_values["material_handling_cost"] > 0.0
    assert report.objective_values["flow_distance"] > 0.0
    assert report.objective_values["area_utilization"] > 0.0


# ---------------------------------------------------------------------------
# 11. Edge Cases: Duplicate Placements and Fixed Orientation
# ---------------------------------------------------------------------------

def test_duplicate_placement_dictionary_semantics():
    """Test 30: ContinuousLayout dictionary semantics overwrite duplicate department IDs."""
    placements = {
        "DEP_A": ContinuousPlacement(department_id="DEP_A", x=10.0, y=10.0, width=20.0, height=20.0),
    }
    # Simulate adding duplicate key
    placements["DEP_A"] = ContinuousPlacement(department_id="DEP_A", x=50.0, y=50.0, width=20.0, height=20.0)
    
    layout = ContinuousLayout(
        facility_width=100.0,
        facility_height=100.0,
        placements=placements,
    )
    
    assert len(layout.placements) == 1
    assert layout.placements["DEP_A"].x == 50.0


def test_fixed_orientation_check():
    """Test 31: Verify fixed orientation validation on Department model."""
    dept_fixed = Department(
        id="DEP_FIXED_ROT",
        name="Fixed Machine",
        required_area=200.0,
        fixed_orientation=0.0,
    )
    assert dept_fixed.fixed_orientation == 0.0
