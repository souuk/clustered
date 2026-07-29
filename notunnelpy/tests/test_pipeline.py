from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

from notunnelpy.generate_demo_data import generate_demo_scan
from notunnelpy.plot_stm import level_matrix, plot_scan_set
from notunnelpy.stm_io import load_scan_set, parse_parameter_file


class SyntheticPipelineTests(unittest.TestCase):
    def test_generator_matches_binary_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            forward, backward, parameters = generate_demo_scan(
                directory,
                points=8,
                lines=6,
                pattern="bump",
                noise=0.0,
                backward_offset=0.0,
            )

            parsed = parse_parameter_file(parameters)
            self.assertEqual(parsed.points, 8)
            self.assertEqual(parsed.lines, 6)
            self.assertTrue(parsed.synthetic)
            self.assertEqual(parsed.expected_samples, 48)
            self.assertEqual(parsed.expected_bytes, 96)
            self.assertEqual(forward.stat().st_size, 96)
            self.assertEqual(backward.stat().st_size, 96)

            scan = load_scan_set(directory)
            self.assertEqual(scan.forward.shape, (6, 8))
            self.assertIsNotNone(scan.backward_aligned)
            np.testing.assert_array_equal(scan.forward, scan.backward_aligned)

    def test_incomplete_forward_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            forward, _, _ = generate_demo_scan(
                directory,
                points=5,
                lines=4,
                noise=0.0,
            )
            forward.write_bytes(forward.read_bytes()[:-2])

            with self.assertRaisesRegex(ValueError, "Unexpected file length"):
                load_scan_set(directory)

    def test_forward_only_plot_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _, backward, _ = generate_demo_scan(
                directory,
                points=10,
                lines=7,
                pattern="slope",
            )
            backward.unlink()

            scan = load_scan_set(directory)
            self.assertIsNone(scan.backward_aligned)
            output = plot_scan_set(scan, directory / "forward-only.png", dpi=72)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    def test_full_comparison_plot_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            generate_demo_scan(
                directory,
                points=12,
                lines=9,
                pattern="double-bump",
                seed=7,
            )
            scan = load_scan_set(directory, require_backward=True)
            output = plot_scan_set(
                scan,
                directory / "comparison.png",
                level="line",
                dpi=72,
            )
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    def test_plane_leveling_removes_a_plane(self) -> None:
        yy, xx = np.indices((8, 10), dtype=float)
        plane = (3.0 * xx) - (2.0 * yy) + 9.0
        leveled = level_matrix(plane, "plane")
        self.assertLess(float(np.max(np.abs(leveled))), 1e-10)


if __name__ == "__main__":
    unittest.main()
