"""Quantitative, non-calibrating quality checks for one STM scan set."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

if __package__:
    from .stm_io import ScanSet
else:
    from stm_io import ScanSet


@dataclass(frozen=True)
class ScanQuality:
    """Summary values that can be computed without a physical Z calibration."""

    requested_samples: int
    forward_valid_samples: int
    backward_valid_samples: int
    paired_valid_samples: int
    forward_range: tuple[float, float]
    backward_range: tuple[float, float]
    paired_correlation: float
    paired_rmse_counts: float
    anomalous_forward_rows: tuple[int, ...]
    anomalous_backward_rows: tuple[int, ...]


def _finite_range(matrix: npt.ArrayLike) -> tuple[float, float]:
    values = np.asarray(matrix, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return (float("nan"), float("nan"))
    return (float(np.min(values)), float(np.max(values)))


def _anomalous_rows(matrix: npt.ArrayLike) -> tuple[int, ...]:
    """Flag rows whose within-row spread is far above the robust baseline."""

    values = np.asarray(matrix, dtype=np.float64)
    valid_counts = np.count_nonzero(np.isfinite(values), axis=1)
    spreads = np.array(
        [
            np.std(row[np.isfinite(row)])
            if np.any(np.isfinite(row))
            else np.nan
            for row in values
        ],
        dtype=np.float64,
    )
    usable = spreads[valid_counts >= max(3, values.shape[1] // 2)]
    if usable.size < 3:
        return ()
    center = float(np.median(usable))
    mad = float(np.median(np.abs(usable - center)))
    threshold = center + max(8.0 * 1.4826 * mad, 5.0 * center, 100.0)
    return tuple(
        int(index)
        for index, (spread, count) in enumerate(zip(spreads, valid_counts))
        if count >= max(3, values.shape[1] // 2) and spread > threshold
    )


def assess_scan(scan: ScanSet) -> ScanQuality:
    """Compute coverage, paired-direction agreement, and row anomaly metrics."""

    forward = np.asarray(scan.forward, dtype=np.float64)
    backward = np.asarray(scan.backward_aligned, dtype=np.float64)
    paired = np.isfinite(forward) & np.isfinite(backward)
    if np.count_nonzero(paired) >= 2:
        paired_correlation = float(np.corrcoef(forward[paired], backward[paired])[0, 1])
        paired_rmse = float(np.sqrt(np.mean((forward[paired] - backward[paired]) ** 2)))
    else:
        paired_correlation = float("nan")
        paired_rmse = float("nan")

    return ScanQuality(
        requested_samples=scan.parameters.expected_samples,
        forward_valid_samples=scan.forward_valid_samples,
        backward_valid_samples=scan.backward_valid_samples,
        paired_valid_samples=scan.paired_valid_samples,
        forward_range=_finite_range(forward),
        backward_range=_finite_range(backward),
        paired_correlation=paired_correlation,
        paired_rmse_counts=paired_rmse,
        anomalous_forward_rows=_anomalous_rows(forward),
        anomalous_backward_rows=_anomalous_rows(backward),
    )


def _row_label(rows: tuple[int, ...]) -> str:
    return ", ".join(str(row) for row in rows) if rows else "none"


def format_quality_report(scan: ScanSet, quality: ScanQuality) -> str:
    """Render an evidence-focused text report for archiving with a scan."""

    parameter = scan.parameters
    exact = (
        quality.forward_valid_samples == quality.requested_samples
        and quality.backward_valid_samples == quality.requested_samples
    )
    completion_agrees = parameter.firmware_reports_complete == exact
    lines = [
        "TUNNELPY STM12 VALIDATION REPORT",
        "================================",
        "",
        f"Files: {scan.forward_path.name}, {scan.backward_path.name}, {scan.parameter_path.name}",
        f"Requested matrix: {parameter.points} x {parameter.lines} = {quality.requested_samples} samples/direction",
        (
            "Coverage: "
            f"F {quality.forward_valid_samples}/{quality.requested_samples}, "
            f"B {quality.backward_valid_samples}/{quality.requested_samples}, "
            f"paired {quality.paired_valid_samples}/{quality.requested_samples}"
        ),
        f"Binary completeness: {'PASS' if exact else 'FAIL'}",
        (
            "Parameter completion record: "
            f"{'complete' if parameter.firmware_reports_complete else 'incomplete'}; "
            f"{'agrees' if completion_agrees else 'DISAGREES with binary lengths'}"
        ),
        "",
        "STM12 source-contract checks:",
        "- Reference: source.zip, Teensy_STM12_July_29_2026_v1.ino.",
        "- Values decode as little-endian signed 16-bit PID-output Q counts.",
        "- Forward and backward samples reshape in acquisition order.",
        "- Backward rows are reversed in X for spatial comparison.",
        "- Firmware completion counters track the scan loop, not confirmed file bytes.",
        "- Per-sample SD write return values are not checked by the firmware.",
        "- Missing samples remain masked; TunnelPy does not synthesize replacements.",
        "",
        (
            f"Forward range: {quality.forward_range[0]:.0f} to "
            f"{quality.forward_range[1]:.0f} counts"
        ),
        (
            f"Backward range: {quality.backward_range[0]:.0f} to "
            f"{quality.backward_range[1]:.0f} counts"
        ),
        f"Paired F/B correlation after spatial alignment: {quality.paired_correlation:.6f}",
        f"Paired F/B RMSE after spatial alignment: {quality.paired_rmse_counts:.3f} counts",
        f"High-spread forward rows (zero-based): {_row_label(quality.anomalous_forward_rows)}",
        f"High-spread backward rows (zero-based): {_row_label(quality.anomalous_backward_rows)}",
        "",
        "Conclusion:",
        "- The file format and reconstruction path are usable.",
        (
            "- This triplet is not an exact complete scan because at least one "
            "binary direction is short."
            if not exact
            else "- This triplet has exact binary lengths in both directions."
        ),
        (
            "- The P-file completion counters contradict the stored binary length."
            if not completion_agrees
            else "- The P-file completion counters agree with the stored binary lengths."
        ),
        "- These checks do not establish tunneling, atomic resolution, or physical height.",
        "- Physical Z units require an independently measured counts-to-displacement calibration.",
    ]
    if quality.anomalous_forward_rows or quality.anomalous_backward_rows:
        lines.insert(
            -4,
            "- Several rows have unusually large within-row variation and should be reviewed as acquisition artifacts.",
        )
    return "\n".join(lines) + "\n"
