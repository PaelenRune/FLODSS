"""Optimization foundation interfaces for multi-objective and exact solvers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution


class ParetoFront(BaseModel):
    """Set of non-dominated Pareto solutions in multi-objective optimization."""

    problem_id: str
    solutions: List[LayoutSolution] = Field(default_factory=list)
    objective_names: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseMultiObjectiveOptimizer(ABC):
    """Abstract interface for multi-objective optimization (e.g. NSGA-II, Pareto search)."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def optimize(
        self,
        problem: FacilityLayoutProblem,
        objectives: List[str],
        **kwargs,
    ) -> ParetoFront:
        """Produce a Pareto frontier of alternative layouts."""
        pass
