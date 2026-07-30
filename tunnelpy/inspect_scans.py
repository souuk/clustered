#!/usr/bin/env python3
"""Inventory STM data sets without plotting or modifying them."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re

if __package__:
    from .stm_io import parse_parameter_records
else:
    from stm_io import parse_parameter_records


PARAMETER_NAME_RE = re.compile(r"^(?P<prefix>.+)P(?P<number>\d+)\.txt$", re.I)


@dataclass(frozen=True)
class InventoryRow:
    key: str
    dimensions: str
    records: str
    forward_samples: str
    backward_samples: str
    status: str


def _samples(path: Path) -> int | None:
    if not path.is_file():
        return None
    byte_count = path.stat().st_size
    if byte_count % 2:
        return -1
    return byte_count // 2


def _count_label(value: int | None) -> str:
    if value is None:
        return "missing"
    if value < 0:
        return "odd bytes"
    return str(value)


def inventory(directory: Path | str) -> list[InventoryRow]:
    root = Path(directory)
    rows: list[InventoryRow] = []
    for parameter_path in sorted(root.glob("*P*.txt"), key=lambda item: item.name):
        match = PARAMETER_NAME_RE.match(parameter_path.name)
        if match is None:
            continue
        prefix = match.group("prefix")
        number = int(match.group("number"))
        forward_path = root / f"{prefix}F{number}.hex"
        backward_path = root / f"{prefix}B{number}.hex"
        forward_samples = _samples(forward_path)
        backward_samples = _samples(backward_path)

        try:
            records = parse_parameter_records(parameter_path)
            selected = records[-1]
            expected = selected.expected_samples
            dimensions = f"{selected.points}x{selected.lines}"
            record_label = str(len(records))
            counts = (forward_samples, backward_samples)
            if None in counts:
                status = "missing direction"
            elif any(value == -1 for value in counts):
                status = "invalid odd-byte file"
            elif any(value == 0 for value in counts):
                status = "empty"
            elif all(value == expected for value in counts):
                status = (
                    "exact size"
                    if selected.firmware_reports_complete
                    else "exact size; completion counter disagrees"
                )
            elif any(value > expected for value in counts):
                status = "appended/ambiguous"
            else:
                shared = min(value for value in counts if value is not None)
                complete_lines = shared // selected.points
                missing_f = expected - int(forward_samples or 0)
                missing_b = expected - int(backward_samples or 0)
                status = (
                    f"partial; {complete_lines}/{selected.lines} complete shared rows; "
                    f"missing F={max(missing_f, 0)}, B={max(missing_b, 0)}"
                )
                if selected.firmware_reports_complete:
                    status += "; completion record disagrees"
        except (OSError, ValueError) as exc:
            dimensions = "unknown"
            record_label = "0"
            status = f"invalid parameters: {exc}"

        rows.append(
            InventoryRow(
                key=f"{prefix} scan {number}",
                dimensions=dimensions,
                records=record_label,
                forward_samples=_count_label(forward_samples),
                backward_samples=_count_label(backward_samples),
                status=status,
            )
        )
    return rows


def format_inventory(rows: list[InventoryRow], directory: Path | str) -> str:
    headers = ("scan", "selected size", "P records", "F samples", "B samples", "status")
    values = [
        (row.key, row.dimensions, row.records, row.forward_samples, row.backward_samples, row.status)
        for row in rows
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in values))
        if values
        else len(headers[index])
        for index in range(len(headers))
    ]
    lines = [f"STM scan inventory: {Path(directory).resolve()}", ""]
    lines.append(
        "  ".join(
            header.ljust(width) for header, width in zip(headers, widths)
        ).rstrip()
    )
    lines.append("  ".join("-" * width for width in widths).rstrip())
    lines.extend(
        "  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip()
        for row in values
    )
    lines.extend(
        (
            "",
            "Notes:",
            "- Sample counts are signed 16-bit values, not bytes.",
            "- 'Appended/ambiguous' means the firmware reused a filename; choose a segment only with evidence.",
            "- 'Partial' can be plotted with --allow-partial; masked reconstruction preserves valid samples.",
            "- A completion-record disagreement means the P file says complete but a binary file is short.",
            "- Stored values remain uncalibrated PID-output Q counts.",
        )
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = format_inventory(inventory(args.input_dir), args.input_dir)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote inventory: {args.output.resolve()}")


if __name__ == "__main__":
    main()
