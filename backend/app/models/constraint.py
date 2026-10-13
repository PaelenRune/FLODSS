"""Facility layout constraint definitions and data models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ConstraintClassification(str, Enum):
    """Classification of constraint strictness."""

    HARD = "hard"  # Infeasible if violated
    SOFT = "soft"  # Feasible but penalized in the objective function


class ConstraintType(str, Enum):
    """Categorization of geometric and operational layout constraints."""

    NON_OVERLAPPING = "non_overlapping"          # Departments must not overlap in space
    BOUNDARY = "boundary"                        # Department must stay entirely inside facility boundaries
    FIXED_POSITION = "fixed_position"            # Department fixed to specific coordinates
    MIN_DISTANCE = "min_distance"                # Keep departments separated by at least D (safety/hazards)
    MAX_DISTANCE = "max_distance"                # Keep departments within at most D (high interaction)
    SEPARATION = "separation"                    # Enforce physical separation distance between departments
    ASPECT_RATIO = "aspect_ratio"                # Limit distortion of width / height
    FORBIDDEN_ZONE = "forbidden_zone"            # Prevent placement inside specific coordinate region
    ZONE_MEMBERSHIP = "zone_membership"          # Restrict department to specific building wing / floor
    ADJACENCY = "adjacency"                      # Must share a common wall / border
    CUSTOM = "custom"                            # Extensible domain-specific constraint


# Canonical mapping for aliases
CONSTRAINT_TYPE_ALIASES = {
    "minimum_distance": ConstraintType.MIN_DISTANCE,
    "min_distance": ConstraintType.MIN_DISTANCE,
    "maximum_distance": ConstraintType.MAX_DISTANCE,
    "max_distance": ConstraintType.MAX_DISTANCE,
    "non_overlap": ConstraintType.NON_OVERLAPPING,
    "non_overlapping": ConstraintType.NON_OVERLAPPING,
    "separation": ConstraintType.SEPARATION,
}


class Constraint(BaseModel):
    """Represents a geometric, operational, or safety constraint in the facility layout."""

    id: str = Field(..., description="Unique constraint identifier (e.g. 'CST_NO_OVERLAP')")
    type: ConstraintType = Field(..., description="Type of constraint")
    involved_departments: List[str] = Field(
        default_factory=list,
        description="Department IDs subject to this constraint. Empty list implies all departments.",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Constraint-specific parameters (e.g. {'distance': 5.0, 'zone': [0, 0, 10, 10]})",
    )
    classification: ConstraintClassification = Field(
        default=ConstraintClassification.HARD,
        description="Whether the constraint is HARD (strict requirement) or SOFT (penalized)",
    )
    penalty: float = Field(
        default=1000.0,
        ge=0,
        description="Penalty multiplier or cost added to objective function when soft constraint is violated",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata (e.g. regulation source, OSHA code, description)",
    )

    @field_validator("type", mode="before")
    @classmethod
    def normalize_constraint_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            key = v.strip().lower()
            if key in CONSTRAINT_TYPE_ALIASES:
                return CONSTRAINT_TYPE_ALIASES[key]
            # Try directly resolving enum value
            for ct in ConstraintType:
                if ct.value == key:
                    return ct
        return v

    @field_validator("classification", mode="before")
    @classmethod
    def normalize_classification(cls, v: Any) -> Any:
        if isinstance(v, str):
            clean = v.strip().lower()
            if clean in ("hard", "soft"):
                return ConstraintClassification(clean)
            raise ValueError(f"Invalid constraint classification '{v}'. Must be 'HARD' or 'SOFT'.")
        return v


class ConstraintViolation(BaseModel):
    """Records an occurrence of a violated constraint during evaluation."""

    constraint_id: str = Field(..., description="ID of violated constraint")
    constraint_type: ConstraintType = Field(..., description="Type of violated constraint")
    classification: ConstraintClassification = Field(..., description="Hard or soft constraint")
    involved_departments: List[str] = Field(default_factory=list, description="Departments triggering the violation")
    magnitude: float = Field(..., ge=0, description="Quantitative magnitude of violation (e.g. overlap area, excess distance)")
    penalty_cost: float = Field(default=0.0, ge=0, description="Assessed penalty cost")
    description: str = Field(default="", description="Diagnostic explanation of the violation")

    # Granular measurement fields for AI explanations & academic reporting
    measured_value: Optional[float] = Field(default=None, description="Measured spatial value")
    required_value: Optional[float] = Field(default=None, description="Required threshold value")

    @property
    def departments(self) -> List[str]:
        return self.involved_departments

    @property
    def violation_amount(self) -> float:
        return self.magnitude

    @property
    def penalty(self) -> float:
        return self.penalty_cost

    @property
    def message(self) -> str:
        return self.description
