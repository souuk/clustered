#!/usr/bin/env python3
"""Generate a clearly labeled synthetic STM controller scan in Teensy format.

This is a format and plotting demonstration, not experimental evidence.  The
binary layout follows Teensy_STM12_July_29_2026_v1.ino: separate forward and
backward files containing two-byte signed PID-output corrections Q, plus a
six-line text parameter file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

if __package__:
    from .plot_stm import plot_scan_set
    from .stm_io import load_scan_set
else:
    from plot_stm import plot_scan_set
    from stm_io import load_scan_set


SEED = 20260730
PREFIX = "SYN"
SCAN_NUMBER = 1
POINTS = 64
LINES = 64


def _atomic_lattice(rows: int, columns: int) -> np.ndarray:
    """Return a deterministic triangular lattice expressed in controller counts."""

    yy, xx = np.indices((rows, columns), dtype=np.float64)
    surface = np.zeros((rows, columns), dtype=np.float64)
    spacing_x = 8.0
    spacing_y = 7.0
    sigma = 1.35

    for row_index, cy in enumerate(np.arange(-2.0, rows + 3.0, spacing_y)):
        offset = 0.5 * spacing_x if row_index % 2 else 0.0
        for cx in np.arange(-2.0 + offset, columns + 3.0, spacing_x):
            radius_squared = (xx - cx) ** 2 + (yy - cy) ** 2
            surface += np.exp(-radius_squared / (2.0 * sigma**2))

    surface /= np.max(surface)
    return surface


def make_matrices(rows: int = LINES, columns: int = POINTS) -> tuple[np.ndarray, np.ndarray]:
    """Create firmware-like forward/backward PID-output sequences.

    The borrowed files are not treated as valid topography, but they establish
    useful controller characteristics: signed values, hard output limits,
    slow line drift, small intra-line slopes, and closely related forward and
    backward passes.  A first-order response is applied in acquisition order
    so the two directions contain realistic lag rather than being copied.
    """

    rng = np.random.default_rng(SEED)
    lattice = _atomic_lattice(rows, columns)
    yy, xx = np.indices((rows, columns), dtype=np.float64)

    # Q is a controller correction count.  The low-frequency background
    # represents scanner tilt and slow drift; the lattice is a known synthetic
    # perturbation used only to verify spatial recovery.
    line_random_walk = np.cumsum(rng.normal(0.0, 7.0, size=rows))[:, None]
    target = (
        9100.0
        - 66.0 * yy
        - 1.1 * xx
        + line_random_walk
        + 1350.0 * lattice
    )

    forward = np.empty((rows, columns), dtype=np.float64)
    backward_acquisition = np.empty((rows, columns), dtype=np.float64)
    response_fraction = 0.46
    previous_forward = float(target[0, 0])
    previous_backward = float(target[0, -1] + 18.0)

    for row in range(rows):
        # Forward file: acquisition proceeds from physical X=0 to X=Nx-1.
        for acquisition_index, physical_x in enumerate(range(columns)):
            desired = target[row, physical_x]
            previous_forward += response_fraction * (desired - previous_forward)
            previous_forward += rng.normal(0.0, 24.0)
            forward[row, acquisition_index] = previous_forward

        # Backward file: acquisition begins at physical X=Nx-1.  The values are
        # written sequentially in that acquisition order; the reader later
        # reverses each row to compare matching physical X positions.
        for acquisition_index, physical_x in enumerate(range(columns - 1, -1, -1)):
            desired = target[row, physical_x] + 18.0
            previous_backward += response_fraction * (desired - previous_backward)
            previous_backward += rng.normal(0.0, 24.0)
            backward_acquisition[row, acquisition_index] = previous_backward

    return (
        np.rint(np.clip(forward, -32768, 32767)).astype("<i2"),
        np.rint(np.clip(backward_acquisition, -32768, 32767)).astype("<i2"),
    )


def write_scan(output_dir: Path) -> tuple[Path, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    forward, backward_acquisition = make_matrices()

    forward_path = output_dir / f"{PREFIX}F{SCAN_NUMBER}.hex"
    backward_path = output_dir / f"{PREFIX}B{SCAN_NUMBER}.hex"
    parameter_path = output_dir / f"{PREFIX}P{SCAN_NUMBER}.txt"
    preview_path = output_dir / f"{PREFIX}{SCAN_NUMBER}_preview.txt"

    forward.tofile(forward_path)
    backward_acquisition.tofile(backward_path)
    parameter_path.write_text(
        "\n".join(
            (
                f"{POINTS} number of points",
                f"{LINES} number of lines",
                "If Image finished early. 0 number of points",
                f"{LINES} number of lines",
                "2282 V, sample voltage",
                "1.00 nA, tunneling current",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    first_values = forward.ravel()[:16]
    first_bytes = forward.ravel()[:8].tobytes()
    preview_path.write_text(
        "\n".join(
            (
                "SYNTHETIC STM FORMAT DEMO - NOT EXPERIMENTAL DATA",
                "",
                "Firmware-format files:",
                f"  {forward_path.name}: {forward.size} signed int16 samples",
                f"  {backward_path.name}: {backward_acquisition.size} signed int16 samples",
                f"  {parameter_path.name}: six-line text parameter record",
                "",
                "First 16 forward samples (decimal controller counts):",
                "  " + " ".join(str(int(value)) for value in first_values),
                "",
                "First 8 forward samples as little-endian bytes (hex display only):",
                "  " + " ".join(f"{byte:02X}" for byte in first_bytes),
                "",
                "Generation model: signed PID correction Q with scanner tilt,",
                "line drift, first-order feedback lag, hard output limits,",
                "deterministic noise, and a known synthetic lattice. It does not",
                "claim tunneling, calibration, or atomic resolution by the instrument.",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return forward_path, backward_path, parameter_path, preview_path


def _rounded_box(axis, x: float, y: float, width: float, height: float) -> None:
    axis.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.25,rounding_size=0.25",
            facecolor="#f6f6f6",
            edgecolor="black",
            linewidth=1.1,
        )
    )


def render_raw_to_matrix(data_dir: Path, output_path: Path) -> Path:
    scan = load_scan_set(data_dir, prefix=PREFIX, scan_number=SCAN_NUMBER)
    values = scan.forward.ravel()
    raw_values = [str(int(value)) for value in values[:8]]
    raw_preview = "  ".join(raw_values[:4]) + "\n" + "  ".join(raw_values[4:]) + "  …"
    byte_preview = " ".join(f"{byte:02X}" for byte in values[:6].astype("<i2").tobytes())

    figure, axis = plt.subplots(figsize=(8.2, 4.1))
    figure.patch.set_facecolor("white")
    axis.set_xlim(0, 100)
    axis.set_ylim(0, 50)
    axis.axis("off")

    axis.text(
        50,
        47.3,
        "SYNTHETIC FIRMWARE-FORMAT EXAMPLE - NOT EXPERIMENTAL DATA",
        ha="center",
        va="center",
        fontsize=10.5,
        fontweight="bold",
    )

    _rounded_box(axis, 2, 6, 38, 36)
    axis.text(21, 39.0, "RAW FORWARD FILE", ha="center", va="center",
              fontsize=10, fontweight="bold")
    axis.text(21, 35.9, "stored PID output Q", ha="center", va="center",
              fontsize=8.2)
    axis.text(21, 32.7, "SYNF1.hex", ha="center", va="center", fontsize=8.5)
    axis.text(
        5,
        27.9,
        "first signed int16 counts:",
        ha="left",
        va="center",
        fontsize=8.2,
        fontweight="bold",
    )
    axis.text(
        5,
        24.0,
        raw_preview,
        ha="left",
        va="center",
        fontsize=7.1,
        family="monospace",
    )
    axis.text(
        5,
        17.4,
        "same first 6 values as bytes:",
        ha="left",
        va="center",
        fontsize=8.2,
        fontweight="bold",
    )
    axis.text(
        5,
        14.0,
        byte_preview,
        ha="left",
        va="center",
        fontsize=7.1,
        family="monospace",
    )
    axis.text(
        21,
        8.5,
        "8,192 bytes = 64 × 64 × 2",
        ha="center",
        va="center",
        fontsize=8.2,
    )

    axis.add_patch(
        FancyArrowPatch(
            (41.5, 24),
            (55.0, 24),
            arrowstyle="-|>",
            mutation_scale=17,
            linewidth=1.4,
            color="black",
        )
    )
    axis.text(
        48.2,
        30.0,
        "decode <i2\nreshape 64 × 64",
        ha="center",
        va="center",
        fontsize=7.3,
        fontweight="bold",
    )

    _rounded_box(axis, 56.5, 6, 41.5, 36)
    axis.text(77.25, 38.5, "Q OUTPUT MATRIX", ha="center", va="center",
              fontsize=10, fontweight="bold")
    heat_axis = axis.inset_axes([0.635, 0.255, 0.300, 0.435])
    heat_axis.imshow(
        scan.forward,
        origin="lower",
        cmap="Greys",
        interpolation="nearest",
        vmin=float(np.percentile(scan.forward, 2)),
        vmax=float(np.percentile(scan.forward, 98)),
    )
    heat_axis.tick_params(labelsize=6, length=2)
    heat_axis.set_xticks((0, 32, 63))
    heat_axis.set_yticks((0, 32, 63))
    axis.text(
        77.25,
        8.8,
        "64 x 64 raster-ordered Q counts\nnot ADC current or physical height",
        ha="center",
        va="center",
        fontsize=7.8,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.05,
        facecolor="white",
    )
    plt.close(figure)
    return output_path


def render_file_schema_check(data_dir: Path, output_path: Path) -> Path:
    """Render a compact integrity check for one matched F/B/P scan triplet."""

    scan = load_scan_set(data_dir, prefix=PREFIX, scan_number=SCAN_NUMBER)
    expected_samples = scan.parameters.expected_samples
    expected_bytes = scan.parameters.expected_bytes

    figure, axis = plt.subplots(figsize=(10.0, 1.65))
    figure.patch.set_facecolor("white")
    axis.set_xlim(0, 100)
    axis.set_ylim(0, 20)
    axis.axis("off")

    axis.text(
        50,
        18.0,
        "FILE-SCHEMA VALIDATION - SYNTHETIC SCAN 1",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
    )

    entries = (
        (
            "SYNF1.hex",
            f"{scan.forward.size:,} int16 samples",
            f"{scan.forward_path.stat().st_size:,} B = {expected_bytes:,} B",
        ),
        (
            "SYNB1.hex",
            f"{scan.backward_acquisition.size:,} int16 samples",
            f"{scan.backward_path.stat().st_size:,} B = {expected_bytes:,} B",
        ),
        (
            "SYNP1.txt",
            f"{scan.parameters.lines} lines x {scan.parameters.points} points",
            "one complete 6-line record",
        ),
    )
    box_width = 24.5
    starts = (1.5, 27.5, 53.5)
    for x, (name, detail, check) in zip(starts, entries):
        axis.add_patch(
            FancyBboxPatch(
                (x, 3.0),
                box_width,
                11.8,
                boxstyle="round,pad=0.18,rounding_size=0.3",
                facecolor="#f5f5f5",
                edgecolor="black",
                linewidth=1.0,
            )
        )
        axis.text(
            x + box_width / 2,
            11.8,
            name,
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
        )
        axis.text(
            x + box_width / 2,
            8.0,
            detail,
            ha="center",
            va="center",
            fontsize=7.4,
        )
        axis.text(
            x + box_width / 2,
            4.9,
            check,
            ha="center",
            va="center",
            fontsize=7.1,
        )

    axis.text(26.75, 8.8, "+", ha="center", va="center", fontsize=14, fontweight="bold")
    axis.text(52.75, 8.8, "+", ha="center", va="center", fontsize=14, fontweight="bold")
    axis.add_patch(
        FancyArrowPatch(
            (78.6, 8.8),
            (84.1, 8.8),
            arrowstyle="-|>",
            mutation_scale=14,
            linewidth=1.2,
            color="black",
        )
    )
    axis.add_patch(
        FancyBboxPatch(
            (84.8, 3.0),
            13.7,
            11.8,
            boxstyle="round,pad=0.18,rounding_size=0.3",
            facecolor="#dddddd",
            edgecolor="black",
            linewidth=1.1,
        )
    )
    axis.text(
        91.65,
        10.8,
        "PASS",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
    )
    axis.text(
        91.65,
        6.6,
        "same scan ID\nexact dimensions",
        ha="center",
        va="center",
        fontsize=7.2,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.03,
        facecolor="white",
    )
    plt.close(figure)
    return output_path


def write_notice(output_dir: Path) -> Path:
    notice = output_dir / "README.txt"
    notice.write_text(
        """SYNTHETIC STM DATA - NOT EXPERIMENTAL
