"""Layout swapper and geometric candidate validator for CRAFT."""

from typing import Optional, Tuple
from app.models.problem import FacilityLayoutProblem
from app.models.geometry import BoundingBox
from app.models.constraint import ConstraintClassification
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.services.geometry_engine import GeometryEngine
from app.constraints.engine import ConstraintEngine
from app.algorithms.craft.config import CRAFTConfig


def create_swapped_layout(
    layout: ContinuousLayout,
    dept_a_id: str,
    dept_b_id: str,
    is_rotational: bool = False,
) -> ContinuousLayout:
    """Produce a new ContinuousLayout by swapping the positions (and optionally rotating) of two departments."""
    p_a = layout.placements[dept_a_id]
    p_b = layout.placements[dept_b_id]

    new_placements = {k: v.model_copy() for k, v in layout.placements.items()}

    if not is_rotational:
        # Direct coordinate swap: A takes B's origin, B takes A's origin
        new_placements[dept_a_id] = ContinuousPlacement(
            department_id=dept_a_id,
            x=p_b.x,
            y=p_b.y,
            width=p_a.width,
            height=p_a.height,
            orientation_degrees=p_a.orientation_degrees,
            metadata=p_a.metadata.copy(),
        )
        new_placements[dept_b_id] = ContinuousPlacement(
            department_id=dept_b_id,
            x=p_a.x,
            y=p_a.y,
            width=p_b.width,
            height=p_b.height,
            orientation_degrees=p_b.orientation_degrees,
            metadata=p_b.metadata.copy(),
        )
    else:
        # Rotational swap: A takes B's origin with transposed dimensions, B takes A's origin with transposed dimensions
        new_placements[dept_a_id] = ContinuousPlacement(
            department_id=dept_a_id,
            x=p_b.x,
            y=p_b.y,
            width=p_a.height,
            height=p_a.width,
            orientation_degrees=(p_a.orientation_degrees + 90.0) % 360.0,
            metadata=p_a.metadata.copy(),
        )
        new_placements[dept_b_id] = ContinuousPlacement(
            department_id=dept_b_id,
            x=p_a.x,
            y=p_a.y,
            width=p_b.height,
            height=p_b.width,
            orientation_degrees=(p_b.orientation_degrees + 90.0) % 360.0,
            metadata=p_b.metadata.copy(),
        )

    return ContinuousLayout(
        id=layout.id,
        name=layout.name,
        problem_id=layout.problem_id,
        facility_width=layout.facility_width,
        facility_height=layout.facility_height,
        reserved_zones=layout.reserved_zones.copy() if layout.reserved_zones else [],
        placements=new_placements,
        metadata=layout.metadata.copy(),
    )


def validate_candidate_swap(
    problem: FacilityLayoutProblem,
    candidate_layout: ContinuousLayout,
    config: CRAFTConfig,
) -> Tuple[bool, Optional[str]]:
    """Strictly validate that candidate swapped layout violates zero physical or hard constraints.
    
    Returns:
        (is_feasible: bool, rejection_reason: Optional[str])
    """
    tol = config.numerical_tolerance
    fac_w = problem.facility.width
    fac_h = problem.facility.height
    fac_box = BoundingBox(x_min=0.0, y_min=0.0, x_max=fac_w, y_max=fac_h)

    placements = list(candidate_layout.placements.values())

    # 1. Boundary containment
    for p in placements:
        if not fac_box.contains_box(p.bounding_box, tolerance=tol):
            return False, f"Department '{p.department_id}' exceeds facility perimeter [{fac_w}x{fac_h}]"

    # 2. Pairwise overlaps
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            p1 = placements[i]
            p2 = placements[j]
            overlap = GeometryEngine.overlap_area(p1.bounding_box, p2.bounding_box, tolerance=tol)
            if overlap > tol:
                return False, f"Overlap detected between '{p1.department_id}' and '{p2.department_id}' ({overlap:.2f} m²)"

    # 3. Reserved zones
    reserved_zones = problem.facility.reserved_zones if hasattr(problem.facility, "reserved_zones") else []
    if reserved_zones:
        for p in placements:
            for rz in reserved_zones:
                if hasattr(rz, "bounding_box") and isinstance(rz.bounding_box, BoundingBox):
                    rz_box = rz.bounding_box
                elif hasattr(rz, "x"):
                    rz_box = BoundingBox(x_min=rz.x, y_min=rz.y, x_max=rz.x + rz.width, y_max=rz.y + rz.height)
                else:
                    continue
                overlap = GeometryEngine.overlap_area(p.bounding_box, rz_box, tolerance=tol)
                if overlap > tol:
                    return False, f"Department '{p.department_id}' infringes reserved zone '{rz.id}'"

    # 4. Problem-level hard constraints via ConstraintEngine
    constraint_engine = ConstraintEngine()
    violations = constraint_engine.check_all(problem, candidate_layout)
    hard_violations = [v for v in violations if v.classification == ConstraintClassification.HARD]
    if hard_violations:
        first_v = hard_violations[0]
        return False, f"Hard constraint '{first_v.constraint_id}' violated: {first_v.message}"

    return True, None
