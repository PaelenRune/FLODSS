"""Academic and industrial test suite for Phase 7.2: Rectangular Layout Feasibility Foundation.

Covers:
    1. Legal Shape Generation (Exact Area Conservation, Bounds, Aspect Ratio)
    2. Maximal Empty Rectangles (MER) Free Space Detection (L-Shape, Overlaps, Reserved Zones)
    3. Independent Placement Feasibility Checking (Boundaries, Overlaps, Fixed Positions)
    4. FLP_INDUSTRIAL_10 Manual Baseline Validation (True Positive)
    5. Deliberate Counter-Examples (Overlap, Out-of-Bounds, Aspect Ratio, Area Mismatch)
    6. ALDEP Geometry Diagnostics (Non-Rectangular Cells, Bounding Box Overlaps, Area Distortion)
    7. Future Representation Paradigms (Slicing Tree, Sequence Pair)
    8. Rectangular Feasibility Service Facade
"""

import json
from pathlib import Path
import pytest

from app.feasibility import (
    ALDEPGeometryDiagnostics,
    DepartmentDiagnosticDetail,
    DepartmentGeometryFailureType,
    DimensionAlternativeTag,
    FreeRectangle,
    FreeRectangleDetector,
    FreeSpaceReport,
    LayoutGeometryDiagnosticReport,
    LegalDimension,
    LegalDimensionGenerator,
    PlacementFeasibilityChecker,
    PlacementFeasibilityResult,
    RectangularFeasibilityService,
    SequencePair,
    SlicingCutType,
    SlicingNode,
    SlicingTree,
    rectangular_feasibility_service,
)
from app.models.department import Department
from app.models.geometry import BoundingBox, Dimensions2D, Point2D, ReservedZone
from app.models.problem import FacilityLayoutProblem
from app.models.facility import Facility
from app.models.representation import ContinuousLayout, ContinuousPlacement, GridLayout, GridDepartmentBlock
from app.services.problem_service import problem_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_dept_100() -> Department:
    """100 m2 department with width bounds [5, 20] and max aspect ratio 2.5."""
    return Department(
        id="DEP_TEST_100",
        name="Test 100m2 Dept",
        required_area=100.0,
        min_width=5.0,
        max_width=20.0,
        min_height=5.0,
        max_height=20.0,
        max_aspect_ratio=2.5,
    )


@pytest.fixture
def industrial_10_problem() -> FacilityLayoutProblem:
    """Load FLP_INDUSTRIAL_10 problem definition."""
    return problem_service.get_example_problem("FLP_INDUSTRIAL_10")