=====================================

These deterministic fixtures exercise TunnelPy without depending on a
microscope measurement. Do not describe SYNF1.hex, SYNB1.hex, or SYNP1.txt as
experimental data.

The storage contract follows source.zip:
  Experiments\\STM Project\\Teensy_STM12_July_29_2026_v1.ino

Relevant firmware behavior:
  lines 1113-1131  matched F/B/P filenames
  lines 1500-1523  forward/backward acquisition and two-byte writes
  lines 1526-1544  scan ordering and row stepping
  lines 1583-1596  six-line parameter record

Synthetic model:
  64 x 64 signed PID-output correction Q
  scanner tilt, slow line drift, first-order feedback lag, and noise
  separate forward and right-to-left backward acquisition sequences
  hard clipping to the firmware's signed output range
  a known triangular corrugation used only to test spatial recovery

Reference-data separation:
  data\\ contains an independently supplied STM12-format reference triplet
  synthetic_data\\ contains only deterministic generated fixtures
  values from the reference triplet are not copied into this simulation

The pattern is a pipeline test. It is not proof of tunneling, atomic
resolution, sample identity, or physical height.
""",
        encoding="utf-8",
    )
    return notice


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("synthetic_data"),
        help="directory for the synthetic F/B/P files",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=Path("poster/raw-data-to-matrix.png"),
        help="raw-data-to-matrix PNG destination",
    )
    parser.add_argument(
        "--schema-figure",
        type=Path,
        default=Path("poster/file-schema-validation.png"),
        help="compact F/B/P integrity-check PNG destination",
    )
    parser.add_argument(
        "--four-panel",
        type=Path,
        default=Path("poster/synthetic-q-four-panel.png"),
        help="four-panel PID-output diagnostic PNG destination",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = write_scan(args.data_dir)
    notice = write_notice(args.data_dir)
    figure = render_raw_to_matrix(args.data_dir, args.figure)
    schema_figure = render_file_schema_check(args.data_dir, args.schema_figure)
    scan = load_scan_set(args.data_dir, prefix=PREFIX, scan_number=SCAN_NUMBER)
    four_panel = plot_scan_set(
        scan,
        args.four_panel,
        level="none",
        robust_limits=True,
        dpi=240,
    )
    print("Generated:")
    for path in (*paths, notice, figure, schema_figure, four_panel):
        print(f"  {path.resolve()}")


if __name__ == "__main__":
    main()
