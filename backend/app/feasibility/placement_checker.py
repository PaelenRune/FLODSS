"""Placement feasibility verification checking geometric, boundary, and overlap rules."""

import math
from typing import Any, Dict, List, Optional, Union

from app.feasibility.models import FreeRectangle, LegalDimension, PlacementFeasibilityResult
from app.models.department import Department
from app.models.geometry import BoundingBox, Dimensions2D, Point2D, ReservedZone
from app.models.representation import ContinuousPlacement


class PlacementFeasibilityChecker:
    """Verifies whether a department can legally be positioned at given coordinates and dimensions."""

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
        """Perform comprehensive constraint checks for a proposed rectangular department placement."""
        rejections: List[str] = []
        w = round(dimensions.width, 2)
        h = round(dimensions.height, 2)
        x = round(coordinates.x, 2)
        y = round(coordinates.y, 2)

        area = w * h
        req_area = department.required_area
        area_diff = abs(area - req_area)

        # 1. Required Area Conservation
        if area_diff > (req_area * 0.02 + 0.1):
            diff_pct = (area_diff / req_area) * 100.0
            rejections.append(
                f"Area conservation failure: allocated area ({area:.2f} m²) differs from required area ({req_area:.2f} m²) by {diff_pct:.1f}%."
            )

        # 2. Dimensional Bounds
        if department.min_width is not None and w < department.min_width - tolerance:
            rejections.append(f"Width ({w:.2f}m) violates minimum width ({department.min_width:.2f}m).")
        if department.max_width is not None and w > department.max_width + tolerance:
            rejections.append(f"Width ({w:.2f}m) exceeds maximum width ({department.max_width:.2f}m).")

        if department.min_height is not None and h < department.min_height - tolerance:
            rejections.append(f"Height ({h:.2f}m) violates minimum height ({department.min_height:.2f}m).")
        if department.max_height is not None and h > department.max_height + tolerance:
            rejections.append(f"Height ({h:.2f}m) exceeds maximum height ({department.max_height:.2f}m).")

        # 3. Aspect Ratio Bounds
        min_dim = min(w, h)
        ar = max(w, h) / min_dim if min_dim > 0 else 1.0
        if department.max_aspect_ratio is not None and ar > department.max_aspect_ratio + tolerance:
            rejections.append(
                f"Aspect ratio ({ar:.2f}) exceeds maximum allowed aspect ratio ({department.max_aspect_ratio:.2f})."
            )
        if department.min_aspect_ratio is not None and ar < department.min_aspect_ratio - tolerance:
            rejections.append(
                f"Aspect ratio ({ar:.2f}) violates minimum allowed aspect ratio ({department.min_aspect_ratio:.2f})."
            )

        # 4. Facility Boundary Containment
        proposed_box = BoundingBox(x_min=x, y_min=y, x_max=x + w, y_max=y + h)
        if (
            proposed_box.x_min < -tolerance
            or proposed_box.y_min < -tolerance
            or proposed_box.x_max > facility_width + tolerance
            or proposed_box.y_max > facility_height + tolerance
        ):
            rejections.append(
                f"Placement exceeds facility boundary: coordinates [{proposed_box.x_min:.1f}..{proposed_box.x_max:.1f}, "
                f"{proposed_box.y_min:.1f}..{proposed_box.y_max:.1f}] exceed [{facility_width:.1f} x {facility_height:.1f}]."
            )

        # 5. Fixed Position Constraint
        if department.fixed_position is not None:
            fp = department.fixed_position
            dist_origin = math.hypot(x - fp.x, y - fp.y)
            dist_centroid = math.hypot(proposed_box.centroid.x - fp.x, proposed_box.centroid.y - fp.y)
            if dist_origin > tolerance and dist_centroid > tolerance:
                rejections.append(
                    f"Violates fixed position constraint: placed at ({x}, {y}), expected ({fp.x}, {fp.y})."
                )

        # 6. Pairwise Overlap with Placed Departments
        total_overlap = 0.0
        for other_id, other_placement in existing_placements.items():
            if other_id == department.id:
                continue
            other_box = other_placement.bounding_box
            overlap = proposed_box.overlap_area(other_box, tolerance=tolerance)
            if overlap > tolerance:
                total_overlap += overlap
                rejections.append(
                    f"Overlap detected with department '{other_id}' (overlap area: {overlap:.2f} m²)."
                )

        # 7. Reserved Zone Overlap
        if reserved_zones:
            for rz in reserved_zones:
                overlap = proposed_box.overlap_area(rz.bounding_box, tolerance=tolerance)
                if overlap > tolerance:
                    total_overlap += overlap
                    rejections.append(
                        f"Overlap detected with reserved zone '{rz.id}' (overlap area: {overlap:.2f} m²)."
                    )

        # 8. Residual Space Metrics
        fac_total_area = facility_width * facility_height
        curr_occupied = sum(p.area for p in existing_placements.values())
        if reserved_zones:
            curr_occupied += sum(rz.bounding_box.area for rz in reserved_zones)
        remaining_area = max(0.0, fac_total_area - (curr_occupied + area))

        remaining_info = {
            "facility_area": fac_total_area,
            "allocated_department_area": area,
            "net_free_area_after_placement": round(remaining_area, 2),
            "free_area_percentage": round((remaining_area / fac_total_area) * 100.0, 2),
        }

        is_feasible = len(rejections) == 0

        return PlacementFeasibilityResult(
            feasible=is_feasible,
            rejection_reasons=rejections,
            department_id=department.id,
            selected_dimensions=dimensions if is_feasible else None,
            selected_coordinates=coordinates if is_feasible else None,
            placed_bounding_box=proposed_box if is_feasible else None,
            area_difference=round(area_diff, 2),
            overlap_area=round(total_overlap, 2),
            remaining_available_space=remaining_info,
        )

    @classmethod
    def can_fit_in_region(
        cls,
        department: Department,
        dimensions: Dimensions2D,
        free_region: FreeRectangle,
        tolerance: float = 1e-4,
    ) -> bool:
        """Quickly check if department with dimensions fits into a specific free rectangle."""
        return free_region.can_accommodate(dimensions.width, dimensions.height, tolerance=tolerance)
