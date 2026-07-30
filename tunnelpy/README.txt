TUNNELPY
========

This folder contains the real-data STM plotting pipeline.

FILES
-----
stm_io.py
  Parses repeated Teensy parameter records, reads little-endian signed int16
  scan values, rejects unsafe file lengths, recovers explicit partial rows, and
  spatially aligns backward scans.

plot_stm.py
  Generates the detailed 2x2 figure: forward, aligned backward, average, and
  forward-minus-backward.

inspect_scans.py
  Audits every F/B/P file set before plotting.

plot_all_scans.py
  Attempts the plotter on every discovered scan and reports skipped inputs.

PLOT_INSTRUCTIONS.txt
  Copy-and-paste commands and explanations for group members.

requirements.txt
  Python dependencies.

tests\
  Automated format, alignment, partial-data, appended-data, leveling, and plot
  tests.

output\
  Generated PNG figures.

QUICK START
-----------
Run from the parent "cosmos presentation" directory:

  python -m pip install -r tunnelpy\requirements.txt
  python -m unittest discover -s tunnelpy\tests -v
  python -m tunnelpy.inspect_scans data --output tunnelpy\scan_inventory.txt
  python -m tunnelpy.plot_stm data --prefix STM1 --scan-number 8 --allow-partial

SCIENTIFIC CAUTION
------------------
These figures visualize stored controller counts. They are not calibrated
topographic height unless a verified counts-to-displacement calibration is
later applied. A smooth or atom-like picture alone does not demonstrate
tunneling or atomic resolution.

The Teensy firmware does not supply a physical Z scalar or automatically
subtract Q_ref. See PLOT_INSTRUCTIONS.txt, "KNOWN Z-CALIBRATION PROBLEM," before
adding a height axis in nanometers or angstroms.
