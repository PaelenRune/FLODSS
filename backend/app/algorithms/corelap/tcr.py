"""Total Closeness Rating (TCR) computation and deterministic department selection logic."""

from typing import Dict, List, Set, Tuple
from app.models.problem import FacilityLayoutProblem
from app.models.department import Department
from app.models.relationship import RELATIONSHIP_DEFAULT_SCORES, ClosenessRating


def get_relationship_weight(
    problem: FacilityLayoutProblem, dept_a: str, dept_b: str
) -> float:
    """Retrieve numerical closeness weight between two departments.
    
    If no explicit relationship is defined between dept_a and dept_b, defaults to U (0.0).
    """
    if dept_a == dept_b:
        return 0.0

    for rel in problem.relationships:
        if (rel.department_a == dept_a and rel.department_b == dept_b) or (
            rel.department_a == dept_b and rel.department_b == dept_a
        ):
            if rel.score is not None:
                return float(rel.score)
            return float(RELATIONSHIP_DEFAULT_SCORES.get(rel.relationship_type, 0.0))

    return 0.0


def calculate_tcr(problem: FacilityLayoutProblem) -> Dict[str, float]:
    """Calculate Total Closeness Rating (TCR) for every department in the problem.
    
    Formula:
        TCR_i = Sum_{j != i} w_ij
        
    Where:
        w_ij = Closeness relationship weight between department i and j.
        Missing pairs default to U = 0.0.
        
    Returns:
        Dict mapping department_id to its Total Closeness Rating.
    """
    dept_ids = [d.id for d in problem.departments]
    tcr_dict: Dict[str, float] = {d_id: 0.0 for d_id in dept_ids}

    # Pre-index defined relationships for fast lookup
    rel_weights: Dict[Tuple[str, str], float] = {}
    for rel in problem.relationships:
        score = rel.score
        if score is None:
            score = RELATIONSHIP_DEFAULT_SCORES.get(rel.relationship_type, 0.0)
        rel_weights[(rel.department_a, rel.department_b)] = float(score)
        rel_weights[(rel.department_b, rel.department_a)] = float(score)

    for i in dept_ids:
        total = 0.0
        for j in dept_ids:
            if i != j:
                total += rel_weights.get((i, j), 0.0)
        tcr_dict[i] = round(total, 2)

    return tcr_dict


def select_initial_department(
    unplaced_departments: List[Department], tcr_map: Dict[str, float]
) -> Department:
    """Select the first department to place according to classical CORELAP rules.
    
    Deterministic Tie-Breaking Hierarchy:
        1. Highest Total Closeness Rating (TCR)
        2. Highest required area (larger anchor footprints stabilize the layout)
        3. Lexicographical / alphabetical department ID
    """
    if not unplaced_departments:
        raise ValueError("Cannot select initial department from empty list.")

    def tie_break_key(dept: Department) -> Tuple[float, float, str]:
        # Tuple to sort descending for TCR and Area, ascending for ID
        return (
            -tcr_map.get(dept.id, 0.0),
            -dept.required_area,
            dept.id,
        )

    sorted_depts = sorted(unplaced_departments, key=tie_break_key)
    return sorted_depts[0]


def select_next_department(
    unplaced_departments: List[Department],
    placed_department_ids: Set[str],
    problem: FacilityLayoutProblem,
    tcr_map: Dict[str, float],
) -> Tuple[Department, float]:
    """Select next unplaced department with highest relationship sum to already placed departments.
    
    Formula:
        PlacementScore_i = Sum_{j in Placed} w_ij
        
    Deterministic Tie-Breaking Hierarchy:
        1. Highest PlacementScore_i (maximum affinity with current cluster)
        2. Highest Total Closeness Rating (TCR_i)
        3. Highest required area
        4. Lexicographical / alphabetical department ID
        
    Returns:
        Tuple of (Selected Department, Placed Affinity Score)
    """
    if not unplaced_departments:
        raise ValueError("Cannot select next department from empty list.")

    # Pre-index defined relationships
    rel_weights: Dict[Tuple[str, str], float] = {}
    for rel in problem.relationships:
        score = rel.score
        if score is None:
            score = RELATIONSHIP_DEFAULT_SCORES.get(rel.relationship_type, 0.0)
        rel_weights[(rel.department_a, rel.department_b)] = float(score)
        rel_weights[(rel.department_b, rel.department_a)] = float(score)

    def scoring_key(dept: Department) -> Tuple[float, float, float, str]:
        # Sum of affinities with already placed departments
        placed_score = sum(rel_weights.get((dept.id, p_id), 0.0) for p_id in placed_department_ids)
        return (
            -placed_score,
            -tcr_map.get(dept.id, 0.0),
            -dept.required_area,
            dept.id,
        )

    sorted_depts = sorted(unplaced_departments, key=scoring_key)
    selected = sorted_depts[0]
    best_placed_score = sum(rel_weights.get((selected.id, p_id), 0.0) for p_id in placed_department_ids)
    return selected, best_placed_score
