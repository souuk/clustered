#!/usr/bin/env python3
"""Generate the two synthetic computational figures used on poster Sheet 9.

Both outputs are deliberately labeled as simulations.  They illustrate the
offline analysis methods discussed by the poster and must not be presented as
measurements from the STM.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "poster"


def _plane_level(matrix: np.ndarray) -> np.ndarray:
    rows, columns = matrix.shape
    yy, xx = np.indices((rows, columns), dtype=float)
    design = np.column_stack((xx.ravel(), yy.ravel(), np.ones(matrix.size)))
    coefficients, *_ = np.linalg.lstsq(design, matrix.ravel(), rcond=None)
    return matrix - (design @ coefficients).reshape(matrix.shape)


def _line_level(matrix: np.ndarray) -> np.ndarray:
    return matrix - np.median(matrix, axis=1, keepdims=True)


def _remove_mean(matrix: np.ndarray) -> np.ndarray:
    return matrix - np.mean(matrix)


def _synthetic_atomic_surface(size: int = 96) -> np.ndarray:
    """Return a periodic Gaussian lattice in arbitrary controller counts."""

    yy, xx = np.indices((size, size), dtype=float)
    surface = np.zeros((size, size), dtype=float)
    spacing = 12
    sigma = 1.75
    for row in range(6, size, spacing):
        for column in range(6, size, spacing):
            surface += 150.0 * np.exp(
                -((xx - column) ** 2 + (yy - row) ** 2) / (2.0 * sigma**2)
            )
    surface -= np.mean(surface)
    return surface


def build_noise_leveling_figure(output: Path) -> None:
    """Compare leveling choices and quantify recovery over a noise sweep."""

    rng = np.random.default_rng(20260730)
    truth = _synthetic_atomic_surface()
    rows, columns = truth.shape
    yy, xx = np.indices(truth.shape, dtype=float)

    # A reproducible scanner/background artifact used only for this simulation.
    plane = 1.35 * (xx - columns / 2.0) - 0.95 * (yy - rows / 2.0)
    line_offsets = 22.0 * np.sin(2.0 * np.pi * yy / 23.0)
    background = plane + line_offsets

    noise_levels = np.arange(0.0, 81.0, 10.0)
    methods = {
        "No leveling": _remove_mean,
        "Line leveling": _line_level,
        "Plane leveling": _plane_level,
    }
    rmse = {label: [] for label in methods}

    for sigma in noise_levels:
        for _ in range(18):
            measured = truth + background + rng.normal(0.0, sigma, truth.shape)
            for label, operation in methods.items():
                recovered = operation(measured)
                # Compare with the correspondingly centered synthetic truth.
                target = operation(truth)
                rmse[label].append(
                    (sigma, float(np.sqrt(np.mean((recovered - target) ** 2))))
                )

    example_sigma = 30.0
    example = truth + background + rng.normal(0.0, example_sigma, truth.shape)
    example_line = _line_level(example)
    example_plane = _plane_level(example)

    figure = plt.figure(figsize=(9.2, 4.45), facecolor="white")
    grid = figure.add_gridspec(
        2,
        3,
        height_ratios=(1.0, 0.83),
        left=0.065,
        right=0.94,
        bottom=0.20,
        top=0.88,
        hspace=0.48,
        wspace=0.34,
    )

    image_axes = [figure.add_subplot(grid[0, index]) for index in range(3)]
    display = (
        (_remove_mean(example), "No leveling"),
        (example_line, "Line leveling"),
        (example_plane, "Plane leveling"),
    )
    limit = float(np.percentile(np.abs(np.concatenate([item[0].ravel() for item in display])), 99))
    for axis, (matrix, title) in zip(image_axes, display):
        image = axis.imshow(
            matrix,
            origin="lower",
            interpolation="nearest",
            cmap="Greys_r",
            vmin=-limit,
            vmax=limit,
        )
        axis.set_title(title, fontsize=10.5, pad=4)
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_linewidth(0.65)

    colorbar = figure.colorbar(
        image,
        ax=image_axes,
        orientation="vertical",
        fraction=0.018,
        pad=0.012,
    )
    colorbar.set_label("Processed Q (counts)", fontsize=8.5)
    colorbar.ax.tick_params(labelsize=7.5)
    colorbar.outline.set_linewidth(0.6)

    sweep_axis = figure.add_subplot(grid[1, :])
    styles = {
        "No leveling": ("o", "-"),
        "Line leveling": ("s", "--"),
        "Plane leveling": ("^", "-."),
    }
    for label, values in rmse.items():
        means = [
            np.mean([rmse_value for level, rmse_value in values if level == sigma])
            for sigma in noise_levels
        ]
        marker, linestyle = styles[label]
        sweep_axis.plot(
            noise_levels,
            means,
            color="black",
            marker=marker,
            linestyle=linestyle,
            linewidth=1.25,
            markersize=4,
            label=label,
        )
    sweep_axis.set_xlabel("Added Gaussian noise, σ (counts)", fontsize=9)
    sweep_axis.set_ylabel("Recovery RMSE (counts)", fontsize=9)
    sweep_axis.tick_params(labelsize=8)
    sweep_axis.grid(True, color="0.86", linewidth=0.6)
    sweep_axis.legend(
        loc="upper left",
        frameon=False,
        fontsize=8,
        ncol=3,
        handlelength=2.8,
    )

    figure.suptitle(
        "SYNTHETIC NOISE AND LEVELING TEST — NOT EXPERIMENTAL",
        fontsize=12.5,
        fontweight="bold",
        y=0.965,
    )
    figure.text(
        0.5,
        0.035,
        (
            "Periodic test surface + planar tilt + line drift; heatmaps use σ = "
            f"{example_sigma:.0f} counts. RMSE is averaged over 18 fixed-seed trials."
        ),
        ha="center",
        fontsize=7.8,
    )
    figure.savefig(output, dpi=260, facecolor="white")
    plt.close(figure)


def build_eigenvalue_figure(output: Path) -> None:
    """Solve a 2-D nearest-neighbor tight-binding toy Hamiltonian."""

    side = 11
    site_count = side * side
    hopping = 1.0
    defect_strength = -2.5
    hamiltonian = np.zeros((site_count, site_count), dtype=float)

    def index(row: int, column: int) -> int:
        return row * side + column

    for row in range(side):
        for column in range(side):
            current = index(row, column)
            if row + 1 < side:
                neighbor = index(row + 1, column)
                hamiltonian[current, neighbor] = -hopping
                hamiltonian[neighbor, current] = -hopping
            if column + 1 < side:
                neighbor = index(row, column + 1)
                hamiltonian[current, neighbor] = -hopping
                hamiltonian[neighbor, current] = -hopping

    center = index(side // 2, side // 2)
    hamiltonian[center, center] = defect_strength
    eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
    selected = 0
    probability = np.abs(eigenvectors[:, selected].reshape(side, side)) ** 2

    figure, (spectrum_axis, state_axis) = plt.subplots(
        1,
        2,
        figsize=(8.9, 3.55),
        gridspec_kw={"width_ratios": (1.2, 1.0)},
        facecolor="white",
    )

    state_numbers = np.arange(1, site_count + 1)
    spectrum_axis.scatter(
        state_numbers[1:],
        eigenvalues[1:],
        s=11,
        facecolors="white",
        edgecolors="black",
        linewidths=0.55,
    )
    spectrum_axis.scatter(
        [1],
        [eigenvalues[selected]],
        marker="D",
        s=42,
        color="black",
        label=f"selected state, E/t = {eigenvalues[selected]:.2f}",
        zorder=3,
    )
    spectrum_axis.axhspan(-4.0, 4.0, color="0.92", zorder=0)
    spectrum_axis.text(
        site_count * 0.98,
        3.62,
        "ideal 2-D band",
        ha="right",
        va="top",
        fontsize=7.5,
    )
    spectrum_axis.set_xlabel("Eigenstate index n", fontsize=9)
    spectrum_axis.set_ylabel("Energy E / t", fontsize=9)
    spectrum_axis.set_title("Eigenvalue spectrum", fontsize=10.5)
    spectrum_axis.tick_params(labelsize=8)
    spectrum_axis.grid(True, color="0.88", linewidth=0.55)
    spectrum_axis.legend(loc="lower right", frameon=False, fontsize=7.5)

    image = state_axis.imshow(
        probability,
        origin="lower",
        cmap="Greys",
        interpolation="nearest",
    )
    state_axis.scatter(
        [side // 2],
        [side // 2],
        marker="+",
        s=70,
        linewidths=1.0,
        color="black",
    )
    state_axis.set_xlabel("Lattice site x", fontsize=9)
    state_axis.set_ylabel("Lattice site y", fontsize=9)
    state_axis.set_title(r"Selected eigenvector probability $|\phi_1(x,y)|^2$", fontsize=10.5)
    state_axis.tick_params(labelsize=8)
    colorbar = figure.colorbar(image, ax=state_axis, fraction=0.046, pad=0.04)
    colorbar.set_label("Probability", fontsize=8.5)
    colorbar.ax.tick_params(labelsize=7.5)
    colorbar.outline.set_linewidth(0.6)

    figure.suptitle(
        "OFFLINE TIGHT-BINDING MODEL — NOT AN STM MEASUREMENT",
        fontsize=12.3,
        fontweight="bold",
        y=0.975,
    )
    figure.text(
        0.5,
        0.02,
        (
            "11 × 11 square lattice, open boundaries, nearest-neighbor hopping −t, "
            "zero site energy except central defect V = −2.5t."
        ),
        ha="center",
        fontsize=7.8,
    )
    figure.tight_layout(rect=(0.02, 0.065, 0.985, 0.91), w_pad=2.2)
    figure.savefig(output, dpi=260, facecolor="white")
    plt.close(figure)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    noise_output = OUTPUT_DIR / "noise-leveling-sweep.png"
    eigenvalue_output = OUTPUT_DIR / "eigenvalue-spectrum.png"
    build_noise_leveling_figure(noise_output)
    build_eigenvalue_figure(eigenvalue_output)
    print(f"Saved {noise_output}")
    print(f"Saved {eigenvalue_output}")


if __name__ == "__main__":
    main()
