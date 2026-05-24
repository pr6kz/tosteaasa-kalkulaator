from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lifting_loops.loop_catalog import build_default_catalog
from lifting_loops.loop_types import ETA_RULES
from lifting_loops.materials import STEEL_MATERIALS
from lifting_loops.models import (
    CalculationReport,
    ElementInput,
    FactorsInput,
    LoopTypesInput,
    RotationGeometry,
    SelectionMode,
)
from lifting_loops.selection import build_calculation_report


FORM_SURFACE_Q_ADH: dict[str, float] = {
    "oiled_steel_or_plastic_plywood": 1.0,
    "lacquered_planed_wood": 2.0,
    "oiled_rough_wood": 3.0,
}


DYNAMIC_FACTOR_PRESETS: dict[str, float] = {
    "crane": 1.3,
    "smooth_transport": 2.5,
    "rough_transport": 4.0,
}


SELECTION_MODES: tuple[SelectionMode, ...] = ("same_diameter", "split_t1_t34")


@dataclass(frozen=True)
class CalculationInput:
    """UI-facing input model.

    This model stores user choices and defaults. It can be converted into the
    lower-level calculation models used by the formula modules.
    """

    weight: float
    thickness: float
    form_area: float
    l1: float
    l2: float
    l3: float
    l4: float
    alpha: float
    l5: float | None = None
    steel_grade: str = "S355"
    t1_type: str = "NA"
    t2_type: str | None = None
    t3_type: str | None = None
    t4_type: str | None = None
    selection_mode: SelectionMode = "same_diameter"
    form_surface: str = "oiled_steel_or_plastic_plywood"
    q_adh: float | None = None
    dynamic_factor_preset: str = "crane"
    psi_dyn: float | None = None
    gamma_s: float = 3.0
    k_bend: float = 0.8
    tolerance: float = 10.0
    demoulding_sling_angle: float = 0.0
    lifting_sling_angle: float = 0.0
    beta_step: float = 0.5

    def effective_q_adh(self) -> float:
        if self.q_adh is not None:
            return self.q_adh
        return FORM_SURFACE_Q_ADH[self.form_surface]

    def effective_psi_dyn(self) -> float:
        if self.psi_dyn is not None:
            return self.psi_dyn
        return DYNAMIC_FACTOR_PRESETS[self.dynamic_factor_preset]

    def loop_types(self) -> LoopTypesInput:
        return LoopTypesInput(
            t1_type=self.t1_type,
            t2_type=self.t2_type or self.t1_type,
            t3_type=self.t3_type or self.t1_type,
            t4_type=self.t4_type or self.t1_type,
        )

    def geometry(self) -> RotationGeometry:
        return RotationGeometry(
            l1=self.l1,
            l2=self.l2,
            l3=self.l3,
            l4=self.l4,
            alpha=self.alpha,
            l5=self.l5,
        )

    def element(self) -> ElementInput:
        return ElementInput(
            weight=self.weight,
            thickness=self.thickness,
            form_area=self.form_area,
            demoulding_sling_angle=self.demoulding_sling_angle,
            lifting_sling_angle=self.lifting_sling_angle,
        )

    def factors(self) -> FactorsInput:
        return FactorsInput(
            gamma_s=self.gamma_s,
            psi_dyn=self.effective_psi_dyn(),
            q_adh=self.effective_q_adh(),
        )

    def validate(self) -> None:
        _require_positive("weight", self.weight)
        _require_positive("thickness", self.thickness)
        _require_non_negative("form_area", self.form_area)
        for name in ("l1", "l2", "l3", "l4"):
            _require_non_negative(name, getattr(self, name))
        if self.l5 is not None:
            _require_non_negative("l5", self.l5)
        if max(self.l2, self.l2 if self.l5 is None else self.l5) == 0:
            raise ValueError("at least one of l2 and l5 must be greater than zero")
        _require_angle("alpha", self.alpha)
        _require_angle("demoulding_sling_angle", self.demoulding_sling_angle)
        _require_angle("lifting_sling_angle", self.lifting_sling_angle)
        _require_positive("gamma_s", self.gamma_s)
        _require_positive("k_bend", self.k_bend)
        _require_non_negative("tolerance", self.tolerance)
        _require_positive("beta_step", self.beta_step)
        if self.beta_step >= 90:
            raise ValueError("beta_step must be less than 90 degrees")
        if self.q_adh is not None:
            _require_non_negative("q_adh", self.q_adh)
        if self.psi_dyn is not None:
            _require_positive("psi_dyn", self.psi_dyn)
        if self.form_surface not in FORM_SURFACE_Q_ADH:
            valid = ", ".join(FORM_SURFACE_Q_ADH)
            raise ValueError(f"unknown form_surface {self.form_surface!r}; valid: {valid}")
        if self.dynamic_factor_preset not in DYNAMIC_FACTOR_PRESETS:
            valid = ", ".join(DYNAMIC_FACTOR_PRESETS)
            raise ValueError(
                f"unknown dynamic_factor_preset {self.dynamic_factor_preset!r}; valid: {valid}"
            )
        if self.steel_grade not in STEEL_MATERIALS:
            valid = ", ".join(STEEL_MATERIALS)
            raise ValueError(f"unknown steel_grade {self.steel_grade!r}; valid: {valid}")
        for name, value in (
            ("t1_type", self.t1_type),
            ("t2_type", self.t2_type or self.t1_type),
            ("t3_type", self.t3_type or self.t1_type),
            ("t4_type", self.t4_type or self.t1_type),
        ):
            if value not in ETA_RULES:
                valid = ", ".join(ETA_RULES)
                raise ValueError(f"unknown {name} {value!r}; valid: {valid}")
        if self.selection_mode not in SELECTION_MODES:
            valid = ", ".join(SELECTION_MODES)
            raise ValueError(f"unknown selection_mode {self.selection_mode!r}; valid: {valid}")


def build_report_from_input(data: CalculationInput) -> CalculationReport:
    data.validate()
    loops = build_default_catalog(
        steel_grade=data.steel_grade,
        k_bend=data.k_bend,
        tolerance=data.tolerance,
    )
    return build_calculation_report(
        loops=loops,
        element=data.element(),
        factors=data.factors(),
        geometry=data.geometry(),
        loop_types=data.loop_types(),
        mode=data.selection_mode,
        beta_step=data.beta_step,
    )


def input_options() -> dict[str, Any]:
    """Return UI option lists and defaults."""

    return {
        "steel_grades": list(STEEL_MATERIALS),
        "loop_types": list(ETA_RULES),
        "selection_modes": list(SELECTION_MODES),
        "form_surfaces": [
            {"value": key, "q_adh": value}
            for key, value in FORM_SURFACE_Q_ADH.items()
        ],
        "dynamic_factor_presets": [
            {"value": key, "psi_dyn": value}
            for key, value in DYNAMIC_FACTOR_PRESETS.items()
        ],
        "defaults": {
            "steel_grade": "S235",
            "t1_type": "NA",
            "t2_type": "NA",
            "selection_mode": "same_diameter",
            "form_surface": "oiled_steel_or_plastic_plywood",
            "dynamic_factor_preset": "crane",
            "gamma_s": 3.0,
            "k_bend": 0.8,
            "tolerance": 10.0,
            "beta_step": 0.5,
        },
    }


def _require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _require_non_negative(name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_angle(name: str, value: float) -> None:
    if not 0 <= value < 90:
        raise ValueError(f"{name} must satisfy 0 <= angle < 90 degrees")
