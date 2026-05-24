import unittest

from lifting_loops.loop_catalog import build_default_catalog
from lifting_loops.models import (
    ElementInput,
    FactorsInput,
    LoopArrangementInput,
    LoopTypesInput,
    RotationGeometry,
)
from lifting_loops.report import (
    calculation_report_to_dict,
    diameter_rotation_capacity_rows,
    diameter_side_lift_capacity_rows,
    selected_utilization_summary,
)
from lifting_loops.selection import (
    build_calculation_report,
    check_arrangement,
    check_loop,
    select_smallest_suitable_loop,
)
from lifting_loops.utilization import arrangement_rotation_utilization


class SelectionTests(unittest.TestCase):
    def test_select_smallest_suitable_loop_returns_checked_results(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        element = ElementInput(weight=20, thickness=250, form_area=10)
        factors = FactorsInput(gamma_s=3.0, psi_dyn=1.3, q_adh=1.0)
        result = select_smallest_suitable_loop(
            build_default_catalog(steel_grade="S355"),
            element,
            factors,
            geometry,
            LoopTypesInput(t1_type="NA", t3_type="NA", t4_type="NA"),
        )
        self.assertEqual(len(result.checked), 5)
        self.assertIsNotNone(result.selected)
        self.assertEqual(result.selected.arrangement.t1_loop.diameter, result.selected.arrangement.t34_loop.diameter)

    def test_loop_types_can_differ_by_location(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        element = ElementInput(weight=20, thickness=250, form_area=10)
        factors = FactorsInput(gamma_s=3.0, psi_dyn=1.3, q_adh=1.0)
        result = select_smallest_suitable_loop(
            build_default_catalog(steel_grade="S235"),
            element,
            factors,
            geometry,
            LoopTypesInput(t1_type="NA", t3_type="NB", t4_type="CONST"),
        )
        self.assertEqual(
            {check.arrangement.t1_loop.steel_grade for check in result.checked},
            {"S235"},
        )
        self.assertIsNotNone(result.selected)

    def test_selected_result_has_rotation_utilization(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        element = ElementInput(weight=20, thickness=250, form_area=10)
        factors = FactorsInput(gamma_s=3.0, psi_dyn=1.3, q_adh=1.0)
        result = select_smallest_suitable_loop(
            build_default_catalog(steel_grade="S355"),
            element,
            factors,
            geometry,
            LoopTypesInput(t1_type="NA", t3_type="NA", t4_type="NA"),
        )
        self.assertIsNotNone(result.selected)
        combined = arrangement_rotation_utilization(result.selected)
        self.assertGreater(combined.max_mu_rot_1, 0)

    def test_split_mode_checks_all_t1_and_t34_pairs(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        element = ElementInput(weight=20, thickness=250, form_area=10)
        factors = FactorsInput(gamma_s=3.0, psi_dyn=1.3, q_adh=1.0)
        result = select_smallest_suitable_loop(
            build_default_catalog(steel_grade="S355"),
            element,
            factors,
            geometry,
            LoopTypesInput(t1_type="NA", t3_type="NB", t4_type="CONST"),
            mode="split_t1_t34",
        )
        self.assertEqual(len(result.checked), 25)
        self.assertIsNotNone(result.selected)
        self.assertIn(result.selected.arrangement.t34_loop.diameter, {12, 16, 20, 25, 32})

    def test_build_calculation_report_wraps_selection_and_inputs(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        element = ElementInput(weight=20, thickness=250, form_area=10)
        factors = FactorsInput(gamma_s=3.0, psi_dyn=1.3, q_adh=1.0)
        loop_types = LoopTypesInput(t1_type="NA", t3_type="NA", t4_type="NA")
        report = build_calculation_report(
            build_default_catalog(steel_grade="S355"),
            element,
            factors,
            geometry,
            loop_types,
        )
        self.assertEqual(report.element, element)
        self.assertEqual(report.loop_types, loop_types)
        self.assertIsNotNone(report.selection.selected)

        data = calculation_report_to_dict(report)
        self.assertEqual(data["inputs"]["element"]["weight"], 20)
        self.assertIsNotNone(data["selected"])
        self.assertIn("rotation_utilization", data)

        rows = diameter_rotation_capacity_rows(report)
        self.assertEqual(len(rows), 5)
        self.assertIn("governing_beta", rows[0])

        side_rows = diameter_side_lift_capacity_rows(report)
        self.assertEqual(len(side_rows), 5)
        self.assertIn("g_perm_demoulding", side_rows[0])
        self.assertIn("g_perm_lifting", side_rows[0])

        utilizations = selected_utilization_summary(report)
        self.assertIsNotNone(utilizations)
        self.assertIn("demoulding", utilizations)
        self.assertIn("lifting", utilizations)

    def test_l5_controls_effective_working_anchor_count(self):
        element = ElementInput(weight=20, thickness=250, form_area=10)
        factors = FactorsInput(gamma_s=3.0, psi_dyn=1.3, q_adh=1.0)
        loop = build_default_catalog(steel_grade="S355")[0]
        loop_types = LoopTypesInput(t1_type="NA", t3_type="NA", t4_type="NA")

        symmetric = check_loop(
            loop,
            element,
            factors,
            RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30),
            loop_types,
        )
        asymmetric = check_loop(
            loop,
            element,
            factors,
            RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30, l5=500),
            loop_types,
        )

        self.assertEqual(
            RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30).effective_l5,
            2000,
        )
        self.assertLess(asymmetric.g_adm_dyn, symmetric.g_adm_dyn)

    def test_demoulding_and_lifting_sling_angles_are_separate(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        factors = FactorsInput(gamma_s=3.0, psi_dyn=1.3, q_adh=1.0)
        loop = build_default_catalog(steel_grade="S355")[0]
        loop_types = LoopTypesInput(t1_type="NA", t3_type="NA", t4_type="NA")

        demoulding_angled = check_loop(
            loop,
            ElementInput(
                weight=20,
                thickness=250,
                form_area=10,
                demoulding_sling_angle=60,
                lifting_sling_angle=0,
            ),
            factors,
            geometry,
            loop_types,
        )
        lifting_angled = check_loop(
            loop,
            ElementInput(
                weight=20,
                thickness=250,
                form_area=10,
                demoulding_sling_angle=0,
                lifting_sling_angle=60,
            ),
            factors,
            geometry,
            loop_types,
        )

        self.assertLess(demoulding_angled.g_adm_adh, lifting_angled.g_adm_adh)
        self.assertGreater(demoulding_angled.g_adm_dyn, lifting_angled.g_adm_dyn)

    def test_t2_type_controls_side_lifting_but_not_rotation(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        element = ElementInput(
            weight=20,
            thickness=250,
            form_area=10,
            demoulding_sling_angle=60,
            lifting_sling_angle=60,
        )
        factors = FactorsInput(gamma_s=3.0, psi_dyn=1.3, q_adh=1.0)
        loop = build_default_catalog(steel_grade="S355")[0]
        arrangement = LoopArrangementInput(t1_loop=loop, t34_loop=loop)

        all_constant = check_arrangement(
            arrangement,
            element,
            factors,
            geometry,
            LoopTypesInput(t1_type="CONST", t2_type="CONST", t3_type="CONST", t4_type="CONST"),
        )
        t2_reduced = check_arrangement(
            arrangement,
            element,
            factors,
            geometry,
            LoopTypesInput(t1_type="CONST", t2_type="NB", t3_type="CONST", t4_type="CONST"),
        )

        self.assertLess(t2_reduced.g_adm_adh, all_constant.g_adm_adh)
        self.assertLess(t2_reduced.g_adm_dyn, all_constant.g_adm_dyn)
        self.assertEqual(t2_reduced.g_adm_rot_1, all_constant.g_adm_rot_1)


if __name__ == "__main__":
    unittest.main()
