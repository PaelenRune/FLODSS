"""Geometry helpers for CORELAP: department sizing, legal shapes, and candidate placement generation."""

import math
from typing import Any, Dict, List, Optional, Set, Tuple
from app.models.geometry import BoundingBox, ReservedZone
from app.models.department import Department
from app.models.representation import ContinuousPlacement
from app.services.geometry_engine import GeometryEngine
from app.algorithms.corelap.config import CORELAPConfig, InitialAnchorMode, TraceLevel


def determine_department_dimensions(
    dept: Department, config: Optional[CORELAPConfig] = None
) -> Tuple[float, float]:
    """Calculate baseline rectangular dimensions (width, height) satisfying department area and constraints.
    
    Adheres to:
        1. width * height == required_area
        2. min_width, max_width, min_height, max_height constraints
        3. min_aspect_ratio and max_aspect_ratio bounds
        4. Target square-ish aspect ratio (~1.0)
    """
    cfg = config or CORELAPConfig()
    area = dept.required_area
    if area <= 0:
        raise ValueError(f"Department '{dept.id}' has non-positive area ({area}).")

    target_ratio = cfg.aspect_ratio_target or 1.0
    w = math.sqrt(area * target_ratio)
    h = area / w

    if dept.min_width is not None and w < dept.min_width:
        w = dept.min_width
        h = area / w
    if dept.max_width is not None and w > dept.max_width:
        w = dept.max_width
        h = area / w

    if dept.min_height is not None and h < dept.min_height:
        h = dept.min_height
        w = area / h
    if dept.max_height is not None and h > dept.max_height:
        h = dept.max_height
        w = area / h

    if dept.min_width is not None and w < dept.min_width:
        w = dept.min_width
    if dept.max_width is not None and w > dept.max_width:
        w = dept.max_width

    aspect = max(w, h) / min(w, h)
    if dept.max_aspect_ratio is not None and aspect > dept.max_aspect_ratio:
        if w > h:
            w = math.sqrt(area * dept.max_aspect_ratio)
            h = area / w
        else:
            h = math.sqrt(area * dept.max_aspect_ratio)
            w = area / h

    if dept.fixed_orientation in (90.0, 270.0):
        w, h = h, w

    return round(w, 2), round(h, 2)


def generate_legal_department_shapes(
    dept: Department,
    placed_placements: Dict[str, ContinuousPlacement],
    facility_width: float,
    facility_height: float,
    config: Optional[CORELAPConfig] = None,
) -> List[Tuple[float, float, float]]:
    """Generate a small, deterministic, bounded set of legal rectangular shapes (width, height, orientation_degrees).
    
    Considers:
        1. Square-ish baseline shape
        2. Department min_width / max_width / min_height / max_height limits
        3. Placed neighbor dimensions (matching height or width)
        4. Standard facility divisions (e.g. half-height strips)
        5. 0° and 90° orientation variants where permitted
        
    Returns:
        Deduplicated, deterministically ordered list of (width, height, orientation_degrees).
    """
    cfg = config or CORELAPConfig()
    area = dept.required_area
    min_w = dept.min_width or 1.0
    max_w = dept.max_width or facility_width
    min_h = dept.min_height or 1.0
    max_h = dept.max_height or facility_height
    max_ar = dept.max_aspect_ratio or 4.0

    shapes_set: Set[Tuple[float, float, float]] = set()

    def try_add_shape(candidate_w: float, candidate_h: float, orient: float = 0.0) -> None:
        cw = round(candidate_w, 2)
        ch = round(candidate_h, 2)
        if cw < min_w - 1e-4 or cw > max_w + 1e-4:
            return
        if ch < min_h - 1e-4 or ch > max_h + 1e-4:
            return
        if cw * ch <= 0:
            return
        ar = max(cw, ch) / min(cw, ch)
        if ar > max_ar + 1e-4:
            return
        shapes_set.add((cw, ch, orient))

    # 1. Base shape
    base_w, base_h = determine_department_dimensions(dept, cfg)
    try_add_shape(base_w, base_h, 0.0)

    # If shape alternatives are disabled, return base shape (with rotation if allowed)
    if not cfg.allow_shape_alternatives:
        if cfg.evaluate_orientations and dept.fixed_orientation is None and base_w != base_h:
            try_add_shape(base_h, base_w, 90.0)
        return sorted(list(shapes_set), key=lambda s: (abs(s[0] - s[1]), s[0], s[1], s[2]))

    # 2. Minimum and maximum legal widths
    if dept.min_width:
        try_add_shape(dept.min_width, area / dept.min_width, 0.0)
    if dept.max_width:
        try_add_shape(dept.max_width, area / dept.max_width, 0.0)
    if dept.min_height:
        try_add_shape(area / dept.min_height, dept.min_height, 0.0)
    if dept.max_height:
        try_add_shape(area / dept.max_height, dept.max_height, 0.0)

    # 3. Matching placed neighbor dimensions (edges)
    for p in placed_placements.values():
        if p.height > 0:
            try_add_shape(area / p.height, p.height, 0.0)
        if p.width > 0:
            try_add_shape(p.width, area / p.width, 0.0)

    # 4. Standard facility strip subdivisions
    if facility_height > 0:
        half_h = facility_height / 2.0
        try_add_shape(area / half_h, half_h, 0.0)
    if facility_width > 0:
        half_w = facility_width / 2.0
        try_add_shape(half_w, area / half_w, 0.0)

    # 5. Orientation variants (0° vs 90°)
    if cfg.evaluate_orientations and dept.fixed_orientation is None:
        for w, h, _ in list(shapes_set):
            if abs(w - h) > 1e-4:
                try_add_shape(h, w, 90.0)

    # Deterministic sorting: sort by deviation from square-ish, then width, then height, then orientation
    return sorted(list(shapes_set), key=lambda s: (round(abs(s[0] - s[1]), 3), s[0], s[1], s[2]))


