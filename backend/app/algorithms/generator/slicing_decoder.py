"""Area-preserving Slicing Tree decoder and geometric evaluator."""

from typing import Dict, List, Optional, Set, Tuple

from app.feasibility.models import FreeRectangle
from app.feasibility.representations import SlicingCutType, SlicingNode, SlicingTree
from app.models.department import Department
from app.models.geometry import BoundingBox, Point2D
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement


class AreaPreservingSlicingDecoder:
    """Decodes Slicing Trees into ContinuousLayout with mathematical area preservation.
    
    Ensures:
        1. Subtree areas are calculated bottom-up.
        2. Cut ratios are computed algebraically to allocate exact required areas.
        3. Leaf placements are strictly checked against area, min/max dimensions, and aspect ratio.
        4. Infeasible trees are rejected without fudging.
    """

    @classmethod
    def calculate_subtree_areas(
        cls,
        node: SlicingNode,
        dept_map: Dict[str, Department],
    ) -> float:
        """Compute total required area of all leaf departments in subtree."""
        if node.is_leaf and node.department_id:
            dept = dept_map.get(node.department_id)
            return dept.required_area if dept else 0.0

        area_left = cls.calculate_subtree_areas(node.left, dept_map) if node.left else 0.0
        area_right = cls.calculate_subtree_areas(node.right, dept_map) if node.right else 0.0
        return area_left + area_right

    @classmethod
    def decode(
        cls,
        tree: SlicingTree,
        problem: FacilityLayoutProblem,
        enforce_area_proportional_cuts: bool = True,
        slack_allocation: str = "bottom_right",
        tolerance: float = 1e-4,
    ) -> Tuple[ContinuousLayout, bool, List[str]]:
        """Decode slicing tree into a ContinuousLayout and evaluate rectangular feasibility.
        
        Args:
            tree: Binary SlicingTree to decode.
            problem: FacilityLayoutProblem with departments and facility boundary.
            enforce_area_proportional_cuts: If True, derives cut ratios algebraically from subtree areas.
            slack_allocation: How unused plant area is handled.
            tolerance: Geometric floating point tolerance.
            
        Returns:
            Tuple of (ContinuousLayout, is_feasible, violation_reasons).
        """
        dept_map = {d.id: d for d in problem.departments}
        fac_w = problem.facility.width
        fac_h = problem.facility.height
        fac_area = problem.facility.area or (fac_w * fac_h)
        total_req_area = problem.total_required_area

        violations: List[str] = []
        placements: Dict[str, ContinuousPlacement] = {}

        # 1. Check completeness of leaves in tree
        leaves_in_tree: Set[str] = set()

        def collect_leaves(n: Optional[SlicingNode]) -> None:
            if not n:
                return
            if n.is_leaf and n.department_id:
                leaves_in_tree.add(n.department_id)
            else:
                collect_leaves(n.left)
                collect_leaves(n.right)

        collect_leaves(tree.root)
        required_depts = {d.id for d in problem.departments}
        missing_depts = required_depts - leaves_in_tree
        if missing_depts:
            violations.append(f"Slicing tree missing required departments: {sorted(list(missing_depts))}.")

        # 2. Determine base bounding box for slicing
        # If total required area equals facility area, slice over full plant.
        # If total required area < facility area, slice over the packing envelope.
        box_w = fac_w
        box_h = fac_h
        if total_req_area < fac_area - 1.0:
            # Active packing zone scaled to exact required area
            # Scale height proportionally: H_pack = total_req_area / W_plant
            if total_req_area <= fac_w * fac_h:
                box_h = round(total_req_area / fac_w, 4)
                if box_h > fac_h:
                    box_h = fac_h
                    box_w = round(total_req_area / fac_h, 4)

        # 3. Recursive area-preserving slicing
        def slice_recursive(
            n: SlicingNode,
            rx: float,
            ry: float,
            rw: float,
            rh: float,
        ) -> None:
            if n.is_leaf and n.department_id:
                dept_id = n.department_id
                dept = dept_map.get(dept_id)
                placements[dept_id] = ContinuousPlacement(
                    department_id=dept_id,
                    x=round(rx, 2),
                    y=round(ry, 2),
                    width=round(rw, 2),
                    height=round(rh, 2),
                )
                return

            # Compute cut ratio
            if enforce_area_proportional_cuts and n.left and n.right:
                area_l = cls.calculate_subtree_areas(n.left, dept_map)
                area_r = cls.calculate_subtree_areas(n.right, dept_map)
                tot = area_l + area_r
                ratio = (area_l / tot) if tot > 0 else 0.5
            else:
                ratio = n.cut_ratio

            # Clamp ratio safely
            ratio = max(0.01, min(0.99, ratio))

            if n.cut_type == SlicingCutType.VERTICAL:
                w1 = rw * ratio
                w2 = rw - w1
                if n.left:
                    slice_recursive(n.left, rx, ry, w1, rh)
                if n.right:
                    slice_recursive(n.right, rx + w1, ry, w2, rh)
            elif n.cut_type == SlicingCutType.HORIZONTAL:
                h1 = rh * ratio
                h2 = rh - h1
                if n.left:
                    slice_recursive(n.left, rx, ry, rw, h1)
                if n.right:
                    slice_recursive(n.right, rx, ry + h1, rw, h2)

        slice_recursive(tree.root, 0.0, 0.0, box_w, box_h)

        layout = ContinuousLayout(
            problem_id=problem.id,
            facility_width=fac_w,
            facility_height=fac_h,
            placements=placements,
            reserved_zones=problem.reserved_zones,
        )

        # 4. Strict Validation of Every Department Placement
        for dept_id, placement in placements.items():
            dept = dept_map.get(dept_id)
            if not dept:
                continue

            # A. Area Conservation
            alloc_area = placement.area
            req_area = dept.required_area
            if abs(alloc_area - req_area) > (req_area * 0.02 + 0.1):
                err_pct = abs(alloc_area - req_area) / req_area * 100.0
                violations.append(
                    f"[{dept_id}] Area mismatch: allocated {alloc_area:.1f} m² vs required {req_area:.1f} m² ({err_pct:.1f}% error)."
                )

            # B. Dimensional Bounds
            if dept.min_width is not None and placement.width < dept.min_width - tolerance:
                violations.append(f"[{dept_id}] Width ({placement.width:.1f}m) < min_width ({dept.min_width:.1f}m).")
            if dept.max_width is not None and placement.width > dept.max_width + tolerance:
                violations.append(f"[{dept_id}] Width ({placement.width:.1f}m) > max_width ({dept.max_width:.1f}m).")
            if dept.min_height is not None and placement.height < dept.min_height - tolerance:
                violations.append(f"[{dept_id}] Height ({placement.height:.1f}m) < min_height ({dept.min_height:.1f}m).")
            if dept.max_height is not None and placement.height > dept.max_height + tolerance:
                violations.append(f"[{dept_id}] Height ({placement.height:.1f}m) > max_height ({dept.max_height:.1f}m).")

            # C. Aspect Ratio
            ar = placement.aspect_ratio
            if dept.max_aspect_ratio is not None and ar > dept.max_aspect_ratio + tolerance:
                violations.append(f"[{dept_id}] Aspect ratio ({ar:.2f}) > max_aspect_ratio ({dept.max_aspect_ratio:.2f}).")
            if dept.min_aspect_ratio is not None and ar < dept.min_aspect_ratio - tolerance:
                violations.append(f"[{dept_id}] Aspect ratio ({ar:.2f}) < min_aspect_ratio ({dept.min_aspect_ratio:.2f}).")

            # D. Facility Boundaries
            pbox = placement.bounding_box
            if pbox.x_max > fac_w + tolerance or pbox.y_max > fac_h + tolerance:
                violations.append(f"[{dept_id}] Placement exceeds facility boundary [{fac_w}x{fac_h}].")

            # E. Fixed Position
            if dept.fixed_position is not None:
                fx = dept.fixed_position.x
                fy = dept.fixed_position.y
                if abs(placement.x - fx) > tolerance or abs(placement.y - fy) > tolerance:
                    violations.append(f"[{dept_id}] Fixed position mismatch: ({placement.x}, {placement.y}) != ({fx}, {fy}).")

        # 5. Reserved Zone Intersections
        if problem.reserved_zones:
            for dept_id, placement in placements.items():
                pbox = placement.bounding_box
                for rz in problem.reserved_zones:
                    overlap = pbox.overlap_area(rz.bounding_box, tolerance=tolerance)
                    if overlap > tolerance:
                        violations.append(f"[{dept_id}] Overlaps reserved zone '{rz.id}' ({overlap:.1f} m²).")

        is_feasible = len(violations) == 0
        return layout, is_feasible, violations
