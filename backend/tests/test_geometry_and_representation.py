"""Unit and integration tests for Phase 3: Layout Representation & Geometry Engine."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.geometry import Point2D, Dimensions2D, BoundingBox, ReservedZone
from app.models.problem import FacilityLayoutProblem
from app.models.representation import (
    ContinuousPlacement,
    ContinuousLayout,
    GridLayout,
    GridDepartmentBlock,
    LayoutRepresentationType,
)
from app.services.problem_loader import load_problem
from app.services.geometry_engine import GeometryEngine, DistanceMetricType
from app.services.representation_converter import (
    ContinuousToGridConverter,
    GridToContinuousConverter,
)
from app.services.layout_normalizer import normalize_layout, generate_layout_signature
from app.services.layout_validator import LayoutValidator

EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "examples"


@pytest.fixture
def sample_problem() -> FacilityLayoutProblem:
    """Fixture providing the benchmark 10-department problem."""
    return load_problem(EXAMPLES_DIR / "sample_plant.json")


@pytest.fixture
def sample_layout_dict() -> dict:
    """Fixture providing the baseline feasible layout dictionary."""
    with open(EXAMPLES_DIR / "sample_layout.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_continuous_layout(sample_layout_dict: dict) -> ContinuousLayout:
    """Fixture providing parsed ContinuousLayout."""
    return ContinuousLayout.model_validate(sample_layout_dict)


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client fixture."""
    return TestClient(app)


class TestContinuousLayoutRepresentation:
    """Tests for ContinuousLayout and ContinuousPlacement models."""

    def test_valid_continuous_layout_creation(self, sample_continuous_layout: ContinuousLayout):
        """1. Verify valid continuous layout creation and properties."""
        assert sample_continuous_layout.facility_width == 150.0
        assert sample_continuous_layout.facility_height == 80.0
        assert len(sample_continuous_layout.placements) == 10
        assert sample_continuous_layout.representation_type == LayoutRepresentationType.CONTINUOUS

        p = sample_continuous_layout.placements["DEP_RAW_MATERIAL"]
        assert p.x == 0.0
        assert p.y == 0.0
        assert p.width == 32.5
        assert p.height == 40.0
        assert p.area == 1300.0
        assert p.centroid == Point2D(x=16.25, y=20.0)
        assert p.left == 0.0
        assert p.right == 32.5
        assert p.bottom == 0.0
        assert p.top == 40.0

    def test_bounding_box_helper_properties(self):
        """Verify BoundingBox convenience getters and point containment."""
        box = BoundingBox(x_min=10.0, y_min=20.0, x_max=50.0, y_max=80.0)
        assert box.width == 40.0
        assert box.height == 60.0
        assert box.area == 2400.0
        assert box.left == 10.0
        assert box.right == 50.0
        assert box.bottom == 20.0
        assert box.top == 80.0
        assert box.aspect_ratio == 60.0 / 40.0
        assert box.contains_point(Point2D(x=30.0, y=50.0)) is True
        assert box.contains_point(Point2D(x=5.0, y=50.0)) is False


