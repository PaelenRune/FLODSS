"""Services package for application business logic."""

from app.services.health_service import HealthService, SystemStatus
from app.services.matrix_parser import (
    parse_from_to_matrix,
    flows_to_matrix,
    parse_relationship_matrix,
)
from app.services.problem_loader import (
    BaseProblemLoader,
    JSONProblemLoader,
    CSVProblemLoader,
    ExcelProblemLoader,
    ProblemLoaderFactory,
    load_problem,
)
from app.services.problem_analyzer import ProblemAnalyzer, ProblemFingerprint
from app.services.problem_service import (
    ProblemService,
    ProblemSummary,
    ProblemValidationReport,
    problem_service,
)
from app.services.geometry_engine import GeometryEngine, DistanceMetricType
from app.services.representation_converter import (
    ConversionResult,
    ContinuousToGridConverter,
    GridToContinuousConverter,
)
from app.services.layout_normalizer import normalize_layout, generate_layout_signature
from app.services.layout_validator import LayoutValidator, LayoutValidationResult
from app.feasibility.service import RectangularFeasibilityService, rectangular_feasibility_service

__all__ = [
    "HealthService",
    "SystemStatus",
    "parse_from_to_matrix",
    "flows_to_matrix",
    "parse_relationship_matrix",
    "BaseProblemLoader",
    "JSONProblemLoader",
    "CSVProblemLoader",
    "ExcelProblemLoader",
    "ProblemLoaderFactory",
    "load_problem",
    "ProblemAnalyzer",
    "ProblemFingerprint",
    "ProblemService",
    "ProblemSummary",
    "ProblemValidationReport",
    "problem_service",
    "GeometryEngine",
    "DistanceMetricType",
    "ConversionResult",
    "ContinuousToGridConverter",
    "GridToContinuousConverter",
    "normalize_layout",
    "generate_layout_signature",
    "LayoutValidator",
    "LayoutValidationResult",
    "RectangularFeasibilityService",
    "rectangular_feasibility_service",
]
