"""Unit tests for core Pydantic data models."""

import pytest
from pydantic import ValidationError

from app.models.geometry import Point2D, Dimensions2D, BoundingBox
from app.models.facility import Facility
from app.models.department import Department
from app.models.flow import Flow
from app.models.relationship import Relationship, ClosenessRating, DEFAULT_RELATIONSHIP_SCORES
from app.models.constraint import Constraint, ConstraintType, ConstraintClassification
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution, DepartmentPlacement


class TestGeometryModels:
    """Tests for spatial geometric primitives."""

    def test_dimensions_calculations(self):
        dim = Dimensions2D(width=20.0, height=10.0)
        assert dim.area == 200.0
        assert dim.aspect_ratio == 2.0

    def test_bounding_box_centroid_and_intersection(self):
        bb1 = BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10)
        assert bb1.centroid == Point2D(x=5.0, y=5.0)
        assert bb1.area == 100.0

        bb2 = BoundingBox(x_min=5, y_min=5, x_max=15, y_max=15)
        assert bb1.intersects(bb2) is True

        bb3 = BoundingBox(x_min=20, y_min=20, x_max=30, y_max=30)
        assert bb1.intersects(bb3) is False


class TestCoreModels:
    """Tests for industrial facility layout domain models."""

    def test_facility_default_area_computation(self):
        fac = Facility(id="FAC_TEST", name="Test Plant", width=80.0, height=40.0)
        assert fac.area == 3200.0

    def test_department_dimension_validation(self):
        # Valid department
        d = Department(id="D1", name="Milling", required_area=200.0, min_width=10.0, max_width=25.0)
        assert d.min_width == 10.0

        # Invalid min > max width
        with pytest.raises(ValidationError):
            Department(id="D2", name="Drill", required_area=100.0, min_width=30.0, max_width=20.0)

    def test_flow_self_flow_prohibited(self):
        with pytest.raises(ValidationError):
            Flow(source_department="D1", target_department="D1", quantity=50.0)

    def test_relationship_default_scores(self):
        rel_a = Relationship(
            department_a="D1",
            department_b="D2",
            relationship_type=ClosenessRating.A,
        )
        assert rel_a.score == DEFAULT_RELATIONSHIP_SCORES[ClosenessRating.A]

        rel_x = Relationship(
            department_a="D1",
            department_b="D3",
            relationship_type=ClosenessRating.X,
        )
        assert rel_x.score == -8.0

        with pytest.raises(ValidationError):
            Relationship(department_a="D1", department_b="D1", relationship_type=ClosenessRating.E)

    def test_problem_integrity_and_area_utilization(self, sample_problem: FacilityLayoutProblem):
        assert sample_problem.total_required_area == 4100.0
        assert sample_problem.facility.area == 6000.0
        assert round(sample_problem.area_utilization, 4) == round(4100.0 / 6000.0, 4)
        assert sample_problem.get_department("DEP_MACHINING") is not None

    def test_problem_detects_missing_department_in_flow(self, sample_facility: Facility, sample_departments: list[Department]):
        invalid_flows = [
            Flow(source_department="DEP_RECEIVING", target_department="NON_EXISTENT_DEP", quantity=10.0)
        ]
        with pytest.raises(ValidationError):
            FacilityLayoutProblem(
                id="INVALID_CASE",
                facility=sample_facility,
                departments=sample_departments,
                flows=invalid_flows,
            )

    def test_solution_placement_and_bounding_boxes(self, sample_solution: LayoutSolution):
        bbox = sample_solution.get_bounding_box("DEP_RECEIVING")
        assert bbox is not None
        assert bbox.x_min == 0.0
        assert bbox.x_max == 20.0
        assert bbox.y_max == 30.0
        assert sample_solution.feasibility_status is True

    def test_load_sample_plant_json(self):
        import json
        from pathlib import Path
        sample_path = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_plant.json"
        assert sample_path.exists(), f"Sample file not found at {sample_path}"
        with open(sample_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        problem = FacilityLayoutProblem.model_validate(data)
        assert problem.id == "FLP_INDUSTRIAL_10"
        assert len(problem.departments) == 10
        assert len(problem.flows) == 13
        assert len(problem.relationships) == 13
        assert len(problem.constraints) == 4


