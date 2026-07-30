#!/usr/bin/env python3
"""Generate the poster's black-and-white STM data-conversion diagram."""

from __future__ import annotations

import argparse
from math import exp, sin
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


def box(axis, x, y, width, height, title, lines, *, fill="#f2f2f2"):
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.35,rounding_size=0.8",
        linewidth=1.5,
        edgecolor="black",
        facecolor=fill,
    )
    axis.add_patch(patch)
    axis.text(
        x + width / 2,
        y + height - 2.0,
        title,
        ha="center",
        va="center",
        fontsize=10.5,
        fontweight="bold",
    )
    axis.plot(
        [x + 1.1, x + width - 1.1],
        [y + height - 3.35, y + height - 3.35],
        color="black",
        linewidth=0.8,
    )
    axis.text(
        x + width / 2,
        y + height - 4.45,
        "\n".join(lines),
        ha="center",
        va="top",
        fontsize=8.4,
        linespacing=1.35,
    )


def arrow(axis, start_x, end_x, y, label, *, label_size=7.5):
    axis.add_patch(
        FancyArrowPatch(
            (start_x, y),
            (end_x, y),
            arrowstyle="-|>",
            mutation_scale=15,
            linewidth=1.5,
            color="black",
        )
    )
    axis.text(
        (start_x + end_x) / 2,
        y + 1.45,
        label,
        ha="center",
        va="bottom",
        fontsize=label_size,
        fontweight="bold",
    )


def draw_matrix(axis, x, y, width, height):
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.35,rounding_size=0.8",
        linewidth=1.5,
        edgecolor="black",
        facecolor="white",
    )
    axis.add_patch(patch)
    axis.text(
        x + width / 2,
        y + height - 2.0,
        "MATRICES",
        ha="center",
        va="center",
        fontsize=10.5,
        fontweight="bold",
    )
    rows, columns = 4, 6
    grid_width = width - 6.4
    grid_x = x + (width - grid_width) / 2
    # Center the grid vertically within the usable space between the heading
    # and the two-line caption.
    grid_y = y + 5.0
    cell_w, cell_h = grid_width / columns, 1.42
    shades = ("#ffffff", "#dedede", "#bdbdbd", "#8f8f8f")
    for row in range(rows):
        for column in range(columns):
            axis.add_patch(
                Rectangle(
                    (grid_x + column * cell_w, grid_y + row * cell_h),
                    cell_w,
                    cell_h,
                    facecolor=shades[(row + column) % len(shades)],
                    edgecolor="black",
                    linewidth=0.45,
                )
            )
    axis.text(
        x + width / 2,
        y + 1.75,
        "forward + aligned backward\nNy x Nx signed-count arrays",
        ha="center",
        va="center",
        fontsize=7.8,
    )


def draw_output(axis, x, y, width, height):
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.35,rounding_size=0.8",
        linewidth=1.5,
        edgecolor="black",
        facecolor="#f2f2f2",
    )
    axis.add_patch(patch)
    axis.text(
        x + width / 2,
        y + height - 2.0,
        "MATPLOTLIB Q OUTPUT",
        ha="center",
        va="center",
        fontsize=10.5,
        fontweight="bold",
    )
    panel_w, panel_h = 5.0, 3.4
    column_gap, row_gap = 1.0, 0.8
    panel_group_width = (2 * panel_w) + column_gap
    left = x + (width - panel_group_width) / 2
    bottom = y + 3.4
    for row in range(2):
        for column in range(2):
            px = left + column * (panel_w + column_gap)
            py = bottom + row * (panel_h + row_gap)
            panel_index = row * 2 + column
            grid_rows, grid_columns = 6, 9
            for grid_row in range(grid_rows):
                for grid_column in range(grid_columns):
                    gradient = grid_row / (grid_rows - 1)
                    corrugation = exp(
                        -(
                            ((grid_column % 4) - 1.5) ** 2
                            + ((grid_row % 3) - 1.0) ** 2
                        )
                        / 1.8
                    )
                    if panel_index == 3:
                        value = 0.5 + 0.28 * sin(
                            1.35 * grid_column + 0.8 * grid_row
                        )
                    else:
                        directional_shift = 0.05 * column
                        value = 0.58 * gradient + 0.30 * corrugation + directional_shift
                    shade = max(0.16, min(0.96, 0.96 - 0.68 * value))
                    axis.add_patch(
                        Rectangle(
                            (
                                px + grid_column * panel_w / grid_columns,
                                py + grid_row * panel_h / grid_rows,
                            ),
                            panel_w / grid_columns,
                            panel_h / grid_rows,
                            facecolor=str(shade),
                            edgecolor="none",
                        )
                    )
            axis.add_patch(
                Rectangle(
                    (px, py),
                    panel_w,
                    panel_h,
                    facecolor="none",
                    edgecolor="black",
                    linewidth=0.55,
                )
            )
    axis.text(
        x + width / 2,
        y + 1.6,
        "stored Q: forward | backward\nrendered: aligned B | average | F-B",
        ha="center",
        va="center",
        fontsize=7.8,
    )


def generate(output: Path) -> Path:
    figure, axis = plt.subplots(figsize=(14.5, 2.0))
    figure.patch.set_facecolor("white")
    axis.set_xlim(0, 116)
    axis.set_ylim(0, 20)
    axis.axis("off")

    box(
        axis,
        1,
        2,
        22,
        16,
        "MATCHED TEENSY FILES",
        (
            "STM1F<n>.hex  - forward",
            "STM1B<n>.hex  - backward",
            "STM1P<n>.txt  - parameters",
        ),
        fill="white",
    )
    arrow(axis, 23.6, 29.0, 10, "READ")
    box(
        axis,
        29.5,
        2,
        27,
        16,
        "PYTHON CONVERSION",
        (
            "match one scan number",
            "decode little-endian signed int16",
            "validate byte and sample counts",
            "reshape rows; align backward X",
        ),
    )
    # The narrower label keeps clear air between the two adjacent boxes.
    arrow(axis, 57.0, 62.4, 10, "RESHAPE", label_size=6.4)
    draw_matrix(axis, 63, 2, 21, 16)
    arrow(axis, 84.6, 90.0, 10, "RENDER")
    draw_output(axis, 90.5, 2, 24.5, 16)

    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        output,
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.06,
        facecolor="white",
    )
    plt.close(figure)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("poster/data-conversion-architecture.png"),
    )
    args = parser.parse_args()
    rendered = generate(args.output)
    print(f"Saved architecture diagram: {rendered.resolve()}")


if __name__ == "__main__":
    main()
