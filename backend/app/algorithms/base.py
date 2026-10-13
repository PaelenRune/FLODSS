"""Abstract Base Class and contract for all Facility Layout Optimization algorithms."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution


class AlgorithmCategory(str, Enum):
    """Categorization of industrial layout generation and optimization methods."""

    CONSTRUCTION = "construction"      # e.g. CORELAP, ALDEP, MAT
    IMPROVEMENT = "improvement"        # e.g. CRAFT, BLOCPLAN
    METAHEURISTIC = "metaheuristic"    # e.g. Genetic Algorithm, Simulated Annealing, PSO, Tabu Search
    EXACT = "exact"                    # e.g. MILP, MIP, OR-Tools, Branch & Bound
    HYBRID = "hybrid"                  # Multi-stage or combined heuristic approaches


class ValidationResult(BaseModel):
    """Result of algorithm-specific problem compatibility checks."""

    is_valid: bool = Field(..., description="True if problem is solvable by this algorithm")
    errors: List[str] = Field(default_factory=list, description="Fatal incompatibility messages")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings or advisories")


class BaseLayoutAlgorithm(ABC):
    """Abstract Base Class that every layout generation/optimization algorithm must inherit from.
    
    This ensures loose coupling: new algorithms (CORELAP, ALDEP, CRAFT, GA, MILP, etc.)
    can be plugged in without modifying existing codebase.
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """Initialize algorithm with optional custom parameters."""
        self._parameters: Dict[str, Any] = self.default_parameters.copy()
        if parameters:
            self._parameters.update(parameters)

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name of the algorithm (e.g. 'corelap', 'craft', 'genetic_algorithm')."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version string of the algorithm implementation (e.g. '1.0.0')."""
        pass

    @property
    @abstractmethod
    def category(self) -> AlgorithmCategory:
        """Methodology category (CONSTRUCTION, IMPROVEMENT, METAHEURISTIC, EXACT, HYBRID)."""
        pass

    @property
    def default_parameters(self) -> Dict[str, Any]:
        """Default hyperparameter dictionary. Can be overridden by subclasses."""
        return {}

    @property
    def parameters(self) -> Dict[str, Any]:
        """Current runtime parameter configuration."""
        return self._parameters

    @property
    def supported_problem_types(self) -> List[str]:
        """List of problem capabilities supported (e.g. ['unequal_areas', 'fixed_positions', 'continuous'])."""
        return ["equal_areas", "unequal_areas"]

    @property
    def metadata(self) -> Dict[str, Any]:
        """Algorithm metadata including reference literature, time complexity, and author."""
        return {
            "name": self.name,
            "version": self.version,
            "category": self.category.value,
            "parameters": self.parameters,
            "supported_problem_types": self.supported_problem_types,
        }

    def validate(self, problem: FacilityLayoutProblem) -> ValidationResult:
        """Validate whether the given problem meets the preconditions for this algorithm.
        
        Subclasses should override this method to enforce specific constraints (e.g. CRAFT
        requires an initial layout, CORELAP requires a relationship chart).
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not problem.departments:
            errors.append("Problem contains no departments.")

        if problem.facility.area and problem.total_required_area > problem.facility.area:
            warnings.append(
                f"Total department area ({problem.total_required_area}) exceeds facility area ({problem.facility.area})."
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    @abstractmethod
    def solve(self, problem: FacilityLayoutProblem, **kwargs) -> LayoutSolution:
        """Execute the optimization/generation algorithm and return a LayoutSolution.
        
        Args:
            problem: Complete FacilityLayoutProblem specification.
            **kwargs: Dynamic execution options (e.g. progress_callback, random_seed).
            
        Returns:
            LayoutSolution containing placement coordinates, dimensions, and objective values.
        """
        pass


class BaseImprovementAlgorithm(BaseLayoutAlgorithm, ABC):
    """Abstract Base Class for layout improvement algorithms (e.g. CRAFT, 2-opt, Tabu search).
    
    Unlike construction heuristics that create a layout from scratch, improvement algorithms
    require a complete, feasible initial layout and iteratively modify department positions
    to minimize material handling cost or multi-criteria penalty.
    """

    @property
    def category(self) -> AlgorithmCategory:
        return AlgorithmCategory.IMPROVEMENT

    @abstractmethod
    def improve(
        self,
        problem: FacilityLayoutProblem,
        initial_layout: Any,
        **kwargs,
    ) -> LayoutSolution:
        """Iteratively improve an existing layout solution.
        
        Args:
            problem: Problem definition with facility, departments, and flows.
            initial_layout: Complete, feasible initial layout (ContinuousLayout, LayoutSolution, or dict).
            **kwargs: Algorithm hyperparameters and execution options.
            
        Returns:
            Improved LayoutSolution.
        """
        pass

    def solve(self, problem: FacilityLayoutProblem, **kwargs) -> LayoutSolution:
        """Bridge solve() call to improve() using initial_layout argument."""
        initial_layout = kwargs.get("initial_layout")
        if initial_layout is None:
            raise ValueError(
                f"Improvement algorithm '{self.name}' requires an 'initial_layout' keyword argument to execute."
            )
        return self.improve(problem, initial_layout, **kwargs)

