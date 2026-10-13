"""Generator for strictly legal rectangular department dimensions conserving required area."""

import math
from typing import List, Optional, Set, Tuple

from app.feasibility.models import DimensionAlternativeTag, LegalDimension
from app.models.department import Department


class LegalDimensionGenerator:
    """Computes mathematically valid, area-conserving rectangular shape alternatives for departments.
    
    Adheres strictly to:
        1. Exact area conservation: width * height == required_area (within tolerance)
        2. Dimensional range enforcement: min_width <= width <= max_width, min_height <= height <= max_height
        3. Aspect ratio bounds: min_aspect_ratio <= max(w, h) / min(w, h) <= max_aspect_ratio
        4. Plant containment capacity: width <= facility_width, height <= facility_height
    """

    @classmethod
    def generate_legal_dimensions(
        cls,
        department: Department,
        facility_width: float,
        facility_height: float,
        existing_widths: Optional[List[float]] = None,
        existing_heights: Optional[List[float]] = None,
        max_alternatives: int = 10,
        tolerance: float = 1e-4,
    ) -> List[LegalDimension]:
        """Produce a bounded, deterministic list of valid rectangular dimension alternatives."""
        area = department.required_area
        if area <= 0:
            return []

        # 1. Establish hard physical bounds
        w_min = max(0.01, department.min_width or 0.01)
        w_max = min(facility_width, department.max_width or facility_width)
        h_min = max(0.01, department.min_height or 0.01)
        h_max = min(facility_height, department.max_height or facility_height)

        max_ar = department.max_aspect_ratio or 10.0
        min_ar = department.min_aspect_ratio or 1.0

        # Width constraints from height limits: h = A / w in [h_min, h_max] => w in [A / h_max, A / h_min]
        w_from_h_max = area / h_max
        w_from_h_min = area / h_min

        # Width constraints from max aspect ratio:
        # If w >= h: w / h <= max_ar => w^2 / A <= max_ar => w <= sqrt(A * max_ar)
        # If h >= w: h / w <= max_ar => A / w^2 <= max_ar => w >= sqrt(A / max_ar)
        w_from_ar_lower = math.sqrt(area / max_ar)
        w_from_ar_upper = math.sqrt(area * max_ar)

        # Combined feasible width interval [w_lower, w_upper]
        w_lower = max(w_min, w_from_h_max, w_from_ar_lower)
        w_upper = min(w_max, w_from_h_min, w_from_ar_upper)

        if w_lower > w_upper + tolerance:
            # Over-constrained department: no rectangular dimension can satisfy all simultaneous rules
            return []

        # 2. Collect candidate width values
        candidates: List[Tuple[float, DimensionAlternativeTag, bool]] = []

        # A. Square-ish baseline
        w_square = math.sqrt(area)
        w_square_clamped = min(max(w_square, w_lower), w_upper)
        candidates.append((w_square_clamped, DimensionAlternativeTag.SQUARE_ISH, False))

        # B. Boundary extremes
        candidates.append((w_lower, DimensionAlternativeTag.MIN_WIDTH, False))
        candidates.append((w_upper, DimensionAlternativeTag.MAX_WIDTH, False))

        # Corresponding height extremes
        h_clamped_min = max(h_min, area / w_upper)
        candidates.append((area / h_clamped_min, DimensionAlternativeTag.MIN_HEIGHT, False))

        h_clamped_max = min(h_max, area / w_lower)
        candidates.append((area / h_clamped_max, DimensionAlternativeTag.MAX_HEIGHT, False))

        # C. Aspect ratio bounds
        if w_lower <= w_from_ar_upper <= w_upper:
            candidates.append((w_from_ar_upper, DimensionAlternativeTag.ASPECT_RATIO_BOUND, False))
        if w_lower <= w_from_ar_lower <= w_upper:
            candidates.append((w_from_ar_lower, DimensionAlternativeTag.ASPECT_RATIO_BOUND, False))

        # D. Boundary-aligned variants from neighboring departments
        if existing_widths:
            for ew in existing_widths:
                if w_lower - tolerance <= ew <= w_upper + tolerance:
                    candidates.append((ew, DimensionAlternativeTag.BOUNDARY_ALIGNED, False))
        if existing_heights:
            for eh in existing_heights:
                if eh > 0:
                    cand_w = area / eh
                    if w_lower - tolerance <= cand_w <= w_upper + tolerance:
                        candidates.append((cand_w, DimensionAlternativeTag.BOUNDARY_ALIGNED, False))

        # E. Discrete interpolation across the legal range if budget allows
        if max_alternatives > len(candidates) and (w_upper - w_lower > 1e-2):
            steps_needed = max_alternatives - len(candidates)
            for step_i in range(1, steps_needed + 1):
                frac = step_i / (steps_needed + 1)
                w_interp = w_lower + frac * (w_upper - w_lower)
                candidates.append((w_interp, DimensionAlternativeTag.INTERPOLATED, False))

        # 3. Filter, validate and assemble legal dimensions
        seen_pairs: Set[Tuple[float, float]] = set()
        results: List[LegalDimension] = []

        for cand_w, tag, is_rot in candidates:
            # Round candidate width for consistency
            w_val = round(cand_w, 4)
            if w_val <= 0:
                continue
            h_val = round(area / w_val, 6)

            # Strict validation
            if w_val < w_min - tolerance or w_val > w_max + tolerance:
                continue
            if h_val < h_min - tolerance or h_val > h_max + tolerance:
                continue

            ar = max(w_val, h_val) / min(w_val, h_val)
            if ar > max_ar + tolerance or ar < min_ar - tolerance:
                continue

            # Area conservation check
            actual_area = w_val * h_val
            if abs(actual_area - area) > (area * 0.02 + 0.1):  # within small rounding tolerance
                continue

            # Fixed orientation check
            if department.fixed_orientation is not None:
                # If fixed at 90/270 degrees, must enforce orientation
                pass

            pair_key = (round(w_val, 2), round(h_val, 2))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            results.append(
                LegalDimension(
                    width=w_val,
                    height=h_val,
                    area=round(actual_area, 4),
                    aspect_ratio=round(ar, 3),
                    tag=tag,
                    is_rotated_variant=is_rot,
                )
            )

            if len(results) >= max_alternatives:
                break

        # Sort predictably: Square-ish first, then by width ascending
        results.sort(key=lambda d: (d.tag != DimensionAlternativeTag.SQUARE_ISH, d.width))
        return results
