"""Constraint verification engine orchestrating layout rule checks and penalties."""

from typing import Dict, List, Optional, Union
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.models.representation import ContinuousLayout
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
)


class ConstraintEngine:
    """Orchestrates constraint checks across all constraints defined in a problem."""

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

    def register_checker(self, checker: BaseConstraintChecker) -> None:
        self._checkers[checker.supported_type] = checker

    def check_all(
        self,
        problem: FacilityLayoutProblem,
        solution: Union[LayoutSolution, ContinuousLayout],
    ) -> List[ConstraintViolation]:
        """Evaluate all constraints defined on the problem against the solution."""
        violations: List[ConstraintViolation] = []
        for constraint in problem.constraints:
            checker = self._checkers.get(constraint.type)
            if checker:
                v = checker.check(constraint, problem, solution)
                violations.extend(v)
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
