"""Spatial and geometric representation primitives for facility layout."""

from typing import Any, Dict, Optional, Tuple, Union
from pydantic import BaseModel, Field, model_validator


class Point2D(BaseModel):
    """Represents a 2D coordinate point (e.g. centroid or bottom-left corner)."""

    x: float = Field(..., description="X-coordinate in distance units (e.g. meters)")
    y: float = Field(..., description="Y-coordinate in distance units (e.g. meters)")


class Dimensions2D(BaseModel):
    """Represents width and height of an entity."""

    width: float = Field(..., gt=0, description="Width along the X-axis")
    height: float = Field(..., gt=0, description="Height along the Y-axis")

    @property
    def area(self) -> float:
        """Calculate cross-sectional area."""
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (max dimension / min dimension)."""
        return max(self.width, self.height) / min(self.width, self.height)


class BoundingBox(BaseModel):
    """Represents an axis-aligned bounding box defined by min and max coordinates."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        if self.x_max < self.x_min:
            raise ValueError(f"x_max ({self.x_max}) cannot be less than x_min ({self.x_min})")
        if self.y_max < self.y_min:
            raise ValueError(f"y_max ({self.y_max}) cannot be less than y_min ({self.y_min})")
        return self

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
    def left(self) -> float:
        return self.x_min

    @property
    def right(self) -> float:
        return self.x_max

    @property
    def bottom(self) -> float:
        return self.y_min

    @property
    def top(self) -> float:
        return self.y_max

    @property
    def aspect_ratio(self) -> float:
        min_dim = min(self.width, self.height)
        if min_dim <= 0:
            return 1.0
        return max(self.width, self.height) / min_dim

    @property
    def centroid(self) -> Point2D:
        return Point2D(
            x=(self.x_min + self.x_max) / 2.0,
            y=(self.y_min + self.y_max) / 2.0,
        )

    def intersects(self, other: "BoundingBox", tolerance: float = 1e-6) -> bool:
        """Check if two bounding boxes overlap with an optional tolerance."""
        return not (
            self.x_max <= other.x_min + tolerance
            or self.x_min >= other.x_max - tolerance
            or self.y_max <= other.y_min + tolerance
            or self.y_min >= other.y_max - tolerance
        )

    def contains_point(self, point: Point2D, tolerance: float = 1e-6) -> bool:
        """Check if point is inside or on the boundary of this box."""
        return (
            (self.x_min - tolerance) <= point.x <= (self.x_max + tolerance)
            and (self.y_min - tolerance) <= point.y <= (self.y_max + tolerance)
        )

    def contains_box(self, other: "BoundingBox", tolerance: float = 1e-6) -> bool:
        """Check if another bounding box is fully contained within this box."""
        return (
            (self.x_min - tolerance) <= other.x_min
            and (self.x_max + tolerance) >= other.x_max
            and (self.y_min - tolerance) <= other.y_min
            and (self.y_max + tolerance) >= other.y_max
        )

    def intersection(self, other: "BoundingBox", tolerance: float = 1e-6) -> Optional["BoundingBox"]:
        """Compute the intersecting rectangle of two bounding boxes if any."""
        ix_min = max(self.x_min, other.x_min)
        iy_min = max(self.y_min, other.y_min)
        ix_max = min(self.x_max, other.x_max)
        iy_max = min(self.y_max, other.y_max)

        if ix_max > ix_min + tolerance and iy_max > iy_min + tolerance:
            return BoundingBox(x_min=ix_min, y_min=iy_min, x_max=ix_max, y_max=iy_max)
        return None

    def overlap_area(self, other: "BoundingBox", tolerance: float = 1e-6) -> float:
        """Calculate spatial intersection area between two boxes."""
        inter = self.intersection(other, tolerance=tolerance)
        return inter.area if inter else 0.0


class ReservedZone(BaseModel):
    """Represents a structural, clearance, or prohibited placement zone in the facility."""

    id: str = Field(..., description="Unique identifier for the reserved zone (e.g. 'ZONE_ENTRANCE')")
    type: str = Field(
        default="no_placement",
        description="Zone type: 'entrance', 'emergency_exit', 'structural_column', 'no_placement', 'main_aisle'",
    )
    bounding_box: BoundingBox = Field(..., description="Spatial extent of the reserved zone")
    strict: bool = Field(default=True, description="If True, violation is fatal error; if False, non-fatal advisory")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible metadata")

    @model_validator(mode="before")
    @classmethod
    def assemble_reserved_zone(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "zone_type" in data and "type" not in data:
                data["type"] = data["zone_type"]
            if "bounding_box" not in data and "x_min" in data:
                data["bounding_box"] = BoundingBox(
                    x_min=data.pop("x_min"),
                    y_min=data.pop("y_min"),
                    x_max=data.pop("x_max"),
                    y_max=data.pop("y_max"),
                )
        return data
