from __future__ import annotations

import json
from html import escape
from math import ceil, isfinite

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from lifting_loops.input_schema import CalculationInput, build_report_from_input, input_options
from lifting_loops.loads import sling_factor
from lifting_loops.rotation import analyze_rotation_force_components
from lifting_loops.report import (
    arrangement_summary,
    diameter_rotation_capacity_rows,
    diameter_side_lift_capacity_rows,
)
from lifting_loops.utilization import arrangement_rotation_utilization, utilization_ratio


FORM_SURFACE_LABELS = {
    "oiled_steel_or_plastic_plywood": "Õlitatud teras / plastkattega vineer",
    "lacquered_planed_wood": "Lakitud hööveldatud puit",
    "oiled_rough_wood": "Õlitatud kare puit",
}

DYNAMIC_PRESET_LABELS = {
    "crane": "Autokraana/tornkraana",
    "smooth_transport": "Tõstmine/transport siledal pinnal",
    "rough_transport": "Tõstmine/transport ebatasasel pinnal",
}

SLING_ANGLE_OPTIONS = [0.0, 15.0, 30.0]


def input_row(label: str, suffix: str = "", weights: tuple[float, float, float] = (0.72, 1.35, 1.93)):
    label_col, input_col, _ = st.columns(weights)
    label_col.markdown(
        f'<div class="param-label"><strong>{escape(label)}</strong></div>',
        unsafe_allow_html=True,
    )
    return input_col


