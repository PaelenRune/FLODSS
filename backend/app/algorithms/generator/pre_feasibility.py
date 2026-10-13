"""Pre-feasibility analyzer verifying preliminary solvability before search execution."""

from typing import Dict, List

from app.algorithms.generator.models import PreFeasibilityReport
from app.feasibility.dimension_generator import LegalDimensionGenerator
from app.models.problem import FacilityLayoutProblem
from app.models.constraint import ConstraintClassification


class PreFeasibilityAnalyzer:
    """Performs rigorous pre-search physical and geometric compatibility checks.
    
    Identifies impossible problem formulations prior to expending combinatorial search budgets.
    """

    @classmethod
    def analyze(
        cls,
        problem: FacilityLayoutProblem,
        max_shape_alternatives: int = 10,
        tolerance: float = 1e-4,
    ) -> PreFeasibilityReport:
        """Analyze facility bounds, required areas, legal shapes, and fixed placement conditions."""
        errors: List[str] = []
        warnings: List[str] = []

        fac_w = problem.facility.width
        fac_h = problem.facility.height
        fac_area = problem.facility.area or (fac_w * fac_h)

        # 1. Total Area Capacity Check
        req_area_total = problem.total_required_area
        utilization = req_area_total / fac_area if fac_area > 0 else 1.0

        if req_area_total > fac_area + tolerance:
            errors.append(
                f"Total required department area ({req_area_total:.1f} m²) exceeds facility capacity ({fac_area:.1f} m²). "
                f"Area utilization is {utilization * 100.0:.1f}%."
            )
        elif utilization > 0.95:
            warnings.append(
                f"Very tight area utilization ({utilization * 100.0:.1f}%). Packing search space is highly constrained."
            )

        # 2. Individual Department Feasibility & Legal Dimensions
        dept_shapes: Dict[str, int] = {}
        unconstrained: List[str] = []
        constrained: List[str] = []

        for dept in problem.departments:
            # Check if department required area alone exceeds facility
            if dept.required_area > fac_area + tolerance:
                errors.append(
                    f"Department '{dept.id}' requires {dept.required_area:.1f} m², which exceeds total facility area ({fac_area:.1f} m²)."
                )

            # Generate legal rectangular shapes
            legal_dims = LegalDimensionGenerator.generate_legal_dimensions(
                department=dept,
                facility_width=fac_w,
                facility_height=fac_h,
                max_alternatives=max_shape_alternatives,
                tolerance=tolerance,
            )
            dept_shapes[dept.id] = len(legal_dims)

            if len(legal_dims) == 0:
                errors.append(
                    f"Department '{dept.id}' (area={dept.required_area:.1f} m²) has NO legal rectangular dimensions "
                    f"satisfying width bounds [{dept.min_width}..{dept.max_width}], height bounds [{dept.min_height}..{dept.max_height}], "
                    f"and max aspect ratio {dept.max_aspect_ratio} inside facility [{fac_w}x{fac_h}]."
                )

            if dept.min_width or dept.max_width or dept.min_height or dept.max_height or dept.max_aspect_ratio or dept.fixed_position:
                constrained.append(dept.id)
            else:
                unconstrained.append(dept.id)

            # Check fixed position validity
            if dept.fixed_position is not None:
                fx = dept.fixed_position.x
                fy = dept.fixed_position.y
                if fx < -tolerance or fx > fac_w + tolerance or fy < -tolerance or fy > fac_h + tolerance:
                    errors.append(
                        f"Department '{dept.id}' fixed position ({fx}, {fy}) is outside facility boundaries [{fac_w}x{fac_h}]."
                    )

        # 3. Reserved Zones Boundary Verification
        if problem.reserved_zones:
            for rz in problem.reserved_zones:
                box = rz.bounding_box
                if box.x_min < -tolerance or box.y_min < -tolerance or box.x_max > fac_w + tolerance or box.y_max > fac_h + tolerance:
                    errors.append(
                        f"Reserved zone '{rz.id}' [{box.x_min}..{box.x_max}, {box.y_min}..{box.y_max}] exceeds facility boundaries."
                    )

        # 4. Hard Constraints Sanity
        for c in problem.constraints:
            if c.classification == ConstraintClassification.HARD:
                # Basic check for target department existence
                for d_ref in c.involved_departments:
                    if not any(d.id == d_ref for d in problem.departments):
                        errors.append(f"Hard constraint '{c.id}' references non-existent department '{d_ref}'.")

        is_feasible = len(errors) == 0

        return PreFeasibilityReport(
            is_feasible=is_feasible,
            errors=errors,
            warnings=warnings,
            total_required_area=round(req_area_total, 2),
            facility_available_area=round(fac_area, 2),
            area_utilization=round(utilization, 4),
            unconstrained_departments=sorted(unconstrained),
            constrained_departments=sorted(constrained),
            department_shape_counts=dept_shapes,
        )
