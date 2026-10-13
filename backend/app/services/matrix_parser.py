"""Parsers and converters for From-To Flow Matrices and Muther REL Relationship Charts."""

import csv
import io
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from app.models.flow import Flow
from app.models.relationship import Relationship, ClosenessRating, DEFAULT_RELATIONSHIP_SCORES


def parse_from_to_matrix(
    data: Union[np.ndarray, Sequence[Sequence[float]], str, Dict[str, Dict[str, float]]],
    department_ids: Optional[List[str]] = None,
    unit: str = "moves/day",
    cost_per_unit_distance: float = 1.0,
    directed: bool = True,
    skip_zero: bool = True,
) -> List[Flow]:
    """Convert From-To matrix data into a list of validated Flow models.
    
    Supports:
    1. CSV string formatted as a table (header row with dept IDs, first column with source IDs)
    2. NumPy 2D array or nested list with department_ids provided
    3. Nested dict: {source_id: {target_id: quantity}}
    
    Args:
        data: Matrix in one of the supported structures.
        department_ids: Ordered list of department IDs (required for 2D array/list).
        unit: Measurement unit (e.g. 'moves/day', 'pallets/hr').
        cost_per_unit_distance: Unit cost factor.
        directed: If True, keep separate directional flows. If False, combine (i,j) and (j,i) symmetrically.
        skip_zero: If True, exclude zero-volume pairs.
        
    Returns:
        List of Flow models.
    """
    flows: List[Flow] = []

    # Case 1: CSV string table
    if isinstance(data, str):
        reader = csv.reader(io.StringIO(data.strip()))
        rows = [r for r in reader if r]
        if not rows:
            return []
        
        # Header row contains target department IDs
        header = [c.strip() for c in rows[0]]
        # First header cell might be empty or label (e.g. 'From/To')
        parsed_dept_ids = header[1:] if len(header) > 1 else []
        
        flow_dict: Dict[Tuple[str, str], float] = {}

        for row in rows[1:]:
            if not row:
                continue
            src = row[0].strip()
            for col_idx, val_str in enumerate(row[1:]):
                if col_idx < len(parsed_dept_ids):
                    tgt = parsed_dept_ids[col_idx]
                    val_str = val_str.strip()
                    if not val_str or val_str == "-":
                        continue
                    try:
                        qty = float(val_str)
                    except ValueError:
                        raise ValueError(f"Invalid numeric flow value '{val_str}' at ({src}, {tgt}).")
                    if src != tgt:
                        flow_dict[(src, tgt)] = flow_dict.get((src, tgt), 0.0) + qty

        return _build_flows_from_dict(flow_dict, unit, cost_per_unit_distance, directed, skip_zero)

    # Case 2: Nested dictionary
    elif isinstance(data, dict):
        flow_dict = {}
        for src, targets in data.items():
            for tgt, qty in targets.items():
                if src != tgt:
                    flow_dict[(src, tgt)] = float(qty)
        return _build_flows_from_dict(flow_dict, unit, cost_per_unit_distance, directed, skip_zero)

    # Case 3: NumPy array or 2D Sequence
    else:
        matrix = np.asarray(data, dtype=float)
        if matrix.ndim != 2:
            raise ValueError(f"Expected 2D matrix, got shape {matrix.shape}.")
        if matrix.shape[0] != matrix.shape[1]:
            raise ValueError(f"From-To matrix must be square (N x N), got {matrix.shape}.")
        if department_ids is None or len(department_ids) != matrix.shape[0]:
            raise ValueError(
                f"department_ids count ({len(department_ids) if department_ids else 0}) must match matrix dimension ({matrix.shape[0]})."
            )

        flow_dict = {}
        n = matrix.shape[0]
        for i in range(n):
            for j in range(n):
                if i != j:
                    src = department_ids[i]
                    tgt = department_ids[j]
                    qty = float(matrix[i, j])
                    flow_dict[(src, tgt)] = qty

        return _build_flows_from_dict(flow_dict, unit, cost_per_unit_distance, directed, skip_zero)


def _build_flows_from_dict(
    flow_dict: Dict[Tuple[str, str], float],
    unit: str,
    cost_per_unit_distance: float,
    directed: bool,
    skip_zero: bool,
) -> List[Flow]:
    """Helper to assemble Flow objects respecting directionality and zero-skipping."""
    flows: List[Flow] = []

    if directed:
        for (src, tgt), qty in flow_dict.items():
            if qty < 0:
                raise ValueError(f"Negative flow quantity ({qty}) between '{src}' and '{tgt}'.")
            if skip_zero and qty == 0.0:
                continue
            flows.append(
                Flow(
                    source_department=src,
                    target_department=tgt,
                    quantity=qty,
                    unit=unit,
                    cost_per_unit_distance=cost_per_unit_distance,
                )
            )
    else:
        # Combine symmetric pairs: (i, j) and (j, i)
        processed_pairs = set()
        for (src, tgt), qty in flow_dict.items():
            pair_key = tuple(sorted([src, tgt]))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)
            
            d1, d2 = pair_key
            rev_qty = flow_dict.get((tgt, src), 0.0) if (src, tgt) == (d1, d2) else flow_dict.get((src, tgt), 0.0)
            total_qty = qty + rev_qty
            
            if total_qty < 0:
                raise ValueError(f"Negative combined flow quantity ({total_qty}) between '{d1}' and '{d2}'.")
            if skip_zero and total_qty == 0.0:
                continue
            flows.append(
                Flow(
                    source_department=d1,
                    target_department=d2,
                    quantity=total_qty,
                    unit=unit,
                    cost_per_unit_distance=cost_per_unit_distance,
                )
            )

    return flows


