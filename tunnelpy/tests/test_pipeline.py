from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

from tunnelpy.plot_stm import level_matrix, plot_scan_set
from tunnelpy.stm_io import load_scan_set, parse_parameter_records


def write_fixture(
    directory: Path,
    forward: np.ndarray,
    backward_acquisition: np.ndarray,
    *,
    prefix: str = "STM1",
    number: int = 0,
    completed_lines: int | None = None,
) -> None:
    lines, points = forward.shape
    if completed_lines is None:
        completed_lines = lines
    forward.astype("<i2").tofile(directory / f"{prefix}F{number}.hex")
    backward_acquisition.astype("<i2").tofile(directory / f"{prefix}B{number}.hex")
    (directory / f"{prefix}P{number}.txt").write_text(
        f"{points} number of points\n"
        f"{lines} number of lines\n"
        "If Image finished early. 0 number of points\n"
        f"{completed_lines} number of lines\n"
        "2279 V, sample voltage\n"
        "1.00 nA, tunneling current\n",
        encoding="utf-8",
    )


class TunnelPipelineTests(unittest.TestCase):
    def test_exact_scan_and_backward_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            forward = np.arange(24, dtype=np.int16).reshape(4, 6)
            backward_acquisition = np.fliplr(forward)
            write_fixture(directory, forward, backward_acquisition)

            scan = load_scan_set(directory, prefix="STM1", scan_number=0)
            np.testing.assert_array_equal(scan.forward, forward)
            np.testing.assert_array_equal(scan.backward_aligned, forward)
            self.assertFalse(scan.partial)

    def test_multiple_parameter_records_are_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "STM1P0.txt"
            record = (
                "4 number of points\n3 number of lines\n"
                "If Image finished early. 0 number of points\n"
                "3 number of lines\n2279 V, sample voltage\n"
                "1.00 nA, tunneling current\n"
            )
            path.write_text(record + record, encoding="utf-8")
            records = parse_parameter_records(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[-1].record_index, 1)
            self.assertEqual(records[-1].record_count, 2)

    def test_truncated_scan_recovers_complete_shared_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            forward = np.arange(20, dtype=np.int16).reshape(4, 5)
            backward = np.fliplr(forward)
            write_fixture(directory, forward, backward)
            (directory / "STM1F0.hex").write_bytes(
                (directory / "STM1F0.hex").read_bytes()[:-3 * 2]
            )
            (directory / "STM1B0.hex").write_bytes(
                (directory / "STM1B0.hex").read_bytes()[:-2 * 2]
            )

            with self.assertRaisesRegex(ValueError, "incomplete"):
                load_scan_set(directory, prefix="STM1", scan_number=0)
            scan = load_scan_set(
                directory,
                prefix="STM1",
                scan_number=0,
                allow_partial=True,
            )
            self.assertEqual(scan.forward.shape, (3, 5))
            self.assertEqual(scan.backward_aligned.shape, (3, 5))
            self.assertTrue(scan.partial)

    def test_appended_file_requires_explicit_segment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            first = np.arange(12, dtype=np.int16).reshape(3, 4)
            second = first + 100
            write_fixture(directory, first, np.fliplr(first))
            with (directory / "STM1F0.hex").open("ab") as stream:
                second.astype("<i2").tofile(stream)
            with (directory / "STM1B0.hex").open("ab") as stream:
                np.fliplr(second).astype("<i2").tofile(stream)

            with self.assertRaisesRegex(ValueError, "probably appended"):
                load_scan_set(directory, prefix="STM1", scan_number=0)
            scan = load_scan_set(
                directory,
                prefix="STM1",
                scan_number=0,
                segment="end",
            )
            np.testing.assert_array_equal(scan.forward, second)
            np.testing.assert_array_equal(scan.backward_aligned, second)

    def test_four_panel_plot_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            yy, xx = np.indices((12, 16))
            forward = np.rint(1000 + 2 * xx + 4 * yy).astype(np.int16)
            write_fixture(directory, forward, np.fliplr(forward))
            scan = load_scan_set(directory, prefix="STM1", scan_number=0)
            output = plot_scan_set(scan, directory / "four-panel.png", dpi=72)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 10_000)

    def test_plane_leveling_removes_plane(self) -> None:
        yy, xx = np.indices((8, 10), dtype=float)
        plane = 3.0 * xx - 2.0 * yy + 9.0
        self.assertLess(float(np.max(np.abs(level_matrix(plane, "plane")))), 1e-10)


if __name__ == "__main__":
    unittest.main()
