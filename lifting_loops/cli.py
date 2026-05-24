from __future__ import annotations

import argparse
import json

from lifting_loops.input_schema import (
    DYNAMIC_FACTOR_PRESETS,
    FORM_SURFACE_Q_ADH,
    CalculationInput,
    build_report_from_input,
    input_options,
)
from lifting_loops.loads import anchor_count_for_asymmetric_pair
from lifting_loops.materials import STEEL_MATERIALS
from lifting_loops.plotting import save_rotation_utilization_plot
from lifting_loops.utilization import arrangement_rotation_utilization


def positive_float(value: str) -> float:
    x = float(value)
    if x <= 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be positive")
    return x


def non_negative_float(value: str) -> float:
    x = float(value)
    if x < 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be non-negative")
    return x


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-input-options", action="store_true")
    parser.add_argument("--weight", type=positive_float, help="Element weight G [kN]")
    parser.add_argument("--thickness", type=positive_float, help="Element thickness B [mm]")
    parser.add_argument("--form-area", type=non_negative_float, default=0.0, help="Contact form area Af [m2]")
    parser.add_argument("--l1", type=non_negative_float)
    parser.add_argument("--l2", type=non_negative_float)
    parser.add_argument("--l3", type=non_negative_float)
    parser.add_argument("--l4", type=non_negative_float)
    parser.add_argument("--l5", type=non_negative_float)
    parser.add_argument("--alpha", type=non_negative_float)
    parser.add_argument("--steel-grade", choices=tuple(STEEL_MATERIALS), default="S355")
    parser.add_argument("--t1-type", choices=("NA", "NB", "CONST"), default="NA")
    parser.add_argument("--t2-type", choices=("NA", "NB", "CONST"))
    parser.add_argument("--t3-type", choices=("NA", "NB", "CONST"))
    parser.add_argument("--t4-type", choices=("NA", "NB", "CONST"))
    parser.add_argument("--gamma-s", type=positive_float, default=3.0)
    parser.add_argument("--psi-dyn", type=positive_float)
    parser.add_argument(
        "--dynamic-factor-preset",
        choices=tuple(DYNAMIC_FACTOR_PRESETS),
        default="crane",
    )
    parser.add_argument("--q-adh", type=non_negative_float)
    parser.add_argument(
        "--form-surface",
        choices=tuple(FORM_SURFACE_Q_ADH),
        default="oiled_steel_or_plastic_plywood",
    )
    parser.add_argument("--demoulding-sling-angle", type=non_negative_float, default=0.0)
    parser.add_argument("--lifting-sling-angle", type=non_negative_float, default=0.0)
    parser.add_argument("--beta-step", type=positive_float, default=0.5)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--plot-file", default="rotation_utilization.png")
    parser.add_argument(
        "--selection-mode",
        choices=("same_diameter", "split_t1_t34"),
        default="same_diameter",
    )
    args = parser.parse_args()
    if not args.show_input_options:
        required = ("weight", "thickness", "l1", "l2", "l3", "l4", "alpha")
        missing = [f"--{name.replace('_', '-')}" for name in required if getattr(args, name) is None]
        if missing:
            parser.error("the following arguments are required: " + ", ".join(missing))
    return args


def main() -> None:
    args = parse_args()
    if args.show_input_options:
        print(json.dumps(input_options(), indent=2))
        return

    data = CalculationInput(
        weight=args.weight,
        thickness=args.thickness,
        form_area=args.form_area,
        l1=args.l1,
        l2=args.l2,
        l3=args.l3,
        l4=args.l4,
        alpha=args.alpha,
        l5=args.l5,
        steel_grade=args.steel_grade,
        t1_type=args.t1_type,
        t2_type=args.t2_type,
        t3_type=args.t3_type,
        t4_type=args.t4_type,
        selection_mode=args.selection_mode,
        form_surface=args.form_surface,
        q_adh=args.q_adh,
        dynamic_factor_preset=args.dynamic_factor_preset,
        psi_dyn=args.psi_dyn,
        gamma_s=args.gamma_s,
        demoulding_sling_angle=args.demoulding_sling_angle,
        lifting_sling_angle=args.lifting_sling_angle,
        beta_step=args.beta_step,
    )
    report = build_report_from_input(data)
    result = report.selection
    geometry = report.geometry
    loop_types = report.loop_types
    print(
        "Loop types: "
        f"T1={loop_types.t1_type}, T2={loop_types.effective_t2_type}, "
        f"T3={loop_types.t3_type}, T4={loop_types.t4_type}"
    )
    print(
        f"q_adh={report.factors.q_adh:g} kN/m2, "
        f"psi_dyn={report.factors.psi_dyn:g}"
    )
    print(f"Selection mode: {result.mode}")
    working_anchors = anchor_count_for_asymmetric_pair(geometry.l2, geometry.effective_l5)
    print(
        f"Working anchors n={working_anchors:.3f} "
        f"(a=l2={geometry.l2:g}, b=l5={geometry.effective_l5:g})"
    )
    print("T1_d T34_d grade k_grade_T1 k_grade_T34 G_adm governing utilization max_mu_rot")
    for check in result.checked:
        t1_loop = check.arrangement.t1_loop
        t34_loop = check.arrangement.t34_loop
        combined_mu = arrangement_rotation_utilization(check)
        max_mu_rot = max(
            combined_mu.max_mu_rot_1,
            combined_mu.max_mu_rot_3,
            combined_mu.max_mu_rot_4,
        )
        print(
            f"{t1_loop.diameter:>4.0f} {t34_loop.diameter:>5.0f} "
            f"{t1_loop.steel_grade:>5} "
            f"{check.t1_check.k_grade:>10.3f} {check.t34_check.k_grade:>11.3f} "
            f"{check.governing_weight:>7.2f} "
            f"{check.governing_case:>11} {check.utilization:>7.3f} "
            f"{max_mu_rot:>10.3f}"
        )
    if result.selected is None:
        print("No suitable loop found.")
    else:
        t1_loop = result.selected.arrangement.t1_loop
        t34_loop = result.selected.arrangement.t34_loop
        print(
            f"Selected: T1 {t1_loop.diameter:.0f} mm, "
            f"T3/T4 {t34_loop.diameter:.0f} mm, "
            f"{t1_loop.steel_grade}, "
            f"governing case {result.selected.governing_case}"
        )
        if args.plot:
            output = save_rotation_utilization_plot(
                arrangement_rotation_utilization(result.selected),
                args.plot_file,
            )
            print(f"Saved plot: {output}")


if __name__ == "__main__":
    main()
