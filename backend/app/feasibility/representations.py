"""Interface contracts and structural representations for future metaheuristic packing paradigms.

Academic Paradigms:
    - Slicing Tree / Normalized Polish Expression (Otten 1982, Wong & Liu 1986)
    - Sequence-Pair Representation (Murata, Fujiyoshi, Nakatake & Kajitani 1996)
    - Rectangle Packing Heuristics (Guillotine / Best-Fit / Bottom-Left)
    - Feasibility Repair Strategies
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.models.department import Department
from app.models.geometry import BoundingBox, Dimensions2D, Point2D
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement


class SlicingCutType(str, Enum):
    """Orientation of orthogonal bisecting slice."""

    HORIZONTAL = "H"  # Horizontal cut line (splits top and bottom)
    VERTICAL = "V"    # Vertical cut line (splits left and right)


class SlicingNode(BaseModel):
    """Recursive node in a binary slicing tree."""

    department_id: Optional[str] = Field(
        default=None,
        description="Department identifier if this is a leaf node; None for internal cut nodes",
    )
    cut_type: Optional[SlicingCutType] = Field(
        default=None,
        description="Cut orientation ('H' or 'V') if this is an internal cut node",
    )
    cut_ratio: float = Field(
        default=0.5,
        ge=0.01,
        le=0.99,
        description="Normalized cut position along cut axis [0.01, 0.99]",
    )
    left: Optional["SlicingNode"] = Field(
        default=None,
        description="Left / Bottom child node",
    )
    right: Optional["SlicingNode"] = Field(
        default=None,
        description="Right / Top child node",
    )

    @property
    def is_leaf(self) -> bool:
        return self.department_id is not None


class SlicingTree(BaseModel):
    """Slicing Tree layout model guaranteeing 100% non-overlapping rectangular blocks."""

    root: SlicingNode
    problem_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_continuous_layout(
        self,
        facility_width: float,
        facility_height: float,
        problem_id: Optional[str] = None,
    ) -> ContinuousLayout:
        """Evaluate slicing tree geometry recursively into a ContinuousLayout."""
        placements: Dict[str, ContinuousPlacement] = {}

        def slice_region(node: SlicingNode, x: float, y: float, w: float, h: float) -> None:
            if node.is_leaf and node.department_id:
                placements[node.department_id] = ContinuousPlacement(
                    department_id=node.department_id,
                    x=round(x, 2),
                    y=round(y, 2),
                    width=round(w, 2),
                    height=round(h, 2),
                )
                return

            if node.cut_type == SlicingCutType.VERTICAL:
                # Vertical cut divides width: left (x..x + w1) and right (x + w1..x + w)
                w1 = w * node.cut_ratio
                w2 = w - w1
                if node.left:
                    slice_region(node.left, x, y, w1, h)
                if node.right:
                    slice_region(node.right, x + w1, y, w2, h)
            elif node.cut_type == SlicingCutType.HORIZONTAL:
                # Horizontal cut divides height: bottom (y..y + h1) and top (y + h1..y + h)
                h1 = h * node.cut_ratio
                h2 = h - h1
                if node.left:
                    slice_region(node.left, x, y, w, h1)
                if node.right:
                    slice_region(node.right, x, y + h1, w, h2)

        slice_region(self.root, 0.0, 0.0, facility_width, facility_height)

        return ContinuousLayout(
            problem_id=problem_id or self.problem_id,
            facility_width=facility_width,
            facility_height=facility_height,
            placements=placements,
        )

    def to_polish_expression(self) -> List[str]:
        """Convert slicing tree into postorder normalized Polish expression."""
        expr: List[str] = []

        def postorder(node: Optional[SlicingNode]) -> None:
            if not node:
                return
            if node.is_leaf and node.department_id:
                expr.append(node.department_id)
            else:
                postorder(node.left)
                postorder(node.right)
                if node.cut_type:
                    expr.append(node.cut_type.value)

        postorder(self.root)
        return expr

    @classmethod
    def from_polish_expression(cls, expr: List[str], problem_id: Optional[str] = None) -> "SlicingTree":
        """Reconstruct a SlicingTree from a postorder Polish expression."""
        stack: List[SlicingNode] = []
        for token in expr:
            if token in ("H", "V"):
                if len(stack) < 2:
                    raise ValueError(f"Malformed Polish expression: insufficient operands for operator '{token}'.")
                right = stack.pop()
                left = stack.pop()
                cut = SlicingCutType.HORIZONTAL if token == "H" else SlicingCutType.VERTICAL
                stack.append(SlicingNode(cut_type=cut, left=left, right=right))
            else:
                stack.append(SlicingNode(department_id=token))

        if len(stack) != 1:
            raise ValueError(f"Malformed Polish expression: remaining items on stack: {len(stack)}.")

        return cls(root=stack.pop(), problem_id=problem_id)


class SequencePair(BaseModel):
    """Sequence-Pair representation encoding relative 2D topological positions.
    
    References:
        Murata et al. (1996). VLSI module placement based on rectangle-packing by the sequence-pair.
    """

    positive_sequence: List[str] = Field(..., description="Permutation Gamma+ of department IDs")
    negative_sequence: List[str] = Field(..., description="Permutation Gamma- of department IDs")

    def is_left_of(self, dept_a: str, dept_b: str) -> bool:
        """Department A is strictly left of Department B iff A precedes B in both sequences."""
        pos_a = self.positive_sequence.index(dept_a)
        pos_b = self.positive_sequence.index(dept_b)
        neg_a = self.negative_sequence.index(dept_a)
        neg_b = self.negative_sequence.index(dept_b)
        return pos_a < pos_b and neg_a < neg_b

    def is_below(self, dept_a: str, dept_b: str) -> bool:
        """Department A is strictly below Department B iff B precedes A in Gamma+ and A precedes B in Gamma-."""
        pos_a = self.positive_sequence.index(dept_a)
        pos_b = self.positive_sequence.index(dept_b)
        neg_a = self.negative_sequence.index(dept_a)
        neg_b = self.negative_sequence.index(dept_b)
        return pos_b < pos_a and neg_a < neg_b


class BasePackingStrategy(ABC):
    """Abstract interface contract for rectangular packing strategies."""

    @abstractmethod
    def pack(
        self,
        departments: List[Department],
        facility_width: float,
        facility_height: float,
        **kwargs,
    ) -> ContinuousLayout:
        """Pack departments into facility returning continuous rectangular layout."""
        pass


class BaseFeasibilityRepairStrategy(ABC):
    """Abstract interface contract for post-processing layout repair heuristics."""

    @abstractmethod
    def repair(
        self,
        layout: ContinuousLayout,
        problem: FacilityLayoutProblem,
        **kwargs,
    ) -> Tuple[ContinuousLayout, bool, List[str]]:
        """Attempt to eliminate overlaps or boundary violations, returning repaired layout and log."""
        pass
