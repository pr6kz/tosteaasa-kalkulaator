from __future__ import annotations

import math


def sling_factor(angle_from_vertical: float) -> float:
    """Return z = 1 / cos(beta), used with thesis equations 3.1 and 3.3."""

    if not 0 <= angle_from_vertical < 90:
        raise ValueError("sling angle must satisfy 0 <= beta < 90 degrees")
    return 1.0 / math.cos(math.radians(angle_from_vertical))


def anchor_count_for_asymmetric_pair(a: float, b: float) -> float:
    """Effective working anchor count for an asymmetric lift, thesis equation 3.2."""

    if a < 0 or b < 0:
        raise ValueError("distances a and b must be non-negative")
    if max(a, b) == 0:
        raise ValueError("at least one distance must be greater than zero")
    return (a + b) / max(a, b)


def adhesion_load(
    weight: float,
    q_adh: float,
    form_area: float,
    angle_from_vertical: float,
    working_anchors: float,
) -> float:
    """Load on the most loaded loop during demoulding, thesis equation 3.1."""

    return (weight + q_adh * form_area) * sling_factor(angle_from_vertical) / working_anchors


def dynamic_lift_load(
    weight: float,
    psi_dyn: float,
    angle_from_vertical: float,
    working_anchors: float,
) -> float:
    """Load on the most loaded loop during lifting, thesis equation 3.3."""

    return weight * psi_dyn * sling_factor(angle_from_vertical) / working_anchors


def rotation_load(weight: float, psi_dyn: float) -> float:
    """Total rotation load, thesis equation 3.4."""

    return weight * psi_dyn

