#!/usr/bin/env python3
"""Generate synthetic STM files for developing the plotter without tunneling.

The generated files match the planned input contract:

* ``STMF1.hex`` contains forward rows as little-endian signed 16-bit values.
* ``STMB1.hex`` contains backward rows in acquisition order.
* ``STMP1.txt`` begins with the six lines written by the Teensy firmware.

Every parameter file is explicitly marked ``SYNTHETIC``.  These fixtures must
never be presented as experimental STM results.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt

if __package__:
    from .stm_io import scan_paths, write_scan_matrix
else:
    from stm_io import scan_paths, write_scan_matrix


Pattern = Literal["flat", "slope", "bump", "double-bump", "checkerboard"]
PATTERNS: tuple[Pattern, ...] = (
    "flat",
    "slope",
    "bump",
    "double-bump",
    "checkerboard",
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def build_pattern(
    pattern: Pattern,
    *,
    points: int,
    lines: int,
) -> npt.NDArray[np.float64]:
    """Return a normalized synthetic surface with values near zero to one."""

    x = np.linspace(-1.0, 1.0, points)
    y = np.linspace(-1.0, 1.0, lines)
    xx, yy = np.meshgrid(x, y)

    if pattern == "flat":
        surface = np.zeros_like(xx)
    elif pattern == "slope":
        surface = (0.65 * xx) + (0.35 * yy)
    elif pattern == "bump":
        surface = np.exp(-((xx / 0.38) ** 2 + (yy / 0.38) ** 2))
    elif pattern == "double-bump":
        first = np.exp(
            -(((xx + 0.38) / 0.30) ** 2 + ((yy + 0.18) / 0.34) ** 2)
        )
        second = 0.72 * np.exp(
            -(((xx - 0.35) / 0.24) ** 2 + ((yy - 0.28) / 0.27) ** 2)
        )
        surface = first + second
    elif pattern == "checkerboard":
        surface = np.sin(3.0 * np.pi * xx) * np.sin(3.0 * np.pi * yy)
    else:
        raise ValueError(f"Unsupported synthetic pattern: {pattern}")

    maximum = float(np.max(np.abs(surface)))
    if maximum > 0:
        surface = surface / maximum
    return surface


def _parameter_text(
    *,
    points: int,
    lines: int,
    bias_raw: int,
    current_na: float,
    pattern: Pattern,
    seed: int,
) -> str:
    """Return a firmware-shaped parameter file with synthetic provenance."""

    return "\n".join(
        [
            f"{points} number of points",
            f"{lines} number of lines",
            "If Image finished early. 0 number of points",
            f"{lines} number of lines",
            f"{bias_raw} V, sample voltage",
            f"{current_na:g} nA, tunneling current",
            "Data source: SYNTHETIC - NOT EXPERIMENTAL",
            f"Pattern: {pattern}",
            f"Random seed: {seed}",
            (
                "Bias note: firmware-shaped raw bias field; do not interpret "
                "as volts without conversion"
            ),
            "",
        ]
    )


def generate_demo_scan(
    output_dir: Path | str,
    *,
    points: int = 64,
    lines: int = 64,
    pattern: Pattern = "bump",
    baseline: float = 1200.0,
    amplitude: float = 350.0,
    noise: float = 8.0,
    backward_offset: float = 3.0,
    seed: int = 2026,
    prefix: str = "STM",
    scan_number: int = 1,
    bias_raw: int = 2282,
    current_na: float = 1.0,
    overwrite: bool = False,
) -> tuple[Path, Path, Path]:
    """Create one reproducible synthetic forward/backward/parameter file set."""

    if points <= 0 or lines <= 0:
        raise ValueError("points and lines must be greater than zero")
    if noise < 0:
        raise ValueError("noise must be zero or greater")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    forward_path, backward_path, parameter_path = scan_paths(
        destination,
        prefix=prefix,
        scan_number=scan_number,
    )

    existing = [
        path
        for path in (forward_path, backward_path, parameter_path)
        if path.exists()
    ]
    if existing and not overwrite:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing demo files: {joined}. "
            "Use --overwrite to replace them."
        )

    rng = np.random.default_rng(seed)
    normalized = build_pattern(pattern, points=points, lines=lines)
    ideal = baseline + (amplitude * normalized)

    forward_spatial = ideal + rng.normal(0.0, noise, size=ideal.shape)
    backward_spatial = (
        ideal
        + backward_offset
        + rng.normal(0.0, noise, size=ideal.shape)
    )
    backward_acquisition = np.fliplr(backward_spatial)

    write_scan_matrix(forward_path, forward_spatial)
    write_scan_matrix(backward_path, backward_acquisition)
    parameter_path.write_text(
        _parameter_text(
            points=points,
            lines=lines,
            bias_raw=bias_raw,
            current_na=current_na,
            pattern=pattern,
            seed=seed,
        ),
        encoding="utf-8",
    )
    return forward_path, backward_path, parameter_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate clearly labeled synthetic STM files for plotter "
            "development before tunneling works."
        )
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        type=Path,
        default=Path("notunnelpy/demo_output"),
        help="destination directory (default: notunnelpy/demo_output)",
    )
    parser.add_argument("--points", type=positive_int, default=64)
    parser.add_argument("--lines", type=positive_int, default=64)
    parser.add_argument("--pattern", choices=PATTERNS, default="bump")
    parser.add_argument("--baseline", type=float, default=1200.0)
    parser.add_argument("--amplitude", type=float, default=350.0)
    parser.add_argument("--noise", type=nonnegative_float, default=8.0)
    parser.add_argument("--backward-offset", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--prefix", default="STM")
    parser.add_argument("--scan-number", type=positive_int, default=1)
    parser.add_argument("--bias-raw", type=int, default=2282)
    parser.add_argument("--current-na", type=float, default=1.0)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing synthetic file set",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = generate_demo_scan(
        args.output_dir,
        points=args.points,
        lines=args.lines,
        pattern=args.pattern,
        baseline=args.baseline,
        amplitude=args.amplitude,
        noise=args.noise,
        backward_offset=args.backward_offset,
        seed=args.seed,
        prefix=args.prefix,
        scan_number=args.scan_number,
        bias_raw=args.bias_raw,
        current_na=args.current_na,
        overwrite=args.overwrite,
    )
    print("Created SYNTHETIC STM inputs (not experimental data):")
    for path in paths:
        print(f"  {path}")


if __name__ == "__main__":
    main()
