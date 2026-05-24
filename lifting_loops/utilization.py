from __future__ import annotations

import numpy as np

from lifting_loops.models import (
    ArrangementCheckResult,
    FactorsInput,
    LoopInput,
    RotationReductionResult,
    RotationUtilizationResult,
)
from lifting_loops.resistance import characteristic_tension_resistance, cover_reduction_factor


def utilization_ratio(weight: float, admissible_weight: float) -> float:
    if admissible_weight <= 0:
        return float("inf")
    return weight / admissible_weight


def rotation_utilization(
    weight: float,
    thickness: float,
    loop: LoopInput,
    factors: FactorsInput,
    rotation: RotationReductionResult,
) -> RotationUtilizationResult:
    """Rotation utilization curves, thesis equation 4.14."""

    denominator_base = (
        loop.k_bend
        * cover_reduction_factor(thickness, loop)
        * characteristic_tension_resistance(loop)
    )
    numerator = weight * factors.psi_dyn * factors.gamma_s
    beta = np.asarray(rotation.beta, dtype=float)
    k1 = np.asarray(rotation.k_rot_1, dtype=float)
    k3 = np.asarray(rotation.k_rot_3, dtype=float)
    k4 = np.asarray(rotation.k_rot_4, dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        mu1 = numerator / (denominator_base * k1)
        mu3 = numerator / (denominator_base * k3)
        mu4 = numerator / (denominator_base * k4)

    mu1 = np.where(np.isfinite(mu1), mu1, np.inf)
    mu3 = np.where(np.isfinite(mu3), mu3, np.inf)
    mu4 = np.where(np.isfinite(mu4), mu4, np.inf)

    index_1 = int(np.argmax(mu1))
    index_3 = int(np.argmax(mu3))
    index_4 = int(np.argmax(mu4))
    return RotationUtilizationResult(
        beta=rotation.beta,
        mu_rot_1=mu1.tolist(),
        mu_rot_3=mu3.tolist(),
        mu_rot_4=mu4.tolist(),
        max_mu_rot_1=float(mu1[index_1]),
        max_mu_rot_3=float(mu3[index_3]),
        max_mu_rot_4=float(mu4[index_4]),
        beta_max_1=float(beta[index_1]),
        beta_max_3=float(beta[index_3]),
        beta_max_4=float(beta[index_4]),
    )


def arrangement_rotation_utilization(
    result: ArrangementCheckResult,
) -> RotationUtilizationResult:
    """Combined rotation utilization for an arrangement.

    T1 comes from the T1 loop check. T3 and T4 come from the shared T3/T4 loop
    check.
    """

    t1 = result.t1_check.rotation_utilization
    t34 = result.t34_check.rotation_utilization
    return RotationUtilizationResult(
        beta=t1.beta,
        mu_rot_1=t1.mu_rot_1,
        mu_rot_3=t34.mu_rot_3,
        mu_rot_4=t34.mu_rot_4,
        max_mu_rot_1=t1.max_mu_rot_1,
        max_mu_rot_3=t34.max_mu_rot_3,
        max_mu_rot_4=t34.max_mu_rot_4,
        beta_max_1=t1.beta_max_1,
        beta_max_3=t34.beta_max_3,
        beta_max_4=t34.beta_max_4,
    )
