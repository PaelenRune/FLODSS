"""Layout solution data model."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.geometry import Point2D, Dimensions2D, BoundingBox
from app.models.constraint import ConstraintViolation


class SolverTerminationReason(str, Enum):
    """Formal termination reason for layout optimization algorithms."""

    SUCCESS_COMPLETE = "SUCCESS_COMPLETE"
    FAILED_NO_FEASIBLE_CANDIDATE = "FAILED_NO_FEASIBLE_CANDIDATE"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    PARTIAL_INCOMPLETE = "PARTIAL_INCOMPLETE"


class DepartmentPlacement(BaseModel):
    """Detailed spatial placement of an individual department in a solution."""

    department_id: str = Field(..., description="Target department ID")
    origin: Point2D = Field(..., description="Bottom-left (x_min, y_min) corner of the department")
    dimensions: Dimensions2D = Field(..., description="Allocated width and height")
    orientation_degrees: float = Field(default=0.0, description="Orientation angle in degrees")

    @property
    def bounding_box(self) -> BoundingBox:
        """Compute the axis-aligned bounding box."""
        return BoundingBox(
            x_min=self.origin.x,
            y_min=self.origin.y,
            x_max=self.origin.x + self.dimensions.width,
            y_max=self.origin.y + self.dimensions.height,
        )

    @property
    def centroid(self) -> Point2D:
        """Compute center point of the department."""
        return Point2D(
            x=self.origin.x + (self.dimensions.width / 2.0),
            y=self.origin.y + (self.dimensions.height / 2.0),
        )


class LayoutSolution(BaseModel):
    """Represents a generated layout solution produced by an optimization algorithm."""

    problem_id: str = Field(..., description="ID of the problem this solution addresses")
    algorithm_name: str = Field(..., description="Name of the algorithm that produced this solution")
    algorithm_version: Optional[str] = Field(default=None, description="Version of the algorithm")
    layout_signature: Optional[str] = Field(
        default=None,
        description="Deterministic SHA-256 geometric invariant fingerprint",
    )
    
    # Placements
    placements: Dict[str, DepartmentPlacement] = Field(
        default_factory=dict,
        description="Detailed placements keyed by department_id",
    )
    # Simple mapping views for fast numerical calculations
    department_positions: Dict[str, Point2D] = Field(
        default_factory=dict,
        description="Centroid or reference coordinate for each department",
    )
    department_dimensions: Dict[str, Dimensions2D] = Field(
        default_factory=dict,
        description="Width and height for each department",
    )

    # Completion and termination status (Phase 5.1)
    is_complete: bool = Field(
        default=True,
        description="True if all required departments from the problem are placed",
    )
    placed_department_count: int = Field(
        default=0,
        description="Number of departments successfully positioned",
    )
    total_department_count: int = Field(
        default=0,
        description="Total number of departments required by the problem",
    )
    unplaced_departments: List[str] = Field(
        default_factory=list,
        description="IDs of departments that could not be placed",
    )
    termination_reason: Optional[str] = Field(
        default=None,
        description="Formal termination reason status",
    )

    # Performance and evaluation
    objective_values: Dict[str, float] = Field(
        default_factory=dict,
        description="Computed objective values (e.g. {'flow_distance_cost': 1420.5, 'relationship_score': 85.0})",
    )
    constraint_violations: List[ConstraintViolation] = Field(
        default_factory=list,
        description="List of hard or soft constraint violations observed in this layout",
    )
    feasibility_status: bool = Field(
        default=True,
        description="Overall feasibility status (False if any HARD constraint is violated)",
    )
    execution_time_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Elapsed algorithm execution run-time in seconds",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata (e.g. random seed, iteration count, Pareto rank)",
    )

    def get_bounding_box(self, dept_id: str) -> Optional[BoundingBox]:
        """Retrieve bounding box for department."""
        if dept_id in self.placements:
            return self.placements[dept_id].bounding_box
        if dept_id in self.department_positions and dept_id in self.department_dimensions:
            pos = self.department_positions[dept_id]
            dim = self.department_dimensions[dept_id]
            # If position is centroid:
            return BoundingBox(
                x_min=pos.x - dim.width / 2.0,
                y_min=pos.y - dim.height / 2.0,
                x_max=pos.x + dim.width / 2.0,
                y_max=pos.y + dim.height / 2.0,
            )
        return None
