"""Diagnostic analyzer identifying geometric failure modes in ALDEP and grid-to-continuous conversions."""

from typing import Dict, List, Optional, Tuple

from app.feasibility.models import (
    DepartmentDiagnosticDetail,
    DepartmentGeometryFailureType,
    LayoutGeometryDiagnosticReport,
)
from app.models.geometry import BoundingBox
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, GridLayout


class ALDEPGeometryDiagnostics:
    """Rigorous diagnostic analyzer for discrete grid and converted continuous layouts.
    
    Academic Protocol:
        Does not fudge or coerce non-rectangular shapes into artificial validity.
        Separately isolates and tallies discrete shape deformation, dimensional bounds,
        aspect ratio skew, bounding box overlaps, and conversion area distortion.
    """

    @classmethod
    def diagnose_layout(
        cls,
        problem: FacilityLayoutProblem,
        continuous_layout: ContinuousLayout,
        grid_layout: Optional[GridLayout] = None,
        tolerance: float = 1e-4,
    ) -> LayoutGeometryDiagnosticReport:
        """Analyze a layout and produce detailed failure categorization and counts."""
        dept_spec_map = {d.id: d for d in problem.departments}

        failure_counts: Dict[str, int] = {
            DepartmentGeometryFailureType.NON_RECTANGULAR_SHAPE.value: 0,
            DepartmentGeometryFailureType.MIN_WIDTH_VIOLATION.value: 0,
            DepartmentGeometryFailureType.MAX_WIDTH_VIOLATION.value: 0,
            DepartmentGeometryFailureType.MIN_HEIGHT_VIOLATION.value: 0,
            DepartmentGeometryFailureType.MAX_HEIGHT_VIOLATION.value: 0,
            DepartmentGeometryFailureType.ASPECT_RATIO_VIOLATION.value: 0,
            DepartmentGeometryFailureType.BOUNDING_BOX_OVERLAP.value: 0,
            DepartmentGeometryFailureType.OUT_OF_BOUNDS.value: 0,
            DepartmentGeometryFailureType.AREA_DISTORTION.value: 0,
        }

        department_details: Dict[str, DepartmentDiagnosticDetail] = {}
        non_rectangular_list: List[str] = []

        # 1. Inspect Department Grid Topology & Rectangularity
        grid_rectangularity: Dict[str, Tuple[bool, str, Optional[int], Optional[int]]] = {}
        if grid_layout and grid_layout.department_blocks:
            for dept_id, block in grid_layout.department_blocks.items():
                if not block.cells:
                    grid_rectangularity[dept_id] = (False, "empty_cells", 0, 0)
                    continue
                rows = [r for r, _ in block.cells]
                cols = [c for _, c in block.cells]
                d_row = max(rows) - min(rows) + 1
                d_col = max(cols) - min(cols) + 1
                expected_cell_count = d_row * d_col
                actual_cell_count = len(block.cells)

                if actual_cell_count == expected_cell_count:
                    grid_rectangularity[dept_id] = (True, "rectangular_grid_block", actual_cell_count, expected_cell_count)
                else:
                    grid_rectangularity[dept_id] = (
                        False,
                        f"serpentine_or_l_shaped (occupies {actual_cell_count} cells in {d_row}x{d_col} bounding grid)",
                        actual_cell_count,
                        expected_cell_count,
                    )
        else:
            # If grid layout is absent, infer from continuous placement metadata or defaults
            for dept_id in continuous_layout.placements.keys():
                grid_rectangularity[dept_id] = (True, "continuous_block", None, None)

        # 2. Analyze Each Placed Department
        for dept_id, placement in continuous_layout.placements.items():
            dept_spec = dept_spec_map.get(dept_id)
            failures: List[DepartmentGeometryFailureType] = []
            messages: List[str] = []

            is_rect, shape_desc, actual_cells, expected_cells = grid_rectangularity.get(
                dept_id, (True, "standard_rectangle", None, None)
            )
            if not is_rect:
                failures.append(DepartmentGeometryFailureType.NON_RECTANGULAR_SHAPE)
                messages.append(f"Department has non-rectangular geometry on grid: {shape_desc}.")
                failure_counts[DepartmentGeometryFailureType.NON_RECTANGULAR_SHAPE.value] += 1
                non_rectangular_list.append(dept_id)

            req_area = dept_spec.required_area if dept_spec else placement.area
            alloc_area = placement.area
            area_err_pct = abs(alloc_area - req_area) / req_area * 100.0 if req_area > 0 else 0.0

            # Area distortion check
            if area_err_pct > 2.0:
                failures.append(DepartmentGeometryFailureType.AREA_DISTORTION)
                messages.append(
                    f"Area distortion: bounding box area ({alloc_area:.1f}m²) differs from required area ({req_area:.1f}m²) by {area_err_pct:.1f}%."
                )
                failure_counts[DepartmentGeometryFailureType.AREA_DISTORTION.value] += 1

            # Dimensional bound checks
            if dept_spec:
                if dept_spec.min_width is not None and placement.width < dept_spec.min_width - tolerance:
                    failures.append(DepartmentGeometryFailureType.MIN_WIDTH_VIOLATION)
                    messages.append(
                        f"Width ({placement.width:.1f}m) violates min_width ({dept_spec.min_width:.1f}m)."
                    )
                    failure_counts[DepartmentGeometryFailureType.MIN_WIDTH_VIOLATION.value] += 1

                if dept_spec.max_width is not None and placement.width > dept_spec.max_width + tolerance:
                    failures.append(DepartmentGeometryFailureType.MAX_WIDTH_VIOLATION)
                    messages.append(
                        f"Width ({placement.width:.1f}m) exceeds max_width ({dept_spec.max_width:.1f}m)."
                    )
                    failure_counts[DepartmentGeometryFailureType.MAX_WIDTH_VIOLATION.value] += 1

                if dept_spec.min_height is not None and placement.height < dept_spec.min_height - tolerance:
                    failures.append(DepartmentGeometryFailureType.MIN_HEIGHT_VIOLATION)
                    messages.append(
                        f"Height ({placement.height:.1f}m) violates min_height ({dept_spec.min_height:.1f}m)."
                    )
                    failure_counts[DepartmentGeometryFailureType.MIN_HEIGHT_VIOLATION.value] += 1

                if dept_spec.max_height is not None and placement.height > dept_spec.max_height + tolerance:
                    failures.append(DepartmentGeometryFailureType.MAX_HEIGHT_VIOLATION)
                    messages.append(
                        f"Height ({placement.height:.1f}m) exceeds max_height ({dept_spec.max_height:.1f}m)."
                    )
                    failure_counts[DepartmentGeometryFailureType.MAX_HEIGHT_VIOLATION.value] += 1

                # Aspect ratio check
                ar = placement.aspect_ratio
                if dept_spec.max_aspect_ratio is not None and ar > dept_spec.max_aspect_ratio + tolerance:
                    failures.append(DepartmentGeometryFailureType.ASPECT_RATIO_VIOLATION)
                    messages.append(
                        f"Aspect ratio ({ar:.2f}) exceeds max_aspect_ratio ({dept_spec.max_aspect_ratio:.2f})."
                    )
                    failure_counts[DepartmentGeometryFailureType.ASPECT_RATIO_VIOLATION.value] += 1

                if dept_spec.min_aspect_ratio is not None and ar < dept_spec.min_aspect_ratio - tolerance:
                    failures.append(DepartmentGeometryFailureType.ASPECT_RATIO_VIOLATION)
                    messages.append(
                        f"Aspect ratio ({ar:.2f}) violates min_aspect_ratio ({dept_spec.min_aspect_ratio:.2f})."
                    )
                    failure_counts[DepartmentGeometryFailureType.ASPECT_RATIO_VIOLATION.value] += 1

            # Boundary containment check
            p_box = placement.bounding_box
            if (
                p_box.x_min < -tolerance
                or p_box.y_min < -tolerance
                or p_box.x_max > problem.facility.width + tolerance
                or p_box.y_max > problem.facility.height + tolerance
            ):
                failures.append(DepartmentGeometryFailureType.OUT_OF_BOUNDS)
                messages.append("Placement exceeds facility boundaries.")
                failure_counts[DepartmentGeometryFailureType.OUT_OF_BOUNDS.value] += 1

            detail = DepartmentDiagnosticDetail(
                department_id=dept_id,
                is_rectangular=is_rect,
                shape_description=shape_desc,
                allocated_width=placement.width,
                allocated_height=placement.height,
                allocated_area=placement.area,
                required_area=req_area,
                area_error_percentage=round(area_err_pct, 2),
                aspect_ratio=round(placement.aspect_ratio, 3),
                bounding_box=placement.bounding_box,
                discrete_cell_count=actual_cells,
                bounding_box_cell_count=expected_cells,
                failures=failures,
                failure_messages=messages,
            )
            department_details[dept_id] = detail

        # 3. Pairwise Bounding Box Overlap Checks
        overlapping_pairs: List[Tuple[str, str, float]] = []
        placements_items = list(continuous_layout.placements.items())
        for i in range(len(placements_items)):
            id_a, p_a = placements_items[i]
            box_a = p_a.bounding_box
            for j in range(i + 1, len(placements_items)):
                id_b, p_b = placements_items[j]
                box_b = p_b.bounding_box
                overlap_m2 = box_a.overlap_area(box_b, tolerance=tolerance)
                if overlap_m2 > tolerance:
                    overlapping_pairs.append((id_a, id_b, round(overlap_m2, 2)))
                    failure_counts[DepartmentGeometryFailureType.BOUNDING_BOX_OVERLAP.value] += 1
                    # Also append to department failure logs
                    if id_a in department_details:
                        department_details[id_a].failures.append(DepartmentGeometryFailureType.BOUNDING_BOX_OVERLAP)
                        department_details[id_a].failure_messages.append(
                            f"Overlaps with '{id_b}' ({overlap_m2:.2f} m²)."
                        )
                    if id_b in department_details:
                        department_details[id_b].failures.append(DepartmentGeometryFailureType.BOUNDING_BOX_OVERLAP)
                        department_details[id_b].failure_messages.append(
                            f"Overlaps with '{id_a}' ({overlap_m2:.2f} m²)."
                        )

        total_violations = sum(failure_counts.values())
        is_feasible = total_violations == 0

        summary_msg = (
            "Layout is strictly rectangular and geometrically feasible."
            if is_feasible
            else f"Layout has {total_violations} geometric violations: "
            f"{failure_counts[DepartmentGeometryFailureType.NON_RECTANGULAR_SHAPE.value]} non-rectangular, "
            f"{failure_counts[DepartmentGeometryFailureType.BOUNDING_BOX_OVERLAP.value]} overlaps, "
            f"{failure_counts[DepartmentGeometryFailureType.MIN_WIDTH_VIOLATION.value]} min-width violations."
        )

        return LayoutGeometryDiagnosticReport(
            layout_id=continuous_layout.id,
            problem_id=problem.id,
            is_fully_feasible=is_feasible,
            failure_counts=failure_counts,
            total_violations_count=total_violations,
            non_rectangular_departments=sorted(non_rectangular_list),
            overlapping_department_pairs=overlapping_pairs,
            department_details=department_details,
            summary_message=summary_msg,
        )
