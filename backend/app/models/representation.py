"""Layout representation abstractions: Continuous Rectangular and Discrete Grid layouts."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field, model_validator

from app.models.geometry import Point2D, Dimensions2D, BoundingBox, ReservedZone
from app.models.solution import LayoutSolution, DepartmentPlacement


class LayoutRepresentationType(str, Enum):
    """Supported layout representation paradigms."""

    CONTINUOUS = "continuous"  # Continuous 2D rectangular coordinates (x, y, w, h)
    GRID = "grid"              # Discrete cell occupancy grid (unit blocks)


class ContinuousPlacement(BaseModel):
    """Spatial placement of a single department in continuous coordinate space.
    
    Coordinate convention:
    - Origin (0, 0) is at the facility bottom-left corner.
    - X increases to the right.
    - Y increases upwards.
    """

    department_id: str = Field(..., description="Target department identifier")
    x: float = Field(..., description="Bottom-left X coordinate")
    y: float = Field(..., description="Bottom-left Y coordinate")
    width: float = Field(..., gt=0, description="Allocated width along X-axis")
    height: float = Field(..., gt=0, description="Allocated height along Y-axis")
    orientation_degrees: float = Field(
        default=0.0,
        description="Orientation rotation: 0.0 or 90.0 degrees",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y

    @property
    def top(self) -> float:
        return self.y + self.height

    @property
    def aspect_ratio(self) -> float:
        min_dim = min(self.width, self.height)
        if min_dim <= 0:
            return 1.0
        return max(self.width, self.height) / min_dim

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2.0)

    @property
    def centroid(self) -> Point2D:
        return Point2D(
            x=self.center_x,
            y=self.center_y,
        )

    @property
    def bounding_box(self) -> BoundingBox:
        return BoundingBox(
            x_min=self.x,
            y_min=self.y,
            x_max=self.x + self.width,
            y_max=self.y + self.height,
        )

    def to_department_placement(self) -> DepartmentPlacement:
        """Convert to standard DepartmentPlacement model."""
        return DepartmentPlacement(
            department_id=self.department_id,
            origin=Point2D(x=self.x, y=self.y),
            dimensions=Dimensions2D(width=self.width, height=self.height),
            orientation_degrees=self.orientation_degrees,
        )

    @classmethod
    def from_department_placement(cls, dp: DepartmentPlacement) -> "ContinuousPlacement":
        return cls(
            department_id=dp.department_id,
            x=dp.origin.x,
            y=dp.origin.y,
            width=dp.dimensions.width,
            height=dp.dimensions.height,
            orientation_degrees=dp.orientation_degrees,
        )


class BaseLayoutRepresentation(BaseModel, ABC):
    """Abstract Base Class for layout representations."""

    representation_type: LayoutRepresentationType
    id: Optional[str] = Field(default=None, description="Unique layout identifier")
    name: Optional[str] = Field(default=None, description="Human-readable layout name")
    problem_id: Optional[str] = Field(default=None, description="Target problem identifier")
    facility_width: float = Field(..., gt=0, description="Total facility width along X")
    facility_height: float = Field(..., gt=0, description="Total facility height along Y")
    reserved_zones: List[ReservedZone] = Field(default_factory=list, description="No-placement or reserved zones")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary layout metadata")

    @abstractmethod
    def get_department_ids(self) -> List[str]:
        """Return list of placed department IDs."""
        pass

    @abstractmethod
    def get_bounding_box(self, dept_id: str) -> Optional[BoundingBox]:
        """Retrieve bounding box for department."""
        pass


class ContinuousLayout(BaseLayoutRepresentation):
    """Continuous 2D rectangular layout representation."""

    representation_type: LayoutRepresentationType = LayoutRepresentationType.CONTINUOUS
    layout_signature: Optional[str] = Field(
        default=None,
        description="Deterministic SHA-256 geometric invariant fingerprint",
    )
    placements: Dict[str, ContinuousPlacement] = Field(
        default_factory=dict,
        description="Placements indexed by department_id",
    )

    def get_department_ids(self) -> List[str]:
        return sorted(list(self.placements.keys()))

    def get_bounding_box(self, dept_id: str) -> Optional[BoundingBox]:
        placement = self.placements.get(dept_id)
        return placement.bounding_box if placement else None

    @property
    def department_positions(self) -> Dict[str, Point2D]:
        """Backwards compatibility alias returning centroid positions."""
        return {k: Point2D(x=v.center_x, y=v.center_y) for k, v in self.placements.items()}

    @property
    def department_dimensions(self) -> Dict[str, Dimensions2D]:
        """Backwards compatibility alias returning department dimensions."""
        return {k: Dimensions2D(width=v.width, height=v.height) for k, v in self.placements.items()}

    def to_layout_solution(
        self,
        problem_id: str,
        algorithm_name: str = "manual_or_converted",
        algorithm_version: Optional[str] = None,
        objective_values: Optional[Dict[str, float]] = None,
    ) -> LayoutSolution:
        """Export into standard LayoutSolution domain model."""
        dept_placements = {k: v.to_department_placement() for k, v in self.placements.items()}
        positions = {k: v.centroid for k, v in self.placements.items()}
        dimensions = {k: Dimensions2D(width=v.width, height=v.height) for k, v in self.placements.items()}

        return LayoutSolution(
            problem_id=problem_id,
            algorithm_name=algorithm_name,
            algorithm_version=algorithm_version,
            layout_signature=self.layout_signature,
            placements=dept_placements,
            department_positions=positions,
            department_dimensions=dimensions,
            objective_values=objective_values or {},
            feasibility_status=True,
        )

    @classmethod
    def from_layout_solution(
        cls,
        solution: LayoutSolution,
        facility_width: float,
        facility_height: float,
        reserved_zones: Optional[List[ReservedZone]] = None,
    ) -> "ContinuousLayout":
        """Instantiate ContinuousLayout from a LayoutSolution."""
        placements: Dict[str, ContinuousPlacement] = {}
        for dept_id, dp in solution.placements.items():
            pos = solution.department_positions.get(dept_id) if solution.department_positions else None
            if pos and (abs(dp.centroid.x - pos.x) > 1e-4 or abs(dp.centroid.y - pos.y) > 1e-4):
                # Positions were updated directly in LayoutSolution
                placements[dept_id] = ContinuousPlacement(
                    department_id=dept_id,
                    x=pos.x - dp.dimensions.width / 2.0,
                    y=pos.y - dp.dimensions.height / 2.0,
                    width=dp.dimensions.width,
                    height=dp.dimensions.height,
                    orientation_degrees=dp.orientation_degrees,
                )
            else:
                placements[dept_id] = ContinuousPlacement.from_department_placement(dp)

        # Fallback if placements dict was empty but positions/dimensions were filled
        if not placements and solution.department_positions and solution.department_dimensions:
            for dept_id, pos in solution.department_positions.items():
                dim = solution.department_dimensions.get(dept_id)
                if dim:
                    placements[dept_id] = ContinuousPlacement(
                        department_id=dept_id,
                        x=pos.x - dim.width / 2.0,
                        y=pos.y - dim.height / 2.0,
                        width=dim.width,
                        height=dim.height,
                    )

        sol_meta = dict(solution.metadata) if getattr(solution, "metadata", None) else {}
        sig = sol_meta.get("layout_signature") or sol_meta.get("signature")

        return cls(
            id=getattr(solution, "id", None) or f"{solution.algorithm_name}_{solution.problem_id}",
            name=f"{solution.algorithm_name} ({solution.problem_id})",
            problem_id=solution.problem_id,
            facility_width=facility_width,
            facility_height=facility_height,
            layout_signature=sig,
            placements=placements,
            reserved_zones=reserved_zones or [],
            metadata=sol_meta,
        )


class GridDepartmentBlock(BaseModel):
    """Represents a connected block or set of discrete grid cells occupied by a department."""

    department_id: str
    cells: List[Tuple[int, int]] = Field(
        default_factory=list,
        description="List of (row, col) coordinates occupied by this department",
    )

    @property
    def cell_count(self) -> int:
        return len(self.cells)

    def area(self, cell_size: float) -> float:
        return self.cell_count * (cell_size ** 2)

    def bounding_box(self, cell_size: float, origin: Point2D) -> Optional[BoundingBox]:
        """Compute continuous bounding box enclosing all occupied cells."""
        if not self.cells:
            return None
        min_row = min(r for r, _ in self.cells)
        max_row = max(r for r, _ in self.cells)
        min_col = min(c for _, c in self.cells)
        max_col = max(c for _, c in self.cells)

        return BoundingBox(
            x_min=origin.x + min_col * cell_size,
            y_min=origin.y + min_row * cell_size,
            x_max=origin.x + (max_col + 1) * cell_size,
            y_max=origin.y + (max_row + 1) * cell_size,
        )


class GridLayout(BaseLayoutRepresentation):
    """Discrete cell grid occupancy representation."""

    representation_type: LayoutRepresentationType = LayoutRepresentationType.GRID
    cell_size: float = Field(..., gt=0, description="Square cell dimension in meters")
    rows: int = Field(..., gt=0, description="Number of grid rows along Y")
    columns: int = Field(..., gt=0, description="Number of grid columns along X")
    origin: Point2D = Field(default_factory=lambda: Point2D(x=0.0, y=0.0))
    department_blocks: Dict[str, GridDepartmentBlock] = Field(default_factory=dict)
    occupancy_matrix: List[List[Optional[str]]] = Field(default_factory=list)

    @property
    def blocks(self) -> Dict[str, GridDepartmentBlock]:
        """Convenience alias for department_blocks."""
        return self.department_blocks

    @model_validator(mode="before")
    @classmethod
    def pre_validate_grid_layout(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "blocks" in data and "department_blocks" not in data:
                data["department_blocks"] = data["blocks"]
            cell_sz = float(data.get("cell_size", 5.0))
            if "facility_width" not in data and "columns" in data:
                data["facility_width"] = float(data["columns"]) * cell_sz
            if "facility_height" not in data and "rows" in data:
                data["facility_height"] = float(data["rows"]) * cell_sz
        return data

    @model_validator(mode="after")
    def initialize_occupancy_matrix(self) -> "GridLayout":
        """Ensure occupancy matrix matches dimensions and block registrations."""
        if not self.occupancy_matrix or len(self.occupancy_matrix) != self.rows or len(self.occupancy_matrix[0]) != self.columns:
            # Initialize empty matrix
            matrix: List[List[Optional[str]]] = [[None for _ in range(self.columns)] for _ in range(self.rows)]
            # Fill from blocks
            for dept_id, block in self.department_blocks.items():
                for r, c in block.cells:
                    if 0 <= r < self.rows and 0 <= c < self.columns:
                        matrix[r][c] = dept_id
            self.occupancy_matrix = matrix
        return self

    def get_department_ids(self) -> List[str]:
        return sorted(list(self.department_blocks.keys()))

    def get_bounding_box(self, dept_id: str) -> Optional[BoundingBox]:
        block = self.department_blocks.get(dept_id)
        if not block:
            return None
        return block.bounding_box(self.cell_size, self.origin)

    def set_cell(self, row: int, col: int, department_id: Optional[str]) -> None:
        """Assign or clear a grid cell occupancy."""
        if not (0 <= row < self.rows and 0 <= col < self.columns):
            raise IndexError(f"Cell ({row}, {col}) is out of bounds for grid {self.rows}x{self.columns}.")
        
        old_id = self.occupancy_matrix[row][col]
        if old_id and old_id in self.department_blocks:
            self.department_blocks[old_id].cells = [
                cell for cell in self.department_blocks[old_id].cells if cell != (row, col)
            ]

        self.occupancy_matrix[row][col] = department_id
        if department_id:
            if department_id not in self.department_blocks:
                self.department_blocks[department_id] = GridDepartmentBlock(department_id=department_id)
            if (row, col) not in self.department_blocks[department_id].cells:
                self.department_blocks[department_id].cells.append((row, col))

    def get_cell(self, row: int, col: int) -> Optional[str]:
        """Query occupancy of a grid cell."""
        if 0 <= row < self.rows and 0 <= col < self.columns:
            return self.occupancy_matrix[row][col]
        return None

    def to_numpy(self) -> np.ndarray:
        """Return NumPy array view of occupancy (empty cells as empty string '')."""
        arr = np.empty((self.rows, self.columns), dtype=object)
        for r in range(self.rows):
            for c in range(self.columns):
                arr[r, c] = self.occupancy_matrix[r][c] or ""
        return arr

    @property
    def numpy_matrix(self) -> np.ndarray:
        """Convenience property returning NumPy array view of occupancy."""
        return self.to_numpy()

