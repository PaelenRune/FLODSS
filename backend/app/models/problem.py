"""Facility layout problem specification model."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.facility import Facility
from app.models.department import Department
from app.models.flow import Flow
from app.models.relationship import Relationship
from app.models.constraint import Constraint, ConstraintType, ConstraintClassification


class PrimaryObjective(str, Enum):
    """Standard primary optimization objectives in industrial layout planning."""

    MINIMIZE_FLOW_DISTANCE = "minimize_flow_distance"          # Material Handling Cost (MHC)
    MAXIMIZE_RELATIONSHIPS = "maximize_relationships"          # Qualitative closeness rating satisfaction
    MULTI_OBJECTIVE = "multi_objective"                        # Weighted sum or Pareto optimization
    MINIMIZE_TOTAL_COST = "minimize_total_cost"                # Flow cost + reconfig cost + penalties


class DistanceMetric(str, Enum):
    """Distance metrics used in spatial calculations."""

    RECTILINEAR = "rectilinear"  # Manhattan / L1 distance (|dx| + |dy|), standard for aisles
    EUCLIDEAN = "euclidean"      # Straight line / L2 distance (sqrt(dx² + dy²))
    AISLE_NETWORK = "aisle_network"  # Graph-based aisle navigation distance


class ObjectiveDirection(str, Enum):
    """Direction of optimization for an objective."""

    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class ObjectiveItem(BaseModel):
    """Configuration for an individual optimization objective."""

    enabled: bool = Field(default=True, description="Whether this objective is active during optimization")
    weight: float = Field(default=1.0, ge=0.0, description="Relative weight in multi-criteria evaluation")
    direction: ObjectiveDirection = Field(
        default=ObjectiveDirection.MINIMIZE,
        description="Optimization direction: 'minimize' or 'maximize'",
    )

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, v: Any) -> Any:
        if isinstance(v, str):
            clean = v.strip().lower()
            if clean in ("min", "minimize"):
                return ObjectiveDirection.MINIMIZE
            if clean in ("max", "maximize"):
                return ObjectiveDirection.MAXIMIZE
            raise ValueError(f"Invalid objective direction '{v}'. Must be 'minimize' or 'maximize'.")
        return v


class ObjectiveConfig(BaseModel):
    """Configuration for optimization objective weights and metrics."""

    primary_objective: PrimaryObjective = Field(
        default=PrimaryObjective.MINIMIZE_FLOW_DISTANCE,
        description="Main objective target for algorithms",
    )
    distance_metric: DistanceMetric = Field(
        default=DistanceMetric.RECTILINEAR,
        description="Distance metric used for cost computation (Rectilinear is standard for factory aisles)",
    )
    flow_weight: float = Field(default=1.0, ge=0, description="Weight for quantitative flow cost")
    relationship_weight: float = Field(default=1.0, ge=0, description="Weight for qualitative relationship score")
    penalty_weight: float = Field(default=1.0, ge=0, description="Weight multiplier for soft constraint penalties")
    custom_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Arbitrary objective weights for multi-objective optimization",
    )
    objectives: Dict[str, ObjectiveItem] = Field(
        default_factory=dict,
        description="Granular objective configurations (e.g. material_handling_cost, relationship_score, area_utilization)",
    )

    @model_validator(mode="before")
    @classmethod
    def parse_legacy_and_granular(cls, data: Any) -> Any:
        """Handle dictionary of objectives directly passed as config."""
        if isinstance(data, dict):
            # If data contains a top-level "objectives" sub-dict
            if "objectives" not in data and any(
                k in data for k in ("material_handling_cost", "flow_distance", "relationship_score", "area_utilization")
            ):
                # Wrapped granular dictionary passed directly
                objs: Dict[str, Any] = {}
                rest: Dict[str, Any] = {}
                for k, v in data.items():
                    if isinstance(v, dict) and ("enabled" in v or "weight" in v or "direction" in v):
                        objs[k] = v
                    else:
                        rest[k] = v
                rest["objectives"] = objs
                return rest
        return data


class FacilityLayoutProblem(BaseModel):
    """Comprehensive problem formulation defining facility bounds, departments, flows, and constraints."""

    id: str = Field(..., description="Unique problem identifier (e.g. 'FLP_CASE_01')")
    name: str = Field(default="Facility Layout Problem", description="Human-readable case name")
    facility: Facility = Field(..., description="Facility boundary and floor area")
    departments: List[Department] = Field(..., min_length=1, description="List of departments to place")
    flows: List[Flow] = Field(default_factory=list, description="Quantitative material flows between departments")
    relationships: List[Relationship] = Field(
        default_factory=list, description="Qualitative closeness preferences (REL chart)"
    )
    constraints: List[Constraint] = Field(
        default_factory=list, description="Operational, spatial, and regulatory constraints"
    )
    objective_config: ObjectiveConfig = Field(
        default_factory=ObjectiveConfig,
        description="Configuration of objective functions and weights",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata (e.g. author, case study source, version)",
    )

    @model_validator(mode="before")
    @classmethod
    def handle_objective_aliases(cls, data: Any) -> Any:
        """Allow 'objectives' key in JSON to seamlessly populate 'objective_config'."""
        if isinstance(data, dict):
            if "objectives" in data and "objective_config" not in data:
                raw_objs = data.pop("objectives")
                if isinstance(raw_objs, dict):
                    data["objective_config"] = {"objectives": raw_objs}
        return data

    @property
    def objectives(self) -> Dict[str, ObjectiveItem]:
        """Convenience property accessing objective items in objective_config."""
        return self.objective_config.objectives

    @property
    def total_required_area(self) -> float:
        """Sum of required areas for all departments."""
        return sum(d.required_area for d in self.departments)

    @property
    def area_utilization(self) -> float:
        """Ratio of required department area to total facility area."""
        if self.facility.area and self.facility.area > 0:
            return self.total_required_area / self.facility.area
        return 0.0

    @property
    def reserved_zones(self) -> List[Any]:
        """Convenience property accessing facility reserved zones."""
        return self.facility.reserved_zones

    def get_department(self, dept_id: str) -> Optional[Department]:
        """Lookup department by its ID."""
        for dept in self.departments:
            if dept.id == dept_id:
                return dept
        return None

    @model_validator(mode="after")
    def validate_problem_integrity(self) -> "FacilityLayoutProblem":
        """Verify internal consistency and integrity of the problem definition with clear error messages."""
        # 1. Facility dimension checks
        if self.facility.width <= 0:
            raise ValueError(f"Facility width must be positive, got {self.facility.width}.")
        if self.facility.height <= 0:
            raise ValueError(f"Facility height must be positive, got {self.facility.height}.")
        if self.facility.area is not None and self.facility.area <= 0:
            raise ValueError(f"Facility area must be positive, got {self.facility.area}.")

        # 2. Duplicate department checks
        seen_ids = set()
        duplicates = set()
        for dept in self.departments:
            if dept.id in seen_ids:
                duplicates.add(dept.id)
            seen_ids.add(dept.id)
            if dept.required_area <= 0:
                raise ValueError(
                    f"Department '{dept.id}' has invalid required area ({dept.required_area}). Must be positive."
                )

        if duplicates:
            raise ValueError(
                f"Duplicate department IDs found in problem definition: {sorted(list(duplicates))}."
            )

        dept_ids = seen_ids

        # 3. Check total department area vs facility area
        if self.facility.area and self.total_required_area > self.facility.area:
            raise ValueError(
                f"Total department area ({self.total_required_area:.1f}) exceeds facility area ({self.facility.area:.1f})."
            )

        # 4. Validate flow endpoints and flow quantities
        for flow in self.flows:
            if flow.quantity < 0:
                raise ValueError(
                    f"Flow between '{flow.source_department}' and '{flow.target_department}' has negative quantity ({flow.quantity})."
                )
            if flow.source_department not in dept_ids:
                raise ValueError(
                    f"Flow references unknown source department '{flow.source_department}'."
                )
            if flow.target_department not in dept_ids:
                raise ValueError(
                    f"Flow references unknown target department '{flow.target_department}'."
                )

        # 5. Validate relationship endpoints
        for rel in self.relationships:
            if rel.department_a not in dept_ids:
                raise ValueError(
                    f"Relationship references unknown department_a '{rel.department_a}'."
                )
            if rel.department_b not in dept_ids:
                raise ValueError(
                    f"Relationship references unknown department_b '{rel.department_b}'."
                )

        # 6. Validate constraint involved departments
        for cst in self.constraints:
            for involved_id in cst.involved_departments:
                if involved_id not in dept_ids:
                    raise ValueError(
                        f"Constraint '{cst.id}' references unknown department '{involved_id}'."
                    )

        # 7. Validate objective config weights
        if self.objective_config.flow_weight < 0:
            raise ValueError("Flow weight in objective_config cannot be negative.")
        if self.objective_config.relationship_weight < 0:
            raise ValueError("Relationship weight in objective_config cannot be negative.")
        for obj_name, obj_item in self.objective_config.objectives.items():
            if obj_item.weight < 0:
                raise ValueError(f"Objective '{obj_name}' has negative weight ({obj_item.weight}).")

        return self
