"""Unit tests for the Algorithm Interface and Registry."""

import pytest
from app.algorithms.base import BaseLayoutAlgorithm, AlgorithmCategory, ValidationResult
from app.algorithms.registry import AlgorithmRegistry, register_algorithm
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution, DepartmentPlacement
from app.models.geometry import Point2D, Dimensions2D


class DummyConstructionAlgorithm(BaseLayoutAlgorithm):
    """Test implementation of BaseLayoutAlgorithm."""

    @property
    def name(self) -> str:
        return "dummy_construction"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def category(self) -> AlgorithmCategory:
        return AlgorithmCategory.CONSTRUCTION

    @property
    def default_parameters(self) -> dict:
        return {"grid_size": 5.0}

    def solve(self, problem: FacilityLayoutProblem, **kwargs) -> LayoutSolution:
        # Simple dummy placement for testing interface compliance
        x_cursor = 0.0
        placements = {}
        positions = {}
        dimensions = {}

        for dept in problem.departments:
            width = dept.min_width or 10.0
            height = dept.required_area / width
            origin = Point2D(x=x_cursor, y=0.0)
            dim = Dimensions2D(width=width, height=height)

            placement = DepartmentPlacement(
                department_id=dept.id,
                origin=origin,
                dimensions=dim,
            )
            placements[dept.id] = placement
            positions[dept.id] = placement.centroid
            dimensions[dept.id] = dim
            x_cursor += width + 2.0

        return LayoutSolution(
            problem_id=problem.id,
            algorithm_name=self.name,
            algorithm_version=self.version,
            placements=placements,
            department_positions=positions,
            department_dimensions=dimensions,
            objective_values={"simulated_flow_cost": 1500.0},
            feasibility_status=True,
            metadata={"grid_size": self.parameters.get("grid_size")},
        )


class TestAlgorithmInterfaceAndRegistry:
    """Tests ensuring algorithm contract, extensibility, and registry behavior."""

    def test_algorithm_subclass_cannot_instantiate_without_abstract_methods(self):
        class IncompleteAlgorithm(BaseLayoutAlgorithm):
            pass

        with pytest.raises(TypeError):
            IncompleteAlgorithm()  # type: ignore

    def test_algorithm_registration_and_retrieval(self):
        # Register the dummy class
        AlgorithmRegistry.register("dummy_construction")(DummyConstructionAlgorithm)

        # Retrieve instance
        alg = AlgorithmRegistry.get("dummy_construction", parameters={"grid_size": 10.0})
        assert alg.name == "dummy_construction"
        assert alg.parameters["grid_size"] == 10.0
        assert alg.category == AlgorithmCategory.CONSTRUCTION

        # Verify listing
        available = AlgorithmRegistry.list_available()
        names = [item["name"] for item in available]
        assert "dummy_construction" in names

    def test_algorithm_validation_and_solve(self, sample_problem: FacilityLayoutProblem):
        alg = DummyConstructionAlgorithm(parameters={"grid_size": 2.5})
        val = alg.validate(sample_problem)
        assert val.is_valid is True

        solution = alg.solve(sample_problem)
        assert isinstance(solution, LayoutSolution)
        assert solution.problem_id == sample_problem.id
        assert solution.algorithm_name == "dummy_construction"
        assert len(solution.placements) == len(sample_problem.departments)
        assert solution.metadata["grid_size"] == 2.5
