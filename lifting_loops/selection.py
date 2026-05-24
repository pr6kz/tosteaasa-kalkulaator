from __future__ import annotations

from lifting_loops.admissible_weight import (
    admissible_demoulding_weight,
    admissible_dynamic_weight,
    admissible_rotation_weight,
)
from lifting_loops.loads import anchor_count_for_asymmetric_pair
from lifting_loops.loop_types import eta
from lifting_loops.models import (
    ArrangementCheckResult,
    CalculationReport,
    ElementInput,
    FactorsInput,
    LoopArrangementInput,
    LoopCheckResult,
    LoopInput,
    LoopTypesInput,
    RotationGeometry,
    SelectionMode,
    SelectionResult,
)
from lifting_loops.resistance import (
    characteristic_tension_resistance,
    cover_reduction_factor,
    reduced_admissible_resistance,
)
from lifting_loops.rotation import analyze_rotation_reduction
from lifting_loops.utilization import rotation_utilization


def check_loop(
    loop: LoopInput,
    element: ElementInput,
    factors: FactorsInput,
    geometry: RotationGeometry,
    loop_types: LoopTypesInput,
    beta_step: float = 0.5,
) -> LoopCheckResult:
    working_anchors = anchor_count_for_asymmetric_pair(
        geometry.l2,
        geometry.effective_l5,
    )
    rotation = analyze_rotation_reduction(
        geometry=geometry,
        t1_type=loop_types.t1_type,
        t3_type=loop_types.t3_type,
        t4_type=loop_types.t4_type,
        step=beta_step,
    )
    g_adm_adh = admissible_demoulding_weight(
        loop,
        element.thickness,
        element.form_area,
        factors,
        working_anchors,
        element.demoulding_sling_angle,
    )
    g_adm_dyn = admissible_dynamic_weight(
        loop,
        element.thickness,
        factors,
        working_anchors,
        element.lifting_sling_angle,
    )
    g_adm_rot_1 = admissible_rotation_weight(
        loop, element.thickness, factors, rotation.min_k_rot_1
    )
    g_adm_rot_3 = admissible_rotation_weight(
        loop, element.thickness, factors, rotation.min_k_rot_3
    )
    g_adm_rot_4 = admissible_rotation_weight(
        loop, element.thickness, factors, rotation.min_k_rot_4
    )
    governing_cases = {
        "demoulding": g_adm_adh,
        "lifting": g_adm_dyn,
        "rotation_T1": g_adm_rot_1,
        "rotation_T3": g_adm_rot_3,
        "rotation_T4": g_adm_rot_4,
    }
    governing_case, governing_weight = min(governing_cases.items(), key=lambda item: item[1])
    utilization = element.weight / governing_weight if governing_weight > 0 else float("inf")
    rotation_mu = rotation_utilization(
        weight=element.weight,
        thickness=element.thickness,
        loop=loop,
        factors=factors,
        rotation=rotation,
    )
    return LoopCheckResult(
        loop=loop,
        n_rk=characteristic_tension_resistance(loop),
        k_grade=cover_reduction_factor(element.thickness, loop),
        r_adm_red=reduced_admissible_resistance(
            loop, element.thickness, factors.gamma_s
        ),
        g_adm_adh=g_adm_adh,
        g_adm_dyn=g_adm_dyn,
        g_adm_rot_1=g_adm_rot_1,
        g_adm_rot_3=g_adm_rot_3,
        g_adm_rot_4=g_adm_rot_4,
        governing_weight=governing_weight,
        governing_case=governing_case,
        utilization=utilization,
        rotation_reduction=rotation,
        rotation_utilization=rotation_mu,
    )


