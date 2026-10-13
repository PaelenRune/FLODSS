"""Configuration parameters and enums for ALDEP (Automated Layout Design Program)."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SweepDirection(str, Enum):
    """Direction of strips across the facility."""
    VERTICAL = "VERTICAL"      # Vertical bands/columns of width W cells
    HORIZONTAL = "HORIZONTAL"  # Horizontal bands/rows of height H cells


class SelectionTieBreak(str, Enum):
    """Strategy for resolving ties during ALDEP department selection."""
    RANDOM_AMONG_MAX = "RANDOM_AMONG_MAX"            # Classical ALDEP: pick randomly among candidates with maximum rating
    RANDOM_AMONG_THRESHOLD = "RANDOM_AMONG_THRESHOLD"  # Pick randomly among all candidates meeting threshold T


class TraceLevel(str, Enum):
    """Detail level of ALDEP explainability trace."""
    SUMMARY = "SUMMARY"
    DETAILED = "DETAILED"


class ALDEPConfig(BaseModel):
    """Runtime configuration for ALDEP construction heuristic."""

    number_of_candidates: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of candidate layout alternatives to generate using seeded pseudo-random runs",
    )
    random_seed: Optional[int] = Field(
        default=42,
        description="Base random seed for reproducibility across candidate generations",
    )
    cell_size: float = Field(
        default=5.0,
        gt=0.0,
        description="Square grid cell size in meters for spatial discretization",
    )
    strip_width_cells: int = Field(
        default=2,
        ge=1,
        description="Width of each strip in number of grid cells",
    )
    sweep_direction: SweepDirection = Field(
        default=SweepDirection.VERTICAL,
        description="Orientation of layout strips: VERTICAL or HORIZONTAL",
    )
    selection_threshold: float = Field(
        default=8.0,
        description="Minimum Muther relationship score (e.g. 8.0 for 'E', 16.0 for 'A', 4.0 for 'I')",
    )
    tie_breaker: SelectionTieBreak = Field(
        default=SelectionTieBreak.RANDOM_AMONG_MAX,
        description="Rule for breaking ties when multiple unplaced departments qualify",
    )
    allow_strip_splitting: bool = Field(
        default=True,
        description="True for classical ALDEP (departments wrap across strips into serpentine shapes); "
                    "False for FLODSS rectangular adaptation (keeps departments within single strips)",
    )
    serpentine_sweep: bool = Field(
        default=True,
        description="True for alternating boustrophedon sweep direction (up-down-up or left-right-left); "
                    "False for unidirectional sweep",
    )
    trace_level: TraceLevel = Field(
        default=TraceLevel.SUMMARY,
        description="Detail level of generated explainability trace",
    )
