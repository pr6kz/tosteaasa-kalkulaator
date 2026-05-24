from __future__ import annotations

import numpy as np

from lifting_loops.loop_types import eta
from lifting_loops.models import (
    RotationForceComponentsResult,
    RotationGeometry,
    RotationReductionResult,
)


def beta_values(step: float = 0.5):
    if step <= 0:
        raise ValueError("beta step must be positive")
    return np.arange(step, 90.0, step, dtype=float)


def angle_phi(beta, alpha):
    """T3 force angle phi(beta), thesis equation 5.85."""

    result = np.degrees(
        np.arccos(np.sin(np.radians(beta)) * np.sin(np.radians(alpha)))
    ) - beta
    return np.abs(result)


def angle_theta(beta, alpha):
    """Auxiliary angle theta(beta), thesis equation 5.82."""

    return np.degrees(
        np.arcsin(np.sin(np.radians(beta)) * np.sin(np.radians(alpha)))
    )


def angle_omega(beta, alpha):
    """T4 force angle omega(beta), thesis equation 5.87."""

    result = 90.0 - beta + np.degrees(
        np.arcsin(np.sin(np.radians(beta)) * np.sin(np.radians(alpha)))
    )
    return np.abs(result)


def force_f1(beta, geometry: RotationGeometry):
    """Relative rope force at T1, thesis equations 5.62 and 5.64."""

    beta = np.asarray(beta, dtype=float)
    s = np.sin(np.radians(beta)) * np.sin(np.radians(geometry.alpha))
    t = geometry.l4 / 2.0 * np.tan(np.arcsin(s))
    denominator = geometry.l2 + geometry.l3 + geometry.l1 * np.tan(np.radians(beta)) - t
    return (geometry.l3 - t) / denominator


def force_f3(beta, geometry: RotationGeometry):
    """Relative rope force at T3/T4, thesis equation 5.94."""

    beta = np.asarray(beta, dtype=float)
    s = np.sin(np.radians(geometry.alpha)) * np.sin(np.radians(beta))
    numerator = geometry.l2 + geometry.l1 * np.tan(np.radians(beta))
    denominator = (
        2.0
        * (geometry.l2 + geometry.l3 + geometry.l1 * np.tan(np.radians(beta)))
        * np.sqrt(1.0 - s**2)
        - geometry.l4 * s
    )
    return numerator / denominator


def k_rot_1(beta, geometry: RotationGeometry, loop_type: str):
    """Rotation reduction function for T1, thesis equation 5.98."""

    return eta(loop_type, beta) / force_f1(beta, geometry)


def k_rot_3(beta, geometry: RotationGeometry, loop_type: str):
    """Rotation reduction function for T3, thesis equation 5.99."""

    return eta(loop_type, angle_phi(beta, geometry.alpha)) / force_f3(beta, geometry)


def k_rot_4(beta, geometry: RotationGeometry, loop_type: str):
    """Rotation reduction function for T4, thesis equation 5.100."""

    return eta(loop_type, angle_omega(beta, geometry.alpha)) / force_f3(beta, geometry)


def _minimum_from_grid(betas, values):
    finite = np.isfinite(values)
    positive = values > 0
    valid = finite & positive
    if not np.any(valid):
        raise ValueError("no positive finite rotation reduction values found")
    valid_indices = np.flatnonzero(valid)
    local_index = np.argmin(values[valid])
    index = valid_indices[local_index]
    return float(values[index]), float(betas[index])


def analyze_rotation_reduction(
    geometry: RotationGeometry,
    t1_type: str,
    t3_type: str | None = None,
    t4_type: str | None = None,
    step: float = 0.5,
) -> RotationReductionResult:
    """Find minimum rotation reductions over beta, thesis equation 5.101."""

    t3_type = t3_type or t1_type
    t4_type = t4_type or t1_type
    betas = beta_values(step)
    values_1 = k_rot_1(betas, geometry, t1_type)
    values_3 = k_rot_3(betas, geometry, t3_type)
    values_4 = k_rot_4(betas, geometry, t4_type)
    min_1, beta_min_1 = _minimum_from_grid(betas, values_1)
    min_3, beta_min_3 = _minimum_from_grid(betas, values_3)
    min_4, beta_min_4 = _minimum_from_grid(betas, values_4)
    return RotationReductionResult(
        beta=betas.tolist(),
        k_rot_1=values_1.tolist(),
        k_rot_3=values_3.tolist(),
        k_rot_4=values_4.tolist(),
        min_k_rot_1=min_1,
        min_k_rot_3=min_3,
        min_k_rot_4=min_4,
        beta_min_1=beta_min_1,
        beta_min_3=beta_min_3,
        beta_min_4=beta_min_4,
    )


def analyze_rotation_force_components(
    geometry: RotationGeometry,
    weight: float,
    psi_dyn: float,
    step: float = 0.5,
) -> RotationForceComponentsResult:
    """Resolve rotation force components from thesis equations 3.4, 5.62, 5.64, 5.85, 5.87, and 5.94."""

    betas = beta_values(step)
    total_rotation_load = weight * psi_dyn
    f1 = force_f1(betas, geometry) * total_rotation_load
    f3 = force_f3(betas, geometry) * total_rotation_load
    gamma_1 = np.radians(betas)
    gamma_3 = np.radians(angle_phi(betas, geometry.alpha))
    gamma_4 = np.radians(angle_omega(betas, geometry.alpha))
    return RotationForceComponentsResult(
        beta=betas.tolist(),
        t1_vertical=(f1 * np.cos(gamma_1)).tolist(),
        t1_horizontal=(f1 * np.sin(gamma_1)).tolist(),
        t3_vertical=(f3 * np.cos(gamma_3)).tolist(),
        t3_horizontal=(f3 * np.sin(gamma_3)).tolist(),
        t4_vertical=(f3 * np.cos(gamma_4)).tolist(),
        t4_horizontal=(f3 * np.sin(gamma_4)).tolist(),
    )
