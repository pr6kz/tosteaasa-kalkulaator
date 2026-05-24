from __future__ import annotations

import numpy as np


def eta_na(gamma):
    """Relative capacity for NA loops, thesis equation 5.96."""

    gamma = np.asarray(gamma, dtype=float)
    ratio = np.divide(
        77.4,
        gamma,
        out=np.full_like(gamma, np.inf, dtype=float),
        where=gamma != 0,
    )
    return 1.0 - 0.448 / (0.64 + (ratio - 0.9) ** 2)


def eta_nb(gamma):
    """Relative capacity for NB loops, thesis equation 5.97."""

    gamma = np.asarray(gamma, dtype=float)
    return np.where(
        gamma <= 30.0,
        1.0,
        0.3 + 0.7 * np.cos(np.radians(1.5 * gamma - 45.0)),
    )


def eta_constant(gamma):
    return np.ones_like(np.asarray(gamma, dtype=float))


ETA_RULES = {
    "NA": eta_na,
    "NB": eta_nb,
    "CONST": eta_constant,
}


def eta(loop_type: str, gamma):
    try:
        return ETA_RULES[loop_type](gamma)
    except KeyError as exc:
        valid = ", ".join(ETA_RULES)
        raise ValueError(f"Unknown loop type {loop_type!r}. Valid types: {valid}") from exc
