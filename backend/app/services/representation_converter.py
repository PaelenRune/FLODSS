"""Converters between Continuous Rectangular and Discrete Grid layout representations."""

import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, computed_field

from app.models.geometry import Point2D, Dimensions2D, BoundingBox
from app.models.representation import (
    BaseLayoutRepresentation,
    ContinuousLayout,
    ContinuousPlacement,
    GridLayout,
    GridDepartmentBlock,
)


class ConversionResult(BaseModel):
    """Encapsulates outcome, discretization errors, and warnings from representation conversions."""

    representation: Any = Field(..., description="Target layout representation instance")
    is_exact: bool = Field(..., description="True if no area or dimensional distortion occurred")
    area_errors: Dict[str, float] = Field(
        default_factory=dict,
        description="Absolute deviation between original and converted area per department",
    )
    dimensional_errors: Dict[str, float] = Field(
        default_factory=dict,
        description="Maximum coordinate boundary difference per department",
    )
    warnings: List[str] = Field(default_factory=list, description="Non-fatal conversion advisories")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def grid_layout(self) -> Optional[GridLayout]:
        if isinstance(self.representation, GridLayout):
            return self.representation
        return None

    @computed_field
    @property
    def continuous_layout(self) -> Optional[ContinuousLayout]:
        if isinstance(self.representation, ContinuousLayout):
            return self.representation
        return None


class ContinuousToGridConverter:
    """Converts continuous rectangular coordinates into a discrete occupancy grid."""

    def __init__(self, cell_size: float = 5.0):
        self.cell_size = cell_size

    def __call__(self, layout: ContinuousLayout, cell_size: Optional[float] = None) -> ConversionResult:
        return self.convert(layout, cell_size)

    @classmethod
    def convert(
        cls_or_self,
        layout: ContinuousLayout,
        cell_size: Optional[float] = None,
    ) -> ConversionResult:
        if isinstance(cls_or_self, ContinuousToGridConverter):
            actual_cell_size = cell_size if cell_size is not None else cls_or_self.cell_size
        else:
            actual_cell_size = cell_size if cell_size is not None else 5.0

        if actual_cell_size <= 0:
            raise ValueError(f"cell_size must be positive, got {actual_cell_size}.")

        cell_size = actual_cell_size

        cols = int(math.ceil(layout.facility_width / actual_cell_size))
        rows = int(math.ceil(layout.facility_height / actual_cell_size))

        department_blocks: Dict[str, GridDepartmentBlock] = {}
        occupancy_matrix: List[List[Optional[str]]] = [[None for _ in range(cols)] for _ in range(rows)]
        area_errors: Dict[str, float] = {}
        dimensional_errors: Dict[str, float] = {}
        warnings: List[str] = []

        is_exact = True

        for dept_id, placement in layout.placements.items():
            # Compute cell bounds based on cell_size
            col_start = max(0, int(round(placement.x / cell_size)))
            col_end = min(cols, int(round((placement.x + placement.width) / cell_size)))
            row_start = max(0, int(round(placement.y / cell_size)))
            row_end = min(rows, int(round((placement.y + placement.height) / cell_size)))

            # Guarantee at least 1 cell in each dimension if placement is non-zero
            if col_end <= col_start:
                col_end = min(cols, col_start + 1)
            if row_end <= row_start:
                row_end = min(rows, row_start + 1)

            cells = []
            for r in range(row_start, row_end):
                for c in range(col_start, col_end):
                    if occupancy_matrix[r][c] is not None and occupancy_matrix[r][c] != dept_id:
                        warnings.append(
                            f"Cell ({r}, {c}) overlap between '{occupancy_matrix[r][c]}' and '{dept_id}' during grid discretization."
                        )
                        is_exact = False
                    occupancy_matrix[r][c] = dept_id
                    cells.append((r, c))

            department_blocks[dept_id] = GridDepartmentBlock(department_id=dept_id, cells=cells)

            # Compute discrepancies
            discrete_area = len(cells) * (cell_size ** 2)
            original_area = placement.area
            area_err = abs(discrete_area - original_area)
            area_errors[dept_id] = round(area_err, 4)

            # Max boundary deviation
            disc_width = (col_end - col_start) * cell_size
            disc_height = (row_end - row_start) * cell_size
            dim_err = max(abs(disc_width - placement.width), abs(disc_height - placement.height))
            dimensional_errors[dept_id] = round(dim_err, 4)

            if area_err > 1e-4 or dim_err > 1e-4:
                is_exact = False
                if area_err > 0.05 * original_area:
                    warnings.append(
                        f"Department '{dept_id}' area changed by {area_err:.1f} m² ({(area_err/original_area)*100:.1f}%) due to grid resolution ({cell_size}m)."
                    )

        grid_layout = GridLayout(
            facility_width=layout.facility_width,
            facility_height=layout.facility_height,
            cell_size=cell_size,
            rows=rows,
            columns=cols,
            department_blocks=department_blocks,
            occupancy_matrix=occupancy_matrix,
            reserved_zones=layout.reserved_zones,
        )

        return ConversionResult(
            representation=grid_layout,
            is_exact=is_exact,
            area_errors=area_errors,
            dimensional_errors=dimensional_errors,
            warnings=warnings,
            metadata={"cell_size": cell_size, "rows": rows, "columns": cols},
        )


class GridToContinuousConverter:
    """Converts discrete occupancy grid blocks back into continuous rectangular placements."""

    def __init__(self):
        pass

    def __call__(self, layout: GridLayout) -> ConversionResult:
        return self.convert(layout)

    @classmethod
    def convert(cls_or_self, layout: GridLayout) -> ConversionResult:
        placements: Dict[str, ContinuousPlacement] = {}
        area_errors: Dict[str, float] = {}
        dimensional_errors: Dict[str, float] = {}
        warnings: List[str] = []
        is_exact = True

        for dept_id, block in layout.department_blocks.items():
            bbox = block.bounding_box(layout.cell_size, layout.origin)
            if not bbox:
                warnings.append(f"Department '{dept_id}' occupies no cells in grid.")
                is_exact = False
                continue

            placements[dept_id] = ContinuousPlacement(
                department_id=dept_id,
                x=bbox.x_min,
                y=bbox.y_min,
                width=bbox.width,
                height=bbox.height,
            )

            # Check if block is rectangularly contiguous
            bbox_cells_count = int(round(bbox.area / (layout.cell_size ** 2)))
            if block.cell_count != bbox_cells_count:
                is_exact = False
                warnings.append(
                    f"Department '{dept_id}' is non-rectangular or fragmented in grid ({block.cell_count} cells vs {bbox_cells_count} in bounding box)."
                )

            area_errors[dept_id] = abs(bbox.area - block.area(layout.cell_size))
            dimensional_errors[dept_id] = 0.0

        continuous_layout = ContinuousLayout(
            facility_width=layout.facility_width,
            facility_height=layout.facility_height,
            placements=placements,
            reserved_zones=layout.reserved_zones,
        )

        return ConversionResult(
            representation=continuous_layout,
            is_exact=is_exact,
            area_errors=area_errors,
            dimensional_errors=dimensional_errors,
            warnings=warnings,
        )
