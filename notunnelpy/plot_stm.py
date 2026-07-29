#!/usr/bin/env python3
"""Validate STM files and render simple, printer-friendly heatmaps."""

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
PlotView = Literal["forward", "backward", "average", "difference"]
PLOT_VIEWS: tuple[PlotView, ...] = (
    "forward",
    "backward",
    "average",
    "difference",
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def level_matrix(
    matrix: npt.ArrayLike,
    mode: LevelMode = "none",
) -> npt.NDArray[np.float64]:
    """Return a floating-point matrix with an optional documented leveling."""

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
        design = np.column_stack(
            [xx.ravel(), yy.ravel(), np.ones(values.size)]
        )
        coefficients, *_ = np.linalg.lstsq(
            design,
            values.ravel(),
            rcond=None,
        )
        fitted_plane = (design @ coefficients).reshape(values.shape)
        return values - fitted_plane
    raise ValueError(f"Unsupported leveling mode: {mode}")


def _display_limits(
    matrix: npt.NDArray[np.float64],
    *,
    robust: bool,
) -> tuple[float, float]:
    if robust:
        low, high = np.percentile(matrix, [2.0, 98.0])
    else:
        low, high = float(np.min(matrix)), float(np.max(matrix))
    if np.isclose(low, high):
        low -= 1.0
        high += 1.0
    return float(low), float(high)


def _select_view(
    *,
    forward: npt.NDArray[np.float64],
    backward: npt.NDArray[np.float64] | None,
    view: PlotView,
    robust_limits: bool,
) -> tuple[npt.NDArray[np.float64], str, str, tuple[float, float]]:
    """Return the matrix and labels for one requested heatmap."""

    if view == "forward":
        matrix = forward
        title = "Forward scan"
        colorbar_label = "Relative signal (counts)"
        limits = _display_limits(matrix, robust=robust_limits)
        return matrix, title, colorbar_label, limits

    if backward is None:
        raise ValueError(
            f"The {view!r} view requires a valid backward scan"
        )

    if view == "backward":
        matrix = backward
        title = "Backward scan (aligned)"
        colorbar_label = "Relative signal (counts)"
        limits = _display_limits(matrix, robust=robust_limits)
    elif view == "average":
        matrix = (forward + backward) / 2.0
        title = "Forward/backward average"
        colorbar_label = "Relative signal (counts)"
        limits = _display_limits(matrix, robust=robust_limits)
    elif view == "difference":
        matrix = forward - backward
        title = "Forward minus backward"
        colorbar_label = "Difference (counts)"
        difference_abs = float(np.max(np.abs(matrix)))
        if np.isclose(difference_abs, 0.0):
            difference_abs = 1.0
        limits = (-difference_abs, difference_abs)
    else:
        raise ValueError(f"Unsupported plot view: {view}")

    return matrix, title, colorbar_label, limits


def _printer_colormap(plt, *, difference: bool):
    """Return a restrained colormap without near-black endpoints."""

    from matplotlib.colors import ListedColormap

    if difference:
        colors = plt.colormaps["RdBu_r"](np.linspace(0.20, 0.80, 256))
        name = "printer_difference"
    else:
        colors = plt.colormaps["Blues"](np.linspace(0.04, 0.68, 256))
        name = "printer_blues"
    return ListedColormap(colors, name=name)


def plot_scan_set(
    scan: ScanSet,
    output_path: Path | str,
    *,
    level: LevelMode = "none",
    view: PlotView = "forward",
    robust_limits: bool = True,
    dpi: int = 180,
    show: bool = False,
) -> Path:
    """Render one simple heatmap from a validated scan set."""

    if dpi <= 0:
        raise ValueError("dpi must be greater than zero")

    if not show:
        import matplotlib

        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    forward = level_matrix(scan.forward, level)
    backward = (
        level_matrix(scan.backward_aligned, level)
        if scan.backward_aligned is not None
        else None
    )
    matrix, title, colorbar_label, limits = _select_view(
        forward=forward,
        backward=backward,
        view=view,
        robust_limits=robust_limits,
    )

    figure, axis = plt.subplots(figsize=(7.2, 6.2))
    image = axis.imshow(
        matrix,
        origin="lower",
        aspect="equal",
        interpolation="nearest",
        cmap=_printer_colormap(plt, difference=view == "difference"),
        vmin=limits[0],
        vmax=limits[1],
    )
    axis.set_title(title)
    axis.set_xlabel("X point")
    axis.set_ylabel("Y line")
    axis.grid(False)

    colorbar = figure.colorbar(image, ax=axis, shrink=0.88, pad=0.03)
    colorbar.set_label(colorbar_label)
    colorbar.outline.set_linewidth(0.6)

    parameters = scan.parameters
    if parameters.synthetic:
        pattern = parameters.metadata.get("Pattern", "synthetic")
        provenance = (
            f"SYNTHETIC {pattern.replace('-', ' ').upper()} - "
            "NOT EXPERIMENTAL"
        )
    else:
        provenance = "STM HEATMAP - VERIFY PROVENANCE AND CALIBRATION"
    figure.suptitle(provenance, fontweight="bold")

    footer = (
        f"{parameters.points} x {parameters.lines} samples | "
        f"leveling: {level} | "
        "axes are sample indices; signal is not calibrated height"
    )
    figure.text(
        0.5,
        0.018,
        footer,
        ha="center",
        va="bottom",
        fontsize=8,
        color="#4d4d4d",
    )
    figure.tight_layout(rect=(0.0, 0.06, 1.0, 0.94))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        output,
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
    )
    if show:
        plt.show()
    plt.close(figure)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Teensy-format STM files and create one simple heatmap. "
            "Backward input is optional."
        )
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="directory containing STMF*.hex, STMB*.hex, and STMP*.txt",
    )
    parser.add_argument("--prefix", default="STM")
    parser.add_argument("--scan-number", type=positive_int, default=1)
    parser.add_argument(
        "--forward-only",
        action="store_true",
        help="ignore the backward file even if it exists",
    )
    parser.add_argument(
        "--require-backward",
        action="store_true",
        help="fail if the backward file does not exist",
    )
    parser.add_argument("--level", choices=LEVEL_MODES, default="none")
    parser.add_argument(
        "--view",
        choices=PLOT_VIEWS,
        default="forward",
        help="single heatmap to render (default: forward)",
    )
    parser.add_argument(
        "--full-range",
        action="store_true",
        help="use absolute min/max rather than 2nd/98th percentiles",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="output PNG path (default: <input_dir>/<prefix><n>-heatmap.png)",
    )
    parser.add_argument("--dpi", type=positive_int, default=180)
    parser.add_argument("--show", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.forward_only and args.require_backward:
        raise SystemExit("--forward-only and --require-backward cannot be combined")
    if args.forward_only and args.view != "forward":
        raise SystemExit("--forward-only can only be used with --view forward")

    scan = load_scan_set(
        args.input_dir,
        prefix=args.prefix,
        scan_number=args.scan_number,
        include_backward=not args.forward_only,
        require_backward=args.require_backward,
    )
    output = args.output or (
        args.input_dir / f"{args.prefix}{args.scan_number}-heatmap.png"
    )
    rendered = plot_scan_set(
        scan,
        output,
        level=args.level,
        view=args.view,
        robust_limits=not args.full_range,
        dpi=args.dpi,
        show=args.show,
    )

    print(f"Validated matrix shape: {scan.forward.shape}")
    print(f"Expected bytes per direction: {scan.parameters.expected_bytes}")
    input_type = (
        "SYNTHETIC (not experimental)"
        if scan.parameters.synthetic
        else "unknown/experimental"
    )
    print(f"Input type: {input_type}")
    print(f"Rendered view: {args.view}")
    print(f"Saved heatmap: {rendered}")


if __name__ == "__main__":
    main()
