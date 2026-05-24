import unittest
from pathlib import Path
import shutil

from lifting_loops.models import RotationUtilizationResult
from lifting_loops.plotting import save_rotation_utilization_plot


class PlottingTests(unittest.TestCase):
    def test_save_rotation_utilization_plot_writes_file(self):
        result = RotationUtilizationResult(
            beta=[0.5, 1.0, 1.5],
            mu_rot_1=[0.2, 0.3, 0.4],
            mu_rot_3=[0.1, 0.2, 0.3],
            mu_rot_4=[0.3, 0.2, 0.1],
            max_mu_rot_1=0.4,
            max_mu_rot_3=0.3,
            max_mu_rot_4=0.3,
            beta_max_1=1.5,
            beta_max_3=1.5,
            beta_max_4=0.5,
        )
        tmp = Path("test_outputs")
        tmp.mkdir(exist_ok=True)
        try:
            path = tmp / "utilization.png"
            save_rotation_utilization_plot(result, path)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
