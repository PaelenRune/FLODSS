"""Detection of usable free rectangular regions in continuous facility layouts."""

from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.feasibility.models import FreeRectangle, FreeSpaceReport
from app.models.geometry import BoundingBox, ReservedZone
from app.models.representation import ContinuousPlacement


class FreeRectangleDetector:
    """Discovers all maximal empty rectangular regions available for department placement.
    
    Academic Note on Maximal Empty Rectangles (MER):
        Free rectangles frequently overlap because each represents an alternative maximal 
        candidate placement region (e.g. full-height strip vs full-width corridor).
        Their areas MUST NOT be summed to calculate total free area. 
        Total net free area is computed directly as:
            facility_total_area - occupied_area
    """

    @classmethod
    def detect_free_rectangles(
        cls,
        facility_width: float,
        facility_height: float,
        placements: List[Union[ContinuousPlacement, BoundingBox]],
        reserved_zones: Optional[List[Union[ReservedZone, BoundingBox]]] = None,
        min_area_threshold: float = 1.0,
        tolerance: float = 1e-4,
    ) -> FreeSpaceReport:
        """Scan plant space and return maximal empty rectangles and capacity diagnostics."""
        fac_area = facility_width * facility_height

        # 1. Normalize blocked boxes
        blocked_boxes: List[BoundingBox] = []
        for p in placements:
            if isinstance(p, ContinuousPlacement):
                blocked_boxes.append(p.bounding_box)
            elif isinstance(p, BoundingBox):
                blocked_boxes.append(p)

        if reserved_zones:
            for rz in reserved_zones:
                if isinstance(rz, ReservedZone):
                    blocked_boxes.append(rz.bounding_box)
                elif isinstance(rz, BoundingBox):
                    blocked_boxes.append(rz)

        # Clip blocked boxes to facility boundaries
        clipped_boxes: List[BoundingBox] = []
        for b in blocked_boxes:
            c_xmin = max(0.0, min(facility_width, b.x_min))
            c_ymin = max(0.0, min(facility_height, b.y_min))
            c_xmax = max(0.0, min(facility_width, b.x_max))
            c_ymax = max(0.0, min(facility_height, b.y_max))
            if c_xmax > c_xmin + tolerance and c_ymax > c_ymin + tolerance:
                clipped_boxes.append(BoundingBox(x_min=c_xmin, y_min=c_ymin, x_max=c_xmax, y_max=c_ymax))

        # If plant is completely empty, the whole plant is the single maximal empty rectangle
        if not clipped_boxes:
            whole_plant = FreeRectangle(
                x_min=0.0,
                y_min=0.0,
                x_max=facility_width,
                y_max=facility_height,
            )
            return FreeSpaceReport(
                facility_width=facility_width,
                facility_height=facility_height,
                facility_total_area=round(fac_area, 2),
                occupied_area=0.0,
                net_free_area=round(fac_area, 2),
                free_rectangles=[whole_plant],
                largest_free_rectangle_area=round(fac_area, 2),
                fragmentation_index=0.0,
            )

        # 2. Extract orthogonal coordinate cutlines
        x_coords_set: Set[float] = {0.0, facility_width}
        y_coords_set: Set[float] = {0.0, facility_height}

        for b in clipped_boxes:
            x_coords_set.add(round(b.x_min, 4))
            x_coords_set.add(round(b.x_max, 4))
            y_coords_set.add(round(b.y_min, 4))
            y_coords_set.add(round(b.y_max, 4))

        sorted_x = sorted(list(x_coords_set))
        sorted_y = sorted(list(y_coords_set))

        # Filter out negligible intervals
        x_intervals: List[Tuple[float, float]] = []
        for i in range(len(sorted_x) - 1):
            if sorted_x[i + 1] - sorted_x[i] > tolerance:
                x_intervals.append((sorted_x[i], sorted_x[i + 1]))

        y_intervals: List[Tuple[float, float]] = []
        for j in range(len(sorted_y) - 1):
            if sorted_y[j + 1] - sorted_y[j] > tolerance:
                y_intervals.append((sorted_y[j], sorted_y[j + 1]))

        num_cols = len(x_intervals)
        num_rows = len(y_intervals)

        if num_cols == 0 or num_rows == 0:
            return FreeSpaceReport(
                facility_width=facility_width,
                facility_height=facility_height,
                facility_total_area=round(fac_area, 2),
                occupied_area=round(fac_area, 2),
                net_free_area=0.0,
                free_rectangles=[],
                largest_free_rectangle_area=0.0,
                fragmentation_index=1.0,
            )

        # 3. Build 2D elementary occupancy grid
        # grid[row][col] is True if free, False if occupied
        grid: List[List[bool]] = [[True for _ in range(num_cols)] for _ in range(num_rows)]
        occupied_area = 0.0

        for r_idx, (y1, y2) in enumerate(y_intervals):
            y_mid = (y1 + y2) / 2.0
            cell_h = y2 - y1
            for c_idx, (x1, x2) in enumerate(x_intervals):
                x_mid = (x1 + x2) / 2.0
                cell_w = x2 - x1
                # Check if cell center is covered by any blocked box
                for b in clipped_boxes:
                    if (b.x_min - tolerance <= x_mid <= b.x_max + tolerance) and (
                        b.y_min - tolerance <= y_mid <= b.y_max + tolerance
                    ):
                        grid[r_idx][c_idx] = False
                        occupied_area += cell_w * cell_h
                        break

        net_free_area = max(0.0, fac_area - occupied_area)

        # 4. Find all Maximal Empty Rectangles (MER) via 2D row-sweep
        # Precompute contiguous column spans for row pairs
        mer_candidates: Set[Tuple[int, int, int, int]] = set()  # (c_start, r_start, c_end, r_end)

        for r1 in range(num_rows):
            # Track contiguous free column status across rows r1..r2
            combined_row = [True] * num_cols
            for r2 in range(r1, num_rows):
                for c in range(num_cols):
                    if not grid[r2][c]:
                        combined_row[c] = False

                # Find maximal contiguous free column intervals in combined_row
                c_start = None
                for c in range(num_cols):
                    if combined_row[c]:
                        if c_start is None:
                            c_start = c
                    else:
                        if c_start is not None:
                            # Potential candidate [c_start, c - 1] across [r1, r2]
                            mer_candidates.add((c_start, r1, c - 1, r2))
                            c_start = None
                if c_start is not None:
                    mer_candidates.add((c_start, r1, num_cols - 1, r2))

        # 5. Filter for true maximality in all 4 directions
        # A candidate is maximal if it cannot be extended left, right, down, or up
        maximal_rectangles: List[FreeRectangle] = []

        for c_start, r_start, c_end, r_end in mer_candidates:
            # Check left extension: can all rows [r_start, r_end] be extended to c_start - 1?
            if c_start > 0:
                can_extend_left = all(grid[r][c_start - 1] for r in range(r_start, r_end + 1))
                if can_extend_left:
                    continue

            # Check right extension: can all rows [r_start, r_end] be extended to c_end + 1?
            if c_end < num_cols - 1:
                can_extend_right = all(grid[r][c_end + 1] for r in range(r_start, r_end + 1))
                if can_extend_right:
                    continue

            # Check bottom extension: can all cols [c_start, c_end] be extended to r_start - 1?
            if r_start > 0:
                can_extend_down = all(grid[r_start - 1][c] for c in range(c_start, c_end + 1))
                if can_extend_down:
                    continue

            # Check top extension: can all cols [c_start, c_end] be extended to r_end + 1?
            if r_end < num_rows - 1:
                can_extend_up = all(grid[r_end + 1][c] for c in range(c_start, c_end + 1))
                if can_extend_up:
                    continue

            # This rectangle is strictly maximal!
            rect_x_min = x_intervals[c_start][0]
            rect_x_max = x_intervals[c_end][1]
            rect_y_min = y_intervals[r_start][0]
            rect_y_max = y_intervals[r_end][1]

            rect_area = (rect_x_max - rect_x_min) * (rect_y_max - rect_y_min)
            if rect_area >= min_area_threshold:
                maximal_rectangles.append(
                    FreeRectangle(
                        x_min=round(rect_x_min, 2),
                        y_min=round(rect_y_min, 2),
                        x_max=round(rect_x_max, 2),
                        y_max=round(rect_y_max, 2),
                    )
                )

        # Sort maximal rectangles by area descending, then coordinates
        maximal_rectangles.sort(key=lambda r: (-r.area, r.x_min, r.y_min))

        largest_area = maximal_rectangles[0].area if maximal_rectangles else 0.0

        # Fragmentation index: 1.0 - (largest_free_rect / net_free_area) if net_free_area > 0
        if net_free_area > tolerance:
            fragmentation = max(0.0, min(1.0, 1.0 - (largest_area / net_free_area)))
        else:
            fragmentation = 0.0

        return FreeSpaceReport(
            facility_width=round(facility_width, 2),
            facility_height=round(facility_height, 2),
            facility_total_area=round(fac_area, 2),
            occupied_area=round(occupied_area, 2),
            net_free_area=round(net_free_area, 2),
            free_rectangles=maximal_rectangles,
            largest_free_rectangle_area=round(largest_area, 2),
            fragmentation_index=round(fragmentation, 4),
        )
