"""Geometry Engine for spatial calculations, distance metrics, and layout analytics."""

import math
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from app.models.geometry import Point2D, BoundingBox
from app.models.representation import ContinuousLayout, ContinuousPlacement


class DistanceMetricType(str, Enum):
    """Supported spatial distance calculation methods."""

    EUCLIDEAN = "euclidean"                    # Centroid straight-line L2 distance
    CENTROID_EUCLIDEAN = "centroid_euclidean"  # Alias for Euclidean centroid
    MANHATTAN = "manhattan"                    # Centroid rectilinear L1 distance (|dx| + |dy|)
    RECTILINEAR = "rectilinear"                # Alias for Manhattan
    CENTROID_MANHATTAN = "centroid_manhattan"  # Alias for centroid Manhattan
    EDGE_TO_EDGE = "edge_to_edge"              # Minimum Euclidean separation between boundaries


class GeometryEngine:
    """Core computational geometry service decoupled from optimization algorithms."""

    @staticmethod
    def rectangle_intersection(box_a: BoundingBox, box_b: BoundingBox, tolerance: float = 1e-6) -> Optional[BoundingBox]:
        """Compute intersecting rectangle if two boxes overlap."""
        return box_a.intersection(box_b, tolerance=tolerance)

    @staticmethod
    def overlap_area(box_a: BoundingBox, box_b: BoundingBox, tolerance: float = 1e-6) -> float:
        """Compute the area of intersection between two boxes."""
        return box_a.overlap_area(box_b, tolerance=tolerance)

    @staticmethod
    def contains(outer_box: BoundingBox, inner: Union[Point2D, BoundingBox], tolerance: float = 1e-6) -> bool:
        """Check if point or box is fully within outer box."""
        if isinstance(inner, Point2D):
            return outer_box.contains_point(inner, tolerance=tolerance)
        return outer_box.contains_box(inner, tolerance=tolerance)

    @staticmethod
    def _extract_centroid(target: Union[BoundingBox, Point2D, Any]) -> Point2D:
        if isinstance(target, Point2D):
            return target
        if hasattr(target, "centroid"):
            return target.centroid
        raise TypeError(f"Cannot extract centroid from {type(target)}")

    @classmethod
    def centroid_euclidean_distance(cls, a: Union[BoundingBox, Point2D], b: Union[BoundingBox, Point2D]) -> float:
        """Compute L2 Euclidean distance between the centroids or points."""
        c_a = cls._extract_centroid(a)
        c_b = cls._extract_centroid(b)
        dx = c_a.x - c_b.x
        dy = c_a.y - c_b.y
        return math.sqrt(dx * dx + dy * dy)

    @classmethod
    def centroid_manhattan_distance(cls, a: Union[BoundingBox, Point2D], b: Union[BoundingBox, Point2D]) -> float:
        """Compute L1 Rectilinear / Manhattan distance between centroids or points."""
        c_a = cls._extract_centroid(a)
        c_b = cls._extract_centroid(b)
        return abs(c_a.x - c_b.x) + abs(c_a.y - c_b.y)

    @staticmethod
    def edge_to_edge_distance(box_a: BoundingBox, box_b: BoundingBox) -> float:
        """Compute minimum edge-to-edge separation distance between two rectangles.
        
        Returns 0.0 if boxes touch or overlap.
        """
        dx = max(0.0, max(box_a.x_min - box_b.x_max, box_b.x_min - box_a.x_max))
        dy = max(0.0, max(box_a.y_min - box_b.y_max, box_b.y_min - box_a.y_max))
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def is_adjacent(box_a: BoundingBox, box_b: BoundingBox, tolerance: float = 1e-4) -> bool:
        """Check if two boxes share a contiguous boundary edge without volumetric overlap."""
        # Check vertical contact (share X border, overlap in Y)
        vert_touch = (
            abs(box_a.x_max - box_b.x_min) <= tolerance
            or abs(box_b.x_max - box_a.x_min) <= tolerance
        )
        y_overlap = min(box_a.y_max, box_b.y_max) - max(box_a.y_min, box_b.y_min)
        if vert_touch and y_overlap > tolerance:
            return True

        # Check horizontal contact (share Y border, overlap in X)
        horiz_touch = (
            abs(box_a.y_max - box_b.y_min) <= tolerance
            or abs(box_b.y_max - box_a.y_min) <= tolerance
        )
        x_overlap = min(box_a.x_max, box_b.x_max) - max(box_a.x_min, box_b.x_min)
        if horiz_touch and x_overlap > tolerance:
            return True

        return False

    @staticmethod
    def shared_boundary_length(box_a: BoundingBox, box_b: BoundingBox, tolerance: float = 1e-4) -> float:
        """Calculate the length of the common border segment shared by two adjacent boxes."""
        vert_touch = (
            abs(box_a.x_max - box_b.x_min) <= tolerance
            or abs(box_b.x_max - box_a.x_min) <= tolerance
        )
        if vert_touch:
            y_overlap = min(box_a.y_max, box_b.y_max) - max(box_a.y_min, box_b.y_min)
            if y_overlap > tolerance:
                return round(y_overlap, 4)

        horiz_touch = (
            abs(box_a.y_max - box_b.y_min) <= tolerance
            or abs(box_b.y_max - box_a.y_min) <= tolerance
        )
        if horiz_touch:
            x_overlap = min(box_a.x_max, box_b.x_max) - max(box_a.x_min, box_b.x_min)
            if x_overlap > tolerance:
                return round(x_overlap, 4)

        return 0.0

    @classmethod
    def calculate_distance(
        cls,
        box_a: BoundingBox,
        box_b: BoundingBox,
        metric: Union[DistanceMetricType, str] = DistanceMetricType.EUCLIDEAN,
    ) -> float:
        """Dispatch distance calculation based on specified metric."""
        metric_str = metric.value if isinstance(metric, DistanceMetricType) else str(metric).lower().strip()

        if metric_str in ("euclidean", "centroid_euclidean", "l2"):
            return cls.centroid_euclidean_distance(box_a, box_b)
        elif metric_str in ("manhattan", "rectilinear", "centroid_manhattan", "l1"):
            return cls.centroid_manhattan_distance(box_a, box_b)
        elif metric_str in ("edge_to_edge", "min_distance", "clearance"):
            return cls.edge_to_edge_distance(box_a, box_b)
        else:
            raise ValueError(
                f"Unknown distance metric '{metric}'. Supported: {[m.value for m in DistanceMetricType]}."
            )

    @classmethod
    def calculate_layout_metrics(
        cls,
        layout: ContinuousLayout,
        facility_width: Optional[Union[float, Any]] = None,
        facility_height: Optional[float] = None,
    ) -> Dict[str, float]:
        """Compute basic spatial utilization and compactness metrics for a layout."""
        if hasattr(facility_width, "facility"):
            fac_w = facility_width.facility.width
            fac_h = facility_width.facility.height
        else:
            fac_w = facility_width or layout.facility_width
            fac_h = facility_height or layout.facility_height
        fac_area = fac_w * fac_h

        occupied_area = sum(p.area for p in layout.placements.values())
        free_area = max(0.0, fac_area - occupied_area)
        utilization = occupied_area / fac_area if fac_area > 0 else 0.0

        # Total pairwise overlap area
        placements_list = list(layout.placements.values())
        total_overlap = 0.0
        for i in range(len(placements_list)):
            box_i = placements_list[i].bounding_box
            for j in range(i + 1, len(placements_list)):
                box_j = placements_list[j].bounding_box
                total_overlap += cls.overlap_area(box_i, box_j)

        # Minimum bounding envelope enclosing all departments
        if placements_list:
            min_x = min(p.left for p in placements_list)
            max_x = max(p.right for p in placements_list)
            min_y = min(p.bottom for p in placements_list)
            max_y = max(p.top for p in placements_list)
            envelope_w = max_x - min_x
            envelope_h = max_y - min_y
            envelope_area = envelope_w * envelope_h
            compactness = occupied_area / envelope_area if envelope_area > 0 else 1.0
        else:
            envelope_area = 0.0
            compactness = 0.0

        return {
            "occupied_area": round(occupied_area, 2),
            "free_area": round(free_area, 2),
            "utilization_ratio": round(utilization, 4),
            "total_overlap_area": round(total_overlap, 4),
            "bounding_envelope_area": round(envelope_area, 2),
            "compactness": round(compactness, 4),
        }
