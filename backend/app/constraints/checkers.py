"""Concrete constraint checkers for spatial feasibility and operational penalties."""

import math
from typing import Any, Dict, List, Optional, Tuple, Union
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.models.representation import ContinuousLayout
from app.models.constraint import (
    Constraint,
    ConstraintViolation,
    ConstraintType,
    ConstraintClassification,
)
from app.models.geometry import BoundingBox, Point2D
from app.constraints.base import BaseConstraintChecker
from app.services.geometry_engine import GeometryEngine, DistanceMetricType


def _extract_continuous_layout(
    problem: FacilityLayoutProblem,
    solution: Union[LayoutSolution, ContinuousLayout],
) -> ContinuousLayout:
    """Normalize input into ContinuousLayout for geometric queries."""
    if isinstance(solution, ContinuousLayout):
        return solution
    return ContinuousLayout.from_layout_solution(
        solution,
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
    )


class NonOverlappingChecker(BaseConstraintChecker):
    """Enforces that departments do not occupy the same physical floor space."""

    @property
    def supported_type(self) -> ConstraintType:
        return ConstraintType.NON_OVERLAPPING

    def check(
        self,
        constraint: Constraint,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> List[ConstraintViolation]:
        layout = _extract_continuous_layout(problem, solution)
        tolerance = constraint.parameters.get("tolerance", 1e-4)
        violations: List[ConstraintViolation] = []

        placements_list = list(layout.placements.items())
        target_depts = set(constraint.involved_departments)

        for i in range(len(placements_list)):
            id_a, p_a = placements_list[i]
            box_a = p_a.bounding_box
            for j in range(i + 1, len(placements_list)):
                id_b, p_b = placements_list[j]
                # If specific departments are targeted, at least one must be in the set
                if target_depts and id_a not in target_depts and id_b not in target_depts:
                    continue

                box_b = p_b.bounding_box
                overlap = GeometryEngine.overlap_area(box_a, box_b, tolerance=tolerance)
                if overlap > tolerance:
                    penalty = (
                        0.0
                        if constraint.classification == ConstraintClassification.HARD
                        else round(overlap * constraint.penalty, 2)
                    )
                    violations.append(
                        ConstraintViolation(
                            constraint_id=constraint.id,
                            constraint_type=self.supported_type,
                            classification=constraint.classification,
                            involved_departments=[id_a, id_b],
                            magnitude=round(overlap, 4),
                            penalty_cost=penalty,
                            measured_value=round(overlap, 4),
                            required_value=0.0,
                            description=f"Physical overlap of {overlap:.2f} m² detected between '{id_a}' and '{id_b}'.",
                        )
                    )
        return violations


class BoundaryChecker(BaseConstraintChecker):
    """Enforces that all departments remain strictly inside facility perimeter."""

    @property
    def supported_type(self) -> ConstraintType:
        return ConstraintType.BOUNDARY

    def check(
        self,
        constraint: Constraint,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> List[ConstraintViolation]:
        layout = _extract_continuous_layout(problem, solution)
        tolerance = constraint.parameters.get("tolerance", 1e-4)
        fac_w = problem.facility.width
        fac_h = problem.facility.height
        facility_box = BoundingBox(x_min=0.0, y_min=0.0, x_max=fac_w, y_max=fac_h)
        target_depts = set(constraint.involved_departments)
        violations: List[ConstraintViolation] = []

        for dept_id, p in layout.placements.items():
            if target_depts and dept_id not in target_depts:
                continue

            box = p.bounding_box
            if not facility_box.contains_box(box, tolerance=tolerance):
                # Calculate extent of boundary protrusion
                dx = max(0.0, -box.x_min) + max(0.0, box.x_max - fac_w)
                dy = max(0.0, -box.y_min) + max(0.0, box.y_max - fac_h)
                magnitude = round(dx + dy, 4)
                penalty = (
                    0.0
                    if constraint.classification == ConstraintClassification.HARD
                    else round(magnitude * constraint.penalty, 2)
                )
                violations.append(
                    ConstraintViolation(
                        constraint_id=constraint.id,
                        constraint_type=self.supported_type,
                        classification=constraint.classification,
                        involved_departments=[dept_id],
                        magnitude=magnitude,
                        penalty_cost=penalty,
                        measured_value=magnitude,
                        required_value=0.0,
                        description=f"Department '{dept_id}' protrudes outside facility boundary by {magnitude:.2f}m.",
                    )
                )
        return violations


class FixedPositionChecker(BaseConstraintChecker):
    """Enforces fixed coordinate positioning for specific departments."""

    @property
    def supported_type(self) -> ConstraintType:
        return ConstraintType.FIXED_POSITION

    def check(
        self,
        constraint: Constraint,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> List[ConstraintViolation]:
        layout = _extract_continuous_layout(problem, solution)
        tolerance = constraint.parameters.get("tolerance", 1e-4)
        violations: List[ConstraintViolation] = []

        # Check departments defined in constraint or in problem departments
        depts_to_check = constraint.involved_departments or [d.id for d in problem.departments if d.fixed_position]

        for dept_id in depts_to_check:
            placement = layout.placements.get(dept_id)
            if not placement:
                continue

            # Target position from constraint params or problem definition
            target_pt: Optional[Point2D] = None
            if "position" in constraint.parameters:
                p_raw = constraint.parameters["position"]
                if isinstance(p_raw, (list, tuple)) and len(p_raw) >= 2:
                    target_pt = Point2D(x=float(p_raw[0]), y=float(p_raw[1]))
                elif isinstance(p_raw, dict):
                    target_pt = Point2D(x=float(p_raw["x"]), y=float(p_raw["y"]))
            elif "fixed_x" in constraint.parameters and "fixed_y" in constraint.parameters:
                target_pt = Point2D(x=float(constraint.parameters["fixed_x"]), y=float(constraint.parameters["fixed_y"]))
            else:
                dept_spec = next((d for d in problem.departments if d.id == dept_id), None)
                if dept_spec and dept_spec.fixed_position:
                    target_pt = dept_spec.fixed_position

            if target_pt:
                # Check origin or centroid match
                dist_origin = math.hypot(placement.x - target_pt.x, placement.y - target_pt.y)
                dist_centroid = math.hypot(placement.centroid.x - target_pt.x, placement.centroid.y - target_pt.y)
                min_dist = min(dist_origin, dist_centroid)
                if min_dist > tolerance:
                    magnitude = round(min_dist, 4)
                    penalty = (
                        0.0
                        if constraint.classification == ConstraintClassification.HARD
                        else round(magnitude * constraint.penalty, 2)
                    )
                    violations.append(
                        ConstraintViolation(
                            constraint_id=constraint.id,
                            constraint_type=self.supported_type,
                            classification=constraint.classification,
                            involved_departments=[dept_id],
                            magnitude=magnitude,
                            penalty_cost=penalty,
                            measured_value=magnitude,
                            required_value=0.0,
                            description=f"Department '{dept_id}' deviates by {magnitude:.2f}m from required fixed position ({target_pt.x}, {target_pt.y}).",
                        )
                    )
        return violations


class MinDistanceChecker(BaseConstraintChecker):
    """Enforces minimum clearance distance between departments (e.g. fire/chemical hazards)."""

    @property
    def supported_type(self) -> ConstraintType:
        return ConstraintType.MIN_DISTANCE

    def check(
        self,
        constraint: Constraint,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> List[ConstraintViolation]:
        layout = _extract_continuous_layout(problem, solution)
        tolerance = constraint.parameters.get("tolerance", 1e-4)
        req_distance = float(
            constraint.parameters.get(
                "distance",
                constraint.parameters.get(
                    "min_distance",
                    constraint.parameters.get("min_separation", 0.0),
                ),
            )
        )
        use_centroid = constraint.parameters.get("use_centroid", False)
        depts = constraint.involved_departments
        if len(depts) < 2:
            return []

        violations: List[ConstraintViolation] = []
        p_a = layout.placements.get(depts[0])
        p_b = layout.placements.get(depts[1])
        if not p_a or not p_b:
            return []

        if use_centroid:
            dist = GeometryEngine.centroid_euclidean_distance(p_a.centroid, p_b.centroid)
        else:
            dist = GeometryEngine.edge_to_edge_distance(p_a.bounding_box, p_b.bounding_box)

        if dist < req_distance - tolerance:
            deficit = round(req_distance - dist, 4)
            penalty = (
                0.0
                if constraint.classification == ConstraintClassification.HARD
                else round(deficit * constraint.penalty, 2)
            )
            violations.append(
                ConstraintViolation(
                    constraint_id=constraint.id,
                    constraint_type=self.supported_type,
                    classification=constraint.classification,
                    involved_departments=depts[:2],
                    magnitude=deficit,
                    penalty_cost=penalty,
                    measured_value=round(dist, 4),
                    required_value=req_distance,
                    description=f"Clearance between '{depts[0]}' and '{depts[1]}' is {dist:.2f}m, violating required minimum {req_distance:.2f}m (deficit: {deficit:.2f}m).",
                )
            )
        return violations


class MaxDistanceChecker(BaseConstraintChecker):
    """Enforces that critical interacting departments do not exceed a maximum distance."""

    @property
    def supported_type(self) -> ConstraintType:
        return ConstraintType.MAX_DISTANCE

    def check(
        self,
        constraint: Constraint,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> List[ConstraintViolation]:
        layout = _extract_continuous_layout(problem, solution)
        tolerance = constraint.parameters.get("tolerance", 1e-4)
        max_dist = float(constraint.parameters.get("distance", constraint.parameters.get("max_distance", 1e9)))
        use_centroid = constraint.parameters.get("use_centroid", False)
        depts = constraint.involved_departments
        if len(depts) < 2:
            return []

        violations: List[ConstraintViolation] = []
        p_a = layout.placements.get(depts[0])
        p_b = layout.placements.get(depts[1])
        if not p_a or not p_b:
            return []

        if use_centroid:
            dist = GeometryEngine.centroid_euclidean_distance(p_a.centroid, p_b.centroid)
        else:
            dist = GeometryEngine.edge_to_edge_distance(p_a.bounding_box, p_b.bounding_box)

        if dist > max_dist + tolerance:
            excess = round(dist - max_dist, 4)
            penalty = (
                0.0
                if constraint.classification == ConstraintClassification.HARD
                else round(excess * constraint.penalty, 2)
            )
            violations.append(
                ConstraintViolation(
                    constraint_id=constraint.id,
                    constraint_type=self.supported_type,
                    classification=constraint.classification,
                    involved_departments=depts[:2],
                    magnitude=excess,
                    penalty_cost=penalty,
                    measured_value=round(dist, 4),
                    required_value=max_dist,
                    description=f"Distance between '{depts[0]}' and '{depts[1]}' is {dist:.2f}m, exceeding maximum allowed {max_dist:.2f}m (excess: {excess:.2f}m).",
                )
            )
        return violations


class AdjacencyChecker(BaseConstraintChecker):
    """Enforces that two departments share a common boundary (wall/aisle)."""

    @property
    def supported_type(self) -> ConstraintType:
        return ConstraintType.ADJACENCY

    def check(
        self,
        constraint: Constraint,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> List[ConstraintViolation]:
        layout = _extract_continuous_layout(problem, solution)
        tolerance = constraint.parameters.get("tolerance", 1e-4)
        min_length = float(constraint.parameters.get("min_shared_length", 0.0))
        depts = constraint.involved_departments
        if len(depts) < 2:
            return []

        violations: List[ConstraintViolation] = []
        p_a = layout.placements.get(depts[0])
        p_b = layout.placements.get(depts[1])
        if not p_a or not p_b:
            return []

        shared_len = GeometryEngine.shared_boundary_length(p_a.bounding_box, p_b.bounding_box, tolerance=tolerance)
        if shared_len <= tolerance or shared_len < min_length - tolerance:
            edge_dist = GeometryEngine.edge_to_edge_distance(p_a.bounding_box, p_b.bounding_box)
            magnitude = round(edge_dist if edge_dist > tolerance else (min_length - shared_len), 4)
            penalty = (
                0.0
                if constraint.classification == ConstraintClassification.HARD
                else round(constraint.penalty, 2)
            )
            violations.append(
                ConstraintViolation(
                    constraint_id=constraint.id,
                    constraint_type=self.supported_type,
                    classification=constraint.classification,
                    involved_departments=depts[:2],
                    magnitude=magnitude,
                    penalty_cost=penalty,
                    measured_value=round(shared_len, 4),
                    required_value=max(min_length, tolerance),
                    description=f"Departments '{depts[0]}' and '{depts[1]}' are not adjacent (shared boundary: {shared_len:.2f}m, separation: {edge_dist:.2f}m).",
                )
            )
        return violations


class SeparationChecker(MinDistanceChecker):
    """Enforces separation constraint (alias for MinDistanceChecker)."""

    @property
    def supported_type(self) -> ConstraintType:
        return ConstraintType.SEPARATION
