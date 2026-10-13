"""Service layer for problem management, filesystem storage, and validation."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ValidationError

from app.models.problem import FacilityLayoutProblem
from app.services.problem_loader import ProblemLoaderFactory
from app.services.problem_analyzer import ProblemAnalyzer, ProblemFingerprint


class ProblemSummary(BaseModel):
    """Compact summary of a layout problem for listing and cataloging."""

    id: str
    name: str
    facility_width: float
    facility_height: float
    facility_area: float
    department_count: int
    total_required_area: float
    area_utilization: float
    flow_count: int
    relationship_count: int
    constraint_count: int
    file_path: Optional[str] = None


class ProblemValidationReport(BaseModel):
    """Detailed validation outcome report with diagnostics and structural metrics."""

    is_valid: bool = Field(..., description="True if problem is strictly valid and schema-compliant")
    errors: List[str] = Field(default_factory=list, description="Fatal consistency or constraint errors")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal advisories")
    fingerprint: Optional[ProblemFingerprint] = Field(default=None, description="Computed structural fingerprint if valid")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics")


class ProblemService:
    """Manages loading, validation, saving, and cataloging of facility layout problems."""

    def __init__(self, examples_dir: Optional[Union[str, Path]] = None):
        if examples_dir is None:
            # Default to data/examples directory relative to repository root
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            self.examples_dir = base_dir / "data" / "examples"
        else:
            self.examples_dir = Path(examples_dir)

    def load_problem(self, source: Union[str, Path, Dict[str, Any]]) -> FacilityLayoutProblem:
        """Load and validate a layout problem from file or raw dictionary."""
        return ProblemLoaderFactory.load(source)

    def validate_problem(self, data: Union[Dict[str, Any], FacilityLayoutProblem]) -> ProblemValidationReport:
        """Thoroughly validate problem data, catching schema, relational, and geometric errors."""
        errors: List[str] = []
        warnings: List[str] = []
        problem: Optional[FacilityLayoutProblem] = None

        if isinstance(data, FacilityLayoutProblem):
            problem = data
        else:
            try:
                problem = FacilityLayoutProblem.model_validate(data)
            except ValidationError as ve:
                for err in ve.errors():
                    field_loc = " -> ".join(str(loc) for loc in err.get("loc", []))
                    msg = err.get("msg", "Validation error")
                    # Clean up pydantic prefix "Value error, " if present
                    if msg.startswith("Value error, "):
                        msg = msg[len("Value error, "):]
                    err_desc = f"{field_loc}: {msg}" if field_loc else msg
                    errors.append(err_desc)
            except Exception as e:
                errors.append(f"Unexpected parsing error: {str(e)}")

        if problem is not None:
            # Check non-fatal warnings
            if problem.area_utilization > 0.95:
                warnings.append(
                    f"Very high area utilization ({problem.area_utilization * 100:.1f}%). Little or no space remaining for aisles and clearance."
                )
            if problem.area_utilization < 0.30:
                warnings.append(
                    f"Low area utilization ({problem.area_utilization * 100:.1f}%). Plant space might be significantly under-utilized."
                )
            if len(problem.flows) == 0:
                warnings.append("No material flows specified. Optimization will rely solely on qualitative relationships.")

            fingerprint = ProblemAnalyzer.extract_fingerprint(problem)
            stats = {
                "department_count": len(problem.departments),
                "total_required_area": problem.total_required_area,
                "facility_area": problem.facility.area,
                "area_utilization": round(problem.area_utilization, 4),
                "flow_count": len(problem.flows),
                "relationship_count": len(problem.relationships),
                "constraint_count": len(problem.constraints),
            }
            return ProblemValidationReport(
                is_valid=True,
                errors=[],
                warnings=warnings,
                fingerprint=fingerprint,
                stats=stats,
            )
        else:
            return ProblemValidationReport(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                fingerprint=None,
                stats={},
            )

    def save_problem(self, problem: FacilityLayoutProblem, target_path: Union[str, Path]) -> Path:
        """Serialize problem model to formatted JSON file."""
        out_path = Path(target_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(problem.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        return out_path

    def list_example_problems(self) -> List[ProblemSummary]:
        """Scan examples directory and return summary descriptions of available problems."""
        summaries: List[ProblemSummary] = []
        if not self.examples_dir.exists():
            return summaries

        for json_file in sorted(self.examples_dir.glob("*.json")):
            try:
                problem = self.load_problem(json_file)
                facility_area = problem.facility.area or (problem.facility.width * problem.facility.height)
                summaries.append(
                    ProblemSummary(
                        id=problem.id,
                        name=problem.name,
                        facility_width=problem.facility.width,
                        facility_height=problem.facility.height,
                        facility_area=facility_area,
                        department_count=len(problem.departments),
                        total_required_area=problem.total_required_area,
                        area_utilization=round(problem.area_utilization, 4),
                        flow_count=len(problem.flows),
                        relationship_count=len(problem.relationships),
                        constraint_count=len(problem.constraints),
                        file_path=str(json_file),
                    )
                )
            except Exception:
                continue

        return summaries

    def get_example_problem(self, problem_id: str) -> FacilityLayoutProblem:
        """Retrieve an example problem by its problem ID or filename."""
        if not self.examples_dir.exists():
            raise FileNotFoundError(f"Examples directory not found at {self.examples_dir}")

        # Search matching JSON files
        for json_file in self.examples_dir.glob("*.json"):
            if json_file.stem == problem_id:
                return self.load_problem(json_file)
            try:
                prob = self.load_problem(json_file)
                if prob.id == problem_id:
                    return prob
            except Exception:
                continue

        raise KeyError(f"Example problem '{problem_id}' not found in {self.examples_dir}")

    # Backward compatibility alias
    get_example_by_id = get_example_problem


problem_service = ProblemService()
