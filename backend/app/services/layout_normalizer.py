"""Layout normalization and deterministic geometric hashing/signature generation."""

import hashlib
from typing import Dict, Optional
from app.models.representation import ContinuousLayout, ContinuousPlacement


def normalize_layout(
    layout: ContinuousLayout,
    precision: int = 4,
    decimal_places: Optional[int] = None,
) -> ContinuousLayout:
    """Normalize a ContinuousLayout deterministically.
    
    1. Sorts placements alphabetically by department_id.
    2. Rounds floating-point coordinates, dimensions, and orientations to specified precision.
    """
    prec = decimal_places if decimal_places is not None else precision
    sorted_ids = sorted(layout.placements.keys())
    normalized_placements: Dict[str, ContinuousPlacement] = {}

    for dept_id in sorted_ids:
        p = layout.placements[dept_id]
        normalized_placements[dept_id] = ContinuousPlacement(
            department_id=dept_id,
            x=round(p.x, prec),
            y=round(p.y, prec),
            width=round(p.width, prec),
            height=round(p.height, prec),
            orientation_degrees=round(p.orientation_degrees, prec),
            metadata=p.metadata,
        )

    return ContinuousLayout(
        facility_width=round(layout.facility_width, prec),
        facility_height=round(layout.facility_height, prec),
        placements=normalized_placements,
        reserved_zones=layout.reserved_zones,
    )


def generate_layout_signature(
    layout: ContinuousLayout,
    precision: int = 4,
    decimal_places: Optional[int] = None,
) -> str:
    """Generate a deterministic, non-cryptographic geometric signature (SHA-256 hash).
    
    The signature is derived strictly from normalized placement geometries:
    (department_id, x, y, width, height, orientation).
    Objective values, runtimes, and metadata are excluded.
    """
    prec = decimal_places if decimal_places is not None else precision
    normalized = normalize_layout(layout, precision=prec)
    tokens = []

    for dept_id, p in normalized.placements.items():
        token = f"{dept_id}:{p.x:.{precision}f},{p.y:.{precision}f},{p.width:.{precision}f},{p.height:.{precision}f},{p.orientation_degrees:.{precision}f}"
        tokens.append(token)

    canonical_repr = ";".join(tokens)
    hasher = hashlib.sha256()
    hasher.update(canonical_repr.encode("utf-8"))
    return hasher.hexdigest()
