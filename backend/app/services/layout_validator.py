"""Layout Validator for geometric feasibility, boundaries, overlaps, and domain constraints."""

import math
from typing import Any, Dict, List, Optional, Union, Tuple
from pydantic import BaseModel, Field

from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.models.geometry import BoundingBox, ReservedZone
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.services.geometry_engine import GeometryEngine
from app.services.layout_normalizer import generate_layout_signature


class LayoutValidationResult(BaseModel):
    """Detailed geometric validation outcome for a layout."""

    is_valid: bool = Field(..., description="True if strictly feasible without overlaps or boundary violations")
    errors: List[str] = Field(default_factory=list, description="Fatal geometric violations")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal dimensional advisories")
    total_overlap_area: float = Field(default=0.0, description="Total area of overlapping regions in m²")
    checked_departments: List[str] = Field(default_factory=list, description="List of validated department IDs")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Basic layout spatial metrics")
    signature: Optional[str] = Field(default=None, description="Deterministic geometric signature")


class LayoutValidator:
    """Validates layout placements against facility geometry and problem specifications."""

    @classmethod
    def validate(
        cls,
        problem: Union[FacilityLayoutProblem, ContinuousLayout, LayoutSolution, Dict[str, Any]],
        layout: Optional[Union[FacilityLayoutProblem, ContinuousLayout, LayoutSolution, Dict[str, Any]]] = None,
        reserved_zones: Optional[List[ReservedZone]] = None,
        tolerance: float = 1e-4,
    ) -> LayoutValidationResult:
        """Execute geometric and specification validation checks."""
        # Allow flexible order (problem, layout) or (layout, problem)
        if isinstance(problem, (ContinuousLayout, LayoutSolution)) and isinstance(layout, FacilityLayoutProblem):
            problem, layout = layout, problem
        elif isinstance(problem, dict) and "placements" in problem and isinstance(layout, FacilityLayoutProblem):
            problem, layout = layout, problem

        if not isinstance(problem, FacilityLayoutProblem):
            raise TypeError(f"Expected problem to be FacilityLayoutProblem, got {type(problem)}")

        # Convert input into ContinuousLayout
        if isinstance(layout, ContinuousLayout):
            cont_layout = layout
        elif isinstance(layout, LayoutSolution):
            cont_layout = ContinuousLayout.from_layout_solution(
                layout,
                facility_width=problem.facility.width,
                facility_height=problem.facility.height,
            )
        elif isinstance(layout, dict):
            if "placements" in layout:
                cont_layout = ContinuousLayout.model_validate(layout)
            else:
                # Placements passed directly
                cont_layout = ContinuousLayout(
                    facility_width=problem.facility.width,
                    facility_height=problem.facility.height,
                    placements={k: ContinuousPlacement.model_validate(v) for k, v in layout.items()},
                )
        else:
            raise TypeError(f"Unsupported layout type: {type(layout)}")

        errors: List[str] = []
        warnings: List[str] = []

        fac_w = problem.facility.width
        fac_h = problem.facility.height
        facility_box = BoundingBox(x_min=0.0, y_min=0.0, x_max=fac_w, y_max=fac_h)

        problem_depts = {d.id: d for d in problem.departments}
        placed_ids = set(cont_layout.placements.keys())

        # 1. Missing and unexpected departments
        missing = set(problem_depts.keys()) - placed_ids
        if missing:
            errors.append(f"Missing placements for required departments: {sorted(list(missing))}.")

        unexpected = placed_ids - set(problem_depts.keys())
        if unexpected:
            errors.append(f"Layout contains unknown department placements: {sorted(list(unexpected))}.")

        # 2. Check each placement against boundary, dimensions, aspect ratio, and fixed constraints
        for dept_id, placement in cont_layout.placements.items():
            p_box = placement.bounding_box

            # Boundary containment
            if not facility_box.contains_box(p_box, tolerance=tolerance):
                errors.append(
                    f"Department '{dept_id}' exceeds facility boundaries (placed [{placement.left:.1f}..{placement.right:.1f}, {placement.bottom:.1f}..{placement.top:.1f}] vs facility [{fac_w}x{fac_h}])."
                )

            dept_spec = problem_depts.get(dept_id)
            if dept_spec:
                # Required area check
                if abs(placement.area - dept_spec.required_area) > 1e-2:
                    diff_pct = abs(placement.area - dept_spec.required_area) / dept_spec.required_area * 100.0
                    if diff_pct > 2.0:
                        warnings.append(
                            f"Department '{dept_id}' allocated area ({placement.area:.1f} m²) differs from required area ({dept_spec.required_area:.1f} m²) by {diff_pct:.1f}%."
                        )

                # Min/max width
                if dept_spec.min_width is not None and placement.width < dept_spec.min_width - tolerance:
                    errors.append(
                        f"Department '{dept_id}' width ({placement.width:.1f}m) violates minimum width ({dept_spec.min_width:.1f}m)."
                    )
                if dept_spec.max_width is not None and placement.width > dept_spec.max_width + tolerance:
                    errors.append(
                        f"Department '{dept_id}' width ({placement.width:.1f}m) exceeds maximum width ({dept_spec.max_width:.1f}m)."
                    )

                # Min/max height
                if dept_spec.min_height is not None and placement.height < dept_spec.min_height - tolerance:
                    errors.append(
                        f"Department '{dept_id}' height ({placement.height:.1f}m) violates minimum height ({dept_spec.min_height:.1f}m)."
                    )
                if dept_spec.max_height is not None and placement.height > dept_spec.max_height + tolerance:
                    errors.append(
                        f"Department '{dept_id}' height ({placement.height:.1f}m) exceeds maximum height ({dept_spec.max_height:.1f}m)."
                    )

                # Aspect ratio
                if dept_spec.min_aspect_ratio is not None and placement.aspect_ratio < dept_spec.min_aspect_ratio - tolerance:
                    errors.append(
                        f"Department '{dept_id}' aspect ratio ({placement.aspect_ratio:.2f}) violates min_aspect_ratio ({dept_spec.min_aspect_ratio:.2f})."
                    )
                if dept_spec.max_aspect_ratio is not None and placement.aspect_ratio > dept_spec.max_aspect_ratio + tolerance:
                    errors.append(
                        f"Department '{dept_id}' aspect ratio ({placement.aspect_ratio:.2f}) exceeds max_aspect_ratio ({dept_spec.max_aspect_ratio:.2f})."
                    )

                # Fixed position check
                if dept_spec.fixed_position is not None:
                    # Check centroid or origin match
                    expected_pt = dept_spec.fixed_position
                    dist_origin = math.hypot(placement.x - expected_pt.x, placement.y - expected_pt.y)
                    dist_centroid = math.hypot(placement.centroid.x - expected_pt.x, placement.centroid.y - expected_pt.y)
                    if dist_origin > tolerance and dist_centroid > tolerance:
                        errors.append(
                            f"Department '{dept_id}' violates fixed position constraint (placed at ({placement.x}, {placement.y}), expected ({expected_pt.x}, {expected_pt.y}))."
                        )

                # Fixed orientation check
                if dept_spec.fixed_orientation is not None:
                    if abs(placement.orientation_degrees - dept_spec.fixed_orientation) > tolerance:
                        errors.append(
                            f"Department '{dept_id}' violates fixed orientation (placed at {placement.orientation_degrees}°, expected {dept_spec.fixed_orientation}°)."
                        )

        # 3. Pairwise Overlap check
        placements_list = list(cont_layout.placements.items())
        total_overlap = 0.0
        for i in range(len(placements_list)):
            id_i, p_i = placements_list[i]
            box_i = p_i.bounding_box
            for j in range(i + 1, len(placements_list)):
                id_j, p_j = placements_list[j]
                box_j = p_j.bounding_box
                overlap = GeometryEngine.overlap_area(box_i, box_j, tolerance=tolerance)
                if overlap > tolerance:
                    total_overlap += overlap
                    errors.append(
                        f"Overlap detected between department '{id_i}' and '{id_j}' (overlap area: {overlap:.2f} m²)."
                    )

        # 4. Reserved zone violations
        all_reserved = list(cont_layout.reserved_zones)
        if hasattr(problem, "facility") and hasattr(problem.facility, "reserved_zones") and problem.facility.reserved_zones:
            all_reserved.extend(problem.facility.reserved_zones)
        if reserved_zones:
            all_reserved.extend(reserved_zones)

        for zone in all_reserved:
            for dept_id, p in cont_layout.placements.items():
                z_overlap = GeometryEngine.overlap_area(p.bounding_box, zone.bounding_box, tolerance=tolerance)
                if z_overlap > tolerance:
                    errors.append(
                        f"Department '{dept_id}' overlaps with reserved zone '{zone.id}' (type: {zone.type}, overlap: {z_overlap:.2f} m²)."
                    )

        metrics = GeometryEngine.calculate_layout_metrics(
            cont_layout,
            facility_width=fac_w,
            facility_height=fac_h,
        )
        signature = generate_layout_signature(cont_layout)

        return LayoutValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            total_overlap_area=round(total_overlap, 4),
            checked_departments=sorted(list(cont_layout.placements.keys())),
            metrics=metrics,
            signature=signature,
        )

    @classmethod
    def check_completeness_and_feasibility(
        cls,
        problem: FacilityLayoutProblem,
        layout: Union[ContinuousLayout, LayoutSolution, Dict[str, Any]],
        hard_violation_count: int = 0,
        tolerance: float = 1e-4,
    ) -> Tuple[bool, bool, List[str]]:
        """Centrally verify layout completeness and geometric feasibility.
        
        A solution is complete and feasible if:
            1. set(placed_department_ids) == set(problem_department_ids)
            2. LayoutValidator.validate().is_valid is True
            3. hard_violation_count == 0
            
        Returns:
            Tuple of (is_complete, is_fully_feasible, issues_list).
        """
        val_res = cls.validate(problem=problem, layout=layout, tolerance=tolerance)
        placed_ids = set(val_res.checked_departments)
        expected_ids = set(d.id for d in problem.departments)
        
        missing = sorted(list(expected_ids - placed_ids))
        is_complete = len(missing) == 0
        
        issues = list(val_res.errors)
        if hard_violation_count > 0:
            issues.append(f"{hard_violation_count} hard constraint violation(s) present.")
            
        is_fully_feasible = is_complete and val_res.is_valid and (hard_violation_count == 0)
        return is_complete, is_fully_feasible, issues