class TestGeometryEngine:
    """Tests for spatial distances, overlaps, and boundary metrics."""

    def test_euclidean_distance(self):
        """10. Verify Euclidean distance computation between centroids."""
        p1 = Point2D(x=0.0, y=0.0)
        p2 = Point2D(x=3.0, y=4.0)
        dist = GeometryEngine.centroid_euclidean_distance(p1, p2)
        assert dist == pytest.approx(5.0)

    def test_manhattan_distance(self):
        """11. Verify Manhattan distance computation between centroids."""
        p1 = Point2D(x=2.0, y=3.0)
        p2 = Point2D(x=8.0, y=11.0)
        dist = GeometryEngine.centroid_manhattan_distance(p1, p2)
        assert dist == pytest.approx(14.0)

    def test_edge_to_edge_distance_separated_and_overlapping(self):
        """12. Verify edge-to-edge distance between separated and overlapping boxes."""
        b1 = BoundingBox(x_min=0.0, y_min=0.0, x_max=10.0, y_max=10.0)
        b2 = BoundingBox(x_min=15.0, y_min=0.0, x_max=25.0, y_max=10.0)
        # Separated horizontally by 5.0
        assert GeometryEngine.edge_to_edge_distance(b1, b2) == pytest.approx(5.0)

        # Touching
        b3 = BoundingBox(x_min=10.0, y_min=0.0, x_max=20.0, y_max=10.0)
        assert GeometryEngine.edge_to_edge_distance(b1, b3) == pytest.approx(0.0)

        # Diagonal separation: dx=3, dy=4 -> distance = 5.0
        b4 = BoundingBox(x_min=13.0, y_min=14.0, x_max=20.0, y_max=20.0)
        assert GeometryEngine.edge_to_edge_distance(b1, b4) == pytest.approx(5.0)

        # Overlapping
        b5 = BoundingBox(x_min=5.0, y_min=5.0, x_max=15.0, y_max=15.0)
        assert GeometryEngine.edge_to_edge_distance(b1, b5) == pytest.approx(0.0)

    def test_adjacency_and_shared_boundary(self):
        """13 & 14. Verify horizontal and vertical adjacency and shared boundary calculation."""
        # Horizontal adjacent sharing vertical edge x=10 from y=2 to y=8 (length 6)
        b1 = BoundingBox(x_min=0.0, y_min=0.0, x_max=10.0, y_max=10.0)
        b2 = BoundingBox(x_min=10.0, y_min=2.0, x_max=20.0, y_max=8.0)
        assert GeometryEngine.is_adjacent(b1, b2) is True
        assert GeometryEngine.shared_boundary_length(b1, b2) == pytest.approx(6.0)

        # Vertical adjacent sharing horizontal edge y=10 from x=3 to x=7 (length 4)
        b3 = BoundingBox(x_min=3.0, y_min=10.0, x_max=7.0, y_max=15.0)
        assert GeometryEngine.is_adjacent(b1, b3) is True
        assert GeometryEngine.shared_boundary_length(b1, b3) == pytest.approx(4.0)

        # Touching only at corner (10, 10) - boundary overlap is 0
        b4 = BoundingBox(x_min=10.0, y_min=10.0, x_max=20.0, y_max=20.0)
        assert GeometryEngine.shared_boundary_length(b1, b4) == pytest.approx(0.0)
        assert GeometryEngine.is_adjacent(b1, b4) is False

    def test_layout_metrics_calculation(self, sample_continuous_layout: ContinuousLayout, sample_problem: FacilityLayoutProblem):
        """Verify spatial layout metrics calculation."""
        metrics = GeometryEngine.calculate_layout_metrics(sample_continuous_layout, sample_problem)
        assert metrics["occupied_area"] == 11000.0
        assert metrics["free_area"] == 1000.0
        assert metrics["total_overlap_area"] == 0.0
        assert metrics["utilization_ratio"] == pytest.approx(11000.0 / 12000.0, rel=1e-4)
        assert metrics["bounding_envelope_area"] == 12000.0


