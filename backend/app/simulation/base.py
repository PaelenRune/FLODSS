"""Simulation abstractions for discrete-event and traffic flow validation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution


class SimulationConfig(BaseModel):
    """Configuration parameters for dynamic layout simulation."""

    duration_hours: float = Field(default=8.0, gt=0, description="Simulation duration in operating hours")
    warmup_hours: float = Field(default=1.0, ge=0, description="Warmup period before statistics collection")
    random_seed: Optional[int] = Field(default=42, description="Random seed for stochastic events")
    traffic_density_multiplier: float = Field(default=1.0, gt=0, description="Flow stress-test multiplier")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    """Output metrics from layout simulation."""

    layout_id: str
    average_transit_time_minutes: float = Field(default=0.0)
    aisle_congestion_hotspots: List[Dict[str, Any]] = Field(default_factory=list)
    throughput_per_hour: float = Field(default=0.0)
    agv_utilization_percent: float = Field(default=0.0)
    raw_statistics: Dict[str, Any] = Field(default_factory=dict)


class BaseLayoutSimulator(ABC):
    """Abstract interface for discrete-event or flow validation simulators."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def run(
        self,
        problem: FacilityLayoutProblem,
        solution: LayoutSolution,
        config: SimulationConfig,
    ) -> SimulationResult:
        """Simulate dynamic material handling over time."""
        pass
