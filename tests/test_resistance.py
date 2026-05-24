import unittest

from lifting_loops.models import LoopInput
from lifting_loops.resistance import (
    bar_area,
    characteristic_tension_resistance,
    cover_reduction_factor,
)


class ResistanceTests(unittest.TestCase):
    def test_characteristic_tension_resistance_uses_two_branches(self):
        loop = LoopInput(16, "S355", 510, 0.8)
        self.assertAlmostEqual(
            characteristic_tension_resistance(loop),
            2 * bar_area(16) * 510 / 1000,
        )

    def test_cover_reduction_s235(self):
        loop = LoopInput(25, "S235", 360, 0.8, tolerance=10)
        expected = min((250 - 25 - 20) / (6.4 * 25), 1)
        self.assertAlmostEqual(cover_reduction_factor(250, loop), expected)

    def test_cover_reduction_s355(self):
        loop = LoopInput(16, "S355", 510, 0.8, tolerance=10)
        expected = min((250 - 16 - 20) / (9 * 16), 1)
        self.assertAlmostEqual(cover_reduction_factor(250, loop), expected)


if __name__ == "__main__":
    unittest.main()
