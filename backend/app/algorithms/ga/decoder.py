"""Flexible Bay Structure (FBS) Chromosome Decoder."""

from typing import Dict, List, Optional, Tuple

from app.algorithms.ga.models import BayChromosome
from app.constraints.engine import ConstraintEngine
from app.models.constraint import ConstraintClassification
from app.models.department import Department
from app.models.geometry import BoundingBox
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.services.geometry_engine import GeometryEngine


class BayChromosomeDecoder:
    """Decodes a Flexible Bay Structure chromosome into an analytical ContinuousLayout."""

    @classmethod
    def decode(
        cls,
        problem: FacilityLayoutProblem,
        chromosome: BayChromosome,
        tolerance: float = 1e-4,
    ) -> Tuple[ContinuousLayout, bool, List[str]]:
        """Decode chromosome to ContinuousLayout and assess strict feasibility.
        
        Guarantees by analytical construction:
        1. 100% exact department area conservation (width * height == required_area).
        2. Zero pairwise department overlap.
        3. 100% boundary containment as long as total department area <= facility area.
        
        Evaluates domain feasibility:
        - Dimension bounds (min/max width and height).
        - Maximum aspect ratio.
        - Fixed position coordinates.
        - Reserved / keep-out zones.
        - Hard domain constraints (via ConstraintEngine).
        
        Returns:
            Tuple of (layout, is_feasible, violations_list).
        """
        dept_ids = {d.id for d in problem.departments}
        dept_map: Dict[str, Department] = {d.id: d for d in problem.departments}
        fac_w = problem.facility.width
        fac_h = problem.facility.height

        # 1. Structural validity check
        order = chromosome.order
        bay_sizes = chromosome.bay_sizes
        if set(order) != dept_ids or len(order) != len(dept_ids):
            missing = dept_ids - set(order)
            extra = set(order) - dept_ids
            return (
                ContinuousLayout(
                    problem_id=problem.id,
                    facility_width=fac_w,
                    facility_height=fac_h,
                    placements={},
                ),
                False,
                [f"Invalid permutation: missing={missing}, extra={extra}"],
            )

        if sum(bay_sizes) != len(order) or any(b < 1 for b in bay_sizes):
            return (
                ContinuousLayout(
                    problem_id=problem.id,
                    facility_width=fac_w,
                    facility_height=fac_h,
                    placements={},
                ),
                False,
                [f"Invalid bay partitioning: sum({bay_sizes}) != {len(order)} or size < 1"],
            )

        # 2. Slice into bays
        bays: List[List[str]] = []
        idx = 0
        for b_size in bay_sizes:
            bays.append(order[idx : idx + b_size])
            idx += b_size

        placements: Dict[str, ContinuousPlacement] = {}
        violations: List[str] = []
        is_feasible = True

        orientation = chromosome.orientation.lower()

        # 3. Determine active layout envelope span
        tot_area = problem.total_required_area
        area_util = tot_area / (fac_w * fac_h) if (fac_w * fac_h) > 0 else 1.0
        sum_max_w = sum(d.max_width for d in problem.departments if d.max_width is not None)

        if area_util >= 0.40 and (sum_max_w == 0 or fac_w <= sum_max_w):
            active_w = fac_w
            active_h = fac_h
            offset_x = 0.0
            offset_y = 0.0
        else:
            # Low utilization or oversized facility boundary (e.g. academic benchmarks)
            aspect = fac_w / fac_h if fac_h > 0 else 1.0
            active_w = round((tot_area * aspect) ** 0.5, 2)
            active_h = round(tot_area / active_w, 2)
            offset_x = round((fac_w - active_w) / 2.0, 2)
            offset_y = round((fac_h - active_h) / 2.0, 2)

        # 4. Geometric placement
        if orientation == "vertical":
            # Bays stacked horizontally along X, spanning active height
            curr_x = offset_x
            for bay in bays:
                bay_area = sum(dept_map[did].required_area for did in bay)
                bay_w = bay_area / active_h

                curr_y = offset_y
                for did in bay:
                    dept = dept_map[did]
                    dept_h = dept.required_area / bay_w if bay_w > 0 else 0.0
                    placements[did] = ContinuousPlacement(
                        department_id=did,
                        x=round(curr_x, 4),
                        y=round(curr_y, 4),
                        width=round(bay_w, 4),
                        height=round(dept_h, 4),
                    )
                    curr_y += dept_h
                curr_x += bay_w
        else:
            # Horizontal (default): Bays stacked vertically along Y, spanning active width
            curr_y = offset_y
            for bay in bays:
                bay_area = sum(dept_map[did].required_area for did in bay)
                bay_h = bay_area / active_w

                curr_x = offset_x
                for did in bay:
                    dept = dept_map[did]
                    dept_w = dept.required_area / bay_h if bay_h > 0 else 0.0
                    placements[did] = ContinuousPlacement(
                        department_id=did,
                        x=round(curr_x, 4),
                        y=round(curr_y, 4),
                        width=round(dept_w, 4),
                        height=round(bay_h, 4),
                    )
                    curr_x += dept_w
                curr_y += bay_h

        layout = ContinuousLayout(
            problem_id=problem.id,
            facility_width=fac_w,
            facility_height=fac_h,
            placements=placements,
            reserved_zones=problem.reserved_zones,
        )

        # 4. Check domain feasibility
        for did, p in placements.items():
            dept = dept_map[did]

            # Facility boundary check
            if (
                p.x < -tolerance
                or p.y < -tolerance
                or p.x + p.width > fac_w + tolerance
                or p.y + p.height > fac_h + tolerance
            ):
                violations.append(f"Department '{did}' exceeds facility boundary ({fac_w}x{fac_h})")
                is_feasible = False

            # Dimension bounds
            if dept.min_width is not None and p.width < dept.min_width - tolerance:
                violations.append(f"Department '{did}' width {p.width:.2f} < min_width {dept.min_width}")
                is_feasible = False
            if dept.max_width is not None and p.width > dept.max_width + tolerance:
                violations.append(f"Department '{did}' width {p.width:.2f} > max_width {dept.max_width}")
                is_feasible = False
            if dept.min_height is not None and p.height < dept.min_height - tolerance:
                violations.append(f"Department '{did}' height {p.height:.2f} < min_height {dept.min_height}")
                is_feasible = False
            if dept.max_height is not None and p.height > dept.max_height + tolerance:
                violations.append(f"Department '{did}' height {p.height:.2f} > max_height {dept.max_height}")
                is_feasible = False

            # Aspect ratio check
            if p.width > 0 and p.height > 0:
                ar = max(p.width / p.height, p.height / p.width)
                if dept.min_aspect_ratio is not None and ar < dept.min_aspect_ratio - tolerance:
                    violations.append(
                        f"Department '{did}' aspect ratio {ar:.2f} < min_aspect_ratio {dept.min_aspect_ratio}"
                    )
                    is_feasible = False
                if dept.max_aspect_ratio is not None and ar > dept.max_aspect_ratio + tolerance:
                    violations.append(
                        f"Department '{did}' aspect ratio {ar:.2f} > max_aspect_ratio {dept.max_aspect_ratio}"
                    )
                    is_feasible = False

            # Fixed position check
            if dept.fixed_position is not None:
                fx = dept.fixed_position.x
                fy = dept.fixed_position.y
                # Allow tolerance of up to 1.0 meter for grid snapping if close
                if abs(p.x - fx) > 1.0 or abs(p.y - fy) > 1.0:
                    violations.append(
                        f"Department '{did}' fixed position mismatch: placed at ({p.x:.2f}, {p.y:.2f}), expected ({fx:.2f}, {fy:.2f})"
                    )
                    is_feasible = False

            # Reserved zones check
            reserved_zones = getattr(problem, "reserved_zones", None) or getattr(problem.facility, "reserved_zones", None) or []
            if reserved_zones:
                box_p = BoundingBox(x_min=p.x, y_min=p.y, x_max=p.x + p.width, y_max=p.y + p.height)
                for rz in reserved_zones:
                    box_rz = rz.bounding_box
                    overlap_area = GeometryEngine.overlap_area(box_p, box_rz)
                    if overlap_area > tolerance:
                        violations.append(f"Department '{did}' overlaps reserved zone '{rz.id}' (area: {overlap_area:.2f})")
                        is_feasible = False

        # 5. Check hard constraints via ConstraintEngine
        constraint_violations = ConstraintEngine().check_all(problem, layout)
        hard_violations = [cv for cv in constraint_violations if cv.classification == ConstraintClassification.HARD]
        for hv in hard_violations:
            violations.append(f"Hard constraint '{hv.constraint_id}' violated: {hv.message}")
            is_feasible = False

        return layout, is_feasible, violations
