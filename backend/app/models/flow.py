"""Material flow data model."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator


class Flow(BaseModel):
    """Represents directed material flow or traffic volume between two departments."""

    source_department: str = Field(..., description="ID of origin/source department")
    target_department: str = Field(..., description="ID of destination/target department")
    quantity: float = Field(..., ge=0, description="Volume/intensity of flow per time period")
    unit: str = Field(default="moves/day", description="Measurement unit (e.g. trips/day, pallets/hr, kg/week)")
    product_or_process_id: Optional[str] = Field(
        default=None,
        description="Optional product, SKU, routing step, or process identifier",
    )
    cost_per_unit_distance: float = Field(
        default=1.0,
        ge=0,
        description="Material handling cost factor per unit quantity per unit distance",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata (e.g. handling vehicle type, priority, hazard class)",
    )

    @model_validator(mode="after")
    def validate_endpoints(self) -> "Flow":
        if self.source_department == self.target_department:
            raise ValueError(
                f"Self-flow is not allowed: source and target department cannot both be '{self.source_department}'"
            )
        return self
