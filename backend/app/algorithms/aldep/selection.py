"""Department selection logic for ALDEP based on Muther REL affinity and random tie-breaking."""

import random
from typing import Dict, List, Optional, Tuple

from app.algorithms.aldep.config import ALDEPConfig, SelectionTieBreak
from app.algorithms.aldep.models import ALDEPSelectionStep
from app.models.problem import FacilityLayoutProblem
from app.models.relationship import ClosenessRating, DEFAULT_RELATIONSHIP_SCORES


def get_relationship_score(problem: FacilityLayoutProblem, dept_a: str, dept_b: str) -> float:
    """Retrieve numerical affinity score between two departments from problem REL chart.
    
    Defaults to 0.0 (Muther rating 'U' - Unimportant) if no relationship is defined.
    """
    if dept_a == dept_b:
        return 0.0

    for rel in problem.relationships:
        if (rel.department_a == dept_a and rel.department_b == dept_b) or (
            rel.department_a == dept_b and rel.department_b == dept_a
        ):
            if rel.score is not None:
                return float(rel.score)
            return float(DEFAULT_RELATIONSHIP_SCORES.get(rel.relationship_type, 0.0))

    return 0.0


def select_initial_department(
    unplaced: List[str],
    threshold: float,
    rng: random.Random,
) -> Tuple[str, ALDEPSelectionStep]:
    """Select the first department to place using seeded pseudo-random choice.
    
    Classical ALDEP (Seevers & Ihm 1967) begins by randomly choosing an initial department
    from all candidate departments.
    """
    if not unplaced:
        raise ValueError("Cannot select initial department from empty unplaced list.")

    # Sort for deterministic behavior with seeded rng
    sorted_unplaced = sorted(unplaced)
    selected = rng.choice(sorted_unplaced)

    step = ALDEPSelectionStep(
        step_number=1,
        last_department_id=None,
        unplaced_candidates=sorted_unplaced,
        candidate_scores={d: 0.0 for d in sorted_unplaced},
        threshold=threshold,
        eligible_candidates=[],
        selection_mode="INITIAL_RANDOM",
        selected_department=selected,
    )
    return selected, step


def select_next_department(
    last_dept_id: str,
    unplaced: List[str],
    problem: FacilityLayoutProblem,
    config: ALDEPConfig,
    rng: random.Random,
    step_number: int,
) -> Tuple[str, ALDEPSelectionStep]:
    """Select the next department based on Muther REL closeness with the last-placed department.
    
    Rules (Tompkins et al. / Buffa, Armour & Vollmann):
        1. Find all unplaced departments having relationship score >= selection_threshold (T).
        2. If one or more departments qualify:
           - In RANDOM_AMONG_MAX mode (classical): filter to those with the highest score,
             breaking ties randomly among the tied maximal candidates.
           - In RANDOM_AMONG_THRESHOLD mode: pick randomly among all departments >= T.
        3. If NO unplaced department meets the threshold:
           - Fallback to picking randomly from ALL remaining unplaced departments.
    """
    if not unplaced:
        raise ValueError(f"Cannot select next department at step {step_number}: unplaced list is empty.")

    sorted_unplaced = sorted(unplaced)
    candidate_scores: Dict[str, float] = {
        d: get_relationship_score(problem, last_dept_id, d) for d in sorted_unplaced
    }

    # Filter candidates meeting threshold
    eligible = [d for d in sorted_unplaced if candidate_scores[d] >= config.selection_threshold]

    if eligible:
        if config.tie_breaker == SelectionTieBreak.RANDOM_AMONG_MAX:
            max_score = max(candidate_scores[d] for d in eligible)
            tied_max = [d for d in eligible if candidate_scores[d] == max_score]
            selected = rng.choice(tied_max)
            mode = "AFFINITY_MAX"
        else:
            selected = rng.choice(eligible)
            mode = "AFFINITY_THRESHOLD"
    else:
        # Fallback: no candidate has sufficient closeness rating; pick randomly from all unplaced
        selected = rng.choice(sorted_unplaced)
        mode = "RANDOM_FALLBACK"

    step = ALDEPSelectionStep(
        step_number=step_number,
        last_department_id=last_dept_id,
        unplaced_candidates=sorted_unplaced,
        candidate_scores=candidate_scores,
        threshold=config.selection_threshold,
        eligible_candidates=eligible,
        selection_mode=mode,
        selected_department=selected,
    )
    return selected, step


def generate_aldep_sequence(
    problem: FacilityLayoutProblem,
    config: ALDEPConfig,
    rng: random.Random,
    preplaced: Optional[List[str]] = None,
) -> Tuple[List[str], List[ALDEPSelectionStep]]:
    """Generate the complete ordered department sequence using ALDEP selection rules.
    
    Preplaced/fixed departments are excluded from the selection queue as they are positioned
    prior to heuristic sweep.
    """
    preplaced_set = set(preplaced or [])
    all_dept_ids = [d.id for d in problem.departments if d.id not in preplaced_set]

    if not all_dept_ids:
        return [], []

    unplaced = list(all_dept_ids)
    placement_order: List[str] = []
    steps: List[ALDEPSelectionStep] = []

    # Step 1: Initial department
    first_dept, first_step = select_initial_department(
        unplaced=unplaced,
        threshold=config.selection_threshold,
        rng=rng,
    )
    placement_order.append(first_dept)
    steps.append(first_step)
    unplaced.remove(first_dept)

    # Subsequent steps
    step_num = 2
    while unplaced:
        last_dept = placement_order[-1]
        next_dept, next_step = select_next_department(
            last_dept_id=last_dept,
            unplaced=unplaced,
            problem=problem,
            config=config,
            rng=rng,
            step_number=step_num,
        )
        placement_order.append(next_dept)
        steps.append(next_step)
        unplaced.remove(next_dept)
        step_num += 1

    return placement_order, steps
