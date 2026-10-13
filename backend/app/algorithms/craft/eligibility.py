"""Exchange eligibility rules and geometric compatibility checks for CRAFT pairwise swaps."""

from typing import Any, Dict, List, Optional, Set, Tuple
from app.models.problem import FacilityLayoutProblem
from app.models.department import Department
from app.models.constraint import ConstraintType
from app.models.representation import ContinuousLayout
from app.services.geometry_engine import GeometryEngine
from app.algorithms.craft.config import CRAFTConfig


def is_department_fixed(dept_id: str, problem: FacilityLayoutProblem) -> bool:
    """Check if department has a fixed location via Department model or Problem constraint."""
    dept = next((d for d in problem.departments if d.id == dept_id), None)
    if dept and dept.fixed_position is not None:
        return True

    # Check problem constraints
    for c in problem.constraints:
        if c.type == ConstraintType.FIXED_POSITION and dept_id in c.involved_departments:
            return True

    return False


def check_pair_eligibility(
    problem: FacilityLayoutProblem,
    layout: ContinuousLayout,
    dept_a_id: str,
    dept_b_id: str,
    config: CRAFTConfig,
) -> Tuple[bool, bool, Optional[str]]:
    """Determine whether two departments can be physically exchanged in rectangular continuous space.
    
    Returns:
        (is_eligible: bool, is_rotational: bool, reason: Optional[str])
    """
    if dept_a_id == dept_b_id:
        return False, False, "Cannot swap department with itself"

    p_a = layout.placements.get(dept_a_id)
    p_b = layout.placements.get(dept_b_id)
    if not p_a or not p_b:
        return False, False, "Department placement not found in layout"

    # 1. Fixed position protection
    if is_department_fixed(dept_a_id, problem):
        return False, False, f"Department '{dept_a_id}' is fixed and cannot be relocated"
    if is_department_fixed(dept_b_id, problem):
        return False, False, f"Department '{dept_b_id}' is fixed and cannot be relocated"

    dept_a_spec = next((d for d in problem.departments if d.id == dept_a_id), None)
    dept_b_spec = next((d for d in problem.departments if d.id == dept_b_id), None)
    tol = config.numerical_tolerance

    # 2. Case A: Equal Geometry (Direct Coordinate Swap)
    # Both width and height match within tolerance
    if abs(p_a.width - p_b.width) <= tol and abs(p_a.height - p_b.height) <= tol:
        return True, False, None

    # 3. Case B: 90-Degree Rotational Match (Transverse Match)
    # Dimensions match inversely: wA == hB and hA == wB
    if config.allow_rotational_swaps and abs(p_a.width - p_b.height) <= tol and abs(p_a.height - p_b.width) <= tol:
        # Check orientation lock
        if dept_a_spec and dept_a_spec.metadata.get("fixed_orientation") is True:
            return False, False, f"Department '{dept_a_id}' has fixed orientation lock"
        if dept_b_spec and dept_b_spec.metadata.get("fixed_orientation") is True:
            return False, False, f"Department '{dept_b_id}' has fixed orientation lock"

        # Check rotated dimension limits for Dept A (rotated dims: w=p_a.height, h=p_a.width)
        rot_w_a, rot_h_a = p_a.height, p_a.width
        if dept_a_spec:
            if dept_a_spec.min_width is not None and rot_w_a < dept_a_spec.min_width - tol:
                return False, False, f"Department '{dept_a_id}' rotated width violates min_width"
            if dept_a_spec.max_width is not None and rot_w_a > dept_a_spec.max_width + tol:
                return False, False, f"Department '{dept_a_id}' rotated width exceeds max_width"
            if dept_a_spec.min_height is not None and rot_h_a < dept_a_spec.min_height - tol:
                return False, False, f"Department '{dept_a_id}' rotated height violates min_height"
            if dept_a_spec.max_height is not None and rot_h_a > dept_a_spec.max_height + tol:
                return False, False, f"Department '{dept_a_id}' rotated height exceeds max_height"
            if dept_a_spec.max_aspect_ratio is not None:
                ar = max(rot_w_a, rot_h_a) / min(rot_w_a, rot_h_a)
                if ar > dept_a_spec.max_aspect_ratio + tol:
                    return False, False, f"Department '{dept_a_id}' rotated aspect ratio exceeds maximum"

        # Check rotated dimension limits for Dept B (rotated dims: w=p_b.height, h=p_b.width)
        rot_w_b, rot_h_b = p_b.height, p_b.width
        if dept_b_spec:
            if dept_b_spec.min_width is not None and rot_w_b < dept_b_spec.min_width - tol:
                return False, False, f"Department '{dept_b_id}' rotated width violates min_width"
            if dept_b_spec.max_width is not None and rot_w_b > dept_b_spec.max_width + tol:
                return False, False, f"Department '{dept_b_id}' rotated width exceeds max_width"
            if dept_b_spec.min_height is not None and rot_h_b < dept_b_spec.min_height - tol:
                return False, False, f"Department '{dept_b_id}' rotated height violates min_height"
            if dept_b_spec.max_height is not None and rot_h_b > dept_b_spec.max_height + tol:
                return False, False, f"Department '{dept_b_id}' rotated height exceeds max_height"
            if dept_b_spec.max_aspect_ratio is not None:
                ar = max(rot_w_b, rot_h_b) / min(rot_w_b, rot_h_b)
                if ar > dept_b_spec.max_aspect_ratio + tol:
                    return False, False, f"Department '{dept_b_id}' rotated aspect ratio exceeds maximum"

        return True, True, None

    # 4. Case C: Unequal Shapes
    return False, False, "Unequal dimensions without valid rotation (not supported in continuous rectangular v1)"


