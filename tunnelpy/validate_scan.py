#!/usr/bin/env python3
"""Validate one STM12 scan triplet and write a reproducible quality report."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from .quality import assess_scan, format_quality_report
    from .stm_io import load_scan_set
else:
    from quality import assess_scan, format_quality_report
    from stm_io import load_scan_set


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--prefix", default="STM")
    parser.add_argument("--scan-number", type=int, default=1)
    parser.add_argument("--parameter-record", type=int, default=-1)
    parser.add_argument("--segment", choices=("reject", "start", "end"), default="reject")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.scan_number < 0:
        parser.error("--scan-number must be zero or greater")

    scan = load_scan_set(
        args.input_dir,
        prefix=args.prefix,
        scan_number=args.scan_number,
        parameter_record=args.parameter_record,
        allow_partial=True,
        segment=args.segment,
        partial_mode="pad",
    )
    report = format_quality_report(scan, assess_scan(scan))
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote validation report: {args.output.resolve()}")


if __name__ == "__main__":
    main()
