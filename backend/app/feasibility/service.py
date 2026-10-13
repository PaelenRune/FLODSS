"""Centralized service for rectangular layout feasibility, legal shapes, and free space detection."""

from typing import Any, Dict, List, Optional, Tuple, Union

from app.feasibility.aldep_diagnostics import ALDEPGeometryDiagnostics
from app.feasibility.dimension_generator import LegalDimensionGenerator
from app.feasibility.free_rectangles import FreeRectangleDetector
from app.feasibility.models import (
    FreeRectangle,
    FreeSpaceReport,
    LayoutGeometryDiagnosticReport,
    LegalDimension,
    PlacementFeasibilityResult,
)
from app.feasibility.placement_checker import PlacementFeasibilityChecker
from app.models.department import Department
from app.models.geometry import BoundingBox, Dimensions2D, Point2D, ReservedZone
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement, GridLayout


class RectangularFeasibilityService:
    """Unified service consolidating all rectangular layout feasibility capabilities.
    
    Provides:
        1. Legal department dimension alternative generation conserving exact area.
        2. Free rectangular region detection (Maximal Empty Rectangles).
        3. Independent placement feasibility checking with residual space metrics.
        4. Geometry diagnostics for discrete grid-to-continuous conversion failures.
        5. Full continuous rectangular layout validation.
    """

    @classmethod
    def generate_legal_dimensions(
        cls,
        department: Department,
        facility_width: float,
        facility_height: float,
        existing_widths: Optional[List[float]] = None,
        existing_heights: Optional[List[float]] = None,
        max_alternatives: int = 10,
        tolerance: float = 1e-4,
    ) -> List[LegalDimension]:
        """Generate legal rectangular shape alternatives conserving required area."""
        return LegalDimensionGenerator.generate_legal_dimensions(
            department=department,
            facility_width=facility_width,
            facility_height=facility_height,
            existing_widths=existing_widths,
            existing_heights=existing_heights,
            max_alternatives=max_alternatives,
            tolerance=tolerance,
        )

    @classmethod
    def detect_free_rectangles(
        cls,
        facility_width: float,
        facility_height: float,
        placements: List[Union[ContinuousPlacement, BoundingBox]],
        reserved_zones: Optional[List[Union[ReservedZone, BoundingBox]]] = None,
        min_area_threshold: float = 1.0,
        tolerance: float = 1e-4,
    ) -> FreeSpaceReport:
        """Scan facility space and identify all maximal empty rectangular regions."""
        return FreeRectangleDetector.detect_free_rectangles(
            facility_width=facility_width,
            facility_height=facility_height,
            placements=placements,
            reserved_zones=reserved_zones,
            min_area_threshold=min_area_threshold,
            tolerance=tolerance,
        )

    @classmethod
    def check_placement(
        cls,
        department: Department,
        dimensions: Dimensions2D,
        coordinates: Point2D,
        facility_width: float,
        facility_height: float,
        existing_placements: Dict[str, ContinuousPlacement],
        reserved_zones: Optional[List[ReservedZone]] = None,
        tolerance: float = 1e-4,
    ) -> PlacementFeasibilityResult:
        """Verify whether a department can be placed at given coordinates and dimensions."""
        return PlacementFeasibilityChecker.check_placement(
            department=department,
            dimensions=dimensions,
            coordinates=coordinates,
            facility_width=facility_width,
            facility_height=facility_height,
            existing_placements=existing_placements,
            reserved_zones=reserved_zones,
            tolerance=tolerance,
        )

    @classmethod
    def diagnose_layout(
        cls,
        problem: FacilityLayoutProblem,
        continuous_layout: ContinuousLayout,
        grid_layout: Optional[GridLayout] = None,
        tolerance: float = 1e-4,
    ) -> LayoutGeometryDiagnosticReport:
        """Run diagnostic suite categorizing non-rectangularity, overlaps, and bound violations."""
        return ALDEPGeometryDiagnostics.diagnose_layout(
            problem=problem,
            continuous_layout=continuous_layout,
            grid_layout=grid_layout,
            tolerance=tolerance,
        )

    @classmethod
    def validate_rectangular_layout(
        cls,
        problem: FacilityLayoutProblem,
        layout: ContinuousLayout,
        tolerance: float = 1e-4,
    ) -> Tuple[bool, List[str]]:
        """Validate layout against all Section 2 rectangular feasibility rules.
        
        Returns:
            Tuple of (is_feasible, list_of_error_messages).
        """
        report = cls.diagnose_layout(problem=problem, continuous_layout=layout, tolerance=tolerance)
        errors: List[str] = []

        # Check missing departments
        problem_depts = {d.id for d in problem.departments}
        placed_depts = set(layout.placements.keys())
        missing = problem_depts - placed_depts
        if missing:
            errors.append(f"Missing placements for required departments: {sorted(list(missing))}.")

        # Aggregate diagnostic failures
        for dept_id, detail in report.department_details.items():
            for msg in detail.failure_messages:
                errors.append(f"[{dept_id}] {msg}")

        for dept_a, dept_b, overlap_m2 in report.overlapping_department_pairs:
            errors.append(f"Overlap detected between '{dept_a}' and '{dept_b}' ({overlap_m2:.2f} m²).")

        return len(errors) == 0, errors


rectangular_feasibility_service = RectangularFeasibilityService()
