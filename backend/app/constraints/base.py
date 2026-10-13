"""Constraint checking base abstractions."""

from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.models.constraint import Constraint, ConstraintViolation, ConstraintType


class BaseConstraintChecker(ABC):
    """Abstract base class for constraint checkers."""

    @property
    @abstractmethod
    def supported_type(self) -> ConstraintType:
        """The ConstraintType handled by this checker."""
        pass

    @abstractmethod
    def check(
        self,
        constraint: Constraint,
        problem: FacilityLayoutProblem,
        solution: LayoutSolution,
    ) -> List[ConstraintViolation]:
        """Verify the constraint and return violations if any."""
        pass
