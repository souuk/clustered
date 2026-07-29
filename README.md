# Clustered STM Project

This repository organizes materials for the COSMOS 2026 scanning tunneling
microscope project, including source locations, controller-related files,
future measurement output, and surface-reconstruction work.

## Current status

- The poster's course-source citations and their locations in the supplied ZIP
  are documented.
- The Teensy controller firmware defines forward-scan, backward-scan, and
  parameter-file output.
- The surface-reconstruction workflow has been drafted for the poster.
- Complete STM scan files and a tested reconstruction program still need to be
  added.
- `process_stm_input.py` remains a placeholder and does not currently generate
  a surface model.

## Data and visualization

The STM's recorded values are the original measurement output. A two-dimensional
map or three-dimensional surface is a processed representation made from those
measurements, not a direct photograph from the instrument. When complete data
become available, this repository will keep the raw files, processing code,
processing settings, and generated figures together so the transformation can
be checked and reproduced.

## Poster citations

The poster currently uses four numbered references. References `[1]` through
`[3]` are course materials found in the supplied course-material ZIP. Reference
`[4]` is this repository itself, so it does not have a path inside that ZIP.

See [`CITATION_SOURCE_PATHS.txt`](CITATION_SOURCE_PATHS.txt) for the full
citation-to-source-path index.

## Files still to add

- complete forward- and backward-scan files;
- the matching parameter file;
- the tested Python reconstruction program;
- vertical-piezo calibration information;
- final 2D and optional 3D surface figures; and
- processing notes and settings used to generate those figures.
