"""Precomputed matrix services for Distance, Flow, and Relationship evaluations."""

from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field

from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.models.representation import ContinuousLayout
from app.models.relationship import RelationshipType, RELATIONSHIP_DEFAULT_SCORES
from app.services.geometry_engine import GeometryEngine, DistanceMetricType


class DistanceMatrixResult(BaseModel):
    """Pairwise distance matrix across all facility departments."""

    metric: DistanceMetricType
    department_ids: List[str] = Field(..., description="Deterministically sorted department IDs")
    index_mapping: Dict[str, int] = Field(..., description="Mapping of department ID to 0-based matrix index")
    matrix: List[List[float]] = Field(..., description="Dense 2D distance matrix")

    def get_distance(self, dept_a: str, dept_b: str) -> float:
        """Query distance between two departments in O(1) time."""
        idx_a = self.index_mapping.get(dept_a)
        idx_b = self.index_mapping.get(dept_b)
        if idx_a is None or idx_b is None:
            raise KeyError(f"Department '{dept_a if idx_a is None else dept_b}' not found in distance matrix.")
        return self.matrix[idx_a][idx_b]

    @property
    def department_order(self) -> List[str]:
        return self.department_ids

    @property
    def numpy_matrix(self) -> np.ndarray:
        return np.array(self.matrix, dtype=float)


class FlowMatrixResult(BaseModel):
    """Dense directed material flow matrix."""

    department_ids: List[str] = Field(..., description="Deterministically sorted department IDs")
    index_mapping: Dict[str, int] = Field(..., description="Mapping of department ID to 0-based matrix index")
    matrix: List[List[float]] = Field(..., description="Directed flow matrix where row=source, col=target")
    cost_matrix: List[List[float]] = Field(default_factory=list, description="Unit cost per distance C_ij")
    total_flow: float = Field(default=0.0, ge=0, description="Sum of all directed flow quantities")

    @property
    def department_order(self) -> List[str]:
        return self.department_ids

    def get_flow(self, source: str, target: str) -> float:
        """Query directed flow quantity from source to target."""
        idx_src = self.index_mapping.get(source)
        idx_tgt = self.index_mapping.get(target)
        if idx_src is None or idx_tgt is None:
            return 0.0
        return self.matrix[idx_src][idx_tgt]

    def get_unit_cost(self, source: str, target: str, fallback_cost: float = 1.0) -> float:
        """Query unit cost per distance from source to target."""
        idx_src = self.index_mapping.get(source)
        idx_tgt = self.index_mapping.get(target)
        if idx_src is None or idx_tgt is None or not self.cost_matrix:
            return fallback_cost
        return self.cost_matrix[idx_src][idx_tgt]

    @property
    def numpy_matrix(self) -> np.ndarray:
        return np.array(self.matrix, dtype=float)


class RelationshipMatrixResult(BaseModel):
    """Dense Muther SLP relationship score matrix."""

    department_ids: List[str] = Field(..., description="Deterministically sorted department IDs")
    index_mapping: Dict[str, int] = Field(..., description="Mapping of department ID to 0-based matrix index")
    matrix: List[List[float]] = Field(..., description="Symmetric numeric closeness score matrix")
    raw_types: List[List[str]] = Field(default_factory=list, description="Original relationship ratings (A/E/I/O/U/X)")

    @property
    def department_order(self) -> List[str]:
        return self.department_ids

    def get_score(self, dept_a: str, dept_b: str) -> float:
        """Query numerical relationship score between two departments."""
        idx_a = self.index_mapping.get(dept_a)
        idx_b = self.index_mapping.get(dept_b)
        if idx_a is None or idx_b is None:
            return 0.0
        return self.matrix[idx_a][idx_b]

    def get_weight(self, dept_a: str, dept_b: str) -> float:
        """Alias for get_score."""
        return self.get_score(dept_a, dept_b)

    def get_rating(self, dept_a: str, dept_b: str) -> str:
        """Query original Muther rating letter between two departments."""
        idx_a = self.index_mapping.get(dept_a)
        idx_b = self.index_mapping.get(dept_b)
        if idx_a is None or idx_b is None or not self.raw_types:
            return "U"
        return self.raw_types[idx_a][idx_b]

    @property
    def numpy_matrix(self) -> np.ndarray:
        return np.array(self.matrix, dtype=float)


