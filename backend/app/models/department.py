"""Department data model."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.geometry import Point2D


class Department(BaseModel):
    """Represents an activity center, work cell, machine group, or functional department."""

    id: str = Field(..., description="Unique department identifier (e.g. 'DEP_01', 'Milling')")
    name: str = Field(..., description="Descriptive department name")
    required_area: float = Field(..., gt=0, description="Required footprint area in square units (e.g. m²)")

    # Dimensional constraints & aspect ratios
    min_width: Optional[float] = Field(default=None, gt=0, description="Minimum allowable department width")
    max_width: Optional[float] = Field(default=None, gt=0, description="Maximum allowable department width")
    min_height: Optional[float] = Field(default=None, gt=0, description="Minimum allowable department height")
    max_height: Optional[float] = Field(default=None, gt=0, description="Maximum allowable department height")
    min_aspect_ratio: Optional[float] = Field(
        default=None, ge=1.0, description="Minimum allowable aspect ratio (max_dim / min_dim)"
    )
    max_aspect_ratio: Optional[float] = Field(
        default=None, ge=1.0, description="Maximum allowable aspect ratio (prevents highly skewed shapes)"
    )

    # Fixed placements
    fixed_position: Optional[Point2D] = Field(
        default=None,
        description="Fixed coordinate (e.g. centroid or origin) if department location is pre-determined",
    )
    fixed_orientation: Optional[float] = Field(
        default=None,
        description="Fixed orientation in degrees (e.g. 0, 90, 180, 270) if rotation is constrained",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata (e.g. utilities, hazardous rating, floor load, color, department group)",
    )

    @model_validator(mode="after")
    def validate_dimension_ranges(self) -> "Department":
        if self.min_width is not None and self.max_width is not None and self.min_width > self.max_width:
            raise ValueError(f"min_width ({self.min_width}) cannot exceed max_width ({self.max_width})")
        if self.min_height is not None and self.max_height is not None and self.min_height > self.max_height:
            raise ValueError(f"min_height ({self.min_height}) cannot exceed max_height ({self.max_height})")
        if (
            self.min_aspect_ratio is not None
            and self.max_aspect_ratio is not None
            and self.min_aspect_ratio > self.max_aspect_ratio
        ):
            raise ValueError(
                f"min_aspect_ratio ({self.min_aspect_ratio}) cannot exceed max_aspect_ratio ({self.max_aspect_ratio})"
            )
        return self
