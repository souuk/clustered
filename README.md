# Clustered STM code

This public repository contains code and reference indexes for the COSMOS 2026
scanning tunneling microscope project.

## Included

- `tunnelpy/`: STM file discovery, validation, decoding, matrix conversion,
  plotting, synthetic-fixture generation, and regression tests.
- `animate_scan_pattern.py`: a firmware-derived raster scan-order model.
- `generate_computational_figures.py`: reproducible computational figure code.
- `generate_data_architecture.py`: reproducible data-flow diagram code.
- `CITATION_SOURCE_PATHS.txt`: citation names and source locations.
- Python dependency lists and code-use notes.

## Intentionally not included

The public repository does not store the poster's LaTeX source, working
documents, photographs, generated figures, raw scans, or other project assets.
The `poster/`, `documents/`, `images/`, and `hardware-visualizations/`
directories are intentionally empty placeholders. Those materials are kept in
the private `cluster` repository.

Generated output and local data are ignored so they are not accidentally
published.

## Tests

From the repository root:

```console
python -m pip install -r tunnelpy/requirements.txt
python -m unittest discover -s tunnelpy/tests -v
```

## Scientific note

The STM reader treats each binary sample as a little-endian signed 16-bit PID
output count. It does not label those counts as physical height without a
verified piezo calibration. Synthetic fixtures and generated figures are
demonstrations, not experimental evidence.
