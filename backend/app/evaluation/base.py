"""Abstract Base Class for layout metric evaluators."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.evaluation.metrics import EvaluationMetricResult, MetricDirection


class BaseMetricEvaluator(ABC):
    """Abstract Base Class for an independent metric evaluator.
    
    Evaluators are decoupled from algorithms:
    Algorithm -> LayoutSolution -> Evaluation Engine.
    """

    @property
    @abstractmethod
    def metric_name(self) -> str:
        """Unique identifier matching or extending MetricType."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human readable title for reports and UI."""
        pass

    @property
    def unit(self) -> str:
        """Unit of measurement."""
        return ""

    @property
    def direction(self) -> MetricDirection:
        """Whether optimization minimizes or maximizes this metric."""
        return MetricDirection.MINIMIZE

    @abstractmethod
    def evaluate(
        self,
        problem: FacilityLayoutProblem,
        solution: LayoutSolution,
    ) -> EvaluationMetricResult:
        """Calculate the metric score for the given problem and solution.
        
        Args:
            problem: The layout problem definition.
            solution: The proposed layout solution to evaluate.
            
        Returns:
            EvaluationMetricResult containing numerical score and diagnostic details.
        """
        pass
