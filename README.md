# Clustered STM Project

This repository organizes materials for the COSMOS 2026 scanning tunneling
microscope project, including source locations, controller-related files,
future measurement output, and surface-reconstruction work.

## Current status

- The poster's course-source citations and their locations in the supplied ZIP
  are documented.
- The newer STM12 firmware defines matched forward, backward, and parameter
  files and fixes the older backward-array index.
- `tunnelpy` implements file discovery, validation, little-endian signed-int16
  decoding, masked partial-scan reconstruction, backward alignment, quality
  reporting, leveling options, and the four-panel diagnostic plot.
- Eight regression tests currently pass.
- `synthetic_data/` contains a clearly labeled firmware-format demonstration
  of PID-output `Q`; it is not experimental data.
- `data/` contains the other group's STM12 reference triplet. Its format is
  readable, but the forward file is eight samples short and contradicts the
  parameter completion record.
- `results/reference-scan-1/` contains the reproducible validation report and
  raw and line-levelled diagnostic figures for that triplet.
- Sheet 8 is frozen at its current synthetic demonstration until the group
  obtains one reliable, complete scan from its own STM.
- All of Sheet 10 and the diagnostic top half of Sheet 11 are frozen until the
  group obtains the actual measurements required by those plots. The conclusion
  and Error Analysis and Future Work below the Sheet 11 divider remain editable.
- Repeatable tunneling, group-owned scan data, Z-piezo calibration, subsystem
  measurements, and final uncertainty analysis are still required.

## Data and visualization

The STM's recorded values are the original measurement output. A two-dimensional
map or three-dimensional surface is a processed representation made from those
measurements, not a direct photograph from the instrument. Raw files,
processing code, processing settings, and selected generated figures are kept
together so each transformation can be checked and reproduced.

The implemented converter uses the three files produced for one scan:
`<prefix>F<number>.hex`, `<prefix>B<number>.hex`, and
`<prefix>P<number>.txt`. The `.hex` files are binary little-endian signed
16-bit PID-output `Q` values rather than human-readable hexadecimal text.
The parameter file supplies the requested dimensions and completion record.
Backward rows are reversed after decoding so they share the forward scan's
physical X orientation.

## Repository layout

- `poster/main.tex`: authoritative poster source.
- `poster/software-control-flow-large.png`: software-architecture figure used
  by the poster.
- `poster/software-state-sequence.png`: control-state figure used by the
  poster.
- `poster/data-conversion-architecture.png`: current file-to-plot architecture.
- `poster/raw-data-to-matrix.png`: synthetic binary-to-matrix example.
- `poster/synthetic-q-four-panel.png`: frozen Sheet 8 synthetic result.
- `poster/eigenvalue-spectrum.png`: Sheet 9 tight-binding spectrum and selected
  eigenvector-probability calculation.
- `poster/noise-leveling-sweep.png`: Sheet 9 synthetic noise and leveling
  robustness calculation.
- `generate_computational_figures.py`: reproducibly generates both Sheet 9
  computational figures.
- `animate_scan_pattern.py`: firmware-derived scan-order model.
- `poster/scan-pattern-quad-1.png` through
  `poster/scan-pattern-quad-4.png`: the four static stages used by the poster.
- `requirements-animation.txt`: Python dependencies for regenerating the scan
  model.
- `tunnelpy/`: synthetic controller-output generator, validated STM file
  reader, masked reconstruction, quality reporter, diagnostic plotter, and
  regression tests.
- `tunnelpy/generate_synthetic_scan_funny.py`: the "funny," an intentionally
  chaotic and needlessly difficult companion that produces the same synthetic
  artifacts through ceremonial subcommands and excessive abstraction.
- `data/`: unchanged other-group reference triplet plus its provenance notice.
- `results/`: archived validation reports and selected reproducible plots.
- `synthetic_data/`: generated `SYNF1/SYNB1/SYNP1` format demonstration.
- `CITATION_SOURCE_PATHS.txt`: exact locations of cited course sources.
- `POSTER_FORMATTING_AND_WORKFLOW_RULES.txt`: poster layout and content rules.

### Teensy scanning-pattern model

[`animate_scan_pattern.py`](animate_scan_pattern.py) reproduces the scan order
in the Teensy firmware's `Timer2Service`: acquire one line while stepping in
the +X direction, retrace and acquire while stepping in the -X direction,
reset X, increment Y, and repeat.

The current firmware source is S. Chiang,
`Experiments/STM Project/Teensy_STM12_July_29_2026_v1.ino` in the supplied
course-material ZIP ([citation 5](CITATION_SOURCE_PATHS.txt)). Relevant
locations include lines 917-940 for scan initialization, lines 1500-1544 for
forward/backward raster acquisition, and lines 1583-1596 for the parameter
record.

Install its dependencies and open the interactive model:

```console
python -m pip install -r requirements-animation.txt
python animate_scan_pattern.py
```

The defaults use fewer points than the firmware's 512-by-512 default so the
motion is easy to follow. Use `--points`, `--lines`, `--step-size`,
`--initial-x`, and `--initial-y` to change the modeled scan.

The poster uses four static quadrants selected from the model: forward \(+X\),
backward \(-X\), X reset with Y increment, and accumulated raster progress.
The model also displays the firmware's literal `pointcounter` value. The STM12
source stores backward values with
`pointcounter - numpoints`, producing a zero-based array index while preserving
right-to-left acquisition order in the binary file.

## Reproduce the reference-scan analysis

From the repository root:

```console
python -m tunnelpy.inspect_scans data --output tunnelpy/scan_inventory.txt
python -m tunnelpy.validate_scan data --output results/reference-scan-1/validation.txt
python -m tunnelpy.plot_stm data --allow-partial --output results/reference-scan-1/four-panel-raw.png
python -m tunnelpy.plot_stm data --allow-partial --level line --output results/reference-scan-1/four-panel-line-leveled.png
python -m unittest discover -s tunnelpy/tests -v
```

Masked reconstruction retains all 4,088 stored forward values and represents
only the eight absent values as unknown. It does not interpolate replacements.

## Poster citations

The poster currently uses five numbered references. References `[1]`, `[2]`,
`[3]`, and `[5]` are course materials found in the supplied course-material
ZIP. Reference `[4]` is this repository itself.

See [`CITATION_SOURCE_PATHS.txt`](CITATION_SOURCE_PATHS.txt) for the full
citation-to-source-path index.

## Poster source and working rules

The current upload-ready LaTeX source and its PNG diagrams are kept in
[`poster/`](poster/). The comprehensive formatting, content, citation, data,
and workflow conventions are recorded in
[`POSTER_FORMATTING_AND_WORKFLOW_RULES.txt`](POSTER_FORMATTING_AND_WORKFLOW_RULES.txt).

## Files still to add

- one complete group-owned forward/backward/parameter scan triplet;
- vertical-piezo calibration information;
- final subsystem measurements and uncertainty values;
- remaining Figures #1, #2, #4, #5, and #7 TBM (Figures #3 and #6 are
  implemented as clearly labeled calculations on Sheet 9);
- final 2D and optional 3D experimental surface figures; and
- processing settings and provenance for the final experimental figures.

The other-group reference scan does not satisfy the group-owned-data
requirement. Do not replace or revise the current Sheet 8 synthetic
demonstration until a group-owned scan triplet passes the reader's exact-size,
completion, and forward/backward checks. Likewise, do not revise Sheet 10 or
the diagnostic top half of Sheet 11 until the required group-owned measurements
exist. Work remains local until the group requests the next single push to
`main`.