def main() -> None:
    st.set_page_config(
        page_title="Tõsteaasa kalkulaator",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    options = input_options()

    st.title("Tõsteaasa kalkulaator")
    st.markdown(
        """
        <style>
          .param-label {
            padding-top: 2.55rem;
            line-height: 1.25;
          }
          .checkbox-align-spacer {
            height: 2.5rem;
          }
          .select-align-spacer {
            height: 1.6rem;
          }
          .param-label.compact {
            padding-top: 0.75rem;
          }
          .param-label.factor-label {
            padding-top: 2.35rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        input_col, scheme_col = st.columns([1.03, 0.97], gap="large")
        with input_col:
            element_tab, geometry_tab, angles_tab, loops_tab, factors_tab = st.tabs(
                ["Element", "Geomeetria", "Nurgad", "Tõsteaasad", "Tegurid"]
            )

        with element_tab:
            weight_col = input_row("Elemendi kaal", "G [kN]")
            weight = weight_col.number_input(
                "G [kN]",
                min_value=0.0,
                value=100.0,
                step=1.0,
                format="%g",
            )
            thickness_col = input_row("Elemendi paksus", "B [mm]")
            thickness = thickness_col.number_input(
                "B [mm]",
                min_value=1.0,
                value=250.0,
                step=10.0,
                format="%g",
            )
            form_area_col = input_row("Vormipind", "Af [m2]")
            form_area = form_area_col.number_input(
                "Af [m2]",
                min_value=0.0,
                value=10.0,
                step=0.1,
                format="%g",
            )

        with geometry_tab:
            geometry_row_weights = (0.28, 1.35, 2.37)
            l1_col = input_row("l1", "[mm]", weights=geometry_row_weights)
            l1 = l1_col.number_input(
                "l1 [mm]", min_value=0.0, value=1000.0, step=50.0, format="%g"
            )
            l2_col = input_row("l2", "[mm]", weights=geometry_row_weights)
            l2 = l2_col.number_input(
                "l2 [mm]", min_value=0.0, value=2500.0, step=50.0, format="%g"
            )
            l3_col = input_row("l3", "[mm]", weights=geometry_row_weights)
            l3 = l3_col.number_input(
                "l3 [mm]", min_value=0.0, value=3000.0, step=50.0, format="%g"
            )
            l4_col = input_row("l4", "[mm]", weights=geometry_row_weights)
            l4 = l4_col.number_input(
                "l4 [mm]", min_value=0.0, value=1000.0, step=50.0, format="%g"
            )
            l5_label_col, l5_value_col, l5_option_col = st.columns(geometry_row_weights)
            l5_label_col.markdown(
                '<div class="param-label"><strong>l5</strong></div>',
                unsafe_allow_html=True,
            )
            l5_option_col.markdown('<div class="checkbox-align-spacer"></div>', unsafe_allow_html=True)
            use_l5 = l5_option_col.checkbox("Tõsteaasad T1 ja T2 ei asetse sümmeetriliselt", value=False)
            if use_l5:
                l5_value = l5_value_col.number_input(
                    "l5 [mm]",
                    min_value=0.0,
                    value=float(l2),
                    step=50.0,
                    format="%g",
                )
                l5 = l5_value
            else:
                l5_value_col.text_input("l5 [mm]", value=f"{l2:.0f}", disabled=True)
                l5 = None
        with angles_tab:
            angle_row_weights = (0.9, 1.35, 1.75)
            alpha_col = input_row("Alpha", "[deg]", weights=angle_row_weights)
            alpha = alpha_col.number_input(
                "alpha [deg]",
                min_value=0.0,
                max_value=89.9,
                value=30.0,
                step=0.5,
                format="%g",
            )
            demoulding_angle_col = input_row("Trossi nurk vormist vabastamisel", "[deg]", weights=angle_row_weights)
            demoulding_sling_angle = demoulding_angle_col.selectbox(
                "vormist vabastamine [deg]",
                SLING_ANGLE_OPTIONS,
                format_func=lambda value: f"{value:.0f} deg",
            )
            lifting_angle_col = input_row("Trossi nurk tõstmisel", "[deg]", weights=angle_row_weights)
            lifting_sling_angle = lifting_angle_col.selectbox(
                "tõstmine [deg]",
                SLING_ANGLE_OPTIONS,
                index=SLING_ANGLE_OPTIONS.index(30.0),
                format_func=lambda value: f"{value:.0f} deg",
            )
            beta_step_col = input_row("Pöördenurga samm", "[deg]", weights=angle_row_weights)
            beta_step = beta_step_col.number_input(
                "beta samm [deg]",
                min_value=0.1,
                max_value=10.0,
                value=0.5,
                step=0.1,
                format="%g",
            )

        with loops_tab:
            steel_grade_col = input_row("Terase mark")
            steel_grade = steel_grade_col.selectbox(
                "Terase mark",
                options["steel_grades"],
                index=options["steel_grades"].index("S235"),
            )
            loop_type_col = input_row("Tõsteaasa tüüp")
            t1_type = loop_type_col.selectbox(
                "T1 type", options["loop_types"], index=options["loop_types"].index("NA")
            )
            t2_type = loop_type_col.selectbox(
                "T2 type", options["loop_types"], index=options["loop_types"].index("NA")
            )
            t3_type = loop_type_col.selectbox(
                "T3 type", options["loop_types"], index=options["loop_types"].index("NA")
            )
            t4_type = loop_type_col.selectbox(
                "T4 type", options["loop_types"], index=options["loop_types"].index("NA")
            )
            selection_label_col, selection_mode_col, _ = st.columns((0.72, 1.35, 1.93))
            selection_label_col.markdown(
                '<div class="param-label compact"><strong>Läbimõõdu valik</strong></div>',
                unsafe_allow_html=True,
            )
            selection_mode = selection_mode_col.radio(
                "Läbimõõdu valik",
                options["selection_modes"],
                format_func=lambda value: {
                    "same_diameter": "Kõik sama",
                    "split_t1_t34": "T1 ja T3/T4 eraldi",
                }[value],
                label_visibility="collapsed",
                horizontal=True,
            )

        with factors_tab:
            form_surface_values = [item["value"] for item in options["form_surfaces"]]
            q_adh_by_surface = {
                item["value"]: item["q_adh"] for item in options["form_surfaces"]
            }
            factor_row_weights = (0.95, 1.55, 0.72, 0.82, 0.36)
            factor_input_weights = (0.95, 1.55, 1.9)
            r1c1, r1c2, r1c3, r1c4, _ = st.columns(factor_row_weights)
            r1c1.markdown(
                '<div class="param-label factor-label"><strong>Vormipind</strong></div>',
                unsafe_allow_html=True,
            )
            r1c2.markdown('<div class="select-align-spacer"></div>', unsafe_allow_html=True)
            form_surface = r1c2.selectbox(
                "Pinna kvaliteet",
                form_surface_values,
                format_func=lambda value: FORM_SURFACE_LABELS.get(value, value),
                label_visibility="collapsed",
            )
            r1c3.markdown('<div class="checkbox-align-spacer"></div>', unsafe_allow_html=True)
            override_q_adh = r1c3.checkbox(
                "Muuda",
                value=False,
                key="override_q_adh",
            )
            q_adh = r1c4.number_input(
                "q_adh [kN/m2]",
                min_value=0.0,
                value=float(q_adh_by_surface[form_surface]),
                step=0.1,
                format="%g",
                disabled=not override_q_adh,
            )
            if not override_q_adh:
                q_adh = None

            dyn_values = [item["value"] for item in options["dynamic_factor_presets"]]
            psi_by_preset = {
                item["value"]: item["psi_dyn"] for item in options["dynamic_factor_presets"]
            }
            r2c1, r2c2, r2c3, r2c4, _ = st.columns(factor_row_weights)
            r2c1.markdown(
                '<div class="param-label factor-label"><strong>Dünaamikategur</strong></div>',
                unsafe_allow_html=True,
            )
            r2c2.markdown('<div class="select-align-spacer"></div>', unsafe_allow_html=True)
            dynamic_factor_preset = r2c2.selectbox(
                "Dünaamikateguri valik",
                dyn_values,
                format_func=lambda value: DYNAMIC_PRESET_LABELS.get(value, value),
                label_visibility="collapsed",
            )
            r2c3.markdown('<div class="checkbox-align-spacer"></div>', unsafe_allow_html=True)
            override_psi = r2c3.checkbox(
                "Muuda",
                value=False,
                key="override_dynamic_preset",
            )
            psi_dyn = r2c4.number_input(
                "psi_dyn [-]",
                min_value=0.1,
                value=float(psi_by_preset[dynamic_factor_preset]),
                step=0.1,
                format="%g",
                disabled=not override_psi,
            )
            if not override_psi:
                psi_dyn = None

            gamma_s_col = input_row("Terase varutegur", "gamma_s [-]", weights=factor_input_weights)
            gamma_s = gamma_s_col.number_input(
                "gamma_s [-]", min_value=0.1, value=3.0, step=0.1, format="%g"
            )

            k_bend_col = input_row("Painutuse kujutegur", "k_bend [-]", weights=factor_input_weights)
            k_bend = k_bend_col.number_input(
                "k_bend [-]", min_value=0.1, value=0.8, step=0.05, format="%g"
            )

            tolerance_col = input_row("Paigutustolerants", "tol [mm]", weights=factor_input_weights)
            tolerance = tolerance_col.number_input(
                "tol [mm]", min_value=0.0, value=10.0, step=1.0, format="%g"
            )

        with scheme_col:
            components.html(
                geometry_scheme_html(
                    l1=l1,
                    l2=l2,
                    l3=l3,
                    l4=l4,
                    l5=l5 if l5 is not None else l2,
                    l5_is_default=l5 is None,
                    theme_type=getattr(st.context.theme, "type", None),
                ),
                height=430,
                scrolling=False,
            )

    data = CalculationInput(
        weight=weight,
        thickness=thickness,
        form_area=form_area,
        l1=l1,
        l2=l2,
        l3=l3,
        l4=l4,
        l5=l5,
        alpha=alpha,
        steel_grade=steel_grade,
        t1_type=t1_type,
        t2_type=t2_type,
        t3_type=t3_type,
        t4_type=t4_type,
        selection_mode=selection_mode,
        form_surface=form_surface,
        q_adh=q_adh,
        dynamic_factor_preset=dynamic_factor_preset,
        psi_dyn=psi_dyn,
        gamma_s=gamma_s,
        k_bend=k_bend,
        tolerance=tolerance,
        demoulding_sling_angle=demoulding_sling_angle,
        lifting_sling_angle=lifting_sling_angle,
        beta_step=beta_step,
    )

    try:
        report = build_report_from_input(data)
    except ValueError as exc:
        st.error(str(exc))
        return

    selected = report.selection.selected
    if selected is None:
        if not report.selection.checked:
            st.error("No loop arrangements were calculated.")
            return
        selected_for_display = report.selection.checked[-1]
        t1_diameter = selected_for_display.arrangement.t1_loop.diameter
        t34_diameter = selected_for_display.arrangement.t34_loop.diameter
        if t1_diameter == t34_diameter:
            displayed_loops = f"{t1_diameter:.0f} mm tõsteaasale"
        else:
            displayed_loops = f"T1 {t1_diameter:.0f} mm ning T3/T4 {t34_diameter:.0f} mm tõsteaasadele"
        st.warning(
            f"Sobivat tõsteaasa ei leitud. Kuvatakse tulemus {displayed_loops}."
        )
    else:
        selected_for_display = selected

    summary = arrangement_summary(selected_for_display)
    utilizations = utilization_summary_for_result(report, selected_for_display)
    render_summary_cards(
        report.selection.mode,
        summary,
        utilizations,
        selected_for_display.governing_case,
    )

    combined = arrangement_rotation_utilization(selected_for_display)
    force_components = analyze_rotation_force_components(
        report.geometry,
        report.element.weight,
        report.factors.psi_dyn,
        step=data.beta_step,
    )
    side_table_col, _ = st.columns([1, 1])
    with side_table_col:
        st.subheader("Lubatud elemendi kaal vormist vabastamisel ja tõstmisel")
        st.markdown(
            side_lift_capacity_table_html(
                diameter_side_lift_capacity_rows(report),
                report.element.weight,
            ),
            unsafe_allow_html=True,
        )

    rotation_table_col, rotation_chart_col = st.columns([1, 1])
    with rotation_table_col:
        st.subheader("Lubatud elemendi kaal elemendi pööramisel")
        st.markdown(
            rotation_capacity_table_html(
                diameter_rotation_capacity_rows(report),
                report.element.weight,
            ),
            unsafe_allow_html=True,
        )
    with rotation_chart_col:
        st.subheader("Kasutusaste elemendi pööramisel")
        st.altair_chart(rotation_utilization_chart(combined, summary), width="stretch")

    component_table_col, component_chart_col = st.columns([1, 1])
    with component_table_col:
        st.subheader("Tõsteaasale mõjuva jõu komponendid")
        st.dataframe(
            force_component_summary_table(report, force_components),
            width="stretch",
        )
    with component_chart_col:
        st.subheader("Jõukomponendid elemendi pööramisel")
        t1_tab, t3_tab, t4_tab = st.tabs(["T1", "T3", "T4"])
        with t1_tab:
            st.altair_chart(force_components_chart(force_components, "T1"), width="stretch")
        with t3_tab:
            st.altair_chart(force_components_chart(force_components, "T3"), width="stretch")
        with t4_tab:
            st.altair_chart(force_components_chart(force_components, "T4"), width="stretch")

    st.subheader("Elemendi pööramise animatsioon")
    components.html(
        rotation_animation_html(
            l1=l1,
            l2=l2,
            l3=l3,
            l4=l4,
            l5=l5 if l5 is not None else l2,
            alpha=alpha,
            force_components=force_components,
            utilization=combined,
            t1_type=t1_type,
            t3_type=t3_type,
            t4_type=t4_type,
            theme_type=getattr(st.context.theme, "type", None),
        ),
        height=750,
        scrolling=False,
    )


def render_summary_cards(
    selection_mode: str,
    summary: dict,
    utilizations: dict[str, float],
    controlling_case: str,
) -> None:
    rotation_utilization = max(
        utilizations.get("rotation_T1", 0.0),
        utilizations.get("rotation_T3", 0.0),
        utilizations.get("rotation_T4", 0.0),
    )
    cards = []
    if selection_mode == "same_diameter":
        cards.append(("Valitud läbimõõt", f"{summary['t1_diameter']:.0f} mm", ""))
    else:
        cards.extend(
            [
                ("T1 läbimõõt", f"{summary['t1_diameter']:.0f} mm", ""),
                ("T3 / T4 läbimõõt", f"{summary['t34_diameter']:.0f} mm", ""),
            ]
        )
    cards.extend(
        [
            ("Kasutusaste pööramisel", f"{rotation_utilization:.3f}", "rotation"),
            ("Kasutusaste vormist vabastamisel", f"{utilizations.get('demoulding', 0.0):.3f}", "demoulding"),
            ("Kasutusaste tõstmisel", f"{utilizations.get('lifting', 0.0):.3f}", "lifting"),
        ]
    )
    columns = st.columns(len(cards))
    for column, (label, value, group) in zip(columns, cards):
        is_controlling = (
            group == "rotation" and controlling_case.startswith("rotation")
        ) or group == controlling_case
        column.markdown(
            summary_card_html(label, value, is_controlling),
            unsafe_allow_html=True,
        )


def utilization_summary_for_result(report: object, result: object) -> dict[str, float]:
    return {
        "demoulding": utilization_ratio(report.element.weight, result.g_adm_adh),
        "lifting": utilization_ratio(report.element.weight, result.g_adm_dyn),
        "rotation_T1": utilization_ratio(report.element.weight, result.g_adm_rot_1),
        "rotation_T3": utilization_ratio(report.element.weight, result.g_adm_rot_3),
        "rotation_T4": utilization_ratio(report.element.weight, result.g_adm_rot_4),
        "governing": result.utilization,
    }


def summary_card_html(label: str, value: str, is_controlling: bool) -> str:
    class_name = "metric-card controlling" if is_controlling else "metric-card"
    return f"""
    <style>
      .metric-card {{
        border: 1px solid rgba(128, 128, 128, 0.28);
        background: var(--secondary-background-color);
        color: var(--text-color);
        border-radius: 8px;
        padding: 12px 14px;
        min-height: 74px;
      }}
      .metric-card.controlling {{
        border-left: 5px solid rgba(217, 119, 6, 0.9);
        background: color-mix(in srgb, var(--secondary-background-color) 88%, rgb(217, 119, 6) 12%);
      }}
      .metric-card .label {{
        font-size: 12px;
        color: color-mix(in srgb, var(--text-color) 68%, transparent);
        margin-bottom: 8px;
      }}
      .metric-card .value {{
        font-size: 26px;
        line-height: 1.1;
        font-weight: 650;
      }}
    </style>
    <div class="{class_name}">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
    </div>
    """


def compact_mm(value: float) -> str:
    return f"{value:g} mm"


def geometry_scheme_html(
    l1: float,
    l2: float,
    l3: float,
    l4: float,
    l5: float,
    l5_is_default: bool,
    theme_type: str | None = None,
) -> str:
    l5_note = "l5 = l2" if l5_is_default else "eraldi l5"
    if theme_type == "dark":
        scheme_bg = "#111827"
        scheme_panel = "#172033"
        scheme_text = "#e5e7eb"
        scheme_muted = "rgba(203, 213, 225, 0.75)"
        scheme_border = "rgba(148, 163, 184, 0.34)"
        scheme_axis = "rgba(203, 213, 225, 0.5)"
        scheme_dim = "#cbd5e1"
        scheme_dim_soft = "rgba(203, 213, 225, 0.52)"
        fallback_dark_media = ""
    else:
        scheme_bg = "#f8fafc"
        scheme_panel = "#eef2f7"
        scheme_text = "#111827"
        scheme_muted = "rgba(75, 85, 99, 0.78)"
        scheme_border = "rgba(148, 163, 184, 0.45)"
        scheme_axis = "rgba(100, 116, 139, 0.62)"
        scheme_dim = "#475569"
        scheme_dim_soft = "rgba(71, 85, 105, 0.56)"
        fallback_dark_media = "" if theme_type == "light" else """
      @media (prefers-color-scheme: dark) {
        :root {
          --scheme-bg: #111827;
          --scheme-panel: #172033;
          --scheme-text: #e5e7eb;
          --scheme-muted: rgba(203, 213, 225, 0.75);
          --scheme-border: rgba(148, 163, 184, 0.34);
          --scheme-axis: rgba(203, 213, 225, 0.5);
          --scheme-dim: #cbd5e1;
          --scheme-dim-soft: rgba(203, 213, 225, 0.52);
        }
      }
"""
    return f"""
    <style>
      :root {{
        color-scheme: light dark;
        --scheme-bg: {scheme_bg};
        --scheme-panel: {scheme_panel};
        --scheme-text: {scheme_text};
        --scheme-muted: {scheme_muted};
        --scheme-border: {scheme_border};
        --scheme-axis: {scheme_axis};
        --scheme-dim: {scheme_dim};
        --scheme-dim-soft: {scheme_dim_soft};
      }}
      {fallback_dark_media}
      html,
      body {{
        margin: 0;
        background: var(--scheme-bg) !important;
        min-height: 100%;
      }}
      .geometry-card {{
        box-sizing: border-box;
        height: 430px;
        overflow: hidden;
        border: 1px solid var(--scheme-border);
        background: var(--scheme-bg);
        border-radius: 8px;
        padding: 12px 14px 10px;
        color: var(--scheme-text);
      }}
      .scheme-title {{
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-size: 14px;
        font-weight: 650;
        margin: 0 0 4px;
      }}
      svg {{
        width: 100%;
        height: 350px;
        display: block;
      }}
      text {{
        fill: var(--scheme-text);
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      .panel {{
        fill: var(--scheme-panel);
        stroke: var(--scheme-border);
        stroke-width: 2;
      }}
      .axis {{
        stroke: var(--scheme-axis);
        stroke-width: 1.5;
        stroke-dasharray: 8 8;
      }}
      .hook {{
        fill: rgba(20, 184, 166, 0.2);
        stroke: rgb(20, 184, 166);
        stroke-width: 2.4;
      }}
      .hook-label {{
        font-size: 17px;
        font-weight: 700;
      }}
      .g-point {{
        fill: rgb(34, 197, 94);
      }}
      .g-label {{
        fill: rgb(34, 197, 94);
        font-size: 18px;
        font-weight: 800;
      }}
      .dim,
      .tick,
      .ext {{
        stroke: var(--scheme-dim);
        stroke-width: 2.2;
        vector-effect: non-scaling-stroke;
      }}
      .ext {{
        stroke: var(--scheme-dim-soft);
        opacity: 0.55;
        stroke-width: 1.3;
      }}
      .dim-text {{
        fill: var(--scheme-dim);
        font-size: 15px;
        font-weight: 750;
      }}
      .dim-value {{
        fill: var(--scheme-dim);
        font-size: 12px;
        opacity: 0.9;
      }}
      .note {{
        color: var(--scheme-muted);
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-size: 12px;
        line-height: 1.25;
        margin-top: 2px;
      }}
    </style>
    <div class="geometry-card">
      <div class="scheme-title">Geomeetria skeem</div>
      <svg viewBox="0 0 820 390" role="img" aria-label="Geometry dimension scheme">
        <rect class="panel" x="110" y="100" width="560" height="280" rx="2"></rect>
        <line class="axis" x1="110" y1="240" x2="670" y2="240"></line>
        <line class="axis" x1="390" y1="100" x2="390" y2="380"></line>

        <circle class="hook" cx="250" cy="100" r="7"></circle>
        <circle class="hook" cx="530" cy="100" r="7"></circle>
        <circle class="hook" cx="670" cy="170" r="7"></circle>
        <circle class="hook" cx="670" cy="310" r="7"></circle>

        <text class="hook-label" x="226" y="91">T1</text>
        <text class="hook-label" x="506" y="91">T2</text>
        <text class="hook-label" x="688" y="165">T3</text>
        <text class="hook-label" x="688" y="304">T4</text>

        <circle class="g-point" cx="390" cy="240" r="6"></circle>
        <text class="g-label" x="402" y="247">G</text>

        <line class="ext" x1="250" y1="100" x2="250" y2="60"></line>
        <line class="ext" x1="390" y1="100" x2="390" y2="22"></line>
        <line class="ext" x1="530" y1="100" x2="530" y2="60"></line>
        <line class="ext" x1="670" y1="100" x2="670" y2="22"></line>

        <line class="dim" x1="238" y1="62" x2="402" y2="62"></line>
        <line class="tick" x1="244" y1="68" x2="256" y2="56"></line>
        <line class="tick" x1="384" y1="68" x2="396" y2="56"></line>
        <text class="dim-text" x="313" y="49">l2</text>
        <text class="dim-value" x="295" y="79">{escape(compact_mm(l2))}</text>

        <line class="dim" x1="378" y1="62" x2="542" y2="62"></line>
        <line class="tick" x1="524" y1="68" x2="536" y2="56"></line>
        <text class="dim-text" x="453" y="49">l5</text>
        <text class="dim-value" x="435" y="79">{escape(compact_mm(l5))}</text>

        <line class="dim" x1="378" y1="22" x2="682" y2="22"></line>
        <line class="tick" x1="384" y1="28" x2="396" y2="16"></line>
        <line class="tick" x1="664" y1="28" x2="676" y2="16"></line>
        <text class="dim-text" x="522" y="15">l3</text>
        <text class="dim-value" x="506" y="43">{escape(compact_mm(l3))}</text>

        <line class="ext" x1="110" y1="100" x2="74" y2="100"></line>
        <line class="ext" x1="110" y1="240" x2="74" y2="240"></line>
        <line class="dim" x1="80" y1="88" x2="80" y2="252"></line>
        <line class="tick" x1="74" y1="94" x2="86" y2="106"></line>
        <line class="tick" x1="74" y1="234" x2="86" y2="246"></line>
        <text class="dim-text" x="42" y="174">l1</text>
        <text class="dim-value" x="26" y="193">{escape(compact_mm(l1))}</text>

        <line class="ext" x1="670" y1="170" x2="742" y2="170"></line>
        <line class="ext" x1="670" y1="310" x2="742" y2="310"></line>
        <line class="dim" x1="734" y1="158" x2="734" y2="322"></line>
        <line class="tick" x1="728" y1="164" x2="740" y2="176"></line>
        <line class="tick" x1="728" y1="304" x2="740" y2="316"></line>
        <text class="dim-text" x="758" y="244">l4</text>
        <text class="dim-value" x="758" y="263">{escape(compact_mm(l4))}</text>
      </svg>
    </div>
    """


def rotation_animation_html(
    l1: float,
    l2: float,
    l3: float,
    l4: float,
    l5: float,
    alpha: float,
    force_components=None,
    utilization=None,
    t1_type: str = "NA",
    t3_type: str = "NA",
    t4_type: str = "NA",
    theme_type: str | None = None,
) -> str:
    if theme_type == "dark":
        scheme_bg = "#111827"
        scheme_panel = "#172033"
        scheme_text = "#e5e7eb"
        scheme_muted = "rgba(203, 213, 225, 0.72)"
        scheme_border = "rgba(148, 163, 184, 0.34)"
        scheme_axis = "rgba(203, 213, 225, 0.42)"
        rope_color = "#cbd5e1"
        inactive_color = "rgba(148, 163, 184, 0.58)"
    else:
        scheme_bg = "#f8fafc"
        scheme_panel = "#eef2f7"
        scheme_text = "#111827"
        scheme_muted = "rgba(75, 85, 99, 0.76)"
        scheme_border = "rgba(148, 163, 184, 0.45)"
        scheme_axis = "rgba(100, 116, 139, 0.52)"
        rope_color = "#475569"
        inactive_color = "rgba(100, 116, 139, 0.5)"

    def force_magnitude(vertical: list[float], horizontal: list[float]) -> list[float]:
        return [
            (float(v) * float(v) + float(h) * float(h)) ** 0.5
            for v, h in zip(vertical, horizontal)
        ]

    def finite_series(values: list[float]) -> list[float]:
        return [
            float(value) if isfinite(float(value)) else 1e9
            for value in values
        ]

    if force_components is None:
        force_payload = {
            "beta": [0.0, 90.0],
            "T1": [0.0, 0.0],
            "T3": [0.0, 0.0],
            "T4": [0.0, 0.0],
        }
    else:
        force_payload = {
            "beta": [float(value) for value in force_components.beta],
            "T1": force_magnitude(force_components.t1_vertical, force_components.t1_horizontal),
            "T3": force_magnitude(force_components.t3_vertical, force_components.t3_horizontal),
            "T4": force_magnitude(force_components.t4_vertical, force_components.t4_horizontal),
        }

    if utilization is None:
        utilization_payload = {
            "beta": [0.0, 90.0],
            "T1": [0.0, 0.0],
            "T3": [0.0, 0.0],
            "T4": [0.0, 0.0],
            "critical": [],
        }
    else:
        utilization_payload = {
            "beta": [float(value) for value in utilization.beta],
            "T1": finite_series(utilization.mu_rot_1),
            "T3": finite_series(utilization.mu_rot_3),
            "T4": finite_series(utilization.mu_rot_4),
            "critical": [
                {"label": "T1", "beta": float(utilization.beta_max_1)},
                {"label": "T3", "beta": float(utilization.beta_max_3)},
                {"label": "T4", "beta": float(utilization.beta_max_4)},
            ],
        }

    animation_payload = json.dumps(
        {
            "forces": force_payload,
            "utilization": utilization_payload,
            "loopTypes": {"T1": t1_type, "T3": t3_type, "T4": t4_type},
        },
        allow_nan=False,
    )

    return f"""
    <style>
      body {{
        margin: 0;
        background: transparent;
      }}
      .rotation-card {{
        box-sizing: border-box;
        min-height: 734px;
        overflow: hidden;
        border: 1px solid {scheme_border};
        background: {scheme_bg};
        border-radius: 8px;
        padding: 12px 14px 14px;
        color: {scheme_text};
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      .animation-meta {{
        display: flex;
        justify-content: flex-end;
        align-items: start;
        margin-bottom: 8px;
      }}
      .live-table {{
        width: min(100%, 520px);
        border-collapse: collapse;
        font-size: 12px;
        color: {scheme_text};
      }}
      .live-table th,
      .live-table td {{
        border: 1px solid {scheme_border};
        padding: 4px 6px;
        text-align: right;
        font-variant-numeric: tabular-nums;
      }}
      .live-table th:first-child,
      .live-table td:first-child {{
        text-align: left;
      }}
      .animation-surface {{
        height: 550px;
      }}
      svg {{
        width: 100%;
        height: 100%;
        display: block;
      }}
      text {{
        fill: {scheme_text};
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      .panel {{
        fill: {scheme_panel};
        stroke: {scheme_border};
        stroke-width: 2.2;
      }}
      .axis {{
        stroke: {scheme_axis};
        stroke-width: 1.3;
        stroke-dasharray: 7 7;
      }}
      .rope {{
        stroke: {rope_color};
        stroke-width: 2.2;
        fill: none;
        vector-effect: non-scaling-stroke;
      }}
      .rope-secondary {{
        stroke: {rope_color};
        stroke-width: 1.9;
        fill: none;
        vector-effect: non-scaling-stroke;
      }}
      .ellipse-guide {{
        stroke: {inactive_color};
        stroke-width: 1.4;
        stroke-dasharray: 6 7;
        fill: none;
        vector-effect: non-scaling-stroke;
      }}
      .hook {{
        fill: rgba(20, 184, 166, 0.2);
        stroke: rgb(20, 184, 166);
        stroke-width: 3;
        vector-effect: non-scaling-stroke;
      }}
      .hook-unused {{
        fill: transparent;
        stroke: {inactive_color};
        stroke-width: 2.2;
        vector-effect: non-scaling-stroke;
      }}
      .block {{
        fill: {scheme_bg};
        stroke: {rope_color};
        stroke-width: 2.4;
        vector-effect: non-scaling-stroke;
      }}
      .g-point {{
        fill: rgb(34, 197, 94);
      }}
      .g-label {{
        fill: rgb(34, 197, 94);
        font-size: 16px;
        font-weight: 800;
      }}
      .hook-label {{
        font-size: 14px;
        font-weight: 750;
      }}
      .unused-label {{
        fill: {scheme_muted};
        font-size: 13px;
        font-weight: 650;
      }}
      .controls {{
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: 12px;
        align-items: center;
        padding-top: 8px;
      }}
      button {{
        border: 1px solid {scheme_border};
        background: {scheme_panel};
        color: {scheme_text};
        border-radius: 7px;
        min-width: 42px;
        height: 34px;
        font-size: 15px;
        cursor: pointer;
      }}
      input[type="range"] {{
        width: 100%;
        accent-color: rgb(20, 184, 166);
      }}
      .slider-wrap {{
        position: relative;
        padding-top: 15px;
      }}
      .snap-marker {{
        position: absolute;
        top: 0;
        width: 2px;
        height: 10px;
        background: {scheme_muted};
        transform: translateX(-1px);
      }}
      .snap-marker span {{
        position: absolute;
        top: -15px;
        left: 50%;
        transform: translateX(-50%);
        color: {scheme_muted};
        font-size: 10px;
        white-space: nowrap;
      }}
      .beta-readout {{
        min-width: 82px;
        text-align: right;
        color: {scheme_muted};
        font-variant-numeric: tabular-nums;
        font-size: 13px;
      }}
    </style>
    <div class="rotation-card">
      <div class="animation-meta">
        <table class="live-table">
          <thead>
            <tr><th>Aas</th><th>F [kN]</th><th>γ [deg]</th><th>η [-]</th><th>μ [-]</th></tr>
          </thead>
          <tbody>
            <tr><td>T1</td><td id="force-t1"></td><td id="angle-t1"></td><td id="eta-t1"></td><td id="mu-t1"></td></tr>
            <tr><td>T3</td><td id="force-t3"></td><td id="angle-t3"></td><td id="eta-t3"></td><td id="mu-t3"></td></tr>
            <tr><td>T4</td><td id="force-t4"></td><td id="angle-t4"></td><td id="eta-t4"></td><td id="mu-t4"></td></tr>
          </tbody>
        </table>
      </div>
      <div class="animation-surface">
        <svg id="rotation-svg" viewBox="0 0 960 550" role="img" aria-label="Rotation animation scheme"></svg>
      </div>
      <div class="controls">
        <button id="play-button" type="button" title="Käivita animatsioon">▶</button>
        <div class="slider-wrap">
          <div id="snap-markers"></div>
          <input id="beta-slider" type="range" min="0" max="90" value="30" step="0.5" />
        </div>
        <div id="beta-readout" class="beta-readout">30°</div>
      </div>
    </div>
    <script>
      const cfg = {{
        l1: Math.max({float(l1):.12g}, 1),
        l2: {float(l2):.12g},
        l3: Math.max({float(l3):.12g}, 1),
        l4: Math.max({float(l4):.12g}, 0),
        l5: {float(l5):.12g},
        alpha: {float(alpha):.12g},
        svgWidth: 960,
        svgHeight: 550,
        margin: 22,
      }};
      const series = {animation_payload};
      const forceMax = Math.max(
        1,
        ...series.forces.T1,
        ...series.forces.T3,
        ...series.forces.T4
      );

      const svg = document.getElementById("rotation-svg");
      const slider = document.getElementById("beta-slider");
      const readout = document.getElementById("beta-readout");
      const playButton = document.getElementById("play-button");
      const snapMarkers = document.getElementById("snap-markers");
      const ns = "http://www.w3.org/2000/svg";
      let playing = false;
      let direction = 1;
      let lastTime = null;

      function rad(deg) {{
        return deg * Math.PI / 180;
      }}

      function interpolate(xs, ys, x) {{
        if (!xs.length || !ys.length) return 0;
        if (x <= xs[0]) return ys[0];
        for (let i = 1; i < xs.length; i += 1) {{
          if (x <= xs[i]) {{
            const span = Math.max(xs[i] - xs[i - 1], 1e-9);
            const t = (x - xs[i - 1]) / span;
            return ys[i - 1] + t * (ys[i] - ys[i - 1]);
          }}
        }}
        return ys[ys.length - 1];
      }}

      function valueAt(group, key, beta) {{
        return interpolate(group.beta, group[key], beta);
      }}

      function snapBeta(beta) {{
        let snapped = Number(beta);
        let bestDistance = Infinity;
        for (const point of series.utilization.critical || []) {{
          const pointBeta = Number(point.beta);
          const distance = Math.abs(pointBeta - Number(beta));
          if (distance < bestDistance && distance <= 0.35) {{
            bestDistance = distance;
            snapped = pointBeta;
          }}
        }}
        return Math.max(0, Math.min(90, snapped));
      }}

      function utilizationColor(mu) {{
        if (mu >= 1) return "#ef4444";
        if (mu >= 0.8) return "#d97706";
        return "#16a34a";
      }}

      function etaValue(loopType, gamma) {{
        const g = Math.max(Math.abs(Number(gamma)), 0);
        if (loopType === "NB") {{
          return g <= 30 ? 1 : 0.3 + 0.7 * Math.cos(rad(1.5 * g - 45));
        }}
        if (loopType === "CONST") return 1;
        const ratio = g === 0 ? Infinity : 77.4 / g;
        return 1 - 0.448 / (0.64 + Math.pow(ratio - 0.9, 2));
      }}

      function angleState(beta) {{
        const betaRad = rad(beta);
        const alphaRad = rad(cfg.alpha);
        const s = Math.sin(betaRad) * Math.sin(alphaRad);
        const clamped = Math.max(Math.min(s, 1), -1);
        const signedPhi = Math.acos(clamped) * 180 / Math.PI - beta;
        const omega = 90 - beta + Math.asin(clamped) * 180 / Math.PI;
        return {{
          T1: beta,
          T3: Math.abs(signedPhi),
          T4: Math.abs(omega),
        }};
      }}

      function rotate(point, beta) {{
        const angle = -rad(beta);
        const ca = Math.cos(angle);
        const sa = Math.sin(angle);
        const x = point[0];
        const y = point[1];
        return [x * ca + y * sa, -x * sa + y * ca];
      }}

      function lineIntersection(p3, d3, p4, d4) {{
        const det = d3[0] * (-d4[1]) - d3[1] * (-d4[0]);
        if (Math.abs(det) < 1e-9) {{
          return [cfg.l3 + cfg.l1, 0];
        }}
        const rhs = [p4[0] - p3[0], p4[1] - p3[1]];
        const t = (rhs[0] * (-d4[1]) - rhs[1] * (-d4[0])) / det;
        return [p3[0] + t * d3[0], p3[1] + t * d3[1]];
      }}

      function effectiveBeta(beta) {{
        return Math.max(Number(beta), 0.01);
      }}

      function compute(beta) {{
        beta = effectiveBeta(beta);
        const halfWidth = cfg.l3;
        const halfHeight = cfg.l1;
        const gap = cfg.l4;
        const localCorners = [
          [-halfWidth, halfHeight],
          [halfWidth, halfHeight],
          [halfWidth, -halfHeight],
          [-halfWidth, -halfHeight],
        ];
        const localT1 = [-cfg.l2, halfHeight];
        const localT2 = [cfg.l5, halfHeight];
        const localT3 = [halfWidth, gap / 2];
        const localT4 = [halfWidth, -gap / 2];
        const betaRad = rad(beta);
        const alphaRad = rad(cfg.alpha);
        const signedPhi = Math.acos(Math.sin(betaRad) * Math.sin(alphaRad)) - betaRad;
        const omega = rad(90 - beta + Math.asin(Math.sin(betaRad) * Math.sin(alphaRad)) * 180 / Math.PI);
        const d3 = [Math.cos(signedPhi), Math.sin(signedPhi)];
        const d4 = [Math.cos(omega), Math.sin(omega)];
        const localBlock = lineIntersection(localT3, d3, localT4, d4);
        const ropeSum =
          Math.hypot(localBlock[0] - localT3[0], localBlock[1] - localT3[1]) +
          Math.hypot(localBlock[0] - localT4[0], localBlock[1] - localT4[1]);
        const a = Math.max(ropeSum / 2, gap / 2 + 1);
        const c = gap / 2;
        const b = Math.sqrt(Math.max(a * a - c * c, 1));
        const ellipse = [];
        for (let i = 0; i <= 72; i += 1) {{
          const theta = -1.25 + 2.5 * i / 72;
          ellipse.push(rotate([halfWidth + b * Math.cos(theta), a * Math.sin(theta)], beta));
        }}
        const corners = localCorners.map((point) => rotate(point, beta));
        const center = rotate([0, 0], beta);
        const t1 = rotate(localT1, beta);
        const t2 = rotate(localT2, beta);
        const t3 = rotate(localT3, beta);
        const t4 = rotate(localT4, beta);
        const block = rotate(localBlock, beta);
        return {{ corners, center, t1, t2, t3, t4, block, ellipse }};
      }}

      const bounds = (() => {{
        const points = [];
        for (let beta = 0; beta <= 90; beta += 1) {{
          const frame = compute(beta);
          points.push(...frame.corners, frame.center, frame.t1, frame.t2, frame.t3, frame.t4, frame.block);
        }}
        const maxAbsX = Math.max(...points.map((point) => Math.abs(point[0])), 1);
        const minY = Math.min(...points.map((point) => point[1]));
        const maxY = Math.max(...points.map((point) => point[1]));
        const scaleX = (cfg.svgWidth - 2 * cfg.margin) / (2 * maxAbsX);
        const scaleY = (cfg.svgHeight - 2 * cfg.margin) / Math.max(maxY - minY, 1);
        const scale = Math.min(scaleX, scaleY);
        return {{
          minY,
          maxY,
          scale,
          centerX: cfg.svgWidth / 2,
          centerY: cfg.margin + maxY * scale,
        }};
      }})();

      function screen(point) {{
        return [
          bounds.centerX + point[0] * bounds.scale,
          bounds.centerY - point[1] * bounds.scale,
        ];
      }}

      function attrs(element, values) {{
        for (const [key, value] of Object.entries(values)) {{
          element.setAttribute(key, value);
        }}
        return element;
      }}

      function make(name, className, values = {{}}, text = null) {{
        const element = document.createElementNS(ns, name);
        if (className) element.setAttribute("class", className);
        attrs(element, values);
        if (text !== null) element.textContent = text;
        svg.appendChild(element);
        return element;
      }}

      function line(className, start, end) {{
        const a = screen(start);
        const b = screen(end);
        make("line", className, {{ x1: a[0], y1: a[1], x2: b[0], y2: b[1] }});
      }}

      function verticalRopeToTop(point) {{
        const p = screen(point);
        make("line", "rope", {{ x1: p[0], y1: -80, x2: p[0], y2: p[1] }});
      }}

      function circle(className, point, radius) {{
        const p = screen(point);
        make("circle", className, {{ cx: p[0], cy: p[1], r: radius }});
      }}

      function label(className, point, text, dx, dy) {{
        const p = screen(point);
        make("text", className, {{ x: p[0] + dx, y: p[1] + dy }}, text);
      }}

      function styledText(className, point, text, dx, dy, color) {{
        const p = screen(point);
        make("text", className, {{ x: p[0] + dx, y: p[1] + dy, style: "fill: " + color }}, text);
      }}

      function drawArrow(anchor, target, force, maxForce, color) {{
        if (force <= 0 || maxForce <= 0) return;
        const start = screen(anchor);
        const targetPoint = screen(target);
        const dx = targetPoint[0] - start[0];
        const dy = targetPoint[1] - start[1];
        const distance = Math.max(Math.hypot(dx, dy), 1e-9);
        const ux = dx / distance;
        const uy = dy / distance;
        const length = 112 * Math.min(force / maxForce, 1);
        const end = [start[0] + ux * length, start[1] + uy * length];
        make("line", null, {{
          x1: start[0],
          y1: start[1],
          x2: end[0],
          y2: end[1],
          stroke: color,
          "stroke-width": 3.4,
          "stroke-linecap": "round",
        }});
        const head = 11;
        const px = -uy;
        const py = ux;
        const arrowPoints = [
          [end[0], end[1]],
          [end[0] - ux * head + px * head * 0.68, end[1] - uy * head + py * head * 0.68],
          [end[0] - ux * head - px * head * 0.68, end[1] - uy * head - py * head * 0.68],
        ].map((point) => point.map((value) => value.toFixed(1)).join(",")).join(" ");
        make("polygon", null, {{ points: arrowPoints, fill: color }});
      }}

      function setMetric(id, value, digits = 2, color = null) {{
        const element = document.getElementById(id);
        element.textContent = Number(value).toFixed(digits);
        if (color) element.style.color = color;
      }}

      function updateLiveTable(forces, mus, angles) {{
        for (const key of ["T1", "T3", "T4"]) {{
          const suffix = key.toLowerCase();
          const mu = mus[key];
          const color = utilizationColor(mu);
          const eta = etaValue(series.loopTypes[key], angles[key]);
          setMetric("force-" + suffix, forces[key], 1);
          setMetric("angle-" + suffix, angles[key], 1);
          setMetric("eta-" + suffix, eta, 3);
          setMetric("mu-" + suffix, mu, 2, color);
        }}
      }}

      function render(beta) {{
        const betaForGeometry = effectiveBeta(beta);
        svg.replaceChildren();
        const frame = compute(betaForGeometry);
        const forces = {{
          T1: valueAt(series.forces, "T1", betaForGeometry),
          T3: valueAt(series.forces, "T3", betaForGeometry),
          T4: valueAt(series.forces, "T4", betaForGeometry),
        }};
        const mus = {{
          T1: valueAt(series.utilization, "T1", betaForGeometry),
          T3: valueAt(series.utilization, "T3", betaForGeometry),
          T4: valueAt(series.utilization, "T4", betaForGeometry),
        }};
        const angles = angleState(betaForGeometry);
        const ellipsePath = "M " + frame.ellipse.map((point) => screen(point).map((value) => value.toFixed(1)).join(",")).join(" L ");
        make("path", "ellipse-guide", {{ d: ellipsePath }});
        verticalRopeToTop(frame.t1);
        verticalRopeToTop(frame.block);
        line("rope-secondary", frame.t3, frame.block);
        line("rope-secondary", frame.t4, frame.block);
        make("polygon", "panel", {{ points: frame.corners.map((point) => screen(point).map((value) => value.toFixed(1)).join(",")).join(" ") }});
        line("axis", rotate([-cfg.l3, 0], betaForGeometry), rotate([cfg.l3, 0], betaForGeometry));
        line("axis", rotate([0, -cfg.l1], betaForGeometry), rotate([0, cfg.l1], betaForGeometry));
        circle("hook", frame.t1, 9);
        circle("hook-unused", frame.t2, 8);
        circle("hook", frame.t3, 9);
        circle("hook", frame.t4, 9);
        circle("block", frame.block, 8);
        drawArrow(frame.t1, [frame.t1[0], frame.t1[1] + cfg.l1], forces.T1, forceMax, "#2563eb");
        drawArrow(frame.t3, frame.block, forces.T3, forceMax, "#ea580c");
        drawArrow(frame.t4, frame.block, forces.T4, forceMax, "#16a34a");
        circle("g-point", frame.center, 5);
        label("g-label", frame.center, "G", 8, 5);
        label("hook-label", frame.t1, "T1", -24, -10);
        label("unused-label", frame.t2, "T2", 10, -8);
        label("hook-label", frame.t3, "T3", 11, 5);
        label("hook-label", frame.t4, "T4", 11, 5);
        styledText("force-label", frame.t1, "μ " + mus.T1.toFixed(2), -36, 22, utilizationColor(mus.T1));
        styledText("force-label", frame.t3, "μ " + mus.T3.toFixed(2), 14, -12, utilizationColor(mus.T3));
        styledText("force-label", frame.t4, "μ " + mus.T4.toFixed(2), 14, 22, utilizationColor(mus.T4));
        updateLiveTable(forces, mus, angles);
        readout.textContent = Number(betaForGeometry).toFixed(betaForGeometry % 1 === 0 ? 0 : 2) + "°";
      }}

      slider.addEventListener("input", () => {{
        if (playing) {{
          playing = false;
          playButton.textContent = "▶";
        }}
        const snapped = snapBeta(Number(slider.value));
        slider.value = snapped;
        render(snapped);
      }});

      function animate(time) {{
        if (!playing) return;
        if (lastTime === null) lastTime = time;
        const delta = (time - lastTime) / 1000;
        lastTime = time;
        let next = Number(slider.value) + direction * delta * 32;
        if (next >= 90) {{
          next = 90;
          direction = -1;
        }} else if (next <= 0) {{
          next = 0;
          direction = 1;
        }}
        slider.value = next;
        render(next);
        requestAnimationFrame(animate);
      }}

      playButton.addEventListener("click", () => {{
        playing = !playing;
        playButton.textContent = playing ? "⏸" : "▶";
        lastTime = null;
        if (playing) requestAnimationFrame(animate);
      }});

      for (const point of series.utilization.critical || []) {{
        const marker = document.createElement("div");
        marker.className = "snap-marker";
        marker.style.left = (Number(point.beta) / 90 * 100) + "%";
        const label = document.createElement("span");
        label.textContent = point.label;
        marker.appendChild(label);
        snapMarkers.appendChild(marker);
      }}

      render(Number(slider.value));
    </script>
    """


def rotation_capacity_table(rows: list[dict]) -> pd.DataFrame:
    table_rows: list[dict[str, object]] = []
    for label, value_key, beta_key in (
        ("T1", "g_perm_T1", "beta_T1"),
        ("T3", "g_perm_T3", "beta_T3"),
        ("T4", "g_perm_T4", "beta_T4"),
        ("min", "governing_weight", "governing_beta"),
    ):
        row: dict[str, object] = {
            "Tõsteaas": label,
            "Nurk [deg]": rows[0][beta_key] if rows else 0.0,
        }
        for item in rows:
            row[f"{item['diameter']:.0f}"] = item[value_key]
        table_rows.append(row)
    return pd.DataFrame(table_rows)


def side_lift_capacity_table(rows: list[dict]) -> pd.DataFrame:
    table_rows: list[dict[str, object]] = []
    for label, value_key in (
        ("vormist vabastamine", "g_perm_demoulding"),
        ("tõstmine", "g_perm_lifting"),
    ):
        row: dict[str, object] = {"Olukord": label}
        for item in rows:
            row[f"{item['diameter']:.0f}"] = item[value_key]
        table_rows.append(row)
    return pd.DataFrame(table_rows)


def rotation_capacity_table_html(rows: list[dict], weight: float) -> str:
    return capacity_table_html(
        rotation_capacity_table(rows),
        weight,
        non_capacity_columns={"Tõsteaas", "Nurk [deg]"},
    )


def side_lift_capacity_table_html(rows: list[dict], weight: float) -> str:
    return capacity_table_html(
        side_lift_capacity_table(rows),
        weight,
        non_capacity_columns={"Olukord"},
    )


def capacity_table_html(
    table: pd.DataFrame,
    weight: float,
    non_capacity_columns: set[str],
) -> str:
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in table.columns)
    body_rows = []
    for item in table.to_dict("records"):
        cells = []
        for column, value in item.items():
            class_name = ""
            text = str(value)
            if column == "Nurk [deg]":
                text = f"{float(value):.1f}"
            elif column not in non_capacity_columns:
                capacity = float(value)
                class_name = " class=\"ok\"" if capacity >= weight else " class=\"low\""
                text = f"{capacity:.1f}"
            cells.append(f"<td{class_name}>{escape(text)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    body = "".join(body_rows)
    return f"""
    <style>
      .rotation-capacity {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.92rem;
        color: var(--text-color);
      }}
      .rotation-capacity th,
      .rotation-capacity td {{
        border: 1px solid rgba(128, 128, 128, 0.28);
        padding: 0.35rem 0.45rem;
        text-align: right;
        color: var(--text-color);
      }}
      .rotation-capacity th {{
        background: var(--secondary-background-color);
        font-weight: 650;
      }}
      .rotation-capacity th:first-child,
      .rotation-capacity td:first-child {{
        text-align: left;
      }}
      .rotation-capacity td.ok {{
        background: rgba(34, 197, 94, 0.16);
        color: var(--text-color) !important;
      }}
      .rotation-capacity td.low {{
        background: rgba(239, 68, 68, 0.14);
        color: var(--text-color) !important;
      }}
    </style>
    <table class="rotation-capacity">
      <thead><tr>{headers}</tr></thead>
      <tbody>{body}</tbody>
    </table>
    """


def rotation_utilization_frame(result) -> pd.DataFrame:
    wide = pd.DataFrame(
        {
            "beta": result.beta,
            "T1": result.mu_rot_1,
            "T3": result.mu_rot_3,
            "T4": result.mu_rot_4,
            "piir": [1.0] * len(result.beta),
        }
    )
    return wide.melt(
        id_vars="beta",
        value_vars=["T1", "T3", "T4", "piir"],
        var_name="loop",
        value_name="utilization",
    )


def rotation_utilization_chart(result, summary: dict | None = None) -> alt.Chart:
    data = rotation_utilization_frame(result)
    y_max = ceil(max(1.0, float(data["utilization"].max())) * 10) / 10
    y_max = max(1.0, y_max)
    y_values = [round(index / 10, 1) for index in range(0, int(round(y_max * 10)) + 1)]
    y = vertical_axis_y(
        "utilization:Q",
        "Kasutusaste [-]",
        scale=alt.Scale(domain=[0, y_max], zero=True, nice=False),
        values=y_values,
        tick_min_step=0.1,
    )
    chart = (
        alt.Chart(data)
        .mark_line()
        .encode(
            x=alt.X("beta:Q", title="Pöördenurk beta [deg]"),
            y=y,
            color=alt.Color(
                "loop:N",
                legend=top_legend("Tõsteaas"),
                scale=alt.Scale(
                    domain=["T1", "T3", "T4", "piir"],
                    range=["#1f77b4", "#ff7f0e", "#2ca02c", "#e5e7eb"],
                ),
            ),
            strokeDash=alt.StrokeDash(
                "loop:N",
                scale=alt.Scale(
                    domain=["T1", "T3", "T4", "piir"],
                    range=[[1, 0], [1, 0], [1, 0], [6, 4]],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("beta:Q", title="Pöördenurk", format=".1f"),
                alt.Tooltip("loop:N", title="Tõsteaas"),
                alt.Tooltip("utilization:Q", title="Kasutusaste", format=".3f"),
            ],
        )
        .properties(height=360)
    )
    marker_data = rotation_utilization_extreme_frame(result, summary)
    markers = (
        alt.Chart(marker_data)
        .mark_point(filled=True, size=120, stroke="#111827", strokeWidth=1)
        .encode(
            x=alt.X("beta:Q", title="Pöördenurk beta [deg]"),
            y=y,
            color=alt.Color(
                "loop:N",
                legend=None,
                scale=alt.Scale(
                    domain=["T1", "T3", "T4", "piir"],
                    range=["#1f77b4", "#ff7f0e", "#2ca02c", "#e5e7eb"],
                ),
            ),
            tooltip=[
                alt.Tooltip("loop:N", title="Tõsteaas"),
                alt.Tooltip("diameter:N", title="Läbimõõt"),
                alt.Tooltip("beta:Q", title="Pöördenurk", format=".1f"),
                alt.Tooltip("utilization:Q", title="Maks. kasutusaste", format=".3f"),
            ],
        )
    )
    return (chart + markers).resolve_scale(y="shared").configure_axis(labelLimit=120)


def rotation_utilization_extreme_frame(result, summary: dict | None = None) -> pd.DataFrame:
    diameter_by_loop = {"T1": "", "T3": "", "T4": ""}
    if summary is not None:
        diameter_by_loop = {
            "T1": f"{summary['t1_diameter']:.0f} mm",
            "T3": f"{summary['t34_diameter']:.0f} mm",
            "T4": f"{summary['t34_diameter']:.0f} mm",
        }
    rows = []
    for loop, values in (
        ("T1", result.mu_rot_1),
        ("T3", result.mu_rot_3),
        ("T4", result.mu_rot_4),
    ):
        index = int(pd.Series(values).idxmax())
        rows.append(
            {
                "loop": loop,
                "diameter": diameter_by_loop[loop],
                "beta": result.beta[index],
                "utilization": values[index],
            }
        )
    return pd.DataFrame(rows)


def force_components_frame(result: object, loop: str) -> pd.DataFrame:
    wide = force_components_wide_frame(result, loop)
    data = wide.melt(
        id_vars="beta",
        value_vars=["N", "V", "combined"],
        var_name="component",
        value_name="force",
    )
    data["component"] = data["component"].replace({"combined": "summaarne"})
    return data


def force_components_chart(result: object, loop: str) -> alt.Chart:
    data = force_components_frame(result, loop)
    y_max = force_axis_max(float(data["force"].max()))
    tick_step = 10 if y_max <= 100 else 20
    y_values = list(range(0, int(y_max) + tick_step, tick_step))
    y = vertical_axis_y(
        "force:Q",
        "Jõukomponent [kN]",
        scale=alt.Scale(domain=[0, y_max], zero=True, nice=False),
        values=y_values,
        tick_min_step=tick_step,
    )
    chart = (
        alt.Chart(data)
        .mark_line()
        .encode(
            x=alt.X("beta:Q", title="Pöördenurk beta [deg]"),
            y=y,
            color=alt.Color(
                "component:N",
                scale=alt.Scale(
                    domain=["N", "V", "summaarne"],
                    range=["#1f77b4", "#c05621", "#8a8f98"],
                ),
                legend=top_legend("Komponent"),
            ),
            strokeDash=alt.StrokeDash(
                "component:N",
                scale=alt.Scale(
                    domain=["N", "V", "summaarne"],
                    range=[[1, 0], [1, 0], [6, 4]],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("beta:Q", title="Pöördenurk", format=".1f"),
                alt.Tooltip("component:N", title="Komponent"),
                alt.Tooltip("force:Q", title="Jõud", format=".1f"),
            ],
        )
        .properties(height=300)
    )
    markers = (
        alt.Chart(force_component_extreme_points(result, loop))
        .mark_point(filled=True, size=120, stroke="#111827", strokeWidth=1)
        .encode(
            x=alt.X("beta:Q", title="Pöördenurk beta [deg]"),
            y=y,
            color=alt.Color(
                "component:N",
                scale=alt.Scale(
                    domain=["N", "V", "summaarne"],
                    range=["#1f77b4", "#c05621", "#8a8f98"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("extreme:N", title="Äärmus"),
                alt.Tooltip("beta:Q", title="Pöördenurk", format=".1f"),
                alt.Tooltip("component:N", title="Komponent"),
                alt.Tooltip("force:Q", title="Jõud", format=".1f"),
            ],
        )
    )
    return (chart + markers).resolve_scale(y="shared").configure_axis(labelLimit=120)


def top_legend(title: str) -> alt.Legend:
    return alt.Legend(
        title=None,
        orient="top",
        direction="horizontal",
        columns=4,
        labelLimit=160,
        offset=0,
    )


def vertical_axis_y(
    shorthand: str,
    title: str,
    scale: alt.Scale | None = None,
    values: list[float] | list[int] | None = None,
    tick_min_step: float | int | None = None,
) -> alt.Y:
    return alt.Y(
        shorthand,
        title=title,
        scale=scale,
        axis=alt.Axis(
            orient="left",
            titleAngle=-90,
            titlePadding=42,
            labelPadding=8,
            values=values,
            tickMinStep=tick_min_step,
            grid=True,
        ),
    )


def force_axis_max(value: float) -> int:
    step = 10 if value <= 100 else 20
    return max(step, int(ceil(value / step) * step))


def force_component_summary_table(report: object, force_components: object) -> pd.DataFrame:
    rows: list[dict[tuple[str, str, str], object]] = []
    demoulding = side_lift_component_rows(
        report.element.weight + report.factors.q_adh * report.element.form_area,
        report.geometry.l2,
        report.geometry.effective_l5,
        report.element.demoulding_sling_angle,
    )
    lifting = side_lift_component_rows(
        report.element.weight * report.factors.psi_dyn,
        report.geometry.l2,
        report.geometry.effective_l5,
        report.element.lifting_sling_angle,
    )
    for loop in ("T1", "T2", "T3", "T4"):
        row: dict[tuple[str, str, str], object] = {("", "", "Tõsteaas"): loop}
        if loop in {"T1", "T2"}:
            row.update(
                {
                    ("vormist vabastamine", "", "N"): demoulding[loop]["N"],
                    ("vormist vabastamine", "", "V"): demoulding[loop]["V"],
                    ("tõstmine", "", "N"): lifting[loop]["N"],
                    ("tõstmine", "", "V"): lifting[loop]["V"],
                }
            )
        else:
            row.update(
                {
                    ("vormist vabastamine", "", "N"): "-",
                    ("vormist vabastamine", "", "V"): "-",
                    ("tõstmine", "", "N"): "-",
                    ("tõstmine", "", "V"): "-",
                }
            )
        if loop == "T2":
            row.update(rotation_extreme_cells(None))
        else:
            row.update(rotation_extreme_cells(force_components, loop))
        rows.append(row)
    table = pd.DataFrame(rows)
    table.columns = pd.MultiIndex.from_tuples(table.columns)
    table = table.set_index(("", "", "Tõsteaas"))
    table.index.name = "Tõsteaas"
    return table


def side_lift_component_rows(
    vertical_total_load: float,
    l2: float,
    l5: float,
    sling_angle: float,
) -> dict[str, dict[str, float]]:
    denominator = l2 + l5
    t1_vertical = vertical_total_load * l5 / denominator
    t2_vertical = vertical_total_load * l2 / denominator
    z = sling_factor(sling_angle)
    tangent = (z**2 - 1.0) ** 0.5
    return {
        "T1": {
            "N": round(t1_vertical, 1),
            "V": round(t1_vertical * tangent, 1),
        },
        "T2": {
            "N": round(t2_vertical, 1),
            "V": round(t2_vertical * tangent, 1),
        },
    }


def rotation_extreme_cells(
    force_components: object | None,
    loop: str | None = None,
) -> dict[tuple[str, str, str], object]:
    empty = {
        ("pööramine", "max N", "N"): "-",
        ("pööramine", "max N", "V"): "-",
        ("pööramine", "max N", "deg"): "-",
        ("pööramine", "max V", "N"): "-",
        ("pööramine", "max V", "V"): "-",
        ("pööramine", "max V", "deg"): "-",
    }
    if force_components is None or loop is None:
        return empty
    wide = force_components_wide_frame(force_components, loop)
    max_n_index = int(wide["N"].abs().idxmax())
    max_v_index = int(wide["V"].abs().idxmax())
    return {
        ("pööramine", "max N", "N"): round(wide.loc[max_n_index, "N"], 1),
        ("pööramine", "max N", "V"): round(wide.loc[max_n_index, "V"], 1),
        ("pööramine", "max N", "deg"): round(wide.loc[max_n_index, "beta"], 1),
        ("pööramine", "max V", "N"): round(wide.loc[max_v_index, "N"], 1),
        ("pööramine", "max V", "V"): round(wide.loc[max_v_index, "V"], 1),
        ("pööramine", "max V", "deg"): round(wide.loc[max_v_index, "beta"], 1),
    }


def force_component_extreme_points(result: object, loop: str) -> pd.DataFrame:
    wide = force_components_wide_frame(result, loop)
    max_n_index = int(wide["N"].abs().idxmax())
    max_v_index = int(wide["V"].abs().idxmax())
    return pd.DataFrame(
        [
            {
                "extreme": "max N",
                "beta": wide.loc[max_n_index, "beta"],
                "component": "N",
                "force": wide.loc[max_n_index, "N"],
            },
            {
                "extreme": "max V",
                "beta": wide.loc[max_v_index, "beta"],
                "component": "V",
                "force": wide.loc[max_v_index, "V"],
            },
        ]
    )


def force_components_wide_frame(result: object, loop: str) -> pd.DataFrame:
    columns = {
        "T1": ("t1_vertical", "t1_horizontal"),
        "T3": ("t3_vertical", "t3_horizontal"),
        "T4": ("t4_vertical", "t4_horizontal"),
    }
    vertical_key, horizontal_key = columns[loop]
    return pd.DataFrame(
        {
            "beta": result.beta,
            "N": getattr(result, vertical_key),
            "V": getattr(result, horizontal_key),
        }
    ).assign(combined=lambda frame: (frame["N"] ** 2 + frame["V"] ** 2) ** 0.5)


if __name__ == "__main__":
    main()
