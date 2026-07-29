#!/usr/bin/env python3
"""Validate STM files and render forward/backward comparison plots."""

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
    matrices: list[npt.NDArray[np.float64]],
    *,
    robust: bool,
) -> tuple[float, float]:
    merged = np.concatenate([matrix.ravel() for matrix in matrices])
    if robust:
        low, high = np.percentile(merged, [2.0, 98.0])
    else:
        low, high = float(np.min(merged)), float(np.max(merged))
    if np.isclose(low, high):
        low -= 1.0
        high += 1.0
    return float(low), float(high)


def _add_image(
    *,
    figure,
    axis,
    matrix: npt.NDArray[np.float64],
    title: str,
    limits: tuple[float, float],
    colorbar_label: str,
) -> None:
    image = axis.imshow(
        matrix,
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        cmap="gray",
        vmin=limits[0],
        vmax=limits[1],
    )
    axis.set_title(title)
    axis.set_xlabel("X point")
    axis.set_ylabel("Y line")
    colorbar = figure.colorbar(image, ax=axis, shrink=0.86)
    colorbar.set_label(colorbar_label)


def plot_scan_set(
    scan: ScanSet,
    output_path: Path | str,
    *,
    level: LevelMode = "none",
    robust_limits: bool = True,
    dpi: int = 180,
    show: bool = False,
) -> Path:
    """Render one forward-only or forward/backward diagnostic figure."""

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

    if backward is None:
        figure, axis = plt.subplots(figsize=(8.2, 6.4))
        limits = _display_limits([forward], robust=robust_limits)
        _add_image(
            figure=figure,
            axis=axis,
            matrix=forward,
            title="Forward scan",
            limits=limits,
            colorbar_label="Relative correction (counts)",
        )
        axes = [axis]
    else:
        average = (forward + backward) / 2.0
        difference = forward - backward
        common_limits = _display_limits(
            [forward, backward, average],
            robust=robust_limits,
        )
        difference_abs = float(np.max(np.abs(difference)))
        if np.isclose(difference_abs, 0.0):
            difference_abs = 1.0

        figure, grid = plt.subplots(
            2,
            2,
            figsize=(11.5, 8.4),
        )
        axes = list(grid.ravel())
        _add_image(
            figure=figure,
            axis=axes[0],
            matrix=forward,
            title="Forward scan",
            limits=common_limits,
            colorbar_label="Relative correction (counts)",
        )
        _add_image(
            figure=figure,
            axis=axes[1],
            matrix=backward,
            title="Backward scan (spatially aligned)",
            limits=common_limits,
            colorbar_label="Relative correction (counts)",
        )
        _add_image(
            figure=figure,
            axis=axes[2],
            matrix=average,
            title="Forward/backward average",
            limits=common_limits,
            colorbar_label="Relative correction (counts)",
        )
        _add_image(
            figure=figure,
            axis=axes[3],
            matrix=difference,
            title="Forward minus backward",
            limits=(-difference_abs, difference_abs),
            colorbar_label="Difference (counts)",
        )

    parameters = scan.parameters
    provenance = (
        "SYNTHETIC DEMO — NOT EXPERIMENTAL"
        if parameters.synthetic
        else "EXPERIMENTAL INPUT — VERIFY PROVENANCE AND CALIBRATION"
    )
    figure.suptitle(
        f"{provenance}\n"
        f"{parameters.points} × {parameters.lines} samples; "
        f"leveling: {level}",
        fontweight="bold",
    )
    footer = (
        f"Parameters: {scan.parameter_path.name} | "
        f"Forward: {scan.forward_path.name} | "
        f"Backward: "
        f"{scan.backward_path.name if scan.backward_path else 'not loaded'}\n"
        "Vertical values are relative controller counts, not physical height."
    )
    figure.text(0.5, 0.012, footer, ha="center", va="bottom", fontsize=8)
    figure.tight_layout(rect=(0.0, 0.06, 1.0, 0.95), h_pad=1.1, w_pad=1.0)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=dpi, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(figure)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Teensy-format STM files and create diagnostic maps. "
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
        "--full-range",
        action="store_true",
        help="use absolute min/max rather than 2nd/98th percentiles",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="output PNG path (default: <input_dir>/<prefix><n>-plots.png)",
    )
    parser.add_argument("--dpi", type=positive_int, default=180)
    parser.add_argument("--show", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.forward_only and args.require_backward:
        raise SystemExit("--forward-only and --require-backward cannot be combined")

    scan = load_scan_set(
        args.input_dir,
        prefix=args.prefix,
        scan_number=args.scan_number,
        include_backward=not args.forward_only,
        require_backward=args.require_backward,
    )
    output = args.output or (
        args.input_dir / f"{args.prefix}{args.scan_number}-plots.png"
    )
    rendered = plot_scan_set(
        scan,
        output,
        level=args.level,
        robust_limits=not args.full_range,
        dpi=args.dpi,
        show=args.show,
    )

    print(f"Validated matrix shape: {scan.forward.shape}")
    print(f"Expected bytes per direction: {scan.parameters.expected_bytes}")
    print(
        "Input type: "
        + ("SYNTHETIC (not experimental)" if scan.parameters.synthetic else "unknown/experimental")
    )
    print(f"Saved plot: {rendered}")


if __name__ == "__main__":
    main()
