"""Constraint verification engine orchestrating layout rule checks and penalties."""

from typing import Dict, List, Optional, Set, Tuple, Union
import math
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.models.representation import ContinuousLayout
from app.models.geometry import BoundingBox
from app.models.constraint import (
    Constraint,
    ConstraintViolation,
    ConstraintType,
    ConstraintClassification,
)
from app.constraints.base import BaseConstraintChecker
from app.constraints.checkers import (
    NonOverlappingChecker,
    BoundaryChecker,
    FixedPositionChecker,
    MinDistanceChecker,
    MaxDistanceChecker,
    AdjacencyChecker,
    SeparationChecker,
    AspectRatioChecker,
    _extract_continuous_layout,
)
from app.services.geometry_engine import GeometryEngine


class ConstraintEngine:
    """Orchestrates constraint checks across all constraints defined in a problem and intrinsic geometric rules."""

    def __init__(self, checkers: Optional[List[BaseConstraintChecker]] = None):
        self._checkers: Dict[ConstraintType, BaseConstraintChecker] = {}
        if checkers is not None:
            for checker in checkers:
                self.register_checker(checker)
        else:
            # Register all standard concrete checkers by default
            self.register_checker(NonOverlappingChecker())
            self.register_checker(BoundaryChecker())
            self.register_checker(FixedPositionChecker())
            self.register_checker(MinDistanceChecker())
            self.register_checker(MaxDistanceChecker())
            self.register_checker(AdjacencyChecker())
            self.register_checker(SeparationChecker())
            self.register_checker(AspectRatioChecker())

    def register_checker(self, checker: BaseConstraintChecker) -> None:
        self._checkers[checker.supported_type] = checker

    def check_all(
        self,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> List[ConstraintViolation]:
        """Evaluate all constraints defined on the problem and intrinsic department/geometric specifications."""
        violations: List[ConstraintViolation] = []
        for constraint in problem.constraints:
            checker = self._checkers.get(constraint.type)
            if checker:
                v = checker.check(constraint, problem, solution)
                violations.extend(v)

        # Also enforce department-level & intrinsic geometric hard constraints (deduplicated)
        layout = _extract_continuous_layout(problem, solution)
        tolerance = 1e-4
        aspect_tol = 1e-6

        reported_boundary_depts: Set[str] = {
            v.involved_departments[0]
            for v in violations
            if v.constraint_type == ConstraintType.BOUNDARY and len(v.involved_departments) == 1
        }
        reported_overlap_pairs: Set[Tuple[str, str]] = {
            tuple(sorted(v.involved_departments[:2]))  # type: ignore
            for v in violations
            if v.constraint_type == ConstraintType.NON_OVERLAPPING and len(v.involved_departments) >= 2
        }
        reported_fixed_depts: Set[str] = {
            v.involved_departments[0]
            for v in violations
            if v.constraint_type == ConstraintType.FIXED_POSITION and len(v.involved_departments) == 1
        }
        reported_aspect_depts: Set[str] = {
            v.involved_departments[0]
            for v in violations
            if v.constraint_type == ConstraintType.ASPECT_RATIO and len(v.involved_departments) == 1
        }

        fac_w = problem.facility.width
        fac_h = problem.facility.height
        facility_box = BoundingBox(x_min=0.0, y_min=0.0, x_max=fac_w, y_max=fac_h)
        problem_depts = {d.id: d for d in problem.departments}

        for dept_id, placement in layout.placements.items():
            p_box = placement.bounding_box

            # 1. Intrinsic Facility Boundary Containment
            if dept_id not in reported_boundary_depts and not facility_box.contains_box(p_box, tolerance=tolerance):
                dx = max(0.0, -p_box.x_min) + max(0.0, p_box.x_max - fac_w)
                dy = max(0.0, -p_box.y_min) + max(0.0, p_box.y_max - fac_h)
                mag = round(dx + dy, 4)
                violations.append(
                    ConstraintViolation(
                        constraint_id=f"CST_HARD_BOUNDARY_{dept_id}",
                        constraint_type=ConstraintType.BOUNDARY,
                        classification=ConstraintClassification.HARD,
                        involved_departments=[dept_id],
                        magnitude=mag,
                        penalty_cost=0.0,
                        measured_value=mag,
                        required_value=0.0,
                        description=f"Department '{dept_id}' exceeds facility boundaries (placed [{placement.left:.1f}..{placement.right:.1f}, {placement.bottom:.1f}..{placement.top:.1f}] vs facility [{fac_w}x{fac_h}]).",
                    )
                )

            dept_spec = problem_depts.get(dept_id)
            if not dept_spec:
                continue

            # 2. Department Aspect Ratio Constraints (min_aspect_ratio / max_aspect_ratio)
            if dept_id not in reported_aspect_depts:
                if dept_spec.min_aspect_ratio is not None and placement.aspect_ratio < dept_spec.min_aspect_ratio - aspect_tol:
                    deficit = round(dept_spec.min_aspect_ratio - placement.aspect_ratio, 4)
                    violations.append(
                        ConstraintViolation(
                            constraint_id=f"CST_HARD_MIN_ASPECT_RATIO_{dept_id}",
                            constraint_type=ConstraintType.ASPECT_RATIO,
                            classification=ConstraintClassification.HARD,
                            involved_departments=[dept_id],
                            magnitude=deficit,
                            penalty_cost=0.0,
                            measured_value=round(placement.aspect_ratio, 4),
                            required_value=dept_spec.min_aspect_ratio,
                            description=f"Department '{dept_id}' aspect ratio ({placement.aspect_ratio:.2f}) violates min_aspect_ratio ({dept_spec.min_aspect_ratio:.2f}).",
                        )
                    )
                if dept_spec.max_aspect_ratio is not None and placement.aspect_ratio > dept_spec.max_aspect_ratio + aspect_tol:
                    excess = round(placement.aspect_ratio - dept_spec.max_aspect_ratio, 4)
                    violations.append(
                        ConstraintViolation(
                            constraint_id=f"CST_HARD_MAX_ASPECT_RATIO_{dept_id}",
                            constraint_type=ConstraintType.ASPECT_RATIO,
                            classification=ConstraintClassification.HARD,
                            involved_departments=[dept_id],
                            magnitude=excess,
                            penalty_cost=0.0,
                            measured_value=round(placement.aspect_ratio, 4),
                            required_value=dept_spec.max_aspect_ratio,
                            description=f"Department '{dept_id}' aspect ratio ({placement.aspect_ratio:.2f}) exceeds max_aspect_ratio ({dept_spec.max_aspect_ratio:.2f}).",
                        )
                    )

            # 3. Department Dimensional Limits (min/max width & height)
            if dept_spec.min_width is not None and placement.width < dept_spec.min_width - tolerance:
                deficit = round(dept_spec.min_width - placement.width, 4)
                violations.append(
                    ConstraintViolation(
                        constraint_id=f"CST_HARD_MIN_WIDTH_{dept_id}",
                        constraint_type=ConstraintType.CUSTOM,
                        classification=ConstraintClassification.HARD,
                        involved_departments=[dept_id],
                        magnitude=deficit,
                        penalty_cost=0.0,
                        measured_value=round(placement.width, 4),
                        required_value=dept_spec.min_width,
                        description=f"Department '{dept_id}' width ({placement.width:.1f}m) violates minimum width ({dept_spec.min_width:.1f}m).",
                    )
                )
            if dept_spec.max_width is not None and placement.width > dept_spec.max_width + tolerance:
                excess = round(placement.width - dept_spec.max_width, 4)
                violations.append(
                    ConstraintViolation(
                        constraint_id=f"CST_HARD_MAX_WIDTH_{dept_id}",
                        constraint_type=ConstraintType.CUSTOM,
                        classification=ConstraintClassification.HARD,
                        involved_departments=[dept_id],
                        magnitude=excess,
                        penalty_cost=0.0,
                        measured_value=round(placement.width, 4),
                        required_value=dept_spec.max_width,
                        description=f"Department '{dept_id}' width ({placement.width:.1f}m) exceeds maximum width ({dept_spec.max_width:.1f}m).",
                    )
                )
            if dept_spec.min_height is not None and placement.height < dept_spec.min_height - tolerance:
                deficit = round(dept_spec.min_height - placement.height, 4)
                violations.append(
                    ConstraintViolation(
                        constraint_id=f"CST_HARD_MIN_HEIGHT_{dept_id}",
                        constraint_type=ConstraintType.CUSTOM,
                        classification=ConstraintClassification.HARD,
                        involved_departments=[dept_id],
                        magnitude=deficit,
                        penalty_cost=0.0,
                        measured_value=round(placement.height, 4),
                        required_value=dept_spec.min_height,
                        description=f"Department '{dept_id}' height ({placement.height:.1f}m) violates minimum height ({dept_spec.min_height:.1f}m).",
                    )
                )
            if dept_spec.max_height is not None and placement.height > dept_spec.max_height + tolerance:
                excess = round(placement.height - dept_spec.max_height, 4)
                violations.append(
                    ConstraintViolation(
                        constraint_id=f"CST_HARD_MAX_HEIGHT_{dept_id}",
                        constraint_type=ConstraintType.CUSTOM,
                        classification=ConstraintClassification.HARD,
                        involved_departments=[dept_id],
                        magnitude=excess,
                        penalty_cost=0.0,
                        measured_value=round(placement.height, 4),
                        required_value=dept_spec.max_height,
                        description=f"Department '{dept_id}' height ({placement.height:.1f}m) exceeds maximum height ({dept_spec.max_height:.1f}m).",
                    )
                )

            # 4. Department Fixed Position & Orientation
            if dept_id not in reported_fixed_depts and dept_spec.fixed_position is not None:
                expected_pt = dept_spec.fixed_position
                dist_origin = math.hypot(placement.x - expected_pt.x, placement.y - expected_pt.y)
                dist_centroid = math.hypot(placement.centroid.x - expected_pt.x, placement.centroid.y - expected_pt.y)
                min_dist = min(dist_origin, dist_centroid)
                if min_dist > tolerance:
                    mag = round(min_dist, 4)
                    violations.append(
                        ConstraintViolation(
                            constraint_id=f"CST_HARD_FIXED_POS_{dept_id}",
                            constraint_type=ConstraintType.FIXED_POSITION,
                            classification=ConstraintClassification.HARD,
                            involved_departments=[dept_id],
                            magnitude=mag,
                            penalty_cost=0.0,
                            measured_value=mag,
                            required_value=0.0,
                            description=f"Department '{dept_id}' violates fixed position constraint (placed at ({placement.x}, {placement.y}), expected ({expected_pt.x}, {expected_pt.y})).",
                        )
                    )
            if dept_spec.fixed_orientation is not None:
                if abs(placement.orientation_degrees - dept_spec.fixed_orientation) > tolerance:
                    mag = round(abs(placement.orientation_degrees - dept_spec.fixed_orientation), 4)
                    violations.append(
                        ConstraintViolation(
                            constraint_id=f"CST_HARD_FIXED_ORIENT_{dept_id}",
                            constraint_type=ConstraintType.FIXED_POSITION,
                            classification=ConstraintClassification.HARD,
                            involved_departments=[dept_id],
                            magnitude=mag,
                            penalty_cost=0.0,
                            measured_value=placement.orientation_degrees,
                            required_value=dept_spec.fixed_orientation,
                            description=f"Department '{dept_id}' violates fixed orientation (placed at {placement.orientation_degrees}°, expected {dept_spec.fixed_orientation}°).",
                        )
                    )

        # 5. Intrinsic Pairwise Non-Overlapping
        placements_list = list(layout.placements.items())
        for i in range(len(placements_list)):
            id_a, p_a = placements_list[i]
            box_a = p_a.bounding_box
            for j in range(i + 1, len(placements_list)):
                id_b, p_b = placements_list[j]
                pair_key = (min(id_a, id_b), max(id_a, id_b))
                if pair_key in reported_overlap_pairs:
                    continue
                overlap = GeometryEngine.overlap_area(box_a, p_b.bounding_box, tolerance=tolerance)
                if overlap > tolerance:
                    violations.append(
                        ConstraintViolation(
                            constraint_id=f"CST_HARD_NON_OVERLAP_{id_a}_{id_b}",
                            constraint_type=ConstraintType.NON_OVERLAPPING,
                            classification=ConstraintClassification.HARD,
                            involved_departments=[id_a, id_b],
                            magnitude=round(overlap, 4),
                            penalty_cost=0.0,
                            measured_value=round(overlap, 4),
                            required_value=0.0,
                            description=f"Physical overlap of {overlap:.2f} m² detected between '{id_a}' and '{id_b}'.",
                        )
                    )

        # 6. Intrinsic Reserved Zone Clearance
        all_reserved = list(layout.reserved_zones)
        if hasattr(problem, "facility") and hasattr(problem.facility, "reserved_zones") and problem.facility.reserved_zones:
            seen_z_ids = {z.id for z in all_reserved}
            for z in problem.facility.reserved_zones:
                if z.id not in seen_z_ids:
                    all_reserved.append(z)
                    seen_z_ids.add(z.id)

        for zone in all_reserved:
            for dept_id, p in layout.placements.items():
                z_overlap = GeometryEngine.overlap_area(p.bounding_box, zone.bounding_box, tolerance=tolerance)
                if z_overlap > tolerance:
                    violations.append(
                        ConstraintViolation(
                            constraint_id=f"CST_HARD_RESERVED_ZONE_{zone.id}_{dept_id}",
                            constraint_type=ConstraintType.FORBIDDEN_ZONE,
                            classification=ConstraintClassification.HARD,
                            involved_departments=[dept_id],
                            magnitude=round(z_overlap, 4),
                            penalty_cost=0.0,
                            measured_value=round(z_overlap, 4),
                            required_value=0.0,
                            description=f"Department '{dept_id}' overlaps with reserved zone '{zone.id}' (type: {zone.type}, overlap: {z_overlap:.2f} m²).",
                        )
                    )

        return violations

    @staticmethod
    def calculate_total_penalty(violations: List[ConstraintViolation]) -> float:
        """Sum total penalty assessed across all soft violations."""
        return round(sum(v.penalty_cost for v in violations if v.classification == ConstraintClassification.SOFT), 2)

    @staticmethod
    def count_hard_violations(violations: List[ConstraintViolation]) -> int:
        """Count violations of hard constraints."""
        return sum(1 for v in violations if v.classification == ConstraintClassification.HARD)

    @staticmethod
    def count_soft_violations(violations: List[ConstraintViolation]) -> int:
        """Count violations of soft constraints."""
        return sum(1 for v in violations if v.classification == ConstraintClassification.SOFT)

    @classmethod
    def is_feasible(cls, violations: List[ConstraintViolation]) -> bool:
        """Return True if layout has zero hard constraint violations."""
        return cls.count_hard_violations(violations) == 0