class DistanceMatrixService:
    """Computes and caches inter-department distance matrices for layouts."""

    @classmethod
    def compute(
        cls,
        layout: Union[ContinuousLayout, LayoutSolution],
        metric: DistanceMetricType = DistanceMetricType.MANHATTAN,
    ) -> DistanceMatrixResult:
        """Build full symmetric distance matrix between all placed departments."""
        if isinstance(layout, LayoutSolution):
            cont_layout = ContinuousLayout.from_layout_solution(
                layout,
                facility_width=1.0,  # Only placements are required for distances
                facility_height=1.0,
            )
        else:
            cont_layout = layout

        dept_ids = sorted(list(cont_layout.placements.keys()))
        n = len(dept_ids)
        index_mapping = {dept_id: i for i, dept_id in enumerate(dept_ids)}

        matrix: List[List[float]] = [[0.0 for _ in range(n)] for _ in range(n)]
        boxes = [cont_layout.placements[d_id].bounding_box for d_id in dept_ids]

        for i in range(n):
            for j in range(i + 1, n):
                dist = GeometryEngine.calculate_distance(boxes[i], boxes[j], metric=metric)
                matrix[i][j] = round(dist, 4)
                matrix[j][i] = round(dist, 4)

        return DistanceMatrixResult(
            metric=metric,
            department_ids=dept_ids,
            index_mapping=index_mapping,
            matrix=matrix,
        )


class FlowMatrixService:
    """Constructs deterministic numeric flow matrices from problem definitions."""

    @classmethod
    def compute(
        cls,
        problem: FacilityLayoutProblem,
        department_ids: Optional[List[str]] = None,
        default_cost: float = 1.0,
    ) -> FlowMatrixResult:
        """Build directed flow matrix F_ij and cost matrix C_ij."""
        if department_ids is None:
            dept_ids = sorted([d.id for d in problem.departments])
        else:
            dept_ids = sorted(list(department_ids))

        n = len(dept_ids)
        index_mapping = {dept_id: i for i, dept_id in enumerate(dept_ids)}

        flow_matrix: List[List[float]] = [[0.0 for _ in range(n)] for _ in range(n)]
        cost_matrix: List[List[float]] = [[default_cost for _ in range(n)] for _ in range(n)]
        total_flow = 0.0

        for flow in problem.flows:
            src_idx = index_mapping.get(flow.source_department)
            tgt_idx = index_mapping.get(flow.target_department)
            if src_idx is not None and tgt_idx is not None:
                flow_matrix[src_idx][tgt_idx] += flow.quantity
                cost = flow.cost_per_unit_distance if flow.cost_per_unit_distance is not None else default_cost
                cost_matrix[src_idx][tgt_idx] = cost
                total_flow += flow.quantity

        return FlowMatrixResult(
            department_ids=dept_ids,
            index_mapping=index_mapping,
            matrix=flow_matrix,
            cost_matrix=cost_matrix,
            total_flow=round(total_flow, 4),
        )


class RelationshipMatrixService:
    """Constructs symmetric Muther SLP relationship score matrices."""

    @classmethod
    def compute(
        cls,
        problem: FacilityLayoutProblem,
        department_ids: Optional[List[str]] = None,
    ) -> RelationshipMatrixResult:
        """Build symmetric closeness score matrix R_ij."""
        if department_ids is None:
            dept_ids = sorted([d.id for d in problem.departments])
        else:
            dept_ids = sorted(list(department_ids))

        n = len(dept_ids)
        index_mapping = {dept_id: i for i, dept_id in enumerate(dept_ids)}

        score_matrix: List[List[float]] = [[0.0 for _ in range(n)] for _ in range(n)]
        rating_matrix: List[List[str]] = [["U" for _ in range(n)] for _ in range(n)]

        for rel in problem.relationships:
            idx_a = index_mapping.get(rel.department_a)
            idx_b = index_mapping.get(rel.department_b)
            if idx_a is not None and idx_b is not None:
                # Determine score from explicit field or standard mapping
                score = rel.score
                if score == 0.0 and rel.relationship_type.value != "U":
                    score = RELATIONSHIP_DEFAULT_SCORES.get(rel.relationship_type, 0.0)

                # Muther closeness relationships are symmetric between two areas
                score_matrix[idx_a][idx_b] = score
                score_matrix[idx_b][idx_a] = score
                rating_matrix[idx_a][idx_b] = rel.relationship_type.value
                rating_matrix[idx_b][idx_a] = rel.relationship_type.value

        return RelationshipMatrixResult(
            department_ids=dept_ids,
            index_mapping=index_mapping,
            matrix=score_matrix,
            raw_types=rating_matrix,
        )
