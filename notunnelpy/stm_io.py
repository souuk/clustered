#!/usr/bin/env python3
"""Read and validate the files produced by the Teensy STM firmware.

The supplied firmware creates three files for each scan:

* ``<prefix>F<number>.hex``: forward samples as raw signed 16-bit values.
* ``<prefix>B<number>.hex``: backward samples in acquisition order.
* ``<prefix>P<number>.txt``: dimensions, completion counters, and settings.

Despite the ``.hex`` extension, the two scan files are binary rather than
human-readable hexadecimal text.  The firmware writes two bytes per sample.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Mapping

import numpy as np
import numpy.typing as npt


INT16_LE = np.dtype("<i2")
NUMBER_RE = re.compile(
    r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
)


@dataclass(frozen=True)
class ScanParameters:
    """Values parsed from one Teensy parameter text file."""

    points: int
    lines: int
    completed_points: int | None
    completed_lines: int | None
    bias_field: float | None
    current_na: float | None
    synthetic: bool
    metadata: Mapping[str, str]
    source_path: Path

    @property
    def expected_samples(self) -> int:
        """Number of signed 16-bit values expected in each scan direction."""
        return self.points * self.lines

    @property
    def expected_bytes(self) -> int:
        """Expected byte length of each forward or backward file."""
        return self.expected_samples * INT16_LE.itemsize


@dataclass(frozen=True)
class ScanSet:
    """One validated parameter file and its corresponding scan matrices."""

    parameters: ScanParameters
    forward: npt.NDArray[np.int16]
    backward_acquisition: npt.NDArray[np.int16] | None
    backward_aligned: npt.NDArray[np.int16] | None
    forward_path: Path
    backward_path: Path | None
    parameter_path: Path


def _first_number(line: str, *, field_name: str) -> float:
    match = NUMBER_RE.search(line)
    if match is None:
        raise ValueError(f"Missing numeric {field_name!r} in parameter line: {line!r}")
    return float(match.group(0))


def _optional_number(lines: list[str], index: int, field_name: str) -> float | None:
    if index >= len(lines):
        return None
    return _first_number(lines[index], field_name=field_name)


def parse_parameter_file(path: Path | str) -> ScanParameters:
    """Parse the firmware's text parameter file.

    The parser requires the first two lines (points and lines).  It also reads
    the four fields emitted by ``WriteParametersToFile`` when present.  Extra
    ``key: value`` lines are preserved as metadata so synthetic fixtures can
    identify themselves without changing the firmware-compatible first lines.
    """

    parameter_path = Path(path)
    if not parameter_path.is_file():
        raise FileNotFoundError(f"Parameter file does not exist: {parameter_path}")

    lines = [
        line.strip()
        for line in parameter_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(lines) < 2:
        raise ValueError(
            f"Parameter file must contain at least point and line counts: "
            f"{parameter_path}"
        )

    points = int(_first_number(lines[0], field_name="point count"))
    scan_lines = int(_first_number(lines[1], field_name="line count"))
    if points <= 0 or scan_lines <= 0:
        raise ValueError(
            f"Scan dimensions must be positive; received {points} x {scan_lines}"
        )

    completed_points_value = _optional_number(lines, 2, "completion point count")
    completed_lines_value = _optional_number(lines, 3, "completion line count")
    bias_field = _optional_number(lines, 4, "bias field")
    current_na = _optional_number(lines, 5, "current setting")

    metadata: dict[str, str] = {}
    for line in lines[6:]:
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip()] = value.strip()

    synthetic = any("SYNTHETIC" in line.upper() for line in lines)
    return ScanParameters(
        points=points,
        lines=scan_lines,
        completed_points=(
            int(completed_points_value)
            if completed_points_value is not None
            else None
        ),
        completed_lines=(
            int(completed_lines_value)
            if completed_lines_value is not None
            else None
        ),
        bias_field=bias_field,
        current_na=current_na,
        synthetic=synthetic,
        metadata=metadata,
        source_path=parameter_path,
    )


def read_scan_matrix(
    path: Path | str,
    *,
    parameters: ScanParameters,
) -> npt.NDArray[np.int16]:
    """Read one raw scan file and reshape it into ``(lines, points)``.

    A mismatch is an error.  The reader never pads, truncates, or silently
    reshapes incomplete data.
    """

    scan_path = Path(path)
    if not scan_path.is_file():
        raise FileNotFoundError(f"Scan file does not exist: {scan_path}")

    actual_bytes = scan_path.stat().st_size
    if actual_bytes != parameters.expected_bytes:
        raise ValueError(
            f"Unexpected file length for {scan_path}: expected "
            f"{parameters.expected_bytes} bytes "
            f"({parameters.expected_samples} signed 16-bit samples), "
            f"received {actual_bytes} bytes"
        )

    values = np.fromfile(scan_path, dtype=INT16_LE)
    return values.reshape(parameters.lines, parameters.points)


def write_scan_matrix(path: Path | str, matrix: npt.ArrayLike) -> Path:
    """Write a matrix using the same two-byte signed format as the firmware."""

    output_path = Path(path)
    values = np.asarray(matrix)
    if values.ndim != 2:
        raise ValueError(f"Scan matrix must be two-dimensional, got {values.ndim}D")
    if not np.all(np.isfinite(values)):
        raise ValueError("Scan matrix contains NaN or infinite values")

    rounded = np.rint(values)
    limits = np.iinfo(np.int16)
    if rounded.min() < limits.min or rounded.max() > limits.max:
        raise ValueError(
            f"Scan values must fit signed 16-bit range "
            f"[{limits.min}, {limits.max}]"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rounded.astype(INT16_LE).tofile(output_path)
    return output_path


def align_backward(
    backward_acquisition: npt.ArrayLike,
) -> npt.NDArray[np.int16]:
    """Reverse each backward row into the forward spatial orientation."""

    values = np.asarray(backward_acquisition)
    if values.ndim != 2:
        raise ValueError("Backward scan must be a two-dimensional matrix")
    return np.fliplr(values).copy()


def scan_paths(
    directory: Path | str,
    *,
    prefix: str = "STM",
    scan_number: int = 1,
) -> tuple[Path, Path, Path]:
    """Return forward, backward, and parameter paths for one scan number."""

    if not prefix:
        raise ValueError("File prefix must not be empty")
    if scan_number <= 0:
        raise ValueError("Scan number must be positive")

    root = Path(directory)
    forward = root / f"{prefix}F{scan_number}.hex"
    backward = root / f"{prefix}B{scan_number}.hex"
    parameters = root / f"{prefix}P{scan_number}.txt"
    return forward, backward, parameters


def load_scan_set(
    directory: Path | str,
    *,
    prefix: str = "STM",
    scan_number: int = 1,
    include_backward: bool = True,
    require_backward: bool = False,
) -> ScanSet:
    """Load and validate one set of scan files.

    Backward input is optional because the supplied firmware currently has an
    unsafe backward-array index.  A forward-only workflow remains usable while
    that firmware issue is being corrected.
    """

    forward_path, backward_candidate, parameter_path = scan_paths(
        directory,
        prefix=prefix,
        scan_number=scan_number,
    )
    parameters = parse_parameter_file(parameter_path)
    forward = read_scan_matrix(forward_path, parameters=parameters)

    backward_path: Path | None = None
    backward_acquisition: npt.NDArray[np.int16] | None = None
    backward_aligned: npt.NDArray[np.int16] | None = None
    if include_backward and backward_candidate.is_file():
        backward_path = backward_candidate
        backward_acquisition = read_scan_matrix(
            backward_path,
            parameters=parameters,
        )
        backward_aligned = align_backward(backward_acquisition)
    elif require_backward:
        raise FileNotFoundError(
            f"Backward scan was required but does not exist: {backward_candidate}"
        )

    return ScanSet(
        parameters=parameters,
        forward=forward,
        backward_acquisition=backward_acquisition,
        backward_aligned=backward_aligned,
        forward_path=forward_path,
        backward_path=backward_path,
        parameter_path=parameter_path,
    )
