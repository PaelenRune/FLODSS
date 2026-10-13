"""Problem Fingerprint extractor and structural analyzer."""

from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field

from app.models.problem import FacilityLayoutProblem


class ProblemFingerprint(BaseModel):
    """Normalized statistical and structural characteristics of a layout problem instance."""

    problem_id: str
    department_count: int = Field(..., description="Number of departments to be placed")
    total_required_area: float = Field(..., description="Sum of required department areas")
    facility_area: float = Field(..., description="Total available facility footprint area")
    area_utilization: float = Field(..., description="Ratio of total required area to facility area")
    
    # Flow characteristics
    flow_count: int = Field(..., description="Number of active material flow connections")
    flow_density: float = Field(..., description="Active flows / maximum possible directed pairs N*(N-1)")
    total_flow_volume: float = Field(..., description="Sum of all flow quantities")
    average_flow: float = Field(..., description="Mean volume per active flow")
    max_flow: float = Field(..., description="Highest individual flow volume")
    
    # Dimensional & Geometric Characteristics
    facility_width: float = Field(default=0.0, description="Facility bounding width (m)")
    facility_height: float = Field(default=0.0, description="Facility bounding height (m)")
    aspect_ratio_constrained_count: int = Field(default=0, description="Number of departments with aspect ratio bounds")
    has_aspect_ratio_constraints: bool = Field(default=False, description="True if any department has aspect ratio constraints")
    dimension_constrained_count: int = Field(default=0, description="Number of departments with width/height bounds")
    has_dimension_constraints: bool = Field(default=False, description="True if any department has dimension bounds")

    # Relationships & Constraints
    closeness_relationships_count: int = Field(default=0, description="Total specified closeness ratings")
    undesirable_relationships_count: int = Field(default=0, description="Number of 'X' undesirable ratings")
    rel_density: float = Field(default=0.0, description="Ratio of specified relationships to maximum possible pairs N*(N-1)/2")
    fixed_departments_count: int = Field(..., description="Number of departments with pre-assigned coordinates")
    reserved_zone_count: int = Field(default=0, description="Number of reserved or blocked facility zones")
    reserved_zone_ratio: float = Field(default=0.0, description="Ratio of reserved zone area to facility area")
    hard_constraints_count: int = Field(..., description="Number of hard constraints")
    soft_constraints_count: int = Field(..., description="Number of soft constraints")
    hard_constraint_types: List[str] = Field(default_factory=list, description="Unique hard constraint type identifiers")
    soft_constraint_types: List[str] = Field(default_factory=list, description="Unique soft constraint type identifiers")
    unavailable_features: List[str] = Field(default_factory=list, description="Features explicitly unavailable or not modeled")
    
    # Dispersion / Variation
    area_variation: float = Field(..., description="Coefficient of variation (std / mean) of department areas")
    product_processes_count: int = Field(default=0, description="Distinct product/process route count")


