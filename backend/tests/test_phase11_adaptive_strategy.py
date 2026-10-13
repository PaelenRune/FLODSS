"""Phase 11: Comprehensive unit and integration test suite for Adaptive Strategy Engine v1."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout
from app.models.solution import LayoutSolution
from app.optimization.adaptive import (
    AdaptiveConfig,
    AdaptiveStrategyResult,
    CandidatePortfolio,
    DecisionTraceStep,
    PortfolioCandidateItem,
    ProvenanceRecord,
    RuleBasedStrategySelector,
    StrategyArchetype,
    StrategyExecutionEngine,
    StrategyPipeline,
)
from app.evaluation.canonical import CanonicalEvaluationService
from app.evaluation.config import EvaluationConfig
from app.services.problem_analyzer import ProblemAnalyzer, ProblemFingerprint
from app.services.problem_service import problem_service

DATA_EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "examples"


@pytest.fixture
def academic_4_problem() -> FacilityLayoutProblem:
    return problem_service.load_problem(DATA_EXAMPLES_DIR / "sample_academic_4.json")


@pytest.fixture
def industrial_10_problem() -> FacilityLayoutProblem:
    return problem_service.load_problem(DATA_EXAMPLES_DIR / "sample_plant.json")


@pytest.fixture
def expansion_8_problem() -> FacilityLayoutProblem:
    return problem_service.load_problem(DATA_EXAMPLES_DIR / "sample_expansion_8.json")


@pytest.fixture
def logistics_5_problem() -> FacilityLayoutProblem:
    return problem_service.load_problem(DATA_EXAMPLES_DIR / "sample_logistics_5.json")


class TestProblemFingerprintExtraction:
    """1. Tests for deterministic problem fingerprint extraction and unavailable features."""

    def test_fingerprint_correctness(self, industrial_10_problem):
        fp = ProblemAnalyzer.extract_fingerprint(industrial_10_problem)

        assert fp.problem_id == "FLP_INDUSTRIAL_10"
        assert fp.department_count == 10
        assert fp.facility_width == 150.0
        assert fp.facility_height == 80.0
        assert fp.facility_area == 12000.0
        assert fp.total_required_area == 11000.0
        assert round(fp.area_utilization, 3) == 0.917
        assert fp.dimension_constrained_count == 10
        assert fp.has_dimension_constraints is True
        assert fp.aspect_ratio_constrained_count == 0
        assert fp.has_aspect_ratio_constraints is False
        assert fp.hard_constraints_count == 2
        assert fp.soft_constraints_count == 2
        assert fp.hard_constraint_types == ["boundary", "non_overlapping"]
        assert fp.soft_constraint_types == ["min_distance"]
        assert isinstance(fp.unavailable_features, list)
        assert "multi_floor_elevators" in fp.unavailable_features

    def test_fixed_and_reserved_constraints_in_fingerprint(self, expansion_8_problem):
        fp = ProblemAnalyzer.extract_fingerprint(expansion_8_problem)

        assert fp.problem_id == "FLP_EXPANSION_8"
        assert fp.department_count == 8
        assert fp.reserved_zone_count == 1
        assert fp.reserved_zone_ratio == pytest.approx(0.0417, abs=1e-3)
        assert fp.has_aspect_ratio_constraints is True
        assert "boundary" in fp.hard_constraint_types
        assert "non_overlapping" in fp.hard_constraint_types
        assert "min_distance" in fp.soft_constraint_types


class TestStrategyRuleSelection:
    """2. Tests for RuleBasedStrategySelector and archetype classification."""

    def test_rule_selection_small_unconstrained(self, academic_4_problem):
        fp = ProblemAnalyzer.extract_fingerprint(academic_4_problem)
        strategy = RuleBasedStrategySelector.select_strategy(fp, has_initial_layout=False)

        assert strategy.archetype == StrategyArchetype.SMALL_UNCONSTRAINED_FLOW
        assert strategy.rule_id == "RULE_SMALL_UNCONSTRAINED_FLOW"
        assert strategy.primary_algorithm == "corelap"
        assert "craft" in strategy.improvement_algorithms
        assert strategy.fallback_algorithm == "feasible_layout_generator"
        assert len(strategy.non_working_conditions) > 0

    def test_rule_selection_dense_constrained(self, industrial_10_problem):
        fp = ProblemAnalyzer.extract_fingerprint(industrial_10_problem)
        strategy = RuleBasedStrategySelector.select_strategy(fp, has_initial_layout=False)

        assert strategy.archetype == StrategyArchetype.DENSE_RECTANGULAR_CONSTRAINED
        assert strategy.rule_id == "RULE_DENSE_RECTANGULAR_CONSTRAINED"
        assert strategy.primary_algorithm == "feasible_layout_generator"
        assert "genetic_algorithm" in strategy.improvement_algorithms
        assert strategy.fallback_algorithm == "genetic_algorithm"

    def test_rule_selection_reserved_expansion(self, expansion_8_problem):
        fp = ProblemAnalyzer.extract_fingerprint(expansion_8_problem)
        strategy = RuleBasedStrategySelector.select_strategy(fp, has_initial_layout=False)

        assert strategy.archetype == StrategyArchetype.DENSE_RECTANGULAR_CONSTRAINED
        assert strategy.primary_algorithm == "feasible_layout_generator"

    def test_rule_selection_baseline_provided(self, academic_4_problem):
        fp = ProblemAnalyzer.extract_fingerprint(academic_4_problem)
        strategy = RuleBasedStrategySelector.select_strategy(fp, has_initial_layout=True)

        assert strategy.archetype == StrategyArchetype.BASELINE_IMPROVEMENT
        assert strategy.rule_id == "RULE_BASELINE_IMPROVEMENT"
        assert strategy.primary_algorithm == "craft"
        assert "genetic_algorithm" in strategy.improvement_algorithms


class TestAdaptiveExecutionAndFallback:
    """3. Tests for fallback mechanisms, portfolio management, and budgeting."""

    def test_fallback_after_incomplete_corelap(self, industrial_10_problem, monkeypatch):
        # Force selector to recommend CORELAP on industrial 10 (where CORELAP is incomplete)
        forced_pipeline = StrategyPipeline(
            archetype=StrategyArchetype.SMALL_UNCONSTRAINED_FLOW,
            name="Forced CORELAP Pipeline",
            rule_id="TEST_FORCED_CORELAP",
            rule_description="Test pipeline",
            primary_algorithm="corelap",
            improvement_algorithms=[],
            fallback_algorithm="feasible_layout_generator",
            rationale="Test fallback trigger",
        )
        monkeypatch.setattr(
            RuleBasedStrategySelector,
            "select_strategy",
            lambda fp, has_initial_layout=False: forced_pipeline,
        )

        cfg = AdaptiveConfig(max_total_runtime_seconds=10.0, fallback_enabled=True)
        result = StrategyExecutionEngine.execute(industrial_10_problem, config=cfg)

        assert result.feasible_status is True
        assert len(result.execution_trace) >= 2
        # Verify first step failed and second was fallback
        assert result.execution_trace[0].action == "EXECUTE_PRIMARY_CORELAP"
        assert result.execution_trace[0].success is False
        assert result.execution_trace[1].action == "EXECUTE_FALLBACK_FEASIBLE_LAYOUT_GENERATOR"
        assert result.execution_trace[1].was_fallback is True
        assert result.execution_trace[1].success is True

    def test_fallback_disabled_behavior(self, industrial_10_problem, monkeypatch):
        forced_pipeline = StrategyPipeline(
            archetype=StrategyArchetype.SMALL_UNCONSTRAINED_FLOW,
            name="Forced CORELAP Pipeline",
            rule_id="TEST_FORCED_CORELAP",
            rule_description="Test pipeline",
            primary_algorithm="corelap",
            improvement_algorithms=[],
            fallback_algorithm="feasible_layout_generator",
            rationale="Test fallback disabled",
        )
        monkeypatch.setattr(
            RuleBasedStrategySelector,
            "select_strategy",
            lambda fp, has_initial_layout=False: forced_pipeline,
        )

        cfg = AdaptiveConfig(max_total_runtime_seconds=10.0, fallback_enabled=False)
        result = StrategyExecutionEngine.execute(industrial_10_problem, config=cfg)

        assert result.feasible_status is False
        assert result.termination_reason == "NO_FEASIBLE_SOLUTION_FOUND"
        assert len(result.execution_trace) == 1
        assert result.execution_trace[0].success is False

    def test_infeasible_candidate_excluded_from_pareto(self, industrial_10_problem, monkeypatch):
        forced_pipeline = StrategyPipeline(
            archetype=StrategyArchetype.SMALL_UNCONSTRAINED_FLOW,
            name="Forced CORELAP Pipeline",
            rule_id="TEST_FORCED_CORELAP",
            rule_description="Test pipeline",
            primary_algorithm="corelap",
            improvement_algorithms=[],
            fallback_algorithm="feasible_layout_generator",
            rationale="Test exclusion",
        )
        monkeypatch.setattr(
            RuleBasedStrategySelector,
            "select_strategy",
            lambda fp, has_initial_layout=False: forced_pipeline,
        )

        cfg = AdaptiveConfig(max_total_runtime_seconds=10.0, fallback_enabled=True)
        result = StrategyExecutionEngine.execute(industrial_10_problem, config=cfg)

        # Portfolio has 2 items: 1 infeasible CORELAP, 1 feasible Generator
        assert result.candidate_portfolio.infeasible_candidates_count == 1
        assert result.candidate_portfolio.feasible_candidates_count == 1
        # Pareto candidates must strictly contain only feasible solutions
        assert result.pareto_frontier.valid_candidates_count == 1
        assert result.final_recommendation is not None
        assert result.final_recommendation["source_algorithm"] == "feasible_layout_generator"

    def test_signature_deduplication_and_provenance(self, academic_4_problem):
        # Academic 4: CORELAP then CRAFT
        cfg = AdaptiveConfig(max_total_runtime_seconds=5.0)
        result = StrategyExecutionEngine.execute(academic_4_problem, config=cfg)

        assert result.feasible_status is True
        portfolio = result.candidate_portfolio
        assert portfolio.unique_candidates_count == len(portfolio.items)
        assert len(portfolio.deduplication_map) == portfolio.unique_candidates_count

        for item in portfolio.items:
            assert len(item.provenance_sources) >= 1
            assert item.provenance_sources[0].algorithm_name in ["corelap", "craft", "feasible_layout_generator"]

    def test_algorithm_call_limit_enforcement(self, academic_4_problem):
        cfg = AdaptiveConfig(max_total_runtime_seconds=15.0, max_algorithm_calls=1)
        result = StrategyExecutionEngine.execute(academic_4_problem, config=cfg)

        # Only 1 algorithm call allowed; improvement stage must be skipped
        assert result.total_algorithm_calls == 1
        assert len(result.execution_trace) == 1
        assert result.termination_reason in ["CALL_LIMIT_REACHED", "COMPLETED_SUCCESSFULLY"]

    def test_deterministic_execution_with_seed(self, industrial_10_problem):
        cfg1 = AdaptiveConfig(max_total_runtime_seconds=15.0, random_seed=999, ga_population_size=10, ga_generations=5)
        cfg2 = AdaptiveConfig(max_total_runtime_seconds=15.0, random_seed=999, ga_population_size=10, ga_generations=5)

        res1 = StrategyExecutionEngine.execute(industrial_10_problem, config=cfg1)
        res2 = StrategyExecutionEngine.execute(industrial_10_problem, config=cfg2)

        assert res1.feasible_status == res2.feasible_status
        assert res1.candidate_portfolio.unique_candidates_count == res2.candidate_portfolio.unique_candidates_count
        assert res1.final_recommendation["layout_signature"] == res2.final_recommendation["layout_signature"]
        assert res1.final_recommendation["material_handling_cost"] == res2.final_recommendation["material_handling_cost"]


class TestParetoAndCanonicalEvaluationIntegration:
    """4. Tests for Canonical Evaluation and Multi-Objective Pareto Frontier integration."""

    def test_canonical_evaluation_consistency(self, academic_4_problem):
        cfg = AdaptiveConfig(max_total_runtime_seconds=5.0)
        result = StrategyExecutionEngine.execute(academic_4_problem, config=cfg)

        assert len(result.canonical_evaluations) > 0
        eval_cfg = EvaluationConfig()

        for report in result.canonical_evaluations:
            assert report.is_feasible is True
            assert report.is_complete is True
            assert report.material_handling_cost > 0
            assert report.relationship_satisfaction_percentage >= 0

            # Match with portfolio item
            matching = next((it for it in result.candidate_portfolio.items if it.output_layout_signature == report.layout_signature), None)
            assert matching is not None
            assert matching.material_handling_cost == pytest.approx(report.material_handling_cost, abs=1e-2)

    def test_pareto_frontier_ranking(self, industrial_10_problem):
        cfg = AdaptiveConfig(max_total_runtime_seconds=15.0, ga_population_size=12, ga_generations=6)
        result = StrategyExecutionEngine.execute(industrial_10_problem, config=cfg)

        assert result.pareto_frontier.frontier_count >= 1
        assert len(result.pareto_frontier.frontier_candidate_ids) == result.pareto_frontier.frontier_count
        assert result.final_recommendation is not None
        assert result.final_recommendation["is_on_pareto_frontier"] is True


class TestUnseenBenchmarkProblems:
    """5. Tests evaluating adaptive strategy on unseen benchmark problem variants."""

    def test_expansion_8_adaptive_solve(self, expansion_8_problem):
        cfg = AdaptiveConfig(max_total_runtime_seconds=15.0, ga_population_size=12, ga_generations=6)
        result = StrategyExecutionEngine.execute(expansion_8_problem, config=cfg)

        assert result.problem_id == "FLP_EXPANSION_8"
        assert result.feasible_status is True
        assert result.selected_strategy.archetype == StrategyArchetype.DENSE_RECTANGULAR_CONSTRAINED
        assert result.candidate_portfolio.feasible_candidates_count >= 1
        assert result.final_recommendation["material_handling_cost"] > 0

    def test_logistics_5_adaptive_solve(self, logistics_5_problem):
        cfg = AdaptiveConfig(max_total_runtime_seconds=10.0)
        result = StrategyExecutionEngine.execute(logistics_5_problem, config=cfg)

        assert result.problem_id == "FLP_LOGISTICS_5"
        assert result.feasible_status is True
        assert result.candidate_portfolio.feasible_candidates_count >= 1
        assert result.final_recommendation is not None


class TestAdaptiveStrategyAPI:
    """6. Tests for REST API routes /api/strategy/analyze and /api/strategy/solve."""

    def test_api_strategy_analyze_endpoint(self):
        client = TestClient(app)
        response = client.post("/api/strategy/analyze", json={"problem_id": "FLP_INDUSTRIAL_10"})

        assert response.status_code == 200
        data = response.json()
        assert data["problem_id"] == "FLP_INDUSTRIAL_10"
        assert "fingerprint" in data
        assert data["fingerprint"]["department_count"] == 10
        assert "selected_strategy" in data
        assert data["selected_strategy"]["rule_id"] == "RULE_DENSE_RECTANGULAR_CONSTRAINED"
        assert data["selected_strategy"]["primary_algorithm"] == "feasible_layout_generator"

    def test_api_strategy_solve_endpoint(self):
        client = TestClient(app)
        payload = {
            "problem_id": "FLP_ACADEMIC_4",
            "config": {
                "max_total_runtime_seconds": 5.0,
                "ga_population_size": 10,
                "ga_generations": 5,
            },
        }
        response = client.post("/api/strategy/solve", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["problem_id"] == "FLP_ACADEMIC_4"
        assert data["feasible_status"] is True
        assert "candidate_portfolio" in data
        assert data["candidate_portfolio"]["unique_candidates_count"] >= 1
        assert "execution_trace" in data
        assert len(data["execution_trace"]) >= 1
        assert "final_recommendation" in data
        assert data["final_recommendation"]["material_handling_cost"] > 0
