TUNNELPY
========

This folder contains the real-data STM plotting pipeline.

FILES
-----
stm_io.py
  Parses repeated Teensy parameter records, reads little-endian signed int16
  scan values, rejects unsafe file lengths, preserves partial scans with
  explicit NaN masks, and spatially aligns backward scans.

plot_stm.py
  Generates the detailed 2x2 figure: forward, aligned backward, average, and
  forward-minus-backward.

inspect_scans.py
  Audits every F/B/P file set before plotting.

plot_all_scans.py
  Attempts the plotter on every discovered scan and reports skipped inputs.

validate_scan.py
  Writes a reproducible coverage, completion-consistency, range, agreement,
  and anomalous-row report without claiming a physical Z calibration.

quality.py
  Implements the non-calibrating quality metrics used by validate_scan.py.

generate_synthetic_scan.py
  Creates a deterministic, clearly labeled synthetic F/B/P scan triplet and
  the schema-check, raw-data-to-matrix, and four-panel poster figures. It
  follows the newer STM12 firmware format but does not represent a microscope
  measurement.

generate_synthetic_scan_funny.py
  The "funny": intentionally chaotic, needlessly bureaucratic code that
  produces the same synthetic artifacts. It is an embedded joke, not the
  recommended interface.

PLOT_INSTRUCTIONS.txt
  Copy-and-paste commands and explanations for group members.

requirements.txt
  Python dependencies.

tests\
  Automated format, alignment, partial-data, appended-data, leveling, and plot
  tests.

output\
  Disposable local PNG figures ignored by Git. Selected reviewable results are
  archived under the repository-level results\ directory.

QUICK START
-----------
Run from the parent "cosmos presentation" directory:

  python -m pip install -r tunnelpy\requirements.txt
  python -m unittest discover -s tunnelpy\tests -v
  python -m tunnelpy.inspect_scans data --output tunnelpy\scan_inventory.txt
  python -m tunnelpy.validate_scan data --output results\reference-scan-1\validation.txt
  python -m tunnelpy.plot_stm data --allow-partial --output results\reference-scan-1\four-panel-raw.png

To regenerate the synthetic format demonstration:

  python -m tunnelpy.generate_synthetic_scan

To invoke the "funny" version through its mandatory ceremony:

  python -m tunnelpy.generate_synthetic_scan_funny please generate the images --ritual-token Q-IS-NOT-HEIGHT --i-accept-the-needless-ceremony --publish-committee-minutes

POSTER FREEZE
-------------
Sheet 8 currently uses this synthetic demonstration. Do not revise Sheet 8 or
replace only one of its values. Wait until the group has one complete,
group-owned F/B/P scan triplet that passes the exact-size, completion,
orientation, and forward/backward checks; then update its data, figure,
caption, and summary together.

SCIENTIFIC CAUTION
------------------
These figures visualize the stored PID output Q: the signed correction count
also sent to the Z DAC. Q is not the ADC current sample and is not calibrated
topographic height unless a verified counts-to-displacement calibration is
later applied. A smooth or atom-like picture alone does not demonstrate
tunneling or atomic resolution.

The Teensy firmware does not supply a physical Z scalar or automatically
subtract Q_ref. See PLOT_INSTRUCTIONS.txt, "KNOWN Z-CALIBRATION PROBLEM," before
adding a height axis in nanometers or angstroms.
