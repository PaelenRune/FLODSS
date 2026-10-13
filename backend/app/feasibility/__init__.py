"""Rectangular layout feasibility foundation package."""

from app.feasibility.aldep_diagnostics import ALDEPGeometryDiagnostics
from app.feasibility.dimension_generator import LegalDimensionGenerator
from app.feasibility.free_rectangles import FreeRectangleDetector
from app.feasibility.models import (
    DepartmentDiagnosticDetail,
    DepartmentGeometryFailureType,
    DimensionAlternativeTag,
    FreeRectangle,
    FreeSpaceReport,
    LayoutGeometryDiagnosticReport,
    LegalDimension,
    PlacementFeasibilityResult,
)
from app.feasibility.placement_checker import PlacementFeasibilityChecker
from app.feasibility.representations import (
    BaseFeasibilityRepairStrategy,
    BasePackingStrategy,
    SequencePair,
    SlicingCutType,
    SlicingNode,
    SlicingTree,
)
from app.feasibility.service import (
    RectangularFeasibilityService,
    rectangular_feasibility_service,
)

__all__ = [
    "LegalDimension",
    "DimensionAlternativeTag",
    "FreeRectangle",
    "FreeSpaceReport",
    "PlacementFeasibilityResult",
    "DepartmentGeometryFailureType",
    "DepartmentDiagnosticDetail",
    "LayoutGeometryDiagnosticReport",
    "LegalDimensionGenerator",
    "FreeRectangleDetector",
    "PlacementFeasibilityChecker",
    "ALDEPGeometryDiagnostics",
    "SlicingCutType",
    "SlicingNode",
    "SlicingTree",
    "SequencePair",
    "BasePackingStrategy",
    "BaseFeasibilityRepairStrategy",
    "RectangularFeasibilityService",
    "rectangular_feasibility_service",
]