def generate_candidate_placements(
    dept_id: str,
    width: float,
    height: float,
    placed_placements: Dict[str, ContinuousPlacement],
    facility_width: float,
    facility_height: float,
    config: CORELAPConfig,
    reserved_zones: Optional[List[ReservedZone]] = None,
    shapes: Optional[List[Tuple[float, float, float]]] = None,
) -> Tuple[List[ContinuousPlacement], Dict[str, int]]:
    """Generate and filter all valid contiguous candidate placements for a department.
    
    Supports:
        - Multi-shape candidate generation (when shapes list is provided)
        - Expanded candidate anchors: facility corners, placed edges, coordinate projections
        - Full geometric filtering: facility boundary, department overlap, reserved zones
        - Contiguity requirement: candidates must share a boundary with placed cluster
        
    Returns:
        Tuple of (Valid Candidate Placements, Rejection Reasons Summary)
    """
    tol = config.numerical_tolerance
    gap = config.candidate_gap
    step = config.step_grid_alignment
    res_zones = reserved_zones or []

    rejection_reasons = {
        "out_of_bounds": 0,
        "overlap_department": 0,
        "overlap_reserved_zone": 0,
        "not_adjacent": 0,
    }

    shape_list = shapes if shapes else [(width, height, 0.0)]
    valid_placements: List[ContinuousPlacement] = []
    seen_placements: Set[Tuple[float, float, float, float]] = set()

    for w, h, orient in shape_list:
        raw_candidates: List[Tuple[float, float]] = []

        # Case 1: First department to be placed
        if not placed_placements:
            if config.initial_anchor_mode == InitialAnchorMode.CENTER:
                init_x = max(0.0, (facility_width - w) / 2.0)
                init_y = max(0.0, (facility_height - h) / 2.0)
            else:
                init_x = 0.0
                init_y = 0.0

            if step and step > 0:
                init_x = round(init_x / step) * step
                init_y = round(init_y / step) * step

            raw_candidates.append((init_x, init_y))
        else:
            # Case 2: Subsequent department - generate candidates adjacent to placed departments
            # A. Direct border projections
            for p in placed_placements.values():
                p_box = p.bounding_box

                # Right of placed box
                x_right = p_box.x_max + gap
                raw_candidates.extend([
                    (x_right, p_box.y_min),
                    (x_right, p_box.y_max - h),
                    (x_right, p_box.y_min + (p.height - h) / 2.0),
                    (x_right, p_box.y_max),
                    (x_right, p_box.y_min - h),
                    (x_right, 0.0),
                    (x_right, facility_height - h),
                ])

                # Left of placed box
                x_left = p_box.x_min - w - gap
                raw_candidates.extend([
                    (x_left, p_box.y_min),
                    (x_left, p_box.y_max - h),
                    (x_left, p_box.y_min + (p.height - h) / 2.0),
                    (x_left, p_box.y_max),
                    (x_left, p_box.y_min - h),
                    (x_left, 0.0),
                    (x_left, facility_height - h),
                ])

                # Top of placed box
                y_top = p_box.y_max + gap
                raw_candidates.extend([
                    (p_box.x_min, y_top),
                    (p_box.x_max - w, y_top),
                    (p_box.x_min + (p.width - w) / 2.0, y_top),
                    (p_box.x_max, y_top),
                    (p_box.x_min - w, y_top),
                    (0.0, y_top),
                    (facility_width - w, y_top),
                ])

                # Bottom of placed box
                y_bottom = p_box.y_min - h - gap
                raw_candidates.extend([
                    (p_box.x_min, y_bottom),
                    (p_box.x_max - w, y_bottom),
                    (p_box.x_min + (p.width - w) / 2.0, y_bottom),
                    (p_box.x_max, y_bottom),
                    (p_box.x_min - w, y_bottom),
                    (0.0, y_bottom),
                    (facility_width - w, y_bottom),
                ])

            # B. Expanded anchor combinations (facility corners and edge projections)
            x_anchors: Set[float] = {0.0, round(facility_width - w, 4)}
            y_anchors: Set[float] = {0.0, round(facility_height - h, 4)}
            for p in placed_placements.values():
                pb = p.bounding_box
                x_anchors.add(round(pb.x_min, 4))
                x_anchors.add(round(pb.x_max, 4))
                x_anchors.add(round(pb.x_min - w - gap, 4))
                x_anchors.add(round(pb.x_max + gap, 4))
                x_anchors.add(round(pb.x_min + (p.width - w) / 2.0, 4))

                y_anchors.add(round(pb.y_min, 4))
                y_anchors.add(round(pb.y_max, 4))
                y_anchors.add(round(pb.y_min - h - gap, 4))
                y_anchors.add(round(pb.y_max + gap, 4))
                y_anchors.add(round(pb.y_min + (p.height - h) / 2.0, 4))

            for ax in x_anchors:
                for ay in y_anchors:
                    raw_candidates.append((ax, ay))

        # Deduplicate candidate coordinates
        seen_coords: Set[Tuple[float, float]] = set()
        unique_coords: List[Tuple[float, float]] = []

        for raw_x, raw_y in raw_candidates:
            if step and step > 0:
                cx = round(raw_x / step) * step
                cy = round(raw_y / step) * step
            else:
                cx = round(raw_x, 4)
                cy = round(raw_y, 4)

            coord_key = (round(cx, 4), round(cy, 4))
            if coord_key not in seen_coords:
                seen_coords.add(coord_key)
                unique_coords.append((cx, cy))

        # Deterministic coordinate order (bottom-to-top, left-to-right)
        unique_coords.sort(key=lambda pt: (pt[1], pt[0]))

        # Filter candidates against boundary, overlap, reserved zones, and contiguity
        for cx, cy in unique_coords:
            cand_box = BoundingBox(
                x_min=cx,
                y_min=cy,
                x_max=cx + w,
                y_max=cy + h,
            )

            # 1. Facility boundary containment
            if (
                cand_box.x_min < -tol
                or cand_box.y_min < -tol
                or cand_box.x_max > facility_width + tol
                or cand_box.y_max > facility_height + tol
            ):
                rejection_reasons["out_of_bounds"] += 1
                continue

            # 2. Non-overlapping check with placed departments
            overlaps_dept = False
            for p in placed_placements.values():
                if GeometryEngine.overlap_area(cand_box, p.bounding_box, tolerance=tol) > tol:
                    overlaps_dept = True
                    break

            if overlaps_dept:
                rejection_reasons["overlap_department"] += 1
                continue

            # 3. Non-overlapping check with reserved zones
            overlaps_reserved = False
            for z in res_zones:
                if GeometryEngine.overlap_area(cand_box, z.bounding_box, tolerance=tol) > tol:
                    overlaps_reserved = True
                    break

            if overlaps_reserved:
                rejection_reasons["overlap_reserved_zone"] += 1
                continue

            # 4. Contiguity check (for steps >= 2, must touch at least one placed department)
            if placed_placements:
                is_adj = any(
                    GeometryEngine.is_adjacent(cand_box, p.bounding_box, tolerance=tol)
                    or GeometryEngine.shared_boundary_length(cand_box, p.bounding_box, tolerance=tol) > tol
                    for p in placed_placements.values()
                )
                if not is_adj:
                    rejection_reasons["not_adjacent"] += 1
                    continue

            placement_key = (round(cx, 4), round(cy, 4), round(w, 4), round(h, 4))
            if placement_key not in seen_placements:
                seen_placements.add(placement_key)
                valid_placements.append(
                    ContinuousPlacement(
                        department_id=dept_id,
                        x=round(cx, 4),
                        y=round(cy, 4),
                        width=w,
                        height=h,
                        orientation_degrees=orient,
                    )
                )

    return valid_placements, rejection_reasons
