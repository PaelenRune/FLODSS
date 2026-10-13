"""API endpoints for layout representation, geometric validation, and conversion."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.representation import (
    ContinuousLayout,
    GridLayout,
    LayoutRepresentationType,
)
from app.models.problem import FacilityLayoutProblem
from app.services.problem_service import problem_service
from app.services.layout_validator import LayoutValidator, LayoutValidationResult
from app.services.representation_converter import (
    ContinuousToGridConverter,
    GridToContinuousConverter,
    ConversionResult,
)
from app.services.geometry_engine import GeometryEngine
from app.services.layout_normalizer import normalize_layout, generate_layout_signature


router = APIRouter(prefix="/layouts", tags=["layouts"])

DATA_EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "examples"


class ValidateLayoutRequest(BaseModel):
    """Payload to validate a layout against a problem definition."""
    problem_id: Optional[str] = Field(None, description="Identifier of preloaded example problem")
    problem: Optional[Dict[str, Any]] = Field(None, description="Inline problem definition payload")
    layout: Dict[str, Any] = Field(..., description="Continuous layout or solution payload to validate")
    tolerance: float = Field(default=1e-4, description="Geometric floating point tolerance")


class ConvertContinuousToGridRequest(BaseModel):
    """Request model for continuous to grid conversion."""
    layout: Dict[str, Any] = Field(..., description="Continuous layout specification")
    cell_size: float = Field(default=5.0, gt=0, description="Target discretization grid cell size")


class ConvertGridToContinuousRequest(BaseModel):
    """Request model for grid to continuous conversion."""
    layout: Dict[str, Any] = Field(..., description="Discrete grid layout specification")


class LayoutSignatureResponse(BaseModel):
    """Response containing deterministic layout signature."""
    signature: str = Field(..., description="SHA-256 geometric invariant fingerprint")
    normalized_layout: ContinuousLayout = Field(..., description="Canonically ordered and rounded layout")


@router.get("/examples", response_model=List[Dict[str, Any]], summary="List Layout Examples")
def list_example_layouts() -> List[Dict[str, Any]]:
    """Retrieve catalog of available benchmark layouts stored in the filesystem."""
    layouts = []
    if DATA_EXAMPLES_DIR.exists():
        for file_path in DATA_EXAMPLES_DIR.glob("*layout*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    layouts.append({
                        "id": data.get("id", file_path.stem),
                        "problem_id": data.get("problem_id", ""),
                        "name": data.get("name", file_path.name),
                        "representation_type": data.get("representation_type", "continuous"),
                        "facility_width": data.get("facility_width", 0.0),
                        "facility_height": data.get("facility_height", 0.0),
                        "department_count": len(data.get("placements", {})),
                        "filename": file_path.name,
                    })
            except Exception:
                continue
    return layouts


@router.get("/examples/{layout_id}", response_model=Dict[str, Any], summary="Get Example Layout by ID")
def get_example_layout(layout_id: str) -> Dict[str, Any]:
    """Load and return the complete specification of an example layout."""
    if DATA_EXAMPLES_DIR.exists():
        for file_path in DATA_EXAMPLES_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("id") == layout_id or file_path.stem == layout_id:
                        return data
            except Exception:
                continue

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Example layout '{layout_id}' was not found.",
    )


@router.post("/validate", response_model=LayoutValidationResult, summary="Validate Layout Geometry")
def validate_layout(request: ValidateLayoutRequest) -> LayoutValidationResult:
    """Validate a layout against a problem definition.
    
    Verifies:
    - Facility boundary containment
    - Pairwise physical non-overlap
    - Department coverage (all required present, no unexpected IDs)
    - Department dimensional and aspect ratio limits
    - Fixed position and orientation compliance
    - Reserved zone clearance
    """
    problem: Optional[FacilityLayoutProblem] = None

    if request.problem:
        try:
            problem = FacilityLayoutProblem.model_validate(request.problem)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid problem payload: {str(e)}",
            )
    elif request.problem_id:
        try:
            problem = problem_service.get_example_problem(request.problem_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem '{request.problem_id}' not found.",
            )
    else:
        # Check if problem_id is specified in the layout itself
        layout_problem_id = request.layout.get("problem_id")
        if layout_problem_id:
            try:
                problem = problem_service.get_example_problem(layout_problem_id)
            except KeyError:
                pass

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'problem_id' or inline 'problem' specification must be provided for validation.",
        )

    try:
        result = LayoutValidator.validate(
            problem=problem,
            layout=request.layout,
            tolerance=request.tolerance,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Layout validation failed: {str(e)}",
        )


@router.post("/metrics", response_model=Dict[str, float], summary="Compute Layout Spatial Metrics")
def compute_metrics(layout: ContinuousLayout) -> Dict[str, float]:
    """Compute spatial utilization, bounding envelope, and compactness metrics."""
    return GeometryEngine.calculate_layout_metrics(layout)


@router.post("/signature", response_model=LayoutSignatureResponse, summary="Compute Geometric Signature")
def compute_signature(layout: ContinuousLayout) -> LayoutSignatureResponse:
    """Generate canonical geometric signature and normalized representation."""
    normalized = normalize_layout(layout)
    sig = generate_layout_signature(normalized)
    return LayoutSignatureResponse(signature=sig, normalized_layout=normalized)


@router.post("/convert/continuous-to-grid", response_model=ConversionResult, summary="Convert Continuous to Grid")
def convert_continuous_to_grid(request: ConvertContinuousToGridRequest) -> ConversionResult:
    """Convert continuous rectangular placements into discrete grid occupancy."""
    try:
        cont_layout = ContinuousLayout.model_validate(request.layout)
        converter = ContinuousToGridConverter(cell_size=request.cell_size)
        return converter.convert(cont_layout)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversion failed: {str(e)}",
        )


@router.post("/convert/grid-to-continuous", response_model=ConversionResult, summary="Convert Grid to Continuous")
def convert_grid_to_continuous(request: ConvertGridToContinuousRequest) -> ConversionResult:
    """Reconstruct continuous bounding boxes from discrete grid blocks."""
    try:
        grid_layout = GridLayout.model_validate(request.layout)
        converter = GridToContinuousConverter()
        return converter.convert(grid_layout)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversion failed: {str(e)}",
        )
