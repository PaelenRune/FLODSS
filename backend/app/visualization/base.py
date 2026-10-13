"""Visualization structures for layout rendering."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution


class DepartmentRenderBox(BaseModel):
    """Normalized 2D box for frontend canvas rendering."""

    department_id: str
    name: str
    x: float
    y: float
    width: float
    height: float
    color: str = "#3B82F6"
    label: str = ""


class LayoutRenderData(BaseModel):
    """Frontend-ready representation of the layout."""

    facility_width: float
    facility_height: float
    boxes: List[DepartmentRenderBox] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseLayoutRenderer(ABC):
    """Abstract interface for preparing layout rendering payloads."""

    @abstractmethod
    def prepare_render_data(
        self,
        problem: FacilityLayoutProblem,
        solution: LayoutSolution,
    ) -> LayoutRenderData:
        pass