@pytest.fixture
def industrial_10_baseline_layout() -> ContinuousLayout:
    """Load sample_layout.json baseline layout for FLP_INDUSTRIAL_10."""
    examples_dir = Path(__file__).resolve().parent.parent.parent / "data" / "examples"
    layout_file = examples_dir / "sample_layout.json"
    with open(layout_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ContinuousLayout.model_validate(data)


# ---------------------------------------------------------------------------
# 1. Legal Shape Generation
# ---------------------------------------------------------------------------
class TestLegalDimensionGeneration:
    """Tests for LegalDimensionGenerator and area-conserving rectangular alternatives."""

    def test_square_ish_dimension(self, sample_dept_100: Department):
        """For a 100 m2 dept with [5..20] bounds, the square-ish shape is 10.0 x 10.0."""
        dims = LegalDimensionGenerator.generate_legal_dimensions(
            department=sample_dept_100,
            facility_width=100.0,
            facility_height=60.0,
        )
        assert len(dims) > 0
        square = next((d for d in dims if d.tag == DimensionAlternativeTag.SQUARE_ISH), None)
        assert square is not None
        assert square.width == 10.0
        assert square.height == 10.0
        assert square.aspect_ratio == 1.0
        assert abs(square.area - 100.0) < 1e-4

    def test_all_alternatives_conserve_exact_area(self, sample_dept_100: Department):
        """Every generated alternative must satisfy width * height == required_area within 1e-4."""
        dims = LegalDimensionGenerator.generate_legal_dimensions(
            department=sample_dept_100,
            facility_width=100.0,
            facility_height=60.0,
            max_alternatives=12,
        )
        assert len(dims) >= 3
        for d in dims:
            assert abs(d.area - 100.0) < 1e-4, f"Alternative {d} does not conserve required area!"
            assert sample_dept_100.min_width <= d.width <= sample_dept_100.max_width
            assert sample_dept_100.min_height <= d.height <= sample_dept_100.max_height
            assert d.aspect_ratio <= sample_dept_100.max_aspect_ratio + 1e-4

    def test_impossible_constraints_return_empty(self):
        """When constraints cannot simultaneously satisfy area, returns empty list."""
        # required_area = 100, but min_width = 30 and max_height = 2 -> min area possible = 60 < 100
        # or if min_width = 30, min_height = 30 -> min area = 900 > 100
        impossible_dept = Department(
            id="DEP_IMP",
            name="Impossible",
            required_area=100.0,
            min_width=30.0,
            min_height=30.0,
            max_aspect_ratio=2.0,
        )
        dims = LegalDimensionGenerator.generate_legal_dimensions(
            department=impossible_dept,
            facility_width=100.0,
            facility_height=60.0,
        )
        assert dims == []

    def test_modular_alignment_with_existing_dimensions(self, sample_dept_100: Department):
        """If existing widths/heights exist and are legally within bounds, generator snaps to them."""
        existing_w = [8.0, 12.5, 45.0]  # 8.0 and 12.5 are within [5..20]
        dims = LegalDimensionGenerator.generate_legal_dimensions(
            department=sample_dept_100,
            facility_width=100.0,
            facility_height=60.0,
            existing_widths=existing_w,
        )
        widths = [d.width for d in dims]
        assert 8.0 in widths
        assert 12.5 in widths

    def test_aspect_ratio_enforcement(self):
        """Dept with strict max_aspect_ratio=1.2 must never produce elongated shapes."""
        strict_dept = Department(
            id="DEP_STRICT",
            name="Strict Aspect Ratio",
            required_area=100.0,
            min_width=2.0,
            max_width=50.0,
            max_aspect_ratio=1.2,
        )
        dims = LegalDimensionGenerator.generate_legal_dimensions(
            department=strict_dept,
            facility_width=100.0,
            facility_height=60.0,
        )
        for d in dims:
            assert d.aspect_ratio <= 1.2 + 1e-4


# ---------------------------------------------------------------------------
# 2. Free Rectangle Detection (Maximal Empty Rectangles)
# ---------------------------------------------------------------------------
class TestFreeRectangleDetection:
    """Tests for 2D Maximal Empty Rectangles (MER) discovery and net area calculation."""

    def test_empty_facility(self):
        """Completely empty facility contains exactly 1 MER spanning the entire facility."""
        report = FreeRectangleDetector.detect_free_rectangles(
            facility_width=100.0,
            facility_height=60.0,
            placements=[],
        )
        assert report.total_facility_area == 6000.0
        assert report.net_free_area == 6000.0
        assert report.total_occupied_area == 0.0
        assert len(report.maximal_empty_rectangles) == 1
        mer = report.maximal_empty_rectangles[0]
        assert mer.x == 0.0
        assert mer.y == 0.0
        assert mer.width == 100.0
        assert mer.height == 60.0

    def test_completely_filled_facility(self):
        """Completely filled facility has 0 MERs and 0 net free area."""
        full_block = BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=60.0)
        report = FreeRectangleDetector.detect_free_rectangles(
            facility_width=100.0,
            facility_height=60.0,
            placements=[full_block],
        )
        assert report.net_free_area == 0.0
        assert report.maximal_empty_rectangles == []

    def test_l_shaped_free_space_hand_calculated(self):
        """Hand-calculated benchmark:
        Facility: 50 x 20 (area = 1000).
        Occupied block: [0, 0, 10, 10] (bottom-left corner, area = 100).
        Remaining space is L-shaped:
            R1: [10, 0] to [50, 20] -> width 40, height 20, area = 800.
            R2: [0, 10] to [50, 20] -> width 50, height 10, area = 500.
        Net free area = 1000 - 100 = 900.
        Both R1 and R2 are maximal and overlap over [10..50, 10..20] (area 400).
        """
        block = BoundingBox(x_min=0.0, y_min=0.0, x_max=10.0, y_max=10.0)
        report = FreeRectangleDetector.detect_free_rectangles(
            facility_width=50.0,
            facility_height=20.0,
            placements=[block],
        )

        assert report.total_facility_area == 1000.0
        assert report.total_occupied_area == 100.0
        assert report.net_free_area == 900.0

        mers = report.maximal_empty_rectangles
        assert len(mers) == 2, f"Expected exactly 2 MERs, found {len(mers)}"

        # Check for R1 (40 x 20) and R2 (50 x 10)
        has_r1 = any(abs(r.x - 10.0) < 1e-4 and abs(r.y - 0.0) < 1e-4 and abs(r.width - 40.0) < 1e-4 and abs(r.height - 20.0) < 1e-4 for r in mers)
        has_r2 = any(abs(r.x - 0.0) < 1e-4 and abs(r.y - 10.0) < 1e-4 and abs(r.width - 50.0) < 1e-4 and abs(r.height - 10.0) < 1e-4 for r in mers)

        assert has_r1, "Maximal rectangle R1 [10..50, 0..20] not found!"
        assert has_r2, "Maximal rectangle R2 [0..50, 10..20] not found!"

        # Academic verify: Sum of MER areas (800 + 500 = 1300) > net free area (900) due to overlap
        sum_mer_areas = sum(r.area for r in mers)
        assert sum_mer_areas == 1300.0
        assert sum_mer_areas > report.net_free_area

    def test_reserved_zone_obstruction(self):
        """Reserved zone (e.g. central safety pillar) is treated as an obstacle in free space detection."""
        reserved = ReservedZone(
            id="RES_PILLAR",
            bounding_box=BoundingBox(x_min=40.0, y_min=20.0, x_max=60.0, y_max=40.0),
            description="Pillar",
        )
        report = FreeRectangleDetector.detect_free_rectangles(
            facility_width=100.0,
            facility_height=60.0,
            placements=[],
            reserved_zones=[reserved],
        )
        assert report.total_facility_area == 6000.0
        assert report.total_occupied_area == 400.0
        assert report.net_free_area == 5600.0
        # No MER should intersect the reserved zone strictly inside
        for r in report.maximal_empty_rectangles:
            overlap_w = max(0.0, min(r.x + r.width, 60.0) - max(r.x, 40.0))
            overlap_h = max(0.0, min(r.y + r.height, 40.0) - max(r.y, 20.0))
            assert (overlap_w * overlap_h) < 1e-4, f"MER {r} intersects reserved zone!"