def check_arrangement(
    arrangement: LoopArrangementInput,
    element: ElementInput,
    factors: FactorsInput,
    geometry: RotationGeometry,
    loop_types: LoopTypesInput,
    beta_step: float = 0.5,
) -> ArrangementCheckResult:
    t1_check = check_loop(
        arrangement.t1_loop,
        element,
        factors,
        geometry,
        loop_types,
        beta_step=beta_step,
    )
    t34_check = check_loop(
        arrangement.t34_loop,
        element,
        factors,
        geometry,
        loop_types,
        beta_step=beta_step,
    )
    t1_working_anchors = side_hook_anchor_count(geometry.effective_l5, geometry)
    t2_working_anchors = side_hook_anchor_count(geometry.l2, geometry)
    t1_demoulding_factor = float(
        eta(loop_types.t1_type, element.demoulding_sling_angle)
    )
    t2_demoulding_factor = float(
        eta(loop_types.effective_t2_type, element.demoulding_sling_angle)
    )
    t1_lifting_factor = float(
        eta(loop_types.t1_type, element.lifting_sling_angle)
    )
    t2_lifting_factor = float(
        eta(loop_types.effective_t2_type, element.lifting_sling_angle)
    )
    g_adm_adh = min(
        admissible_demoulding_weight(
            arrangement.t1_loop,
            element.thickness,
            element.form_area,
            factors,
            t1_working_anchors,
            element.demoulding_sling_angle,
            t1_demoulding_factor,
        ),
        admissible_demoulding_weight(
            arrangement.t1_loop,
            element.thickness,
            element.form_area,
            factors,
            t2_working_anchors,
            element.demoulding_sling_angle,
            t2_demoulding_factor,
        ),
    )
    g_adm_dyn = min(
        admissible_dynamic_weight(
            arrangement.t1_loop,
            element.thickness,
            factors,
            t1_working_anchors,
            element.lifting_sling_angle,
            t1_lifting_factor,
        ),
        admissible_dynamic_weight(
            arrangement.t1_loop,
            element.thickness,
            factors,
            t2_working_anchors,
            element.lifting_sling_angle,
            t2_lifting_factor,
        ),
    )
    g_adm_rot_1 = t1_check.g_adm_rot_1
    g_adm_rot_3 = t34_check.g_adm_rot_3
    g_adm_rot_4 = t34_check.g_adm_rot_4
    governing_cases = {
        "demoulding": g_adm_adh,
        "lifting": g_adm_dyn,
        "rotation_T1": g_adm_rot_1,
        "rotation_T3": g_adm_rot_3,
        "rotation_T4": g_adm_rot_4,
    }
    governing_case, governing_weight = min(governing_cases.items(), key=lambda item: item[1])
    utilization = element.weight / governing_weight if governing_weight > 0 else float("inf")
    return ArrangementCheckResult(
        arrangement=arrangement,
        t1_check=t1_check,
        t34_check=t34_check,
        g_adm_adh=g_adm_adh,
        g_adm_dyn=g_adm_dyn,
        g_adm_rot_1=g_adm_rot_1,
        g_adm_rot_3=g_adm_rot_3,
        g_adm_rot_4=g_adm_rot_4,
        governing_weight=governing_weight,
        governing_case=governing_case,
        utilization=utilization,
    )


def side_hook_anchor_count(opposite_distance: float, geometry: RotationGeometry) -> float:
    """Equivalent anchor count for one side-lift hook, based on thesis equation 3.2."""

    total = geometry.l2 + geometry.effective_l5
    if opposite_distance == 0:
        return float("inf")
    return total / opposite_distance


def build_arrangements(
    loops: list[LoopInput],
    mode: SelectionMode,
) -> list[LoopArrangementInput]:
    sorted_loops = sorted(loops, key=lambda item: item.diameter)
    if mode == "same_diameter":
        return [
            LoopArrangementInput(t1_loop=loop, t34_loop=loop)
            for loop in sorted_loops
        ]
    if mode == "split_t1_t34":
        arrangements = [
            LoopArrangementInput(t1_loop=t1_loop, t34_loop=t34_loop)
            for t1_loop in sorted_loops
            for t34_loop in sorted_loops
        ]
        return sorted(
            arrangements,
            key=lambda item: (
                max(item.t1_loop.diameter, item.t34_loop.diameter),
                item.t1_loop.diameter + item.t34_loop.diameter,
                item.t1_loop.diameter,
                item.t34_loop.diameter,
            ),
        )
    raise ValueError(f"unknown selection mode {mode!r}")


def select_smallest_suitable_loop(
    loops: list[LoopInput],
    element: ElementInput,
    factors: FactorsInput,
    geometry: RotationGeometry,
    loop_types: LoopTypesInput,
    mode: SelectionMode = "same_diameter",
    beta_step: float = 0.5,
) -> SelectionResult:
    checked = [
        check_arrangement(
            arrangement,
            element,
            factors,
            geometry,
            loop_types,
            beta_step=beta_step,
        )
        for arrangement in build_arrangements(loops, mode)
    ]
    selected = next(
        (result for result in checked if result.governing_weight >= element.weight),
        None,
    )
    return SelectionResult(mode=mode, selected=selected, checked=checked)


def build_calculation_report(
    loops: list[LoopInput],
    element: ElementInput,
    factors: FactorsInput,
    geometry: RotationGeometry,
    loop_types: LoopTypesInput,
    mode: SelectionMode = "same_diameter",
    beta_step: float = 0.5,
) -> CalculationReport:
    selection = select_smallest_suitable_loop(
        loops=loops,
        element=element,
        factors=factors,
        geometry=geometry,
        loop_types=loop_types,
        mode=mode,
        beta_step=beta_step,
    )
    return CalculationReport(
        element=element,
        factors=factors,
        geometry=geometry,
        loop_types=loop_types,
        selection=selection,
    )
