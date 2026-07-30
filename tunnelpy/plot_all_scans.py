#!/usr/bin/env python3
"""Attempt four-panel plots for every scan set in a data directory."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

if __package__:
    from .plot_stm import LEVEL_MODES, plot_scan_set
    from .stm_io import load_scan_set
else:
    from plot_stm import LEVEL_MODES, plot_scan_set
    from stm_io import load_scan_set


PARAMETER_NAME_RE = re.compile(r"^(?P<prefix>.+)P(?P<number>\d+)\.txt$", re.I)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "output")
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--segment", choices=("reject", "start", "end"), default="reject")
    parser.add_argument("--level", choices=LEVEL_MODES, default="none")
    parser.add_argument("--dpi", type=int, default=180)
    args = parser.parse_args()

    made = 0
    skipped = 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for parameter_path in sorted(args.input_dir.glob("*P*.txt")):
        match = PARAMETER_NAME_RE.match(parameter_path.name)
        if match is None:
            continue
        prefix = match.group("prefix")
        number = int(match.group("number"))
        try:
            scan = load_scan_set(
                args.input_dir,
                prefix=prefix,
                scan_number=number,
                allow_partial=args.allow_partial,
                segment=args.segment,
            )
            output = args.output_dir / f"{prefix}-scan-{number}-four-panel.png"
            plot_scan_set(scan, output, level=args.level, dpi=args.dpi)
            made += 1
            print(f"CREATED {output}")
        except (OSError, ValueError) as exc:
            skipped += 1
            print(f"SKIPPED {prefix}{number}: {exc}")
    print(f"Finished: {made} created, {skipped} skipped")


if __name__ == "__main__":
    main()
