# Generated results

This directory keeps reproducible outputs that are useful to review or cite.
Temporary plots produced during exploration should remain under
`tunnelpy/output/`, which is ignored by Git.

## `reference-scan-1/`

Outputs derived from the other group's `data/STMF1.hex`, `data/STMB1.hex`, and
`data/STMP1.txt` triplet:

- `validation.txt`: coverage, parameter-consistency, range, directional
  agreement, and anomalous-row checks;
- `four-panel-raw.png`: unlevelled forward, aligned backward, mean, and
  difference matrices; and
- `four-panel-line-leveled.png`: the same diagnostic after explicit per-row
  median subtraction.

Missing samples are masked in pale red. These figures display uncalibrated
PID-output Q counts and must not be described as physical height or proof of
tunneling.
