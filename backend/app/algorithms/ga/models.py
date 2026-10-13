"""Data models and configuration schemas for Genetic Layout Optimization."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.representation import ContinuousLayout
from app.models.solution import LayoutSolution


class GATerminationReason(str, Enum):
    """Reason for GA search completion."""

    MAX_GENERATIONS_REACHED = "max_generations_reached"
    STAGNATION_LIMIT_REACHED = "stagnation_limit_reached"
    TIMEOUT = "timeout"
    OPTIMUM_OR_TARGET_REACHED = "target_reached"


class GAConfig(BaseModel):
    """Hyperparameters and runtime settings for Genetic Algorithm."""

    population_size: int = Field(default=50, ge=10, le=500, description="Number of individuals in population")
    generations: int = Field(default=100, ge=0, le=1000, description="Maximum generational cycles")
    crossover_rate: float = Field(default=0.85, ge=0.0, le=1.0, description="Order Crossover probability")
    mutation_rate: float = Field(default=0.30, ge=0.0, le=1.0, description="Individual mutation probability")
    elitism_count: int = Field(default=2, ge=1, le=20, description="Number of top elite individuals preserved")
    tournament_size: int = Field(default=4, ge=2, le=20, description="Tournament selection candidate count")
    random_seed: Optional[int] = Field(default=42, description="Random seed for deterministic reproduction")
    max_runtime_seconds: float = Field(default=30.0, ge=1.0, le=300.0, description="Hard wall-clock timeout in seconds")
    stagnation_limit: int = Field(default=30, ge=5, le=500, description="Generations without improvement before early stopping")
    soft_penalty_weight: float = Field(default=1.0, ge=0.0, description="Weight lambda for soft constraint penalties")
    infeasible_penalty: float = Field(default=1e7, description="Base penalty score added to infeasible individuals")
    min_bays: int = Field(default=2, ge=1, description="Minimum number of bays in layout")
    max_bays: int = Field(default=4, ge=1, description="Maximum number of bays in layout")
    orientation: str = Field(default="horizontal", description="Bay orientation: 'horizontal', 'vertical', or 'auto'")
    seed_with_guillotine: bool = Field(default=True, description="Seed population with Guillotine row packing solution if feasible")
    tolerance: float = Field(default=1e-4, description="Geometric floating point tolerance")


class BayChromosome(BaseModel):
    """Flexible Bay Structure (FBS) chromosome representation.
    
    Encodes:
    1. order: Permutation of department IDs.
    2. bay_sizes: Number of departments in each bay (e.g. [3, 3, 4]).
    3. orientation: 'horizontal' (bays stacked along Y) or 'vertical' (bays stacked along X).
    """

    order: List[str] = Field(..., description="Ordered list of department IDs")
    bay_sizes: List[int] = Field(..., description="Number of departments in each bay; sum(bay_sizes) == len(order)")
    orientation: str = Field(default="horizontal", description="'horizontal' or 'vertical'")

    def copy(self) -> "BayChromosome":
        """Deep copy of chromosome."""
        return BayChromosome(
            order=list(self.order),
            bay_sizes=list(self.bay_sizes),
            orientation=self.orientation,
        )

    def get_bays(self) -> List[List[str]]:
        """Slice department order into list of bays."""
        bays: List[List[str]] = []
        idx = 0
        for size in self.bay_sizes:
            bays.append(self.order[idx : idx + size])
            idx += size
        return bays

    @classmethod
    def from_bays(cls, bays: List[List[str]], orientation: str = "horizontal") -> "BayChromosome":
        """Construct chromosome from list of bay department lists."""
        order: List[str] = []
        bay_sizes: List[int] = []
        for bay in bays:
            order.extend(bay)
            bay_sizes.append(len(bay))
        return cls(order=order, bay_sizes=bay_sizes, orientation=orientation)


class Individual(BaseModel):
    """An individual in the GA population."""

    chromosome: BayChromosome
    fitness: float = Field(default=float("inf"), description="Combined fitness score (MHC + lambda * penalty)")
    raw_mhc: float = Field(default=float("inf"), description="Unpenalized Material Handling Cost")
    soft_penalty: float = Field(default=0.0, description="Sum of soft constraint penalty costs")
    is_feasible: bool = Field(default=False, description="True if satisfies all hard constraints, aspect ratios, etc.")
    violations: List[str] = Field(default_factory=list, description="List of hard constraint or geometric violation messages")
    layout: Optional[ContinuousLayout] = Field(default=None, description="Decoded continuous layout")


def individual_sort_key(ind: Individual) -> tuple:
    """Feasibility-first comparison key (Deb's rule).

    Feasible individuals (tier 0) strictly dominate infeasible ones (tier 1).
    Within feasible: sorted by (fitness, raw_mhc).
    Within infeasible: sorted by (violation count, fitness).
    """
    if ind.is_feasible:
        return (0, ind.fitness, ind.raw_mhc)
    return (1, float(len(ind.violations)), ind.fitness)


class GenerationRecord(BaseModel):
    """Telemetry record for a single generation cycle."""

    generation: int = Field(..., description="Generation index (0-based)")
    best_fitness: float = Field(..., description="Best combined fitness in population")
    best_mhc: float = Field(..., description="Best raw Material Handling Cost among feasible individuals")
    best_soft_penalty: float = Field(default=0.0, description="Soft constraint penalty of the best individual")
    avg_fitness: float = Field(..., description="Average fitness of entire population")
    best_is_feasible: bool = Field(default=True, description="Feasibility status of best individual")
    diversity: float = Field(default=0.0, description="Genetic diversity metric (normalized unique fitness ratio)")
    best_feasible_mhc: Optional[float] = Field(default=None, description="Best raw MHC among feasible individuals")
    feasible_count: int = Field(default=0, description="Number of feasible individuals in current population")
    unique_chromosomes: int = Field(default=0, description="Number of distinct chromosomes in population")
    unique_signatures: int = Field(default=0, description="Number of distinct layout signatures among feasible individuals")
    invalid_offspring_count: int = Field(default=0, description="Count of invalid offspring generated in this cycle")


class GAResult(BaseModel):
    """Comprehensive outcome of a Genetic Algorithm optimization run."""

    best_solution: LayoutSolution = Field(..., description="Best layout solution found")
    best_layout: ContinuousLayout = Field(..., description="Decoded continuous layout of best individual")
    best_chromosome: BayChromosome = Field(..., description="Best individual chromosome representation")
    best_fitness: float = Field(..., description="Best combined fitness achieved")
    best_mhc: float = Field(..., description="Best raw Material Handling Cost")
    best_soft_penalty: float = Field(default=0.0, description="Soft penalty of best solution")
    is_feasible: bool = Field(default=True, description="Feasibility of the best layout")
    generation_count: int = Field(..., description="Total generations completed")
    termination_reason: GATerminationReason = Field(..., description="Reason for search completion")
    runtime_seconds: float = Field(..., description="Total wall-clock runtime in seconds")
    history: List[GenerationRecord] = Field(default_factory=list, description="Generational convergence telemetry")
    initial_mhc: float = Field(..., description="Initial generation best MHC")
    improvement_mhc: float = Field(..., description="Absolute MHC reduction: initial_mhc - best_mhc")
    improvement_percentage: float = Field(..., description="Percentage MHC reduction relative to initial")
    candidate_pool: List[ContinuousLayout] = Field(default_factory=list, description="Unique feasible layouts collected during run")

