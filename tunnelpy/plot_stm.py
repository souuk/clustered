#!/usr/bin/env python3
"""Create the detailed four-panel STM scan comparison figure."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt

if __package__:
    from .stm_io import ScanSet, load_scan_set
else:
    from stm_io import ScanSet, load_scan_set


LevelMode = Literal["none", "mean", "line", "plane"]
LEVEL_MODES: tuple[LevelMode, ...] = ("none", "mean", "line", "plane")


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def level_matrix(
    matrix: npt.ArrayLike, mode: LevelMode = "none"
) -> npt.NDArray[np.float64]:
    """Apply an explicit, reproducible background-leveling operation."""

    values = np.asarray(matrix, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("Plot input must be a two-dimensional matrix")
    if mode == "none":
        return values.copy()
    if mode == "mean":
        return values - np.mean(values)
    if mode == "line":
        return values - np.median(values, axis=1, keepdims=True)
    if mode == "plane":
        rows, columns = values.shape
        yy, xx = np.indices((rows, columns), dtype=np.float64)
        design = np.column_stack((xx.ravel(), yy.ravel(), np.ones(values.size)))
        coefficients, *_ = np.linalg.lstsq(design, values.ravel(), rcond=None)
        return values - (design @ coefficients).reshape(values.shape)
    raise ValueError(f"Unsupported leveling mode: {mode}")


def _limits(values: npt.ArrayLike, robust: bool) -> tuple[float, float]:
    array = np.asarray(values, dtype=np.float64)
    if robust:
        low, high = np.percentile(array, (2.0, 98.0))
    else:
        low, high = np.min(array), np.max(array)
    if np.isclose(low, high):
        low -= 1.0
        high += 1.0
    return float(low), float(high)


def _printer_colormaps(plt):
    from matplotlib.colors import ListedColormap

    signal = ListedColormap(
        plt.colormaps["Greys"](np.linspace(0.06, 0.90, 256)),
        name="printer_signal_grayscale",
    )
    difference = ListedColormap(
        plt.colormaps["Greys"](np.linspace(0.02, 0.98, 256)),
        name="printer_difference_grayscale",
    )
    return signal, difference


def plot_scan_set(
    scan: ScanSet,
    output_path: Path | str,
    *,
    level: LevelMode = "none",
    robust_limits: bool = True,
    dpi: int = 180,
    show: bool = False,
) -> Path:
    """Render forward, aligned backward, average, and difference heatmaps."""

    if dpi <= 0:
        raise ValueError("dpi must be greater than zero")
    if not show:
        import matplotlib

        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    forward = level_matrix(scan.forward, level)
    backward = level_matrix(scan.backward_aligned, level)
    average = (forward + backward) / 2.0
    difference = forward - backward

    signal_limits = _limits(
        np.concatenate((forward.ravel(), backward.ravel(), average.ravel())),
        robust_limits,
    )
    if robust_limits:
        difference_limit = float(np.percentile(np.abs(difference), 98.0))
    else:
        difference_limit = float(np.max(np.abs(difference)))
    if np.isclose(difference_limit, 0.0):
        difference_limit = 1.0

    signal_cmap, difference_cmap = _printer_colormaps(plt)
    figure, axes = plt.subplots(2, 2, figsize=(15.5, 11.2))
    panels = (
        (forward, "Forward scan", signal_cmap, signal_limits, "Controller output (counts)"),
        (
            backward,
            "Backward scan (spatially aligned)",
            signal_cmap,
            signal_limits,
            "Controller output (counts)",
        ),
        (
            average,
            "Forward/backward average",
            signal_cmap,
            signal_limits,
            "Average output (counts)",
        ),
        (
            difference,
            "Forward minus backward",
            difference_cmap,
            (-difference_limit, difference_limit),
            "Difference (counts)",
        ),
    )

    for axis, (matrix, title, cmap, limits, colorbar_label) in zip(
        axes.flat, panels
    ):
        image = axis.imshow(
            matrix,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            cmap=cmap,
            vmin=limits[0],
            vmax=limits[1],
        )
        axis.set_title(title, fontsize=14, pad=9)
        axis.set_xlabel("X point")
        axis.set_ylabel("Y line")
        axis.grid(False)
        colorbar = figure.colorbar(image, ax=axis, fraction=0.046, pad=0.035)
        colorbar.set_label(colorbar_label)
        colorbar.outline.set_linewidth(0.6)

    status = "PARTIAL / UNVERIFIED" if scan.partial else "COMPLETE / UNCALIBRATED"
    figure.suptitle(
        f"STM FOUR-PANEL SCAN DIAGNOSTIC — {status}",
        fontsize=19,
        fontweight="bold",
        y=0.982,
    )
    parameter = scan.parameters
    figure.text(
        0.5,
        0.947,
        (
            f"{parameter.points} X points × {scan.actual_lines} plotted Y lines "
            f"(requested {parameter.lines})  |  leveling: {level}  |  "
            f"parameter record {parameter.record_index + 1}/{parameter.record_count}"
        ),
        ha="center",
        va="center",
        fontsize=10.5,
    )
    figure.text(
        0.5,
        0.018,
        (
            f"Parameters: {scan.parameter_path.name}  |  "
            f"Forward: {scan.forward_path.name}  |  Backward: {scan.backward_path.name}\n"
            "Vertical values are signed controller counts, not calibrated physical height."
        ),
        ha="center",
        va="bottom",
        fontsize=9,
        color="#404040",
    )
    figure.tight_layout(rect=(0.025, 0.065, 0.985, 0.925), h_pad=2.8, w_pad=2.1)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=dpi, bbox_inches="tight", facecolor="white")
    if show:
        plt.show()
    plt.close(figure)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read Teensy STM files and create a 2x2 diagnostic figure containing "
            "forward, aligned backward, average, and difference heatmaps."
        )
    )
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--prefix", default="STM1")
    parser.add_argument("--scan-number", type=nonnegative_int, default=8)
    parser.add_argument(
        "--parameter-record",
        type=int,
        default=-1,
        help="zero-based parameter record; -1 selects the last record",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="recover only complete shared rows from truncated files",
    )
    parser.add_argument(
        "--segment",
        choices=("reject", "start", "end"),
        default="reject",
        help="how to handle a binary file larger than the selected record",
    )
    parser.add_argument("--level", choices=LEVEL_MODES, default="none")
    parser.add_argument(
        "--full-range",
        action="store_true",
        help="use absolute extrema instead of robust 2nd/98th-percentile limits",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dpi", type=positive_int, default=180)
    parser.add_argument("--show", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    scan = load_scan_set(
        args.input_dir,
        prefix=args.prefix,
        scan_number=args.scan_number,
        parameter_record=args.parameter_record,
        allow_partial=args.allow_partial,
        segment=args.segment,
    )
    output = args.output or (
        Path(__file__).resolve().parent
        / "output"
        / f"{args.prefix}-scan-{args.scan_number}-four-panel.png"
    )
    rendered = plot_scan_set(
        scan,
        output,
        level=args.level,
        robust_limits=not args.full_range,
        dpi=args.dpi,
        show=args.show,
    )

    print(f"Plotted matrix: {scan.forward.shape[1]} x {scan.forward.shape[0]}")
    print(f"Status: {'partial/unverified' if scan.partial else 'complete/uncalibrated'}")
    for warning in scan.warnings:
        print(f"WARNING: {warning}")
    print(f"Saved four-panel figure: {rendered.resolve()}")


if __name__ == "__main__":
    main()
