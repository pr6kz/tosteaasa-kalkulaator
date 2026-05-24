import numpy as np
import unittest

from lifting_loops.models import RotationGeometry
from lifting_loops.rotation import (
    angle_omega,
    angle_phi,
    analyze_rotation_force_components,
    analyze_rotation_reduction,
    beta_values,
    force_f1,
    force_f3,
)


class RotationTests(unittest.TestCase):
    def test_beta_values_use_fixed_step(self):
        betas = beta_values(0.5)
        self.assertAlmostEqual(betas[0], 0.5)
        self.assertAlmostEqual(betas[-1], 89.5)

    def test_rotation_reduction_returns_positive_minimums(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        result = analyze_rotation_reduction(geometry, "NA", step=0.5)
        self.assertGreater(result.min_k_rot_1, 0)
        self.assertGreater(result.min_k_rot_3, 0)
        self.assertGreater(result.min_k_rot_4, 0)

    def test_force_f1_accepts_arrays(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        values = force_f1(np.array([10, 20]), geometry)
        self.assertEqual(values.shape, (2,))

    def test_rotation_force_components_use_loop_local_angles(self):
        geometry = RotationGeometry(l1=1000, l2=2000, l3=3000, l4=1000, alpha=30)
        result = analyze_rotation_force_components(geometry, weight=20, psi_dyn=1.3, step=30.0)
        beta = 30.0
        total = 20 * 1.3
        f1 = force_f1(beta, geometry) * total
        f3 = force_f3(beta, geometry) * total
        phi = np.radians(angle_phi(beta, geometry.alpha))
        omega = np.radians(angle_omega(beta, geometry.alpha))

        self.assertAlmostEqual(result.t1_vertical[0], f1 * np.cos(np.radians(beta)))
        self.assertAlmostEqual(result.t1_horizontal[0], f1 * np.sin(np.radians(beta)))
        self.assertAlmostEqual(result.t3_vertical[0], f3 * np.cos(phi))
        self.assertAlmostEqual(result.t3_horizontal[0], f3 * np.sin(phi))
        self.assertAlmostEqual(result.t4_vertical[0], f3 * np.cos(omega))
        self.assertAlmostEqual(result.t4_horizontal[0], f3 * np.sin(omega))


if __name__ == "__main__":
    unittest.main()
