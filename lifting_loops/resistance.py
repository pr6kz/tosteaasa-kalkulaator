from __future__ import annotations

import math

from lifting_loops.models import LoopInput


def bar_area(diameter: float) -> float:
    """Single bar branch area in mm2, thesis equation 4.6."""

    if diameter <= 0:
        raise ValueError("diameter must be positive")
    return math.pi * diameter**2 / 4.0


def characteristic_tension_resistance(loop: LoopInput) -> float:
    """Nrk in kN, thesis equation 4.5."""

    return 2.0 * bar_area(loop.diameter) * loop.fuk / 1000.0


def cover_reduction_factor(
    thickness: float,
    loop: LoopInput,
    effective_thickness: float | None = None,
) -> float:
    """k_grade according to thesis equations 4.3 and 4.4."""

    b = effective_thickness if effective_thickness is not None else thickness
    if b <= 0:
        raise ValueError("thickness must be positive")
    numerator = b - loop.diameter - 2.0 * loop.tolerance
    if loop.steel_grade == "S235":
        denominator = 6.4 * loop.diameter
    elif loop.steel_grade in {"S355", "1.4301"}:
        denominator = 9.0 * loop.diameter
    else:
        raise ValueError(f"unsupported steel grade {loop.steel_grade!r}")
    return max(0.0, min(numerator / denominator, 1.0))


def reduced_admissible_resistance(
    loop: LoopInput,
    thickness: float,
    gamma_s: float,
    effective_thickness: float | None = None,
) -> float:
    """Radm,red in kN, thesis equation 4.7."""

    return (
        loop.k_bend
        * cover_reduction_factor(thickness, loop, effective_thickness)
        * characteristic_tension_resistance(loop)
        / gamma_s
    )


def rotation_admissible_resistance(
    loop: LoopInput,
    thickness: float,
    gamma_s: float,
    k_rot_min: float,
    effective_thickness: float | None = None,
) -> float:
    """Radm,rot,i in kN, thesis equation 4.8."""

    return (
        loop.k_bend
        * cover_reduction_factor(thickness, loop, effective_thickness)
        * k_rot_min
        * characteristic_tension_resistance(loop)
        / gamma_s
    )

