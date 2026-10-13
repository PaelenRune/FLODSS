"""Evaluation package for multi-criteria assessment of facility layouts."""

from app.evaluation.metrics import (
    MetricType,
    MetricDirection,
    EvaluationMetricResult,
)
from app.evaluation.base import BaseMetricEvaluator
from app.evaluation.config import EvaluationConfig
from app.evaluation.matrices import (
    DistanceMatrixService,
    DistanceMatrixResult,
    FlowMatrixService,
    FlowMatrixResult,
    RelationshipMatrixService,
    RelationshipMatrixResult,
)
from app.evaluation.evaluators import (
    FlowDistanceEvaluator,
    MaterialHandlingCostEvaluator,
    RelationshipSatisfactionEvaluator,
    AreaUtilizationEvaluator,
    ConstraintPenaltyEvaluator,
)
from app.evaluation.engine import (
    EvaluationEngine,
    EvaluationReport,
    ComparisonReport,
)

__all__ = [
    "MetricType",
    "MetricDirection",
    "EvaluationMetricResult",
    "BaseMetricEvaluator",
    "EvaluationConfig",
    "DistanceMatrixService",
    "DistanceMatrixResult",
    "FlowMatrixService",
    "FlowMatrixResult",
    "RelationshipMatrixService",
    "RelationshipMatrixResult",
    "FlowDistanceEvaluator",
    "MaterialHandlingCostEvaluator",
    "RelationshipSatisfactionEvaluator",
    "AreaUtilizationEvaluator",
    "ConstraintPenaltyEvaluator",
    "EvaluationEngine",
    "EvaluationReport",
    "ComparisonReport",
    "CanonicalEvaluationReport",
    "CanonicalEvaluationService",
    "compute_problem_provenance_hashes",
    "compute_evaluation_config_hash",
]

from app.evaluation.canonical import (
    CanonicalEvaluationReport,
    CanonicalEvaluationService,
    compute_problem_provenance_hashes,
    compute_evaluation_config_hash,
)
