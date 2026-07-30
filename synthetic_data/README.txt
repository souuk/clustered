SYNTHETIC STM DATA - NOT EXPERIMENTAL
=====================================

These deterministic fixtures exercise TunnelPy without depending on a
microscope measurement. Do not describe SYNF1.hex, SYNB1.hex, or SYNP1.txt as
experimental data.

The storage contract follows source.zip:
  Experiments\STM Project\Teensy_STM12_July_29_2026_v1.ino

Relevant firmware behavior:
  lines 1113-1131  matched F/B/P filenames
  lines 1500-1523  forward/backward acquisition and two-byte writes
  lines 1526-1544  scan ordering and row stepping
  lines 1583-1596  six-line parameter record

Synthetic model:
  64 x 64 signed PID-output correction Q
  scanner tilt, slow line drift, first-order feedback lag, and noise
  separate forward and right-to-left backward acquisition sequences
  hard clipping to the firmware's signed output range
  a known triangular corrugation used only to test spatial recovery

Reference-data separation:
  data\ contains an independently supplied STM12-format reference triplet
  synthetic_data\ contains only deterministic generated fixtures
  values from the reference triplet are not copied into this simulation

The pattern is a pipeline test. It is not proof of tunneling, atomic
resolution, sample identity, or physical height.
