"""Candidate placement scoring and evaluation for CORELAP."""

import math
from typing import Dict, List, Tuple
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousPlacement
from app.services.geometry_engine import GeometryEngine
from app.algorithms.corelap.config import CORELAPConfig, PlacementMode
from app.algorithms.corelap.tcr import get_relationship_weight


def score_candidate_placement(
    candidate: ContinuousPlacement,
    placed_placements: Dict[str, ContinuousPlacement],
    problem: FacilityLayoutProblem,
    config: CORELAPConfig,
) -> Tuple[float, List[str]]:
    """Score a single candidate placement based on affinity with already placed departments.
    
    Mode 1: CLASSICAL_ADJACENCY (Classical CORELAP):
        - Strictly evaluates shared border contact with placed neighbors.
        - Adjacent reward: weight * shared_boundary_length.
        - Non-adjacent department pairs contribute zero score (0.0).
        - No arbitrary distance-decay heuristics or unverified multipliers.
        
    Mode 2: EXTENDED_DISTANCE_WEIGHTED (FLODSS Extension):
        - Incorporates continuous distance decay toward all related departments.
        - Configurable X-relationship penalty multipliers and separation penalties.
        
    Returns:
        Tuple of (Calculated Score, List of Adjacent Placed Department IDs)
    """
    if not placed_placements:
        return 0.0, []

    tol = config.numerical_tolerance
    dept_id = candidate.department_id
    total_score = 0.0
    neighbors: List[str] = []

    for p_id, p_placement in placed_placements.items():
        w = get_relationship_weight(problem, dept_id, p_id)
        if abs(w) < 1e-9:
            continue

        c_box = candidate.bounding_box
        p_box = p_placement.bounding_box

        # Shared wall boundary length
        shared_len = GeometryEngine.shared_boundary_length(c_box, p_box, tolerance=tol)
        is_adj = shared_len > tol or GeometryEngine.is_adjacent(c_box, p_box, tolerance=tol)

        if is_adj:
            neighbors.append(p_id)

        if config.placement_mode == PlacementMode.CLASSICAL_ADJACENCY:
            # Classical CORELAP: only adjacency matters
            if is_adj:
                total_score += w * max(1.0, shared_len)
            # Non-adjacent pairs contribute 0.0 in classical mode
        else:
            # Extended mode with explicit configurable constants
            dist = GeometryEngine.centroid_manhattan_distance(candidate.centroid, p_placement.centroid)
            if is_adj:
                if w > 0:
                    total_score += w * max(1.0, shared_len)
                else:
                    total_score += w * max(1.0, shared_len) * config.x_adjacency_penalty_multiplier
            else:
                if w > 0:
                    total_score += w / (1.0 + config.distance_decay_factor * dist)
                else:
                    total_score -= (abs(w) * config.separated_x_penalty_scale) / (
                        1.0 + config.separated_x_decay_factor * dist
                    )

    return round(total_score, 4), neighbors


def evaluate_and_rank_candidates(
    candidates: List[ContinuousPlacement],
    placed_placements: Dict[str, ContinuousPlacement],
    problem: FacilityLayoutProblem,
    config: CORELAPConfig,
) -> List[Tuple[ContinuousPlacement, float, List[str]]]:
    """Evaluate and deterministically rank candidate placements from best to worst.
    
    Deterministic Tie-Breaking Order:
        1. Highest candidate placement score (descending)
        2. Proximity to facility center (compactness, ascending distance) [if configured]
        3. Bottom-to-top Y coordinate (ascending Y)
        4. Left-to-right X coordinate (ascending X)
    """
    if not candidates:
        return []

    fac_center_x = problem.facility.width / 2.0
    fac_center_y = problem.facility.height / 2.0

    scored_candidates: List[Tuple[ContinuousPlacement, float, List[str]]] = []

    for cand in candidates:
        score, neighbors = score_candidate_placement(cand, placed_placements, problem, config)
        scored_candidates.append((cand, score, neighbors))

    def ranking_key(item: Tuple[ContinuousPlacement, float, List[str]]) -> Tuple[float, float, float, float]:
        cand, score, _ = item
        if config.tie_break_center_compactness:
            dist_to_center = math.hypot(cand.centroid.x - fac_center_x, cand.centroid.y - fac_center_y)
        else:
            dist_to_center = 0.0
            
        return (
            -score,                 # Maximize affinity score
            dist_to_center,         # Prefer central compactness
            cand.y,                 # Deterministic coordinates
            cand.x,
        )

    scored_candidates.sort(key=ranking_key)
    return scored_candidates
