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


def _place_rectangular_blocks(
    rows: int,
    cols: int,
    config: ALDEPConfig,
    blocked: Set[Tuple[int, int]],
    department_order: List[str],
    dept_map: Dict,
    occupancy_matrix: List[List[Optional[str]]],
    placed_blocks: Dict[str, GridDepartmentBlock],
) -> List[str]:
    """FLODSS rectangular adaptation: place each department as a solid block inside the strip grid.

    Each department receives a rectangular block spanning ``k`` adjacent strips (``k`` as small as
    possible, so normally a single strip) placed first-fit along the sweep direction of its first
    strip. The whole block is reserved, so continuous bounding boxes can never overlap.

    Search starts at the strip of the previously placed department (preserving the ALDEP sweep
    locality) and then wraps around to reuse leftover space. A department that fits nowhere is
    reported as unplaced without consuming the sweep cursor, so later departments still get a
    chance to be placed.

    Returns:
        List of unplaced department IDs.
    """
    vertical = config.sweep_direction == SweepDirection.VERTICAL
    lanes_total = cols if vertical else rows      # axis across strips
    along_total = rows if vertical else cols      # axis along a strip
    strip_width = config.strip_width_cells
    num_strips = int(math.ceil(lanes_total / strip_width))
    cell_size = config.cell_size

    def cell(lane: int, along: int) -> Tuple[int, int]:
        return (along, lane) if vertical else (lane, along)

    used: Set[Tuple[int, int]] = set(blocked)
    current_strip = 0
    unplaced: List[str] = []

    for dept_id in department_order:
        dept = dept_map.get(dept_id)
        if not dept:
            continue
        req_cells = max(1, int(round(dept.required_area / (cell_size ** 2))))

        def shape_ok(lanes: int, length: int) -> bool:
            """True when a lanes x length block meets the department's dimension / aspect limits."""
            across_m, along_m = lanes * cell_size, length * cell_size
            w, h = (across_m, along_m) if vertical else (along_m, across_m)
            tol = 1e-6
            if dept.min_width is not None and w < dept.min_width - tol:
                return False
            if dept.max_width is not None and w > dept.max_width + tol:
                return False
            if dept.min_height is not None and h < dept.min_height - tol:
                return False
            if dept.max_height is not None and h > dept.max_height + tol:
                return False
            if dept.max_aspect_ratio is not None and max(w, h) / max(min(w, h), tol) > dept.max_aspect_ratio + 1e-3:
                return False
            return True

        def try_place(s: int, k: int) -> bool:
            lane_start = s * strip_width
            lane_end = min((s + k) * strip_width, lanes_total)
            width = lane_end - lane_start
            length = int(math.ceil(req_cells / width))
            if length > along_total:
                return False
            reverse = config.serpentine_sweep and s % 2 == 1  # odd strips sweep the other way
            starts = range(along_total - length, -1, -1) if reverse else range(0, along_total - length + 1)
            for a0 in starts:
                along_seq = range(a0 + length - 1, a0 - 1, -1) if reverse else range(a0, a0 + length)
                block = [cell(lane, a) for a in along_seq for lane in range(lane_start, lane_end)]
                if any(c in used for c in block):
                    continue
                dept_cells = block[:req_cells]
                used.update(block)  # reserve the full rectangle, including a partial last row
                for r, c in dept_cells:
                    occupancy_matrix[r][c] = dept_id
                placed_blocks[dept_id] = GridDepartmentBlock(department_id=dept_id, cells=dept_cells)
                return True
            return False

        def span_shape_ok(s: int, k: int) -> bool:
            width = min((s + k) * strip_width, lanes_total) - s * strip_width
            return shape_ok(width, int(math.ceil(req_cells / width)))

        # Pass 1: only spans whose block respects the department's shape limits.
        # Pass 2 (fallback): any span that fits, so the department is still placed if possible.
        strip_order = list(range(current_strip, num_strips)) + list(range(0, current_strip))
        placed = False
        for require_shape in (True, False):
            for s in strip_order:
                for k in range(1, num_strips - s + 1):
                    if require_shape and not span_shape_ok(s, k):
                        continue
                    if try_place(s, k):
                        current_strip = s
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break

        if not placed:
            unplaced.append(dept_id)

    return unplaced


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

    When ``config.allow_strip_splitting`` is None (AUTO), the overlap-free rectangular adaptation is
    tried first; classical strip splitting is used only if it places strictly more departments.
    """
    if config.allow_strip_splitting is None:
        rect = create_strip_sweep_layout(
            problem, department_order, config.model_copy(update={"allow_strip_splitting": False})
        )
        if not rect[3]:
            return rect
        split = create_strip_sweep_layout(
            problem, department_order, config.model_copy(update={"allow_strip_splitting": True})
        )
        return split if len(split[3]) < len(rect[3]) else rect

    cell_size = config.cell_size
    # Floor (not round): a partially covered trailing cell would extend the grid past the
    # facility boundary (e.g. 48 m / 5 m -> round = 10 cells = 50 m). The epsilon keeps exact
    # multiples (50 m / 5 m) from losing a cell to floating-point error.
    cols = max(1, int(math.floor(problem.facility.width / cell_size + 1e-9)))
    rows = max(1, int(math.floor(problem.facility.height / cell_size + 1e-9)))

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
        unplaced_departments.extend(
            _place_rectangular_blocks(
                rows=rows,
                cols=cols,
                config=config,
                blocked=reserved_cells | preoccupied_cells,
                department_order=[d for d in department_order if d not in placed_blocks],
                dept_map=dept_map,
                occupancy_matrix=occupancy_matrix,
                placed_blocks=placed_blocks,
            )
        )

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
