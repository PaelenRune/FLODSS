"""Spatial grid discretization and strip-sweep placement engine for ALDEP."""

import math
from typing import Dict, List, Optional, Set, Tuple

from app.algorithms.aldep.config import ALDEPConfig, SweepDirection
from app.algorithms.aldep.models import ALDEPDepartmentShapeDiagnostic
from app.models.geometry import BoundingBox, Point2D
from app.models.problem import FacilityLayoutProblem
from app.models.representation import (
    ContinuousLayout,
    ContinuousPlacement,
    GridLayout,
    GridDepartmentBlock,
)


def _mark_reserved_cells(
    problem: FacilityLayoutProblem,
    cell_size: float,
    rows: int,
    cols: int,
) -> Set[Tuple[int, int]]:
    """Identify grid cells intersecting facility reserved zones."""
    reserved_cells: Set[Tuple[int, int]] = set()
    zones = list(problem.facility.reserved_zones) if hasattr(problem.facility, "reserved_zones") else []

    for zone in zones:
        bbox = zone.bounding_box
        c_min = max(0, int(math.floor(bbox.x_min / cell_size)))
        c_max = min(cols - 1, int(math.floor((bbox.x_max - 1e-6) / cell_size)))
        r_min = max(0, int(math.floor(bbox.y_min / cell_size)))
        r_max = min(rows - 1, int(math.floor((bbox.y_max - 1e-6) / cell_size)))

        for r in range(r_min, r_max + 1):
            for c in range(c_min, c_max + 1):
                reserved_cells.add((r, c))

    return reserved_cells


