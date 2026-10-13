"""Qualitative closeness relationship (REL Chart) data model."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator


class ClosenessRating(str, Enum):
    """Muther's standard Systematic Layout Planning (SLP) closeness ratings."""

    A = "A"  # Absolutely Necessary
    E = "E"  # Especially Important
    I = "I"  # Important
    O = "O"  # Ordinary Closeness OK
    U = "U"  # Unimportant
    X = "X"  # Undesirable / Prohibited closeness


DEFAULT_RELATIONSHIP_SCORES: Dict[ClosenessRating, float] = {
    ClosenessRating.A: 16.0,
    ClosenessRating.E: 8.0,
    ClosenessRating.I: 4.0,
    ClosenessRating.O: 2.0,
    ClosenessRating.U: 0.0,
    ClosenessRating.X: -8.0,
}

# Aliases for terminology flexibility
RelationshipType = ClosenessRating
RELATIONSHIP_DEFAULT_SCORES = DEFAULT_RELATIONSHIP_SCORES


class Relationship(BaseModel):
    """Represents a qualitative closeness preference between two departments."""

    department_a: str = Field(..., description="First department ID")
    department_b: str = Field(..., description="Second department ID")
    relationship_type: ClosenessRating = Field(
        ...,
        description="SLP Closeness rating: A (Absolute), E (Especially), I (Important), O (Ordinary), U (Unimportant), X (Undesirable)",
    )
    score: Optional[float] = Field(
        default=None,
        description="Numerical affinity weight. Defaults to standard SLP score if omitted.",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Justification code or description (e.g. '1: Shared equipment', '2: Noise hazard')",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata (e.g. surveyed by, confidence index)",
    )

    @model_validator(mode="after")
    def validate_relationship(self) -> "Relationship":
        if self.department_a == self.department_b:
            raise ValueError(
                f"Relationship cannot link department '{self.department_a}' to itself."
            )
        if self.score is None:
            self.score = DEFAULT_RELATIONSHIP_SCORES.get(self.relationship_type, 0.0)
        return self
