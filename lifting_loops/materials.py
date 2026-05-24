from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SteelMaterial:
    grade: str
    fuk: float


STEEL_MATERIALS: dict[str, SteelMaterial] = {
    "S235": SteelMaterial("S235", 360.0),
    "S355": SteelMaterial("S355", 510.0),
    "1.4301": SteelMaterial("1.4301", 500.0),
}


def get_material(grade: str) -> SteelMaterial:
    try:
        return STEEL_MATERIALS[grade]
    except KeyError as exc:
        valid = ", ".join(STEEL_MATERIALS)
        raise ValueError(f"Unknown steel grade {grade!r}. Valid grades: {valid}") from exc