class TestLayoutValidator:
    """Tests for geometric and specification validation."""

    def test_sample_layout_passes_validation(self, sample_problem: FacilityLayoutProblem, sample_continuous_layout: ContinuousLayout):
        """20. Verify sample baseline layout passes validation with zero errors/warnings."""
        result = LayoutValidator.validate(sample_problem, sample_continuous_layout)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.total_overlap_area == 0.0
        assert len(result.checked_departments) == 10

    def test_overlap_detection(self, sample_problem: FacilityLayoutProblem, sample_continuous_layout: ContinuousLayout):
        """2. Verify overlapping departments are caught as errors with overlap area reported."""
        # Shift DEP_CUTTING into DEP_RAW_MATERIAL (overlap: 10m x 30m = 300m^2)
        invalid_layout = sample_continuous_layout.model_copy(deep=True)
        invalid_layout.placements["DEP_CUTTING"].x = 22.5  # overlaps [22.5, 32.5] x [0, 30]

        result = LayoutValidator.validate(sample_problem, invalid_layout)
        assert result.is_valid is False
        assert any("Overlap detected between" in err for err in result.errors)
        assert result.total_overlap_area == pytest.approx(300.0)

    def test_boundary_violation_detection(self, sample_problem: FacilityLayoutProblem, sample_continuous_layout: ContinuousLayout):
        """3. Verify boundary violations (outside facility perimeter) are rejected."""
        # Move DEP_SHIPPING past right boundary (x + w = 135 + 22.5 = 157.5 > 150)
        invalid_layout = sample_continuous_layout.model_copy(deep=True)
        invalid_layout.placements["DEP_SHIPPING"].x = 135.0

        result = LayoutValidator.validate(sample_problem, invalid_layout)
        assert result.is_valid is False
        assert any("exceeds facility boundaries" in err for err in result.errors)

    def test_missing_department_detection(self, sample_problem: FacilityLayoutProblem, sample_continuous_layout: ContinuousLayout):
        """4. Verify missing required department is flagged."""
        invalid_layout = sample_continuous_layout.model_copy(deep=True)
        del invalid_layout.placements["DEP_QUALITY"]

        result = LayoutValidator.validate(sample_problem, invalid_layout)
        assert result.is_valid is False
        assert any("DEP_QUALITY" in err for err in result.errors)

    def test_unexpected_department_detection(self, sample_problem: FacilityLayoutProblem, sample_continuous_layout: ContinuousLayout):
        """5. Verify unmodeled/unexpected department is flagged as error."""
        invalid_layout = sample_continuous_layout.model_copy(deep=True)
        invalid_layout.placements["DEP_GHOST"] = ContinuousPlacement(
            department_id="DEP_GHOST",
            x=50.0,
            y=50.0,
            width=10.0,
            height=10.0,
        )

        result = LayoutValidator.validate(sample_problem, invalid_layout)
        assert result.is_valid is False
        assert any("DEP_GHOST" in err for err in result.errors)

    def test_minimum_dimension_violation(self, sample_problem: FacilityLayoutProblem, sample_continuous_layout: ContinuousLayout):
        """7. Verify min_width violation triggers error."""
        # DEP_CUTTING min_width is 20.0. Set width to 15.0, height to 60.0
        invalid_layout = sample_continuous_layout.model_copy(deep=True)
        invalid_layout.placements["DEP_CUTTING"].width = 15.0
        invalid_layout.placements["DEP_CUTTING"].height = 60.0

        result = LayoutValidator.validate(sample_problem, invalid_layout)
        assert result.is_valid is False
        assert any("violates minimum width" in err for err in result.errors)

    def test_aspect_ratio_violation(self, sample_problem: FacilityLayoutProblem, sample_continuous_layout: ContinuousLayout):
        """8. Verify max aspect ratio violation when department is excessively elongated."""
        problem_copy = sample_problem.model_copy(deep=True)
        for dept in problem_copy.departments:
            if dept.id == "DEP_CUTTING":
                dept.max_aspect_ratio = 2.0

        invalid_layout = sample_continuous_layout.model_copy(deep=True)
        # Width 45.0, Height 20.0 -> aspect ratio = 2.25 > 2.0
        invalid_layout.placements["DEP_CUTTING"].width = 45.0
        invalid_layout.placements["DEP_CUTTING"].height = 20.0

        result = LayoutValidator.validate(problem_copy, invalid_layout)
        assert any("exceeds max_aspect_ratio" in err for err in result.errors)

    def test_fixed_position_violation(self, sample_problem: FacilityLayoutProblem, sample_continuous_layout: ContinuousLayout):
        """6. Verify fixed position constraint violation is caught."""
        problem_copy = sample_problem.model_copy(deep=True)
        for dept in problem_copy.departments:
            if dept.id == "DEP_RAW_MATERIAL":
                dept.fixed_position = Point2D(x=10.0, y=10.0)

        # Layout has RAW_MATERIAL at (0, 0)
        result = LayoutValidator.validate(problem_copy, sample_continuous_layout)
        assert result.is_valid is False
        assert any("violates fixed position constraint" in err for err in result.errors)

    def test_reserved_zone_overlap(self, sample_problem: FacilityLayoutProblem, sample_continuous_layout: ContinuousLayout):
        """9. Verify department overlapping a reserved zone triggers error."""
        reserved = [
            ReservedZone(
                id="RZ_PILLAR_1",
                type="structural_column",
                bounding_box=BoundingBox(x_min=10.0, y_min=10.0, x_max=20.0, y_max=20.0),
                strict=True,
            )
        ]
        # RAW_MATERIAL is in [0, 32.5] x [0, 40], so it overlaps this zone!
        result = LayoutValidator.validate(sample_problem, sample_continuous_layout, reserved_zones=reserved)
        assert result.is_valid is False
        assert any("overlaps with reserved zone 'RZ_PILLAR_1'" in err for err in result.errors)


class TestConverters:
    """Tests for ContinuousToGridConverter and GridToContinuousConverter."""

    def test_continuous_to_grid_conversion(self, sample_continuous_layout: ContinuousLayout):
        """15 & 17. Verify continuous to grid conversion with cell size 5.0 and error metadata."""
        converter = ContinuousToGridConverter(cell_size=5.0)
        result = converter.convert(sample_continuous_layout)

        assert result.grid_layout is not None
        assert result.grid_layout.cell_size == 5.0
        assert result.grid_layout.columns == 30   # 150 / 5
        assert result.grid_layout.rows == 16      # 80 / 5
        assert len(result.grid_layout.blocks) == 10
        assert "DEP_RAW_MATERIAL" in result.grid_layout.blocks
        assert len(result.area_errors) == 10

        # Verify grid blocks contain occupied cells
        raw_block = result.grid_layout.blocks["DEP_RAW_MATERIAL"]
        assert len(raw_block.cells) > 0
        assert result.grid_layout.occupancy_matrix is not None
        assert result.grid_layout.numpy_matrix.shape == (16, 30)

    def test_grid_to_continuous_conversion(self):
        """16. Verify discrete grid reconstruction back into continuous bounding boxes."""
        cells = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
        block = GridDepartmentBlock(department_id="DEP_TEST", cells=cells)
        grid_layout = GridLayout(
            cell_size=5.0,
            columns=10,
            rows=10,
            blocks={"DEP_TEST": block},
        )

        converter = GridToContinuousConverter()
        result = converter.convert(grid_layout)

        assert result.continuous_layout is not None
        p = result.continuous_layout.placements["DEP_TEST"]
        assert p.x == 0.0
        assert p.y == 0.0
        assert p.width == 15.0  # 3 cols * 5
        assert p.height == 10.0 # 2 rows * 5
        assert p.area == 150.0


