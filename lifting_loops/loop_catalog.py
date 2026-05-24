from __future__ import annotations

from lifting_loops.materials import get_material
from lifting_loops.models import LoopInput


DEFAULT_DIAMETERS = (12.0, 16.0, 20.0, 25.0, 32.0)


def build_default_catalog(
    steel_grade: str = "S355",
    k_bend: float = 0.8,
    tolerance: float = 10.0,
) -> list[LoopInput]:
    """Build loop candidates using one steel grade for all diameters."""

    material = get_material(steel_grade)
    loops = []
    for diameter in DEFAULT_DIAMETERS:
        loops.append(
            LoopInput(
                diameter=diameter,
                steel_grade=material.grade,
                fuk=material.fuk,
                k_bend=k_bend,
                tolerance=tolerance,
            )
        )
    return loops
