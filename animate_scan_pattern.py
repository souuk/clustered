#!/usr/bin/env python3
"""Animate the scan order implemented by the Teensy STM firmware.

The firmware takes ``numpoints`` samples while increasing X, then takes
``numpoints`` samples while decreasing X.  At the end of that forward/backward
pair it resets X to its initial value, increments Y, and begins the next line.

This script intentionally models the order of operations in ``Timer2Service``:
the current X value is sent to the DAC before X is changed for the next timer
tick.  Consequently, a line with N points samples these positions:

    forward:  x0, x0 + step, ..., x0 + (N - 1) * step
    backward: x0 + N * step, ..., x0 + step

Run without ``--output`` for an interactive window, or save a GIF/MP4:

    python animate_scan_pattern.py
    python animate_scan_pattern.py --output scan-pattern.gif
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

import matplotlib.animation as mpl_animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


Phase = Literal["forward", "backward"]


@dataclass(frozen=True)
class ScanSample:
    """One timer-driven sample in the Teensy scan."""

    sequence: int
    line: int
    pointcounter: int
    phase: Phase
    x: int
    y: int
    completes_line: bool


def positive_int(value: str) -> int:
    """Argparse type for a strictly positive integer."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_scan_samples(
    *,
    points: int,
    lines: int,
    step_size: int = 1,
    initial_x: int = 0,
    initial_y: int = 0,
) -> list[ScanSample]:
    """Reproduce the sample positions and counters from ``Timer2Service``."""
    if points <= 0 or lines <= 0:
        raise ValueError("points and lines must be greater than zero")
    if step_size == 0:
        raise ValueError("step_size must be non-zero")

    samples: list[ScanSample] = []
    x = initial_x
    y = initial_y
    sequence = 0

    for line in range(lines):
        for pointcounter in range(points):
            samples.append(
                ScanSample(
                    sequence=sequence,
                    line=line,
                    pointcounter=pointcounter,
                    phase="forward",
                    x=x,
                    y=y,
                    completes_line=False,
                )
            )
            sequence += 1
            x += step_size

        for pointcounter in range(points, 2 * points):
            completes_line = pointcounter == (2 * points - 1)
            samples.append(
                ScanSample(
                    sequence=sequence,
                    line=line,
                    pointcounter=pointcounter,
                    phase="backward",
                    x=x,
                    y=y,
                    completes_line=completes_line,
                )
            )
            sequence += 1
            x -= step_size

        # The firmware performs both operations after the final backward sample.
        y += step_size
        x = initial_x

    return samples


def print_summary(samples: Sequence[ScanSample], points: int, lines: int) -> None:
    """Print a compact, testable description of the generated scan."""
    first_forward = samples[0]
    last_forward = samples[points - 1]
    first_backward = samples[points]
    last_backward = samples[(2 * points) - 1]
    print(f"{len(samples)} samples: {lines} lines x {points} forward/backward pairs")
    print(
        "First line forward positions: "
        f"{first_forward.x} through {last_forward.x}"
    )
    print(
        "First line backward positions: "
        f"{first_backward.x} through {last_backward.x}"
    )
    print(
        "Firmware pointcounter ranges: "
        f"forward 0..{points - 1}, backward {points}..{2 * points - 1}"
    )


