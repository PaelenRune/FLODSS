"""Facility data model."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.geometry import ReservedZone


class Facility(BaseModel):
    """Represents the global plant or facility boundary inside which departments are placed."""

    id: str = Field(..., description="Unique identifier for the facility")
    name: str = Field(..., description="Human-readable facility name")
    width: float = Field(..., gt=0, description="Total width of the facility along the X-axis")
    height: float = Field(..., gt=0, description="Total length/height of the facility along the Y-axis")
    area: Optional[float] = Field(
        default=None,
        gt=0,
        description="Total available floor area. If omitted, defaults to width * height.",
    )
    reserved_zones: List[ReservedZone] = Field(
        default_factory=list,
        description="Structural columns, emergency paths, or forbidden placement zones",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata (e.g. site location, columns, coordinate system, building code)",
    )

    @model_validator(mode="after")
    def compute_default_area(self) -> "Facility":
        """Compute area automatically if not explicitly provided."""
        if self.area is None:
            self.area = round(self.width * self.height, 4)
        return self
