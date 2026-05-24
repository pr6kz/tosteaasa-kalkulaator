from __future__ import annotations

from dataclasses import asdict
from typing import Any

from lifting_loops.models import ArrangementCheckResult, CalculationReport
from lifting_loops.utilization import arrangement_rotation_utilization, utilization_ratio


def arrangement_summary(result: ArrangementCheckResult) -> dict[str, Any]:
    t1_loop = result.arrangement.t1_loop
    t34_loop = result.arrangement.t34_loop
    combined_mu = arrangement_rotation_utilization(result)
    return {
        "t1_diameter": t1_loop.diameter,
        "t34_diameter": t34_loop.diameter,
        "steel_grade": t1_loop.steel_grade,
        "governing_case": result.governing_case,
        "governing_weight": result.governing_weight,
        "utilization": result.utilization,
        "max_rotation_utilization": max(
            combined_mu.max_mu_rot_1,
            combined_mu.max_mu_rot_3,
            combined_mu.max_mu_rot_4,
        ),
        "admissible_weights": {
            "demoulding": result.g_adm_adh,
            "lifting": result.g_adm_dyn,
            "rotation_T1": result.g_adm_rot_1,
            "rotation_T3": result.g_adm_rot_3,
            "rotation_T4": result.g_adm_rot_4,
        },
        "checks": {
            "T1": {
                "k_grade": result.t1_check.k_grade,
                "n_rk": result.t1_check.n_rk,
                "r_adm_red": result.t1_check.r_adm_red,
            },
            "T3_T4": {
                "k_grade": result.t34_check.k_grade,
                "n_rk": result.t34_check.n_rk,
                "r_adm_red": result.t34_check.r_adm_red,
            },
        },
    }


def diameter_rotation_capacity_rows(report: CalculationReport) -> list[dict[str, Any]]:
    """Return one rotation capacity row per diameter.

    The row is based on arrangements where T1 and T3/T4 have the same diameter.
    This makes the table stable in both selection modes.
    """

    rows = []
    for candidate in report.selection.checked:
        t1_loop = candidate.arrangement.t1_loop
        t34_loop = candidate.arrangement.t34_loop
        if t1_loop.diameter != t34_loop.diameter:
            continue
        values = {
            "rotation_T1": (
                candidate.g_adm_rot_1,
                candidate.t1_check.rotation_reduction.beta_min_1,
            ),
            "rotation_T3": (
                candidate.g_adm_rot_3,
                candidate.t34_check.rotation_reduction.beta_min_3,
            ),
            "rotation_T4": (
                candidate.g_adm_rot_4,
                candidate.t34_check.rotation_reduction.beta_min_4,
            ),
        }
        governing_case, (governing_weight, governing_beta) = min(
            values.items(),
            key=lambda item: item[1][0],
        )
        rows.append(
            {
                "diameter": t1_loop.diameter,
                "steel_grade": t1_loop.steel_grade,
                "g_perm_T1": values["rotation_T1"][0],
                "beta_T1": values["rotation_T1"][1],
                "g_perm_T3": values["rotation_T3"][0],
                "beta_T3": values["rotation_T3"][1],
                "g_perm_T4": values["rotation_T4"][0],
                "beta_T4": values["rotation_T4"][1],
                "governing_case": governing_case,
                "governing_weight": governing_weight,
                "governing_beta": governing_beta,
            }
        )
    return sorted(rows, key=lambda row: row["diameter"])


def diameter_side_lift_capacity_rows(report: CalculationReport) -> list[dict[str, Any]]:
    """Return demoulding and lifting capacity rows for same-diameter arrangements."""

    rows = []
    for candidate in report.selection.checked:
        t1_loop = candidate.arrangement.t1_loop
        t34_loop = candidate.arrangement.t34_loop
        if t1_loop.diameter != t34_loop.diameter:
            continue
        rows.append(
            {
                "diameter": t1_loop.diameter,
                "steel_grade": t1_loop.steel_grade,
                "g_perm_demoulding": candidate.g_adm_adh,
                "g_perm_lifting": candidate.g_adm_dyn,
            }
        )
    return sorted(rows, key=lambda row: row["diameter"])


def selected_utilization_summary(report: CalculationReport) -> dict[str, float] | None:
    selected = report.selection.selected
    if selected is None:
        return None
    return {
        "demoulding": utilization_ratio(report.element.weight, selected.g_adm_adh),
        "lifting": utilization_ratio(report.element.weight, selected.g_adm_dyn),
        "rotation_T1": utilization_ratio(report.element.weight, selected.g_adm_rot_1),
        "rotation_T3": utilization_ratio(report.element.weight, selected.g_adm_rot_3),
        "rotation_T4": utilization_ratio(report.element.weight, selected.g_adm_rot_4),
        "governing": selected.utilization,
    }


def calculation_report_to_dict(
    report: CalculationReport,
    include_candidates: bool = True,
    include_curves: bool = True,
) -> dict[str, Any]:
    selected = (
        arrangement_summary(report.selection.selected)
        if report.selection.selected is not None
        else None
    )
    data: dict[str, Any] = {
        "inputs": {
            "element": asdict(report.element),
            "factors": asdict(report.factors),
            "geometry": asdict(report.geometry),
            "loop_types": asdict(report.loop_types),
        },
        "selection_mode": report.selection.mode,
        "selected": selected,
        "selected_utilizations": selected_utilization_summary(report),
    }
    if include_candidates:
        data["candidates"] = [
            arrangement_summary(candidate)
            for candidate in report.selection.checked
        ]
        data["diameter_rotation_capacity"] = diameter_rotation_capacity_rows(report)
        data["diameter_side_lift_capacity"] = diameter_side_lift_capacity_rows(report)
    if include_curves and report.selection.selected is not None:
        data["rotation_utilization"] = asdict(
            arrangement_rotation_utilization(report.selection.selected)
        )
    return data
