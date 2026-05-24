import unittest

from lifting_loops.loop_catalog import build_default_catalog
from lifting_loops.models import ElementInput, FactorsInput, LoopTypesInput, RotationGeometry
from lifting_loops.selection import check_loop
from lifting_loops.utilization import utilization_ratio


class UtilizationTests(unittest.TestCase):
    def test_utilization_ratio_handles_non_positive_admissible_weight(self):
        self.assertEqual(utilization_ratio(10, 0), float("inf"))

    def test_rotation_utilization_is_attached_to_check_result(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        element = ElementInput(weight=20, thickness=250, form_area=10)
        factors = FactorsInput(gamma_s=3.0, psi_dyn=1.3, q_adh=1.0)
        loop = build_default_catalog(steel_grade="S355")[0]
        result = check_loop(
            loop,
            element,
            factors,
            geometry,
            LoopTypesInput(t1_type="NA", t3_type="NB", t4_type="CONST"),
        )
        self.assertEqual(
            len(result.rotation_reduction.beta),
            len(result.rotation_utilization.mu_rot_1),
        )
        self.assertGreater(result.rotation_utilization.max_mu_rot_1, 0)


if __name__ == "__main__":
    unittest.main()

