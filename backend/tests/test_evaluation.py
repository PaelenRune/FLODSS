"""Unit tests for the Evaluation Engine and metric evaluators."""

from app.evaluation.base import BaseMetricEvaluator
from app.evaluation.metrics import (
    MetricType,
    MetricDirection,
    EvaluationMetricResult,
)
from app.evaluation.engine import EvaluationEngine, EvaluationReport, ComparisonReport
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution


class FlowDistanceCostEvaluator(BaseMetricEvaluator):
    """Sample metric evaluator computing rectilinear flow distance cost."""

    @property
    def metric_name(self) -> str:
        return MetricType.TOTAL_FLOW_DISTANCE.value

    @property
    def display_name(self) -> str:
        return "Total Flow Distance Cost"

    @property
    def unit(self) -> str:
        return "m-moves"

    def evaluate(self, problem: FacilityLayoutProblem, solution: LayoutSolution) -> EvaluationMetricResult:
        total_cost = 0.0
        # Compute sum of (flow * rectilinear_distance)
        for flow in problem.flows:
            pos_src = solution.department_positions.get(flow.source_department)
            pos_tgt = solution.department_positions.get(flow.target_department)
            if pos_src and pos_tgt:
                dist = abs(pos_src.x - pos_tgt.x) + abs(pos_src.y - pos_tgt.y)
                total_cost += flow.quantity * dist * flow.cost_per_unit_distance

        return EvaluationMetricResult(
            metric_name=self.metric_name,
            display_name=self.display_name,
            value=round(total_cost, 2),
            unit=self.unit,
            direction=MetricDirection.MINIMIZE,
        )


class AreaUtilizationEvaluator(BaseMetricEvaluator):
    """Sample metric evaluator computing floor area utilization ratio."""

    @property
    def metric_name(self) -> str:
        return MetricType.AREA_UTILIZATION.value

    @property
    def display_name(self) -> str:
        return "Floor Area Utilization"

    @property
    def unit(self) -> str:
        return "%"

    @property
    def direction(self) -> MetricDirection:
        return MetricDirection.MAXIMIZE

    def evaluate(self, problem: FacilityLayoutProblem, solution: LayoutSolution) -> EvaluationMetricResult:
        utilization = problem.area_utilization * 100.0
        return EvaluationMetricResult(
            metric_name=self.metric_name,
            display_name=self.display_name,
            value=round(utilization, 2),
            unit=self.unit,
            direction=MetricDirection.MAXIMIZE,
        )


class TestEvaluationEngine:
    """Tests ensuring decoupling of evaluation from optimization algorithms."""

    def test_evaluation_engine_execution(
        self,
        sample_problem: FacilityLayoutProblem,
        sample_solution: LayoutSolution,
    ):
        engine = EvaluationEngine()
        engine.register_evaluator(FlowDistanceCostEvaluator())
        engine.register_evaluator(AreaUtilizationEvaluator())

        assert MetricType.TOTAL_FLOW_DISTANCE.value in engine.registered_metrics
        assert MetricType.AREA_UTILIZATION.value in engine.registered_metrics

        report: EvaluationReport = engine.evaluate(sample_problem, sample_solution)

        assert isinstance(report, EvaluationReport)
        assert report.problem_id == sample_problem.id
        assert report.algorithm_name == sample_solution.algorithm_name
        assert report.is_feasible is True
        assert MetricType.TOTAL_FLOW_DISTANCE.value in report.metrics
        assert report.metrics[MetricType.TOTAL_FLOW_DISTANCE.value].value > 0

    def test_evaluation_engine_comparison(
        self,
        sample_problem: FacilityLayoutProblem,
        sample_solution: LayoutSolution,
    ):
        engine = EvaluationEngine([FlowDistanceCostEvaluator()])

        # Create a second alternative solution with higher cost
        alt_solution = sample_solution.model_copy(deep=True)
        alt_solution.algorithm_name = "alternative_solution_b"
        # Shift positions further apart
        for pos in alt_solution.department_positions.values():
            pos.x *= 2.0

        comparison: ComparisonReport = engine.compare(
            sample_problem, [alt_solution, sample_solution]
        )

        assert comparison.solution_count == 2
        # Best solution (lower flow distance) ranked first
        assert comparison.ranking[0] == sample_solution.algorithm_name
