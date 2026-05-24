import unittest

from lifting_loops.input_schema import CalculationInput, build_report_from_input, input_options


class InputSchemaTests(unittest.TestCase):
    def test_options_expose_ui_choices(self):
        options = input_options()
        self.assertIn("S355", options["steel_grades"])
        self.assertIn("NA", options["loop_types"])
        self.assertIn("same_diameter", options["selection_modes"])
        self.assertEqual(options["defaults"]["beta_step"], 0.5)

    def test_presets_resolve_to_factors(self):
        data = CalculationInput(
            weight=20,
            thickness=250,
            form_area=10,
            l1=1000,
            l2=2000,
            l3=3000,
            l4=1000,
            alpha=30,
            form_surface="lacquered_planed_wood",
            dynamic_factor_preset="smooth_transport",
        )
        self.assertEqual(data.effective_q_adh(), 2.0)
        self.assertEqual(data.effective_psi_dyn(), 2.5)
        self.assertEqual(data.geometry().effective_l5, 2000)

    def test_manual_values_override_presets(self):
        data = CalculationInput(
            weight=20,
            thickness=250,
            form_area=10,
            l1=1000,
            l2=2000,
            l3=3000,
            l4=1000,
            alpha=30,
            q_adh=1.7,
            psi_dyn=1.4,
        )
        self.assertEqual(data.effective_q_adh(), 1.7)
        self.assertEqual(data.effective_psi_dyn(), 1.4)

    def test_tolerance_is_passed_to_loop_catalog(self):
        report = build_report_from_input(
            CalculationInput(
                weight=20,
                thickness=250,
                form_area=10,
                l1=1000,
                l2=2000,
                l3=3000,
                l4=1000,
                alpha=30,
                tolerance=5,
            )
        )
        self.assertEqual(report.selection.checked[0].arrangement.t1_loop.tolerance, 5)

    def test_build_report_from_formal_input(self):
        report = build_report_from_input(
            CalculationInput(
                weight=20,
                thickness=250,
                form_area=10,
                l1=1000,
                l2=2000,
                l3=3000,
                l4=1000,
                alpha=30,
                selection_mode="split_t1_t34",
                t2_type="CONST",
                t3_type="NB",
                t4_type="CONST",
            )
        )
        self.assertEqual(report.selection.mode, "split_t1_t34")
        self.assertEqual(report.loop_types.effective_t2_type, "CONST")
        self.assertEqual(report.loop_types.t3_type, "NB")
        self.assertIsNotNone(report.selection.selected)

    def test_invalid_angle_is_rejected(self):
        data = CalculationInput(
            weight=20,
            thickness=250,
            form_area=10,
            l1=1000,
            l2=2000,
            l3=3000,
            l4=1000,
            alpha=90,
        )
        with self.assertRaises(ValueError):
            data.validate()


if __name__ == "__main__":
    unittest.main()