def flows_to_matrix(flows: List[Flow], department_ids: List[str]) -> Tuple[List[str], np.ndarray]:
    """Convert a list of Flow objects into a square NumPy From-To matrix.
    
    Returns:
        (department_ids, matrix)
    """
    dept_index = {d_id: idx for idx, d_id in enumerate(department_ids)}
    n = len(department_ids)
    matrix = np.zeros((n, n), dtype=float)

    for flow in flows:
        if flow.source_department in dept_index and flow.target_department in dept_index:
            i = dept_index[flow.source_department]
            j = dept_index[flow.target_department]
            matrix[i, j] += flow.quantity

    return department_ids, matrix


def parse_relationship_matrix(
    data: Union[Sequence[Sequence[str]], str, Dict[str, Dict[str, str]], List[Dict[str, Any]]],
    department_ids: Optional[List[str]] = None,
) -> List[Relationship]:
    """Convert Muther REL Chart matrix or tabular records into a list of Relationship models.
    
    Supports:
    1. CSV string formatted as list of records: 'department_a,department_b,relationship,reason'
    2. CSV string or 2D matrix formatted as Upper Triangular / Square REL grid:
           A, B, C
        A, -, A, E
        B, -, -, I
        C, -, -, -
    3. Nested dict: {dept_a: {dept_b: 'A'}}
    4. List of dicts: [{'department_a': 'A', 'department_b': 'B', 'relationship': 'E', 'reason': '...'}]
    
    Returns:
        List of Relationship models.
    """
    relationships: List[Relationship] = []

    # Case 1: List of dicts
    if isinstance(data, list) and data and isinstance(data[0], dict):
        for item in data:
            dept_a = item.get("department_a") or item.get("dept_a")
            dept_b = item.get("department_b") or item.get("dept_b")
            rel_str = item.get("relationship") or item.get("relationship_type") or item.get("rating")
            reason = item.get("reason")
            score = item.get("score")
            if dept_a and dept_b and rel_str:
                rating = _normalize_closeness_rating(rel_str)
                relationships.append(
                    Relationship(
                        department_a=str(dept_a).strip(),
                        department_b=str(dept_b).strip(),
                        relationship_type=rating,
                        reason=str(reason).strip() if reason else None,
                        score=float(score) if score is not None else None,
                    )
                )
        return relationships

    # Case 2: String (either tabular rows or grid)
    if isinstance(data, str):
        lines = [line.strip() for line in data.strip().splitlines() if line.strip()]
        if not lines:
            return []

        # Check if it's record-based CSV (e.g. contains 'department_a' or has <= 4 columns)
        first_line_cells = [c.strip() for c in lines[0].split(",")]
        is_tabular_records = any(h in first_line_cells[0].lower() for h in ("department", "dept", "source"))

        if is_tabular_records:
            reader = csv.DictReader(lines)
            for row in reader:
                dept_a = row.get("department_a") or row.get("dept_a") or row.get("source")
                dept_b = row.get("department_b") or row.get("dept_b") or row.get("target")
                rel_str = row.get("relationship") or row.get("relationship_type") or row.get("rating")
                reason = row.get("reason")
                score = row.get("score")
                if dept_a and dept_b and rel_str:
                    rating = _normalize_closeness_rating(rel_str)
                    relationships.append(
                        Relationship(
                            department_a=str(dept_a).strip(),
                            department_b=str(dept_b).strip(),
                            relationship_type=rating,
                            reason=str(reason).strip() if reason else None,
                            score=float(score) if score is not None and score != "" else None,
                        )
                    )
            return relationships
        else:
            # Matrix / Grid layout
            reader = csv.reader(lines)
            grid_rows = [[c.strip() for c in r] for r in reader if r]
            header = grid_rows[0]
            parsed_dept_ids = header[1:] if len(header) > 1 else []
            
            for row in grid_rows[1:]:
                if not row:
                    continue
                dept_a = row[0]
                for col_idx, cell_val in enumerate(row[1:]):
                    if col_idx < len(parsed_dept_ids):
                        dept_b = parsed_dept_ids[col_idx]
                        if cell_val in ("-", "", " "):
                            continue
                        if dept_a == dept_b:
                            continue
                        rating = _normalize_closeness_rating(cell_val)
                        relationships.append(
                            Relationship(
                                department_a=dept_a,
                                department_b=dept_b,
                                relationship_type=rating,
                            )
                        )
            return relationships

    # Case 3: Nested dict
    elif isinstance(data, dict):
        for dept_a, targets in data.items():
            for dept_b, rating_val in targets.items():
                if dept_a != dept_b and rating_val not in ("-", "", " "):
                    rating = _normalize_closeness_rating(rating_val)
                    relationships.append(
                        Relationship(
                            department_a=dept_a,
                            department_b=dept_b,
                            relationship_type=rating,
                        )
                    )
        return relationships

    # Case 4: 2D Sequence with department_ids
    else:
        if department_ids is None:
            raise ValueError("department_ids is required when parsing a 2D sequence of relationship ratings.")
        n = len(department_ids)
        for i in range(len(data)):
            for j in range(len(data[i])):
                if i < n and j < n and i != j:
                    val = str(data[i][j]).strip()
                    if val not in ("-", "", " "):
                        rating = _normalize_closeness_rating(val)
                        relationships.append(
                            Relationship(
                                department_a=department_ids[i],
                                department_b=department_ids[j],
                                relationship_type=rating,
                            )
                        )
        return relationships


def _normalize_closeness_rating(val: str) -> ClosenessRating:
    """Validate and convert string character to ClosenessRating enum."""
    clean = val.strip().upper()
    try:
        return ClosenessRating(clean)
    except ValueError:
        raise ValueError(
            f"Invalid Muther SLP closeness rating '{val}'. Allowed values are: {[r.value for r in ClosenessRating]}."
        )
