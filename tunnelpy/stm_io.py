#!/usr/bin/env python3
"""Read the binary scan files written by the Teensy STM firmware.

The ``.hex`` files are not hexadecimal text.  They contain consecutive
little-endian signed 16-bit integers, two bytes per sample.  In the STM12
firmware each value is the PID output Q that is also sent to the Z DAC; it is
not the ADC-current input or calibrated physical height.  A scan normally has
three files:

``<prefix>F<number>.hex``
    Forward samples in left-to-right acquisition order.
``<prefix>B<number>.hex``
    Backward samples in right-to-left acquisition order.
``<prefix>P<number>.txt``
    Six lines describing the requested dimensions, completion counters, and
    controller settings.

The firmware opens files in append mode, so a reused filename may contain
several parameter records and more than one binary scan.  This module refuses
to guess which appended binary segment is correct unless the caller explicitly
selects the start or end segment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal, Mapping, Sequence

import numpy as np
import numpy.typing as npt


INT16_LE = np.dtype("<i2")
NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
RECORD_START_RE = re.compile(r"^\s*\d+\s+number\s+of\s+points\s*$", re.I)
SegmentMode = Literal["reject", "start", "end"]


@dataclass(frozen=True)
class ParameterRecord:
    """One six-line record from a Teensy parameter file."""

    points: int
    lines: int
    completed_points: int | None
    completed_lines: int | None
    bias_setting: float | None
    current_na: float | None
    record_index: int
    record_count: int
    metadata: Mapping[str, str]
    source_path: Path

    @property
    def expected_samples(self) -> int:
        return self.points * self.lines

    @property
    def expected_bytes(self) -> int:
        return self.expected_samples * INT16_LE.itemsize

    @property
    def firmware_reports_complete(self) -> bool:
        return self.completed_points == 0 and self.completed_lines == self.lines


@dataclass(frozen=True)
class ScanSet:
    """One selected parameter record and its spatially comparable matrices."""

    parameters: ParameterRecord
    forward: npt.NDArray[np.int16]
    backward_acquisition: npt.NDArray[np.int16]
    backward_aligned: npt.NDArray[np.int16]
    forward_path: Path
    backward_path: Path
    parameter_path: Path
    partial: bool
    warnings: tuple[str, ...]

    @property
    def actual_lines(self) -> int:
        return int(self.forward.shape[0])


def _first_number(line: str, field_name: str) -> float:
    match = NUMBER_RE.search(line)
    if match is None:
        raise ValueError(f"Missing {field_name} in parameter line: {line!r}")
    return float(match.group(0))


def _optional_number(lines: Sequence[str], index: int, field_name: str) -> float | None:
    if index >= len(lines):
        return None
    return _first_number(lines[index], field_name)


def parse_parameter_records(path: Path | str) -> tuple[ParameterRecord, ...]:
    """Parse every valid six-line record in a parameter text file."""

    parameter_path = Path(path)
    if not parameter_path.is_file():
        raise FileNotFoundError(f"Parameter file does not exist: {parameter_path}")

    try:
        text = parameter_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Parameter file is not UTF-8 text and may be corrupt: {parameter_path}"
        ) from exc

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    starts = [index for index, line in enumerate(lines) if RECORD_START_RE.match(line)]
    if not starts:
        raise ValueError(f"No Teensy parameter records found in {parameter_path}")

    raw_records: list[tuple[int, int, int | None, int | None, float | None, float | None, dict[str, str]]] = []
    for record_number, start in enumerate(starts):
        end = starts[record_number + 1] if record_number + 1 < len(starts) else len(lines)
        block = lines[start:end]
        if len(block) < 2:
            raise ValueError(
                f"Incomplete parameter record {record_number} in {parameter_path}"
            )

        points = int(_first_number(block[0], "point count"))
        scan_lines = int(_first_number(block[1], "line count"))
        if points <= 0 or scan_lines <= 0:
            raise ValueError(
                f"Record {record_number} has invalid dimensions "
                f"{points} x {scan_lines}"
            )

        completed_points = _optional_number(block, 2, "completion point count")
        completed_lines = _optional_number(block, 3, "completion line count")
        bias_setting = _optional_number(block, 4, "bias setting")
        current_na = _optional_number(block, 5, "current setting")
        metadata: dict[str, str] = {}
        for line in block[6:]:
            key, separator, value = line.partition(":")
            if separator:
                metadata[key.strip()] = value.strip()
        raw_records.append(
            (
                points,
                scan_lines,
                int(completed_points) if completed_points is not None else None,
                int(completed_lines) if completed_lines is not None else None,
                bias_setting,
                current_na,
                metadata,
            )
        )

    record_count = len(raw_records)
    return tuple(
        ParameterRecord(
            points=values[0],
            lines=values[1],
            completed_points=values[2],
            completed_lines=values[3],
            bias_setting=values[4],
            current_na=values[5],
            record_index=index,
            record_count=record_count,
            metadata=values[6],
            source_path=parameter_path,
        )
        for index, values in enumerate(raw_records)
    )


def select_parameter_record(
    records: Sequence[ParameterRecord], index: int = -1
) -> ParameterRecord:
    """Select a record using normal Python indexing, with a clearer error."""

    if not records:
        raise ValueError("No parameter records were supplied")
    try:
        return records[index]
    except IndexError as exc:
        raise ValueError(
            f"Parameter record {index} does not exist; file has {len(records)} record(s)"
        ) from exc


def scan_paths(
    directory: Path | str,
    *,
    prefix: str = "STM1",
    scan_number: int = 8,
) -> tuple[Path, Path, Path]:
    """Return forward, backward, and parameter paths for one scan."""

    if not prefix:
        raise ValueError("File prefix must not be empty")
    if scan_number < 0:
        raise ValueError("Scan number must be zero or greater")
    root = Path(directory)
    return (
        root / f"{prefix}F{scan_number}.hex",
        root / f"{prefix}B{scan_number}.hex",
        root / f"{prefix}P{scan_number}.txt",
    )


def _read_int16(path: Path) -> npt.NDArray[np.int16]:
    if not path.is_file():
        raise FileNotFoundError(f"Scan file does not exist: {path}")
    byte_count = path.stat().st_size
    if byte_count % INT16_LE.itemsize:
        raise ValueError(
            f"{path} has {byte_count} bytes; signed 16-bit data requires an even length"
        )
    return np.fromfile(path, dtype=INT16_LE)


def _extract_matrix(
    values: npt.NDArray[np.int16],
    *,
    path: Path,
    parameters: ParameterRecord,
    allow_partial: bool,
    segment: SegmentMode,
) -> tuple[npt.NDArray[np.int16], bool, tuple[str, ...]]:
    expected = parameters.expected_samples
    actual = int(values.size)
    warnings: list[str] = []

    if actual == expected:
        return values.reshape(parameters.lines, parameters.points), False, ()

    if actual > expected:
        if segment == "reject":
            raise ValueError(
                f"{path.name} contains {actual} samples, more than the selected "
                f"record's {expected}. The file was probably appended. Re-run "
                "with --segment start or --segment end only if that choice is known."
            )
        selected = values[:expected] if segment == "start" else values[-expected:]
        warnings.append(
            f"{path.name}: selected the {segment} {expected} samples from an "
            f"appended {actual}-sample file"
        )
        return selected.reshape(parameters.lines, parameters.points), False, tuple(warnings)

    if not allow_partial:
        raise ValueError(
            f"{path.name} is incomplete: expected {expected} samples "
            f"({parameters.expected_bytes} bytes), found {actual} samples "
            f"({actual * INT16_LE.itemsize} bytes). Use --allow-partial to recover "
            "only complete rows."
        )

    complete_lines = actual // parameters.points
    if complete_lines < 1:
        raise ValueError(
            f"{path.name} does not contain one complete {parameters.points}-point row"
        )
    usable = complete_lines * parameters.points
    warnings.append(
        f"{path.name}: recovered {complete_lines}/{parameters.lines} complete rows; "
        f"ignored {actual - usable} trailing sample(s)"
    )
    return (
        values[:usable].reshape(complete_lines, parameters.points),
        True,
        tuple(warnings),
    )


def align_backward(
    backward_acquisition: npt.ArrayLike,
) -> npt.NDArray[np.int16]:
    """Reverse every backward row into the forward spatial orientation."""

    matrix = np.asarray(backward_acquisition)
    if matrix.ndim != 2:
        raise ValueError("Backward scan must be a two-dimensional matrix")
    return np.fliplr(matrix).copy()


def load_scan_set(
    directory: Path | str,
    *,
    prefix: str = "STM1",
    scan_number: int = 8,
    parameter_record: int = -1,
    allow_partial: bool = False,
    segment: SegmentMode = "reject",
) -> ScanSet:
    """Load forward/backward files and make their spatial dimensions agree."""

    if segment not in ("reject", "start", "end"):
        raise ValueError(f"Unsupported segment mode: {segment}")

    forward_path, backward_path, parameter_path = scan_paths(
        directory, prefix=prefix, scan_number=scan_number
    )
    parameters = select_parameter_record(
        parse_parameter_records(parameter_path), parameter_record
    )

    forward, forward_partial, forward_warnings = _extract_matrix(
        _read_int16(forward_path),
        path=forward_path,
        parameters=parameters,
        allow_partial=allow_partial,
        segment=segment,
    )
    backward, backward_partial, backward_warnings = _extract_matrix(
        _read_int16(backward_path),
        path=backward_path,
        parameters=parameters,
        allow_partial=allow_partial,
        segment=segment,
    )

    warnings = list(forward_warnings + backward_warnings)
    shared_lines = min(forward.shape[0], backward.shape[0])
    if forward.shape[0] != backward.shape[0]:
        if not allow_partial:
            raise ValueError(
                "Forward and backward files contain different numbers of rows"
            )
        warnings.append(
            f"Forward/backward row counts differ; cropped both to {shared_lines} rows"
        )
        forward = forward[:shared_lines]
        backward = backward[:shared_lines]

    partial = (
        forward_partial
        or backward_partial
        or shared_lines < parameters.lines
        or not parameters.firmware_reports_complete
    )
    if not parameters.firmware_reports_complete:
        warnings.append(
            "Selected parameter record reports an early/incomplete scan "
            f"(point counter {parameters.completed_points}, "
            f"line counter {parameters.completed_lines})"
        )

    return ScanSet(
        parameters=parameters,
        forward=forward,
        backward_acquisition=backward,
        backward_aligned=align_backward(backward),
        forward_path=forward_path,
        backward_path=backward_path,
        parameter_path=parameter_path,
        partial=partial,
        warnings=tuple(warnings),
    )