def find_eligible_pairs(
    problem: FacilityLayoutProblem,
    layout: ContinuousLayout,
    config: CRAFTConfig,
) -> List[Tuple[str, str, bool]]:
    """Enumerate all eligible department pairs in strictly deterministic order.
    
    Returns:
        List of (dept_a, dept_b, is_rotational) sorted lexicographically by (dept_a, dept_b).
    """
    dept_ids = sorted(list(layout.placements.keys()))
    eligible: List[Tuple[str, str, bool]] = []

    for i in range(len(dept_ids)):
        for j in range(i + 1, len(dept_ids)):
            d_a = dept_ids[i]
            d_b = dept_ids[j]
            is_ok, is_rot, _ = check_pair_eligibility(problem, layout, d_a, d_b, config)
            if is_ok:
                eligible.append((d_a, d_b, is_rot))

    return eligible


def detect_unequal_adjacent_pairs(
    problem: FacilityLayoutProblem,
    layout: ContinuousLayout,
    tolerance: float = 1e-4,
) -> List[Dict[str, Any]]:
    """Detect adjacent/touching departments that have unequal dimensions.
    
    These pairs would be candidates for classical grid/reshape CRAFT, but are ineligible
    in continuous rectangular representation v1 without dynamic reshaping.
    """
    dept_ids = sorted(list(layout.placements.keys()))
    unequal_adjacent: List[Dict[str, Any]] = []

    for i in range(len(dept_ids)):
        for j in range(i + 1, len(dept_ids)):
            d_a = dept_ids[i]
            d_b = dept_ids[j]
            p_a = layout.placements[d_a]
            p_b = layout.placements[d_b]

            # Check adjacency
            if GeometryEngine.is_adjacent(p_a.bounding_box, p_b.bounding_box, tolerance=tolerance):
                # Check if dimensions are unequal (both direct and rotational)
                is_equal = abs(p_a.width - p_b.width) <= tolerance and abs(p_a.height - p_b.height) <= tolerance
                is_rot = abs(p_a.width - p_b.height) <= tolerance and abs(p_a.height - p_b.width) <= tolerance
                if not is_equal and not is_rot:
                    unequal_adjacent.append({
                        "department_a": d_a,
                        "department_b": d_b,
                        "dims_a": {"width": p_a.width, "height": p_a.height, "area": p_a.area},
                        "dims_b": {"width": p_b.width, "height": p_b.height, "area": p_b.area},
                        "shared_boundary": GeometryEngine.shared_boundary_length(
                            p_a.bounding_box, p_b.bounding_box, tolerance=tolerance
                        ),
                        "reason": "Adjacent departments have unequal shapes; requires reshaping not supported in v1",
                    })

    return unequal_adjacent
