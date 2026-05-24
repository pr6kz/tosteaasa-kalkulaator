from __future__ import annotations

from lifting_loops.loads import sling_factor
from lifting_loops.models import FactorsInput, LoopInput
from lifting_loops.resistance import characteristic_tension_resistance, cover_reduction_factor


def admissible_demoulding_weight(
    loop: LoopInput,
    thickness: float,
    form_area: float,
    factors: FactorsInput,
    working_anchors: float,
    sling_angle: float,
    direction_factor: float = 1.0,
) -> float:
    """Gadm,adh in kN, thesis equation 4.10."""

    z = sling_factor(sling_angle)
    base = (
        working_anchors
        * loop.k_bend
        * cover_reduction_factor(thickness, loop)
        * direction_factor
        * characteristic_tension_resistance(loop)
        / (z * factors.gamma_s)
    )
    return base - factors.q_adh * form_area


def admissible_dynamic_weight(
    loop: LoopInput,
    thickness: float,
    factors: FactorsInput,
    working_anchors: float,
    sling_angle: float,
    direction_factor: float = 1.0,
) -> float:
    """Gadm,dyn in kN, thesis equation 4.11."""

    z = sling_factor(sling_angle)
    return (
        working_anchors
        * loop.k_bend
        * cover_reduction_factor(thickness, loop)
        * direction_factor
        * characteristic_tension_resistance(loop)
        / (factors.psi_dyn * z * factors.gamma_s)
    )


def admissible_rotation_weight(
    loop: LoopInput,
    thickness: float,
    factors: FactorsInput,
    k_rot_min: float,
) -> float:
    """Gadm,rot,i in kN, thesis equation 4.12."""

    return (
        loop.k_bend
        * cover_reduction_factor(thickness, loop)
        * k_rot_min
        * characteristic_tension_resistance(loop)
        / (factors.psi_dyn * factors.gamma_s)
    )
