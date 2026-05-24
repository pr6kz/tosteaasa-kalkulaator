import unittest

from lifting_loops.loads import dynamic_lift_load, sling_factor


class LoadTests(unittest.TestCase):
    def test_sling_factor_zero_angle_is_one(self):
        self.assertAlmostEqual(sling_factor(0), 1.0)

    def test_sling_factor_60_degrees(self):
        self.assertAlmostEqual(sling_factor(60), 2.0)

    def test_dynamic_lift_load(self):
        self.assertAlmostEqual(dynamic_lift_load(100, 1.3, 0, 2), 65.0)

    def test_sling_factor_rejects_90_degrees(self):
        with self.assertRaises(ValueError):
            sling_factor(90)


if __name__ == "__main__":
    unittest.main()
