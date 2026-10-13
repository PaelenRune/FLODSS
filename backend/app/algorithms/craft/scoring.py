"""Objective function evaluation for CRAFT: Material Handling Cost calculation."""

import math
from typing import Dict, Optional
from app.models.problem import FacilityLayoutProblem
from app.models.geometry import Point2D
from app.models.representation import ContinuousLayout
from app.services.geometry_engine import DistanceMetricType
from app.algorithms.craft.config import CRAFTConfig


def compute_mhc(
    problem: FacilityLayoutProblem,
    layout: ContinuousLayout,
    config: Optional[CRAFTConfig] = None,
) -> float:
    """Compute the total Material Handling Cost (MHC) across all directed flows in the problem.
    
    Formula: MHC = Sum( flow.quantity * distance(centroid_i, centroid_j) * unit_cost )
    
    Matches the standardized evaluation engine MaterialHandlingCostEvaluator exactly.
    """
    default_cost = config.default_cost_per_unit_distance if config else 1.0
    metric = config.distance_metric if config else DistanceMetricType.MANHATTAN

    centroids: Dict[str, Point2D] = {k: v.centroid for k, v in layout.placements.items()}

    total_cost = 0.0
    for flow in problem.flows:
        c_src = centroids.get(flow.source_department)
        c_tgt = centroids.get(flow.target_department)
        if c_src is None or c_tgt is None:
            continue

        if metric in (DistanceMetricType.MANHATTAN, DistanceMetricType.RECTILINEAR, DistanceMetricType.CENTROID_MANHATTAN):
            dist = abs(c_src.x - c_tgt.x) + abs(c_src.y - c_tgt.y)
        else:
            dx = c_src.x - c_tgt.x
            dy = c_src.y - c_tgt.y
            dist = math.sqrt(dx * dx + dy * dy)

        unit_cost = flow.cost_per_unit_distance if flow.cost_per_unit_distance is not None else default_cost
        total_cost += flow.quantity * dist * unit_cost

    return round(total_cost, 4)