# ---------------------------------------------------------------------------
# 3. Placement Feasibility Checking
# ---------------------------------------------------------------------------
class TestPlacementFeasibilityChecking:
    """Tests for PlacementFeasibilityChecker independent validation."""

    def test_valid_placement(self, sample_dept_100: Department):
        """Valid placement inside facility with correct dimensions returns is_feasible=True."""
        res = PlacementFeasibilityChecker.check_placement(
            department=sample_dept_100,
            dimensions=Dimensions2D(width=10.0, height=10.0),
            coordinates=Point2D(x=10.0, y=10.0),
            facility_width=100.0,
            facility_height=60.0,
            existing_placements={},
        )
        assert res.is_feasible is True
        assert res.errors == []
        assert res.boundary_contained is True
        assert res.overlap_free is True
        assert res.area_conserved is True
        assert res.dimensions_valid is True
        assert res.aspect_ratio_valid is True
        assert res.residual_free_space_m2 == 5900.0

    def test_out_of_boundary_placement(self, sample_dept_100: Department):
        """Placement exceeding boundary is rejected with detailed error."""
        res = PlacementFeasibilityChecker.check_placement(
            department=sample_dept_100,
            dimensions=Dimensions2D(width=10.0, height=10.0),
            coordinates=Point2D(x=95.0, y=10.0),  # x + width = 105 > 100
            facility_width=100.0,
            facility_height=60.0,
            existing_placements={},
        )
        assert res.is_feasible is False
        assert res.boundary_contained is False
        assert any("exceeds facility boundary" in e for e in res.errors)

    def test_overlapping_placement(self, sample_dept_100: Department):
        """Placement overlapping existing department is rejected."""
        existing = {
            "DEP_EXISTING": ContinuousPlacement(
                department_id="DEP_EXISTING",
                x=10.0,
                y=10.0,
                width=20.0,
                height=20.0,
            )
        }
        res = PlacementFeasibilityChecker.check_placement(
            department=sample_dept_100,
            dimensions=Dimensions2D(width=10.0, height=10.0),
            coordinates=Point2D(x=15.0, y=15.0),  # Overlaps existing [10..30, 10..30]
            facility_width=100.0,
            facility_height=60.0,
            existing_placements=existing,
        )
        assert res.is_feasible is False
        assert res.overlap_free is False
        assert "DEP_EXISTING" in res.overlapping_departments
        assert any("Overlap detected with department" in e for e in res.errors)

    def test_area_mismatch_placement(self, sample_dept_100: Department):
        """Placement where width * height != required_area is rejected."""
        res = PlacementFeasibilityChecker.check_placement(
            department=sample_dept_100,
            dimensions=Dimensions2D(width=8.0, height=8.0),  # area = 64 != 100
            coordinates=Point2D(x=0.0, y=0.0),
            facility_width=100.0,
            facility_height=60.0,
            existing_placements={},
        )
        assert res.is_feasible is False
        assert res.area_conserved is False
        assert any("Area conservation failure" in e for e in res.errors)

    def test_aspect_ratio_violation(self, sample_dept_100: Department):
        """Placement exceeding max_aspect_ratio is rejected."""
        # width = 20, height = 5 -> aspect_ratio = 4.0 > 2.5
        res = PlacementFeasibilityChecker.check_placement(
            department=sample_dept_100,
            dimensions=Dimensions2D(width=20.0, height=5.0),
            coordinates=Point2D(x=0.0, y=0.0),
            facility_width=100.0,
            facility_height=60.0,
            existing_placements={},
        )
        assert res.is_feasible is False
        assert res.aspect_ratio_valid is False
        assert any("Aspect ratio" in e for e in res.errors)

    def test_fixed_position_respected(self, sample_dept_100: Department):
        """Department with fixed_position placed elsewhere is rejected."""
        dept_fixed = sample_dept_100.model_copy(deep=True)
        dept_fixed.fixed_position = Point2D(x=30.0, y=20.0)

        # Place at wrong coordinates (10, 10)
        res = PlacementFeasibilityChecker.check_placement(
            department=dept_fixed,
            dimensions=Dimensions2D(width=10.0, height=10.0),
            coordinates=Point2D(x=10.0, y=10.0),
            facility_width=100.0,
            facility_height=60.0,
            existing_placements={},
        )
        assert res.is_feasible is False
        assert res.fixed_position_respected is False

        # Place at correct coordinates (30, 20)
        res_ok = PlacementFeasibilityChecker.check_placement(
            department=dept_fixed,
            dimensions=Dimensions2D(width=10.0, height=10.0),
            coordinates=Point2D(x=30.0, y=20.0),
            facility_width=100.0,
            facility_height=60.0,
            existing_placements={},
        )
        assert res_ok.is_feasible is True
        assert res_ok.fixed_position_respected is True


