from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RotationGeometry:
    """Geometry used for the rotation model in thesis chapter 5."""

    l1: float
    l2: float
    l3: float
    l4: float
    alpha: float
    l5: float | None = None

    @property
    def effective_l5(self) -> float:
        return self.l2 if self.l5 is None else self.l5


@dataclass(frozen=True)
class ElementInput:
    """Element level inputs.

    Weight and forces are expected in kN. Lengths are expected in mm unless a
    formula explicitly uses areas in m2.
    """

    weight: float
    thickness: float
    form_area: float
    demoulding_sling_angle: float = 0.0
    lifting_sling_angle: float = 0.0


@dataclass(frozen=True)
class LoopInput:
    """Lifting loop properties."""

    diameter: float
    steel_grade: str
    fuk: float
    k_bend: float
    tolerance: float = 10.0


@dataclass(frozen=True)
class LoopTypesInput:
    """Loop types by location in the rotation model."""

    t1_type: str
    t3_type: str
    t4_type: str
    t2_type: str | None = None

    @property
    def effective_t2_type(self) -> str:
        return self.t1_type if self.t2_type is None else self.t2_type


@dataclass(frozen=True)
class FactorsInput:
    """Load and safety factors."""

    gamma_s: float = 3.0
    psi_dyn: float = 1.3
    q_adh: float = 1.0


@dataclass(frozen=True)
class RotationReductionResult:
    beta: list[float]
    k_rot_1: list[float]
    k_rot_3: list[float]
    k_rot_4: list[float]
    min_k_rot_1: float
    min_k_rot_3: float
    min_k_rot_4: float
    beta_min_1: float
    beta_min_3: float
    beta_min_4: float


@dataclass(frozen=True)
class RotationUtilizationResult:
    beta: list[float]
    mu_rot_1: list[float]
    mu_rot_3: list[float]
    mu_rot_4: list[float]
    max_mu_rot_1: float
    max_mu_rot_3: float
    max_mu_rot_4: float
    beta_max_1: float
    beta_max_3: float
    beta_max_4: float


@dataclass(frozen=True)
class RotationForceComponentsResult:
    beta: list[float]
    t1_vertical: list[float]
    t1_horizontal: list[float]
    t3_vertical: list[float]
    t3_horizontal: list[float]
    t4_vertical: list[float]
    t4_horizontal: list[float]


@dataclass(frozen=True)
class LoopCheckResult:
    loop: LoopInput
    n_rk: float
    k_grade: float
    r_adm_red: float
    g_adm_adh: float
    g_adm_dyn: float
    g_adm_rot_1: float
    g_adm_rot_3: float
    g_adm_rot_4: float
    governing_weight: float
    governing_case: str
    utilization: float
    rotation_reduction: RotationReductionResult
    rotation_utilization: RotationUtilizationResult


@dataclass(frozen=True)
class LoopArrangementInput:
    """Candidate loop arrangement.

    T3 and T4 are represented by one shared loop size because they must always
    use the same diameter.
    """

    t1_loop: LoopInput
    t34_loop: LoopInput


@dataclass(frozen=True)
class ArrangementCheckResult:
    arrangement: LoopArrangementInput
    t1_check: LoopCheckResult
    t34_check: LoopCheckResult
    g_adm_adh: float
    g_adm_dyn: float
    g_adm_rot_1: float
    g_adm_rot_3: float
    g_adm_rot_4: float
    governing_weight: float
    governing_case: str
    utilization: float


SelectionMode = Literal["same_diameter", "split_t1_t34"]


@dataclass(frozen=True)
class SelectionResult:
    mode: SelectionMode
    selected: ArrangementCheckResult | None
    checked: list[ArrangementCheckResult]


@dataclass(frozen=True)
class CalculationReport:
    element: ElementInput
    factors: FactorsInput
    geometry: RotationGeometry
    loop_types: LoopTypesInput
    selection: SelectionResult
