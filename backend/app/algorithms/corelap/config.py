"""Configuration models for the CORELAP layout construction algorithm."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class PlacementMode(str, Enum):
    """Candidate position scoring mode.
    
    CLASSICAL_ADJACENCY:
        Pure Muther SLP shared border contact scoring.
        Reward = relationship_weight * shared_boundary_length.
        Non-adjacent pairs receive zero score.
        Adheres to classical CORELAP literature principles without arbitrary distance decay.
        
    EXTENDED_DISTANCE_WEIGHTED:
        FLODSS engineering extension incorporating continuous Euclidean/Manhattan
        distance decay and configurable X-relationship separation penalties.
    """

    CLASSICAL_ADJACENCY = "classical_adjacency"
    EXTENDED_DISTANCE_WEIGHTED = "extended_distance_weighted"

    # Legacy aliases
    ADJACENCY = "classical_adjacency"
    DISTANCE_WEIGHTED = "extended_distance_weighted"


class InitialAnchorMode(str, Enum):
    """Placement anchor for the very first department."""

    CENTER = "center"          # Center of facility floor (classical growth outwards)
    ORIGIN = "origin"          # Bottom-left origin (0, 0)
    BOTTOM_LEFT = "bottom_left"


class TraceLevel(str, Enum):
    """Verbosity level of the explainability trace."""

    SUMMARY = "SUMMARY"        # Compact step-level summary (default)
    DETAILED = "DETAILED"      # Step-level plus detailed candidate evaluation logs


class CORELAPConfig(BaseModel):
    """Hyperparameter and operational configuration for CORELAP v1.0."""

    placement_mode: PlacementMode = Field(
        default=PlacementMode.CLASSICAL_ADJACENCY,
        description="Scoring methodology: 'classical_adjacency' (pure shared border) or 'extended_distance_weighted'",
    )
    initial_anchor_mode: InitialAnchorMode = Field(
        default=InitialAnchorMode.CENTER,
        description="Positioning location for the first selected department",
    )
    candidate_gap: float = Field(
        default=0.0,
        ge=0.0,
        description="Minimum gap clearance between adjacent departments (0.0 for direct wall sharing)",
    )
    aspect_ratio_target: float = Field(
        default=1.0,
        ge=1.0,
        description="Target shape aspect ratio for base rectangular shape (1.0 = square-ish)",
    )
    allow_shape_alternatives: bool = Field(
        default=True,
        description="Generate bounded legal shape variations (min/max width, neighbor matching, strips)",
    )
    evaluate_orientations: bool = Field(
        default=True,
        description="Evaluate both 0 and 90 degree orientations when permitted by department constraints",
    )
    
    # Extended mode scoring parameters (explicitly named, zero magic numbers)
    x_adjacency_penalty_multiplier: float = Field(
        default=1.0,
        ge=1.0,
        description="Multiplier amplifying adjacency penalties for X relationships (1.0 in classical mode)",
    )
    distance_decay_factor: float = Field(
        default=0.1,
        gt=0.0,
        description="Distance discount coefficient used in extended_distance_weighted mode",
    )
    separated_x_penalty_scale: float = Field(
        default=5.0,
        ge=0.0,
        description="Separation penalty scale for X-relationships in extended mode",
    )
    separated_x_decay_factor: float = Field(
        default=0.05,
        gt=0.0,
        description="Separation discount coefficient for X-relationships in extended mode",
    )
    tie_break_center_compactness: bool = Field(
        default=True,
        description="Secondary tie-breaker preferring candidate positions closer to facility center",
    )
    
    # Precision and diagnostics
    numerical_tolerance: float = Field(
        default=1e-4,
        gt=0.0,
        description="Floating point geometric tolerance for boundary and overlap checks",
    )
    step_grid_alignment: Optional[float] = Field(
        default=None,
        description="Grid discretization step (in meters) for candidate snapping, or None for continuous",
    )
    trace_level: TraceLevel = Field(
        default=TraceLevel.SUMMARY,
        description="Trace verbosity level ('SUMMARY' or 'DETAILED')",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible configuration metadata",
    )

    @field_validator("placement_mode", mode="before")
    @classmethod
    def normalize_placement_mode(cls, v: Any) -> Any:
        """Allow legacy 'adjacency' and 'distance_weighted' strings."""
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("adjacency", "classical_adjacency"):
                return PlacementMode.CLASSICAL_ADJACENCY
            if v_lower in ("distance_weighted", "extended_distance_weighted"):
                return PlacementMode.EXTENDED_DISTANCE_WEIGHTED
        return v
