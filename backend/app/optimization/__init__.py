"""Optimization package for multi-objective, exact, and metaheuristic solvers."""

from app.optimization.base import ParetoFront, BaseMultiObjectiveOptimizer
from app.optimization.pareto import (
    DecisionSupportRecommendation,
    ExcludedCandidate,
    ObjectiveDefinition,
    ObjectiveDirection,
    ParetoAnalysisResult,
    ParetoCandidate,
    ParetoFrontierService,
    TradeOffComparison,
    get_default_pareto_objectives,
)

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

__all__ = [
    "ParetoFront",
    "BaseMultiObjectiveOptimizer",
    "DecisionSupportRecommendation",
    "ExcludedCandidate",
    "ObjectiveDefinition",
    "ObjectiveDirection",
    "ParetoAnalysisResult",
    "ParetoCandidate",
    "ParetoFrontierService",
    "TradeOffComparison",
    "get_default_pareto_objectives",
    "AdaptiveConfig",
    "AdaptiveStrategyResult",
    "CandidatePortfolio",
    "DecisionTraceStep",
    "PortfolioCandidateItem",
    "ProvenanceRecord",
    "RuleBasedStrategySelector",
    "StrategyArchetype",
    "StrategyExecutionEngine",
    "StrategyPipeline",
]