def _build_serpentine_cell_sequence(
    rows: int,
    cols: int,
    config: ALDEPConfig,
    reserved_cells: Set[Tuple[int, int]],
    preoccupied_cells: Set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """Generate the ordered list of free grid cells following the strip-sweep path."""
    sequence: List[Tuple[int, int]] = []
    blocked = reserved_cells | preoccupied_cells

    if config.sweep_direction == SweepDirection.VERTICAL:
        strip_width = config.strip_width_cells
        num_strips = int(math.ceil(cols / strip_width))

        for s in range(num_strips):
            c_start = s * strip_width
            c_end = min((s + 1) * strip_width, cols)

            # Determine vertical traversal direction for this strip
            is_odd_strip = (s % 2 == 1)
            if config.serpentine_sweep and is_odd_strip:
                row_order = range(rows - 1, -1, -1)  # Top to bottom
            else:
                row_order = range(rows)              # Bottom to top

            for r in row_order:
                for c in range(c_start, c_end):
                    if (r, c) not in blocked:
                        sequence.append((r, c))

    else:  # SweepDirection.HORIZONTAL
        strip_height = config.strip_width_cells
        num_strips = int(math.ceil(rows / strip_height))

        for s in range(num_strips):
            r_start = s * strip_height
            r_end = min((s + 1) * strip_height, rows)

            # Determine horizontal traversal direction for this strip
            is_odd_strip = (s % 2 == 1)
            if config.serpentine_sweep and is_odd_strip:
                col_order = range(cols - 1, -1, -1)  # Right to left
            else:
                col_order = range(cols)              # Left to right

            for c in col_order:
                for r in range(r_start, r_end):
                    if (r, c) not in blocked:
                        sequence.append((r, c))

    return sequence


def create_strip_sweep_layout(
    problem: FacilityLayoutProblem,
    department_order: List[str],
    config: ALDEPConfig,
) -> Tuple[
    GridLayout,
    ContinuousLayout,
    Dict[str, ALDEPDepartmentShapeDiagnostic],
    List[str],
]:
    """Execute strip-sweep placement for ordered departments on a discretized facility grid.
    
    Returns:
        Tuple of (GridLayout, ContinuousLayout, shape_diagnostics_dict, unplaced_department_ids).
    """
    cell_size = config.cell_size
    cols = max(1, int(round(problem.facility.width / cell_size)))
    rows = max(1, int(round(problem.facility.height / cell_size)))

    reserved_cells = _mark_reserved_cells(problem, cell_size, rows, cols)
    preoccupied_cells: Set[Tuple[int, int]] = set()

    dept_map = {d.id: d for d in problem.departments}
    placed_blocks: Dict[str, GridDepartmentBlock] = {}
    occupancy_matrix: List[List[Optional[str]]] = [[None for _ in range(cols)] for _ in range(rows)]

    # 1. Position pre-fixed departments if any
    for d in problem.departments:
        if d.fixed_position is not None:
            w = d.min_width or math.sqrt(d.required_area)
            h = d.required_area / w
            c_start = max(0, int(round(d.fixed_position.x / cell_size)))
            c_end = min(cols, max(c_start + 1, int(round((d.fixed_position.x + w) / cell_size))))
            r_start = max(0, int(round(d.fixed_position.y / cell_size)))
            r_end = min(rows, max(r_start + 1, int(round((d.fixed_position.y + h) / cell_size))))

            f_cells = []
            for r in range(r_start, r_end):
                for c in range(c_start, c_end):
                    f_cells.append((r, c))
                    preoccupied_cells.add((r, c))
                    occupancy_matrix[r][c] = d.id

            placed_blocks[d.id] = GridDepartmentBlock(department_id=d.id, cells=f_cells)

    unplaced_departments: List[str] = []

    # 2. Place queued departments along the sweep
    if config.allow_strip_splitting:
        # Classical ALDEP: Continuous serpentine cell-by-cell allocation
        free_cells = _build_serpentine_cell_sequence(
            rows=rows,
            cols=cols,
            config=config,
            reserved_cells=reserved_cells,
            preoccupied_cells=preoccupied_cells,
        )

        cell_cursor = 0
        total_free_cells = len(free_cells)

        for dept_id in department_order:
            if dept_id in placed_blocks:
                continue

            dept = dept_map.get(dept_id)
            if not dept:
                continue

            req_cells = max(1, int(round(dept.required_area / (cell_size ** 2))))
            if cell_cursor + req_cells > total_free_cells:
                # Capacity exceeded: department cannot be fully accommodated
                unplaced_departments.append(dept_id)
                continue

            dept_cells: List[Tuple[int, int]] = []
            for _ in range(req_cells):
                r, c = free_cells[cell_cursor]
                dept_cells.append((r, c))
                occupancy_matrix[r][c] = dept_id
                cell_cursor += 1

            placed_blocks[dept_id] = GridDepartmentBlock(department_id=dept_id, cells=dept_cells)

    else:
        # Rectangular strip adaptation (no splitting across strips)
        blocked = reserved_cells | preoccupied_cells
        strip_width = config.strip_width_cells

        if config.sweep_direction == SweepDirection.VERTICAL:
            num_strips = int(math.ceil(cols / strip_width))
            current_strip = 0
            current_row = 0

            for dept_id in department_order:
                if dept_id in placed_blocks:
                    continue
                dept = dept_map.get(dept_id)
                if not dept:
                    continue

                req_cells = max(1, int(round(dept.required_area / (cell_size ** 2))))

                # Check if department fits in current strip
                placed = False
                while current_strip < num_strips:
                    actual_strip_width = min(strip_width, cols - current_strip * strip_width)
                    if actual_strip_width <= 0:
                        break
                    rows_needed = int(math.ceil(req_cells / actual_strip_width))

                    if current_row + rows_needed <= rows:
                        # Allocate cells
                        c_start = current_strip * strip_width
                        c_end = min(c_start + strip_width, cols)
                        d_cells = []
                        cells_count = 0

                        # Determine row sweep direction for strip
                        if config.serpentine_sweep and (current_strip % 2 == 1):
                            # Top to bottom in strip
                            r_start = (rows - 1) - current_row
                            r_end = r_start - rows_needed
                            row_indices = range(r_start, r_end, -1)
                        else:
                            # Bottom to top
                            r_start = current_row
                            r_end = current_row + rows_needed
                            row_indices = range(r_start, r_end)

                        for r in row_indices:
                            for c in range(c_start, c_end):
                                if (r, c) not in blocked and cells_count < req_cells:
                                    d_cells.append((r, c))
                                    occupancy_matrix[r][c] = dept_id
                                    cells_count += 1

                        if cells_count == req_cells:
                            placed_blocks[dept_id] = GridDepartmentBlock(department_id=dept_id, cells=d_cells)
                            current_row += rows_needed
                            placed = True
                            break
                        else:
                            # Revert any partial cells if blocked
                            for r, c in d_cells:
                                occupancy_matrix[r][c] = None
                            current_strip += 1
                            current_row = 0
                    else:
                        current_strip += 1
                        current_row = 0

                if not placed:
                    unplaced_departments.append(dept_id)

        else:  # Horizontal strips adaptation
            num_strips = int(math.ceil(rows / strip_width))
            current_strip = 0
            current_col = 0

            for dept_id in department_order:
                if dept_id in placed_blocks:
                    continue
                dept = dept_map.get(dept_id)
                if not dept:
                    continue

                req_cells = max(1, int(round(dept.required_area / (cell_size ** 2))))

                placed = False
                while current_strip < num_strips:
                    actual_strip_height = min(strip_width, rows - current_strip * strip_width)
                    if actual_strip_height <= 0:
                        break
                    cols_needed = int(math.ceil(req_cells / actual_strip_height))

                    if current_col + cols_needed <= cols:
                        r_start = current_strip * strip_width
                        r_end = min(r_start + strip_width, rows)
                        d_cells = []
                        cells_count = 0

                        if config.serpentine_sweep and (current_strip % 2 == 1):
                            c_start = (cols - 1) - current_col
                            c_end = c_start - cols_needed
                            col_indices = range(c_start, c_end, -1)
                        else:
                            c_start = current_col
                            c_end = current_col + cols_needed
                            col_indices = range(c_start, c_end)

                        for c in col_indices:
                            for r in range(r_start, r_end):
                                if (r, c) not in blocked and cells_count < req_cells:
                                    d_cells.append((r, c))
                                    occupancy_matrix[r][c] = dept_id
                                    cells_count += 1

                        if cells_count == req_cells:
                            placed_blocks[dept_id] = GridDepartmentBlock(department_id=dept_id, cells=d_cells)
                            current_col += cols_needed
                            placed = True
                            break
                        else:
                            for r, c in d_cells:
                                occupancy_matrix[r][c] = None
                            current_strip += 1
                            current_col = 0
                    else:
                        current_strip += 1
                        current_col = 0

                if not placed:
                    unplaced_departments.append(dept_id)

    # 3. Construct ContinuousLayout and calculate shape diagnostics
    placements: Dict[str, ContinuousPlacement] = {}
    shape_diagnostics: Dict[str, ALDEPDepartmentShapeDiagnostic] = {}

    for dept_id, block in placed_blocks.items():
        dept = dept_map.get(dept_id)
        if not dept:
            continue

        bbox = block.bounding_box(cell_size, Point2D(x=0.0, y=0.0))
        if not bbox:
            continue

        placements[dept_id] = ContinuousPlacement(
            department_id=dept_id,
            x=bbox.x_min,
            y=bbox.y_min,
            width=bbox.width,
            height=bbox.height,
        )

        allocated_cells = block.cell_count
        allocated_area = allocated_cells * (cell_size ** 2)
        area_error = abs(allocated_area - dept.required_area)
        area_error_pct = (area_error / dept.required_area * 100.0) if dept.required_area > 0 else 0.0

        bbox_cells = int(round((bbox.width * bbox.height) / (cell_size ** 2)))
        is_rectangular = (allocated_cells == bbox_cells)

        min_dim = min(bbox.width, bbox.height)
        aspect_ratio = (max(bbox.width, bbox.height) / min_dim) if min_dim > 0 else 1.0

        shape_diagnostics[dept_id] = ALDEPDepartmentShapeDiagnostic(
            department_id=dept_id,
            required_area=dept.required_area,
            allocated_cells=allocated_cells,
            allocated_area=allocated_area,
            area_error=round(area_error, 4),
            area_error_pct=round(area_error_pct, 2),
            bounding_box=bbox,
            is_rectangular=is_rectangular,
            aspect_ratio=round(aspect_ratio, 2),
            grid_cells=list(block.cells),
        )

    grid_layout = GridLayout(
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
        cell_size=cell_size,
        rows=rows,
        columns=cols,
        department_blocks=placed_blocks,
        occupancy_matrix=occupancy_matrix,
        reserved_zones=problem.facility.reserved_zones if hasattr(problem.facility, "reserved_zones") else [],
    )

    continuous_layout = ContinuousLayout(
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
        placements=placements,
        reserved_zones=problem.facility.reserved_zones if hasattr(problem.facility, "reserved_zones") else [],
    )

    return grid_layout, continuous_layout, shape_diagnostics, unplaced_departments
