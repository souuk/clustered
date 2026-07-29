#!/usr/bin/env python3
"""Placeholder interface for future STM data-to-model processing.

The raw file supplied to this program is the original STM measurement output.
No image or surface model is generated yet. The future implementation will
parse that input and create a clearly labeled processed representation.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def read_stm_input(input_path: Path) -> bytes:
    """Read an STM output file without modifying it."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    return input_path.read_bytes()


def build_surface_model(raw_data: bytes) -> object:
    """Convert raw STM measurements into a model in a future revision."""
    raise NotImplementedError(
        "STM data-to-model processing has not been implemented yet."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load an original STM output file for future processing."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the original STM measurement file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_data = read_stm_input(args.input)

    print(f"Loaded {len(raw_data)} bytes from: {args.input}")
    print("Placeholder only: no processed image or surface model was generated.")
    print("The original input file was not modified.")

    # TODO: Call build_surface_model(raw_data) after the file format and
    # visualization method have been finalized.


if __name__ == "__main__":
    main()