def create_animation(
    samples: Sequence[ScanSample],
    *,
    points: int,
    lines: int,
    step_size: int,
    initial_x: int,
    initial_y: int,
    interval_ms: int,
) -> tuple[plt.Figure, mpl_animation.FuncAnimation]:
    """Build the Matplotlib animation."""
    forward_color = "#1677b8"
    backward_color = "#e67817"
    complete_color = "#7357b8"
    neutral_color = "#b7bec7"

    fig, ax = plt.subplots(figsize=(10.5, 6.4), constrained_layout=True)
    fig.patch.set_facecolor("#f7f8fa")
    ax.set_facecolor("#ffffff")

    x_end = initial_x + points * step_size
    y_end = initial_y + max(lines - 1, 1) * step_size
    x_padding = max(abs(step_size) * 1.2, abs(x_end - initial_x) * 0.04)
    y_padding = max(abs(step_size) * 0.8, abs(y_end - initial_y) * 0.08)

    ax.set_xlim(min(initial_x, x_end) - x_padding, max(initial_x, x_end) + x_padding)
    ax.set_ylim(
        min(initial_y, y_end) - y_padding,
        max(initial_y, y_end) + y_padding,
    )
    ax.set_xlabel("X DAC count (relative scan position)")
    ax.set_ylabel("Y DAC count (scan line)")
    ax.set_title("Teensy STM bidirectional scanning pattern", loc="left", weight="bold")
    ax.grid(axis="y", color="#dfe3e8", linewidth=0.8)
    ax.grid(axis="x", color="#eef0f3", linewidth=0.6)
    for spine in ax.spines.values():
        spine.set_color("#c8cdd3")

    for line in range(lines):
        y = initial_y + line * step_size
        ax.plot(
            [initial_x, x_end],
            [y, y],
            color=neutral_color,
            linewidth=1,
            alpha=0.38,
            zorder=0,
        )

    completed_lines = ax.scatter(
        [],
        [],
        s=22,
        color=complete_color,
        alpha=0.5,
        edgecolors="none",
        zorder=1,
    )
    forward_points = ax.scatter(
        [],
        [],
        s=34,
        color=forward_color,
        edgecolors="#ffffff",
        linewidths=0.45,
        zorder=3,
    )
    backward_points = ax.scatter(
        [],
        [],
        s=24,
        facecolors="none",
        edgecolors=backward_color,
        linewidths=1.4,
        zorder=4,
    )
    current_point = ax.scatter(
        [],
        [],
        s=120,
        marker="D",
        color=forward_color,
        edgecolors="#20242a",
        linewidths=0.8,
        zorder=5,
    )

    status = ax.text(
        0.01,
        0.985,
        "",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=10.5,
        color="#20242a",
        bbox={
            "boxstyle": "round,pad=0.45",
            "facecolor": "#ffffff",
            "edgecolor": "#c8cdd3",
            "alpha": 0.94,
        },
        zorder=6,
    )
    transition = ax.text(
        0.99,
        0.02,
        "",
        transform=ax.transAxes,
        va="bottom",
        ha="right",
        fontsize=9.5,
        color="#4f5660",
        zorder=6,
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor=forward_color,
            markeredgecolor="none",
            label="Forward sample (+X)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor="none",
            markeredgecolor=backward_color,
            label="Backward sample (−X)",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            linestyle="none",
            markerfacecolor="#8a8f98",
            markeredgecolor="#20242a",
            label="Current tip position",
        ),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper right",
        frameon=True,
        facecolor="#ffffff",
        edgecolor="#c8cdd3",
        framealpha=0.94,
    )

    def as_offsets(selected: Sequence[ScanSample]) -> np.ndarray:
        coordinates = [(sample.x, sample.y) for sample in selected]
        return np.asarray(coordinates, dtype=float).reshape((-1, 2))

    def update(frame: int) -> tuple[object, ...]:
        visible = samples[: frame + 1]
        current = samples[frame]
        previous_lines = [
            sample for sample in visible if sample.line < current.line
        ]
        current_forward = [
            sample
            for sample in visible
            if sample.line == current.line and sample.phase == "forward"
        ]
        current_backward = [
            sample
            for sample in visible
            if sample.line == current.line and sample.phase == "backward"
        ]

        completed_lines.set_offsets(as_offsets(previous_lines))
        forward_points.set_offsets(as_offsets(current_forward))
        backward_points.set_offsets(as_offsets(current_backward))
        current_point.set_offsets([(current.x, current.y)])
        current_point.set_facecolor(
            forward_color if current.phase == "forward" else backward_color
        )

        direction = "+X" if current.phase == "forward" else "−X"
        status.set_text(
            f"Line {current.line + 1}/{lines}  •  "
            f"{current.phase.capitalize()} {direction}\n"
            f"pointcounter = {current.pointcounter}  •  "
            f"DAC position = ({current.x}, {current.y})"
        )
        if current.completes_line:
            transition.set_text("Line complete → reset X, increment Y, pulse trigger")
        else:
            transition.set_text("")

        return (
            completed_lines,
            forward_points,
            backward_points,
            current_point,
            status,
            transition,
        )

    animation = mpl_animation.FuncAnimation(
        fig,
        update,
        frames=len(samples),
        interval=interval_ms,
        blit=False,
        repeat=True,
    )
    return fig, animation


def save_animation(
    animation: mpl_animation.FuncAnimation,
    output: Path,
    *,
    interval_ms: int,
    dpi: int,
) -> None:
    """Save to GIF with Pillow or to MP4 with FFmpeg."""
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fps = max(1, round(1000 / interval_ms))

    if output.suffix.lower() == ".gif":
        writer = mpl_animation.PillowWriter(fps=fps)
    elif output.suffix.lower() == ".mp4":
        if not mpl_animation.writers.is_available("ffmpeg"):
            raise RuntimeError(
                "Saving MP4 requires FFmpeg. Use a .gif output or install FFmpeg."
            )
        writer = mpl_animation.FFMpegWriter(fps=fps, bitrate=1800)
    else:
        raise ValueError("output must end in .gif or .mp4")

    animation.save(output, writer=writer, dpi=dpi)
    print(f"Saved animation: {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Animate the forward/backward raster pattern implemented in the "
            "Teensy STM firmware."
        )
    )
    parser.add_argument(
        "--points",
        type=positive_int,
        default=24,
        help="samples in each forward or backward pass (default: 24)",
    )
    parser.add_argument(
        "--lines",
        type=positive_int,
        default=10,
        help="number of Y scan lines to animate (default: 10)",
    )
    parser.add_argument(
        "--step-size",
        type=int,
        default=1,
        help="X/Y DAC increment per step; must be non-zero (default: 1)",
    )
    parser.add_argument(
        "--initial-x",
        type=int,
        default=0,
        help="initial X DAC count (default: 0)",
    )
    parser.add_argument(
        "--initial-y",
        type=int,
        default=0,
        help="initial Y DAC count (default: 0)",
    )
    parser.add_argument(
        "--interval-ms",
        type=positive_int,
        default=45,
        help="animation delay per sample in milliseconds (default: 45)",
    )
    parser.add_argument(
        "--dpi",
        type=positive_int,
        default=110,
        help="output resolution when saving (default: 110)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="save to a .gif or .mp4 instead of opening a window",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="print the modeled scan ranges without drawing the animation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.step_size == 0:
        raise SystemExit("--step-size must be non-zero")

    samples = build_scan_samples(
        points=args.points,
        lines=args.lines,
        step_size=args.step_size,
        initial_x=args.initial_x,
        initial_y=args.initial_y,
    )
    print_summary(samples, args.points, args.lines)

    if args.summary_only:
        return

    if args.output:
        # Avoid requiring a working desktop/Tk installation for file exports.
        plt.switch_backend("Agg")

    fig, animation = create_animation(
        samples,
        points=args.points,
        lines=args.lines,
        step_size=args.step_size,
        initial_x=args.initial_x,
        initial_y=args.initial_y,
        interval_ms=args.interval_ms,
    )
    if args.output:
        save_animation(
            animation,
            args.output,
            interval_ms=args.interval_ms,
            dpi=args.dpi,
        )
        plt.close(fig)
    else:
        plt.show()


if __name__ == "__main__":
    main()