# ---------------------------------------------------------------------------
# 4. FLP_INDUSTRIAL_10 Manual Baseline Validation (True Positive)
# ---------------------------------------------------------------------------
class TestIndustrial10ManualBaseline:
    """Verifies that the complete manual baseline for FLP_INDUSTRIAL_10 passes 100%."""

    def test_manual_baseline_full_validation(
        self,
        industrial_10_problem: FacilityLayoutProblem,
        industrial_10_baseline_layout: ContinuousLayout,
    ):
        """The manual baseline layout must be strictly valid according to rectangular feasibility rules."""
        is_valid, errors = RectangularFeasibilityService.validate_rectangular_layout(
            problem=industrial_10_problem,
            layout=industrial_10_baseline_layout,
        )
        assert is_valid is True, f"Manual baseline validation failed with errors: {errors}"
        assert len(errors) == 0

        # Run detailed diagnostic suite
        report = RectangularFeasibilityService.diagnose_layout(
            problem=industrial_10_problem,
            continuous_layout=industrial_10_baseline_layout,
        )
        assert report.is_strictly_valid is True
        assert report.overlapping_department_pairs == []
        assert len(report.department_details) == 10

        for dept_id, detail in report.department_details.items():
            assert detail.failure_types == [], f"Department {dept_id} had failures: {detail.failure_types}"
            assert abs(detail.area_distortion_ratio - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# 5. Deliberate Counter-Examples (Strict False Rejection)
# ---------------------------------------------------------------------------
class TestDeliberateCounterExamples:
    """Verifies that deliberate corruptions of the valid baseline are strictly rejected."""

    def test_overlap_counter_example(
        self,
        industrial_10_problem: FacilityLayoutProblem,
        industrial_10_baseline_layout: ContinuousLayout,
    ):
        """Corrupting DEP_CUTTING position to overlap DEP_RAW_MATERIAL must fail validation."""
        corrupted = industrial_10_baseline_layout.model_copy(deep=True)
        # Shift DEP_CUTTING (adjacent to DEP_RAW_MATERIAL) into DEP_RAW_MATERIAL's area
        p1 = corrupted.placements["DEP_RAW_MATERIAL"]
        corrupted.placements["DEP_CUTTING"].x = p1.x + 5.0
        corrupted.placements["DEP_CUTTING"].y = p1.y

        is_valid, errors = RectangularFeasibilityService.validate_rectangular_layout(
            problem=industrial_10_problem,
            layout=corrupted,
        )
        assert is_valid is False
        assert any("Overlap detected between" in e for e in errors)

    def test_boundary_overflow_counter_example(
        self,
        industrial_10_problem: FacilityLayoutProblem,
        industrial_10_baseline_layout: ContinuousLayout,
    ):
        """Corrupting DEP_FINISHED_GOODS position to cross facility boundary must fail validation."""
        corrupted = industrial_10_baseline_layout.model_copy(deep=True)
        # Shift DEP_FINISHED_GOODS rightwards past facility.width (150)
        corrupted.placements["DEP_FINISHED_GOODS"].x = 130.0

        is_valid, errors = RectangularFeasibilityService.validate_rectangular_layout(
            problem=industrial_10_problem,
            layout=corrupted,
        )
        assert is_valid is False
        assert any("exceeds facility boundary" in e or "exceeds facility boundaries" in e for e in errors)

    def test_aspect_ratio_counter_example(
        self,
        industrial_10_problem: FacilityLayoutProblem,
        industrial_10_baseline_layout: ContinuousLayout,
    ):
        """Corrupting DEP_RAW_MATERIAL dimensions into an excessively thin strip must fail aspect ratio."""
        prob = industrial_10_problem.model_copy(deep=True)
        prob.departments[0].max_aspect_ratio = 2.0  # Set strict aspect ratio limit

        corrupted = industrial_10_baseline_layout.model_copy(deep=True)
        # Required area is 1300. Make it 130 x 10 -> aspect ratio = 13.0 (exceeds 2.0)
        corrupted.placements["DEP_RAW_MATERIAL"].width = 130.0
        corrupted.placements["DEP_RAW_MATERIAL"].height = 10.0

        is_valid, errors = RectangularFeasibilityService.validate_rectangular_layout(
            problem=prob,
            layout=corrupted,
        )
        assert is_valid is False
        assert any("Aspect ratio" in e for e in errors)

    def test_area_mismatch_counter_example(
        self,
        industrial_10_problem: FacilityLayoutProblem,
        industrial_10_baseline_layout: ContinuousLayout,
    ):
        """Corrupting DEP_RAW_MATERIAL dimensions so area != 1300 must fail area conservation."""
        corrupted = industrial_10_baseline_layout.model_copy(deep=True)
        # Set 20 x 20 = 400 != 1300
        corrupted.placements["DEP_RAW_MATERIAL"].width = 20.0
        corrupted.placements["DEP_RAW_MATERIAL"].height = 20.0

        is_valid, errors = RectangularFeasibilityService.validate_rectangular_layout(
            problem=industrial_10_problem,
            layout=corrupted,
        )
        assert is_valid is False
        assert any("Area distortion" in e for e in errors)

    def test_missing_department_counter_example(
        self,
        industrial_10_problem: FacilityLayoutProblem,
        industrial_10_baseline_layout: ContinuousLayout,
    ):
        """Dropping a department from the layout must fail validation."""
        corrupted = industrial_10_baseline_layout.model_copy(deep=True)
        del corrupted.placements["DEP_FINISHED_GOODS"]

        is_valid, errors = RectangularFeasibilityService.validate_rectangular_layout(
            problem=industrial_10_problem,
            layout=corrupted,
        )
        assert is_valid is False
        assert any("Missing placements for required departments: ['DEP_FINISHED_GOODS']" in e for e in errors)


# ---------------------------------------------------------------------------
# 6. ALDEP Geometry Diagnostics
# ---------------------------------------------------------------------------
class TestALDEPGeometryDiagnostics:
    """Tests isolating discrete non-rectangular shapes, bounding box overlaps, and distortion."""

    def test_discrete_non_rectangular_cells_detection(self, industrial_10_problem: FacilityLayoutProblem):
        """Serpentine wrap across strips creates an L-shaped discrete cluster.
        Cells: (0,0), (0,1), (1,1) -> 3 cells, but bounding box is 2x2 = 4 cells.
        Diagnostic must flag DISCRETE_NON_RECTANGULAR_CELLS.
        """
        grid = GridLayout(
            problem_id="FLP_INDUSTRIAL_10",
            facility_width=100.0,
            facility_height=60.0,
            cell_size=10.0,
            rows=6,
            columns=10,
            department_blocks={
                "DEP_01": GridDepartmentBlock(
                    department_id="DEP_01",
                    cells=[(0, 0), (0, 1), (1, 1)],
                )
            },
        )
        # Bounding box of DEP_01 is [0..20, 0..20]
        cont = ContinuousLayout(
            problem_id="FLP_INDUSTRIAL_10",
            facility_width=100.0,
            facility_height=60.0,
            placements={
                "DEP_01": ContinuousPlacement(department_id="DEP_01", x=0.0, y=0.0, width=20.0, height=20.0)
            },
        )

        report = ALDEPGeometryDiagnostics.diagnose_layout(
            problem=industrial_10_problem,
            continuous_layout=cont,
            grid_layout=grid,
        )

        detail = report.department_details["DEP_01"]
        assert DepartmentGeometryFailureType.DISCRETE_NON_RECTANGULAR_CELLS in detail.failure_types
        assert detail.discrete_cell_count == 3
        assert detail.bounding_box_cell_count == 4
        assert detail.is_rectangular_in_grid is False

    def test_bounding_box_overlap_vs_discrete_disjointness(self, industrial_10_problem: FacilityLayoutProblem):
        """Two L-shaped departments interlock without sharing any discrete cells:
        DEP_01: (0,0), (0,1), (1,0) -> 3 cells, bounding box [0..2, 0..2]
        DEP_02: (1,1)                -> 1 cell, bounding box [1..2, 1..2]
        Grid cells have zero overlap, but their continuous bounding boxes OVERLAP on (1,1)!
        Diagnostic must report BOUNDING_BOX_OVERLAP while noting cells were disjoint.
        """
        grid = GridLayout(
            problem_id="FLP_INDUSTRIAL_10",
            facility_width=100.0,
            facility_height=60.0,
            cell_size=10.0,
            rows=6,
            columns=10,
            department_blocks={
                "DEP_01": GridDepartmentBlock(
                    department_id="DEP_01",
                    cells=[(0, 0), (0, 1), (1, 0)],
                ),
                "DEP_02": GridDepartmentBlock(
                    department_id="DEP_02",
                    cells=[(1, 1)],
                ),
            },
        )
        cont = ContinuousLayout(
            problem_id="FLP_INDUSTRIAL_10",
            facility_width=100.0,
            facility_height=60.0,
            placements={
                "DEP_01": ContinuousPlacement(department_id="DEP_01", x=0.0, y=0.0, width=20.0, height=20.0),
                "DEP_02": ContinuousPlacement(department_id="DEP_02", x=10.0, y=10.0, width=10.0, height=10.0),
            },
        )

        report = ALDEPGeometryDiagnostics.diagnose_layout(
            problem=industrial_10_problem,
            continuous_layout=cont,
            grid_layout=grid,
        )

        # Continuous bounding boxes overlap on [10..20, 10..20] (area 100)
        assert len(report.overlapping_department_pairs) == 1
        p_a, p_b, area = report.overlapping_department_pairs[0]
        assert {p_a, p_b} == {"DEP_01", "DEP_02"}
        assert area == 100.0
        assert DepartmentGeometryFailureType.BOUNDING_BOX_OVERLAP in report.department_details["DEP_01"].failure_types
        assert DepartmentGeometryFailureType.BOUNDING_BOX_OVERLAP in report.department_details["DEP_02"].failure_types

    def test_area_distortion_diagnosis(self, industrial_10_problem: FacilityLayoutProblem):
        """When an allocated bounding box differs from required area,
        diagnostic must flag AREA_DISTORTION.
        """
        cont = ContinuousLayout(
            problem_id="FLP_INDUSTRIAL_10",
            facility_width=150.0,
            facility_height=80.0,
            placements={
                "DEP_RAW_MATERIAL": ContinuousPlacement(department_id="DEP_RAW_MATERIAL", x=0.0, y=0.0, width=20.0, height=20.0)
            },
        )
        report = ALDEPGeometryDiagnostics.diagnose_layout(
            problem=industrial_10_problem,
            continuous_layout=cont,
        )
        detail = report.department_details["DEP_RAW_MATERIAL"]
        assert DepartmentGeometryFailureType.AREA_DISTORTION in detail.failure_types
        assert detail.area_distortion_ratio == round(400.0 / 1300.0, 4)


# ---------------------------------------------------------------------------
# 7. Future Representation Paradigms
# ---------------------------------------------------------------------------
class TestFutureRepresentationParadigms:
    """Tests for Slicing Tree and Sequence Pair metaheuristic representations."""

    def test_slicing_tree_evaluation_and_polish_expression(self):
        """Slicing tree guarantees 100% non-overlapping placements."""
        # Tree:
        #        V (0.5)
        #       /       \
        #    DEP_A       H (0.4)
        #               /       \
        #            DEP_B     DEP_C
        root = SlicingNode(
            cut_type=SlicingCutType.VERTICAL,
            cut_ratio=0.5,
            left=SlicingNode(department_id="DEP_A"),
            right=SlicingNode(
                cut_type=SlicingCutType.HORIZONTAL,
                cut_ratio=0.4,
                left=SlicingNode(department_id="DEP_B"),
                right=SlicingNode(department_id="DEP_C"),
            ),
        )
        tree = SlicingTree(root=root, problem_id="TEST_SLICING")

        # Evaluate into continuous layout on 100 x 60 facility
        layout = tree.to_continuous_layout(facility_width=100.0, facility_height=60.0)

        assert len(layout.placements) == 3
        # DEP_A gets left half: x=0, y=0, w=50, h=60 (area 3000)
        pa = layout.placements["DEP_A"]
        assert pa.x == 0.0 and pa.y == 0.0 and pa.width == 50.0 and pa.height == 60.0

        # DEP_B gets right bottom: x=50, y=0, w=50, h=24 (area 1200)
        pb = layout.placements["DEP_B"]
        assert pb.x == 50.0 and pb.y == 0.0 and pb.width == 50.0 and pb.height == 24.0

        # DEP_C gets right top: x=50, y=24, w=50, h=36 (area 1800)
        pc = layout.placements["DEP_C"]
        assert pc.x == 50.0 and pc.y == 24.0 and pc.width == 50.0 and pc.height == 36.0

        # Sum of areas = 3000 + 1200 + 1800 = 6000 (Exact facility area!)
        assert sum(p.width * p.height for p in layout.placements.values()) == 6000.0

        # Polish Expression postorder: ["DEP_A", "DEP_B", "DEP_C", "H", "V"]
        expr = tree.to_polish_expression()
        assert expr == ["DEP_A", "DEP_B", "DEP_C", "H", "V"]

        # Reconstruct tree from Polish expression
        tree_reconstructed = SlicingTree.from_polish_expression(expr)
        expr2 = tree_reconstructed.to_polish_expression()
        assert expr == expr2

    def test_sequence_pair_topological_precedence(self):
        """Murata (1996) Sequence Pair encodes horizontal and vertical relative positions."""
        # Gamma+ = ["A", "B", "C"], Gamma- = ["A", "B", "C"]
        # Both orders agree -> A is left of B, B is left of C, A is left of C
        sp_horizontal = SequencePair(
            positive_sequence=["A", "B", "C"],
            negative_sequence=["A", "B", "C"],
        )
        assert sp_horizontal.is_left_of("A", "B") is True
        assert sp_horizontal.is_left_of("B", "C") is True
        assert sp_horizontal.is_left_of("A", "C") is True
        assert sp_horizontal.is_below("A", "B") is False

        # Gamma+ = ["B", "A"], Gamma- = ["A", "B"]
        # B precedes A in Gamma+, but A precedes B in Gamma- -> A is below B
        sp_vertical = SequencePair(
            positive_sequence=["B", "A"],
            negative_sequence=["A", "B"],
        )
        assert sp_vertical.is_below("A", "B") is True
        assert sp_vertical.is_left_of("A", "B") is False


# ---------------------------------------------------------------------------
# 8. Rectangular Feasibility Service Facade
# ---------------------------------------------------------------------------
class TestRectangularFeasibilityServiceFacade:
    """Verifies that RectangularFeasibilityService methods delegate accurately."""

    def test_service_facade_methods(self, sample_dept_100: Department):
        # generate_legal_dimensions
        dims = rectangular_feasibility_service.generate_legal_dimensions(
            department=sample_dept_100,
            facility_width=100.0,
            facility_height=60.0,
        )
        assert len(dims) > 0

        # detect_free_rectangles
        free = rectangular_feasibility_service.detect_free_rectangles(
            facility_width=100.0,
            facility_height=60.0,
            placements=[],
        )
        assert free.net_free_area == 6000.0

        # check_placement
        chk = rectangular_feasibility_service.check_placement(
            department=sample_dept_100,
            dimensions=Dimensions2D(width=10.0, height=10.0),
            coordinates=Point2D(x=0.0, y=0.0),
            facility_width=100.0,
            facility_height=60.0,
            existing_placements={},
        )
        assert chk.is_feasible is True