class ProblemAnalyzer:
    """Analyzes a FacilityLayoutProblem and extracts its characteristic structural fingerprint."""

    @staticmethod
    def extract_fingerprint(problem: FacilityLayoutProblem) -> ProblemFingerprint:
        """Compute the structural fingerprint for algorithm selection and benchmarking."""
        n = len(problem.departments)
        fac_w = float(problem.facility.width)
        fac_h = float(problem.facility.height)
        facility_area = problem.facility.area or (fac_w * fac_h)
        utilization = problem.area_utilization

        # Area variation
        areas = [d.required_area for d in problem.departments]
        if areas and len(areas) > 1:
            mean_area = float(np.mean(areas))
            std_area = float(np.std(areas))
            area_var = round(std_area / mean_area, 4) if mean_area > 0 else 0.0
        else:
            area_var = 0.0

        # Flow stats
        flow_qtys = [f.quantity for f in problem.flows]
        flow_count = len(flow_qtys)
        max_possible_directed = n * (n - 1) if n > 1 else 1
        flow_density = round(flow_count / max_possible_directed, 4) if max_possible_directed > 0 else 0.0
        total_vol = float(sum(flow_qtys)) if flow_qtys else 0.0
        avg_flow = round(float(np.mean(flow_qtys)), 2) if flow_qtys else 0.0
        max_flow = float(max(flow_qtys)) if flow_qtys else 0.0

        # Unique products / processes
        unique_prods = {f.product_or_process_id for f in problem.flows if f.product_or_process_id}

        # Relationships
        rel_count = len(problem.relationships)
        max_possible_undirected = (n * (n - 1)) / 2 if n > 1 else 1
        rel_density = round(rel_count / max_possible_undirected, 4) if max_possible_undirected > 0 else 0.0
        x_count = sum(1 for r in problem.relationships if r.relationship_type.value == "X")

        # Fixed departments
        fixed_count = sum(1 for d in problem.departments if d.fixed_position is not None)

        # Aspect ratio and dimension constraints
        aspect_constrained = sum(
            1 for d in problem.departments
            if d.min_aspect_ratio is not None or d.max_aspect_ratio is not None
        )
        dimension_constrained = sum(
            1 for d in problem.departments
            if d.min_width is not None or d.max_width is not None
            or d.min_height is not None or d.max_height is not None
        )

        # Reserved zones
        reserved_zones = getattr(problem.facility, "reserved_zones", None) or []
        res_count = len(reserved_zones)
        res_area = 0.0
        for z in reserved_zones:
            if hasattr(z, "bounding_box") and z.bounding_box is not None:
                res_area += z.bounding_box.width * z.bounding_box.height
            elif hasattr(z, "width") and hasattr(z, "height"):
                res_area += float(z.width) * float(z.height)
        res_ratio = round(res_area / facility_area, 4) if facility_area > 0 else 0.0

        # Constraints
        hard_types = sorted(list({c.type.value for c in problem.constraints if c.classification.value == "hard"}))
        soft_types = sorted(list({c.type.value for c in problem.constraints if c.classification.value == "soft"}))
        hard_count = sum(1 for c in problem.constraints if c.classification.value == "hard")
        soft_count = sum(1 for c in problem.constraints if c.classification.value == "soft")

        # Track unavailable or unmodeled features honestly
        unavailable = []
        if flow_count == 0:
            unavailable.append("flow_matrix")
        if rel_count == 0:
            unavailable.append("rel_matrix")
        if res_count == 0:
            unavailable.append("reserved_zones")
        # Structural 3D / stochastic features not supported in 2D continuous benchmark
        unavailable.extend(["multi_floor_elevators", "3d_clearance_heights", "stochastic_demand_variations"])

        return ProblemFingerprint(
            problem_id=problem.id,
            department_count=n,
            total_required_area=round(problem.total_required_area, 2),
            facility_area=round(facility_area, 2),
            area_utilization=round(utilization, 4),
            facility_width=fac_w,
            facility_height=fac_h,
            aspect_ratio_constrained_count=aspect_constrained,
            has_aspect_ratio_constraints=aspect_constrained > 0,
            dimension_constrained_count=dimension_constrained,
            has_dimension_constraints=dimension_constrained > 0,
            flow_count=flow_count,
            flow_density=flow_density,
            total_flow_volume=round(total_vol, 2),
            average_flow=avg_flow,
            max_flow=max_flow,
            closeness_relationships_count=rel_count,
            undesirable_relationships_count=x_count,
            rel_density=rel_density,
            fixed_departments_count=fixed_count,
            reserved_zone_count=res_count,
            reserved_zone_ratio=res_ratio,
            hard_constraints_count=hard_count,
            soft_constraints_count=soft_count,
            hard_constraint_types=hard_types,
            soft_constraint_types=soft_types,
            unavailable_features=unavailable,
            area_variation=area_var,
            product_processes_count=len(unique_prods),
        )
