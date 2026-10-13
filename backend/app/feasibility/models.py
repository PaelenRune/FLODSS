"""Data models for rectangular layout feasibility, dimensions, free space, and diagnostics."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.models.geometry import BoundingBox, Dimensions2D, Point2D, ReservedZone


class DimensionAlternativeTag(str, Enum):
    """Categorical tag for generated rectangular dimension alternatives."""

    SQUARE_ISH = "square_ish"
    MIN_WIDTH = "min_width"
    MAX_WIDTH = "max_width"
    MIN_HEIGHT = "min_height"
    MAX_HEIGHT = "max_height"
    ASPECT_RATIO_BOUND = "aspect_ratio_bound"
    BOUNDARY_ALIGNED = "boundary_aligned"
    INTERPOLATED = "interpolated"


class LegalDimension(BaseModel):
    """Valid rectangular dimension candidate for a department strictly conserving required area."""

    width: float = Field(..., gt=0, description="Width along the X-axis in meters")
    height: float = Field(..., gt=0, description="Height along the Y-axis in meters")
    area: float = Field(..., gt=0, description="Total cross-sectional area (width * height)")
    aspect_ratio: float = Field(..., ge=1.0, description="Aspect ratio: max(width, height) / min(width, height)")
    tag: DimensionAlternativeTag = Field(
        default=DimensionAlternativeTag.SQUARE_ISH,
        description="Origin rationale of this dimension alternative",
    )
    is_rotated_variant: bool = Field(
        default=False,
        description="True if derived by exchanging width and height (90 degree rotation)",
    )


class FreeRectangle(BaseModel):
    """Usable empty rectangular space inside the facility boundaries."""

    x_min: float = Field(..., description="Bottom-left X coordinate")
    y_min: float = Field(..., description="Bottom-left Y coordinate")
    x_max: float = Field(..., description="Top-right X coordinate")
    y_max: float = Field(..., description="Top-right Y coordinate")

    @property
    def x(self) -> float:
        return self.x_min

    @property
    def y(self) -> float:
        return self.y_min

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def bounding_box(self) -> BoundingBox:
        return BoundingBox(
            x_min=self.x_min,
            y_min=self.y_min,
            x_max=self.x_max,
            y_max=self.y_max,
        )

    def can_accommodate(self, width: float, height: float, tolerance: float = 1e-4) -> bool:
        """Check if a rectangular department with (width, height) fits into this region."""
        return (width <= self.width + tolerance) and (height <= self.height + tolerance)


class FreeSpaceReport(BaseModel):
    """Detailed report on available free rectangular regions and facility capacity."""

    facility_width: float
    facility_height: float
    facility_total_area: float
    occupied_area: float
    net_free_area: float
    free_rectangles: List[FreeRectangle] = Field(
        default_factory=list,
        description="List of maximal empty rectangular regions (can overlap as alternative placements)",
    )
    largest_free_rectangle_area: float = 0.0
    fragmentation_index: float = Field(
        default=0.0,
        description="Metric [0, 1] describing free space scattering (0 = contiguous, 1 = heavily fragmented)",
    )

    @property
    def total_facility_area(self) -> float:
        return self.facility_total_area

    @property
    def total_occupied_area(self) -> float:
        return self.occupied_area

    @property
    def maximal_empty_rectangles(self) -> List[FreeRectangle]:
        return self.free_rectangles


class PlacementFeasibilityResult(BaseModel):
    """Evaluation outcome of a proposed department placement."""

    feasible: bool = Field(..., description="True if placement satisfies all physical, geometric and domain constraints")
    rejection_reasons: List[str] = Field(default_factory=list, description="List of constraint violations causing rejection")
    department_id: str
    selected_dimensions: Optional[Dimensions2D] = None
    selected_coordinates: Optional[Point2D] = None
    placed_bounding_box: Optional[BoundingBox] = None
    area_difference: float = Field(default=0.0, description="|allocated_area - required_area|")
    overlap_area: float = Field(default=0.0, description="Total overlap area with other entities in m²")
    remaining_available_space: Dict[str, Any] = Field(
        default_factory=dict,
        description="Residual space metrics after proposed placement",
    )

    @property
    def is_feasible(self) -> bool:
        return self.feasible

    @property
    def errors(self) -> List[str]:
        return self.rejection_reasons

    @property
    def boundary_contained(self) -> bool:
        return not any(
            ("facility boundary" in e or "exceeds facility width" in e or "exceeds facility height" in e)
            for e in self.rejection_reasons
        )

    @property
    def overlap_free(self) -> bool:
        return self.overlap_area == 0.0 and not any("Overlap detected" in e for e in self.rejection_reasons)

    @property
    def area_conserved(self) -> bool:
        return not any(
            ("Area conservation failure" in e or "Area mismatch" in e)
            for e in self.rejection_reasons
        )

    @property
    def dimensions_valid(self) -> bool:
        return not any(
            ("violates minimum" in e or "exceeds maximum" in e)
            for e in self.rejection_reasons
        )

    @property
    def aspect_ratio_valid(self) -> bool:
        return not any("Aspect ratio" in e for e in self.rejection_reasons)

    @property
    def fixed_position_respected(self) -> bool:
        return not any("fixed position" in e for e in self.rejection_reasons)

    @property
    def residual_free_space_m2(self) -> float:
        return float(self.remaining_available_space.get("net_free_area_after_placement", 0.0))

    @property
    def overlapping_departments(self) -> List[str]:
        depts: List[str] = []
        for r in self.rejection_reasons:
            if "Overlap detected with department '" in r:
                start = r.find("Overlap detected with department '") + len("Overlap detected with department '")
                end = r.find("'", start)
                if end != -1:
                    depts.append(r[start:end])
        return depts


class DepartmentGeometryFailureType(str, Enum):
    """Categories of geometric layout failure."""

    NON_RECTANGULAR_SHAPE = "non_rectangular_department_shape"
    DISCRETE_NON_RECTANGULAR_CELLS = "non_rectangular_department_shape"
    MIN_WIDTH_VIOLATION = "minimum_width_violation"
    MAX_WIDTH_VIOLATION = "maximum_width_violation"
    MIN_HEIGHT_VIOLATION = "minimum_height_violation"
    MAX_HEIGHT_VIOLATION = "maximum_height_violation"
    ASPECT_RATIO_VIOLATION = "aspect_ratio_violation"
    BOUNDING_BOX_OVERLAP = "bounding_box_overlap"
    OUT_OF_BOUNDS = "out_of_bounds"
    AREA_DISTORTION = "area_distortion"
    AREA_DISTORTION_IN_BOUNDING_BOX = "area_distortion"
    FIXED_POSITION_VIOLATION = "fixed_position_violation"
    RESERVED_ZONE_VIOLATION = "reserved_zone_violation"


class DepartmentDiagnosticDetail(BaseModel):
    """Department-specific diagnostic outcome."""

    department_id: str
    is_rectangular: bool
    shape_description: str  # e.g. "rectangular_block", "L-shaped", "serpentine_wrap"
    allocated_width: float
    allocated_height: float
    allocated_area: float
    required_area: float
    area_error_percentage: float
    aspect_ratio: float
    bounding_box: BoundingBox
    discrete_cell_count: Optional[int] = None
    bounding_box_cell_count: Optional[int] = None
    failures: List[DepartmentGeometryFailureType] = Field(default_factory=list)
    failure_messages: List[str] = Field(default_factory=list)

    @property
    def failure_types(self) -> List[DepartmentGeometryFailureType]:
        return self.failures

    @property
    def is_rectangular_in_grid(self) -> bool:
        return self.is_rectangular

    @property
    def area_distortion_ratio(self) -> float:
        if self.required_area > 0:
            return round(self.allocated_area / self.required_area, 4)
        return 1.0


class LayoutGeometryDiagnosticReport(BaseModel):
    """Comprehensive geometric diagnosis for discrete and continuous layout representations."""

    layout_id: Optional[str] = None
    problem_id: str
    is_fully_feasible: bool
    failure_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of each failure category across the layout",
    )
    total_violations_count: int = 0
    non_rectangular_departments: List[str] = Field(default_factory=list)
    overlapping_department_pairs: List[Tuple[str, str, float]] = Field(
        default_factory=list,
        description="Pairs of overlapping departments with overlap area: [(dept_a, dept_b, area_m2)]",
    )
    department_details: Dict[str, DepartmentDiagnosticDetail] = Field(default_factory=dict)
    summary_message: str

    @property
    def is_strictly_valid(self) -> bool:
        return self.is_fully_feasible