class TestLayoutNormalizerAndSignature:
    """Tests for canonical sorting, rounding, and SHA-256 geometric signatures."""

    def test_deterministic_normalization(self, sample_continuous_layout: ContinuousLayout):
        """18. Verify layout normalization produces sorted department keys and rounded coordinates."""
        normalized = normalize_layout(sample_continuous_layout, decimal_places=3)
        dept_ids = list(normalized.placements.keys())
        assert dept_ids == sorted(dept_ids)

        p = normalized.placements["DEP_RAW_MATERIAL"]
        assert isinstance(p.x, float)
        assert round(p.x, 3) == p.x

    def test_deterministic_signature_invariance(self, sample_continuous_layout: ContinuousLayout):
        """19. Verify SHA-256 signature is deterministic and order-independent."""
        sig1 = generate_layout_signature(sample_continuous_layout)
        assert len(sig1) == 64  # SHA-256 hex string

        # Create reversed layout dictionary
        shuffled_dict = sample_continuous_layout.model_dump()
        items = list(shuffled_dict["placements"].items())
        shuffled_dict["placements"] = dict(reversed(items))
        shuffled_layout = ContinuousLayout.model_validate(shuffled_dict)

        sig2 = generate_layout_signature(shuffled_layout)
        assert sig1 == sig2, "Signature must be invariant to placement dictionary ordering"

        # Slight coordinate change must produce different signature
        modified_dict = sample_continuous_layout.model_dump()
        modified_dict["placements"]["DEP_RAW_MATERIAL"]["width"] += 0.5
        modified_layout = ContinuousLayout.model_validate(modified_dict)
        sig3 = generate_layout_signature(modified_layout)
        assert sig1 != sig3, "Signature must change when geometry changes"


class TestLayoutAPIEndpoints:
    """21. Tests for Phase 3 layout API endpoints."""

    def test_api_list_example_layouts(self, client: TestClient):
        response = client.get("/api/layouts/examples")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(item["id"] == "LAYOUT_SAMPLE_INDUSTRIAL_10" for item in data)

    def test_api_get_example_layout_by_id(self, client: TestClient):
        response = client.get("/api/layouts/examples/LAYOUT_SAMPLE_INDUSTRIAL_10")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "LAYOUT_SAMPLE_INDUSTRIAL_10"
        assert len(data["placements"]) == 10

    def test_api_validate_layout_valid(self, client: TestClient, sample_layout_dict: dict):
        payload = {
            "problem_id": "FLP_INDUSTRIAL_10",
            "layout": sample_layout_dict,
        }
        response = client.post("/api/layouts/validate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert len(data["errors"]) == 0
        assert data["total_overlap_area"] == 0.0

    def test_api_validate_layout_with_overlap(self, client: TestClient, sample_layout_dict: dict):
        bad_layout = dict(sample_layout_dict)
        bad_layout["placements"] = dict(sample_layout_dict["placements"])
        # Move cutting into raw material
        bad_layout["placements"]["DEP_CUTTING"] = dict(bad_layout["placements"]["DEP_CUTTING"])
        bad_layout["placements"]["DEP_CUTTING"]["x"] = 20.0

        payload = {
            "problem_id": "FLP_INDUSTRIAL_10",
            "layout": bad_layout,
        }
        response = client.post("/api/layouts/validate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

    def test_api_layout_metrics(self, client: TestClient, sample_layout_dict: dict):
        response = client.post("/api/layouts/metrics", json=sample_layout_dict)
        assert response.status_code == 200
        data = response.json()
        assert data["occupied_area"] == 11000.0
        assert data["total_overlap_area"] == 0.0
        assert data["utilization_ratio"] == pytest.approx(11000.0 / 12000.0, rel=1e-4)

    def test_api_layout_signature(self, client: TestClient, sample_layout_dict: dict):
        response = client.post("/api/layouts/signature", json=sample_layout_dict)
        assert response.status_code == 200
        data = response.json()
        assert "signature" in data
        assert len(data["signature"]) == 64
        assert "normalized_layout" in data

    def test_api_continuous_to_grid_conversion(self, client: TestClient, sample_layout_dict: dict):
        payload = {
            "layout": sample_layout_dict,
            "cell_size": 5.0,
        }
        response = client.post("/api/layouts/convert/continuous-to-grid", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "grid_layout" in data
        assert data["grid_layout"]["cell_size"] == 5.0
        assert len(data["area_errors"]) == 10
