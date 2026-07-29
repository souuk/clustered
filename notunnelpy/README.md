# No-Tunneling STM Plotter Development

This folder lets the group build and validate the STM plotting workflow before
the microscope produces a tunneling signal. It generates synthetic files with
the same planned names and binary layout as the Teensy output, then reads and
plots them.

Synthetic files and figures are development fixtures. They must never be
presented as experimental STM results.

## Files

- `stm_io.py`: discovers, parses, and validates one scan's input files.
- `generate_demo_data.py`: creates reproducible synthetic forward, backward,
  and parameter files.
- `plot_stm.py`: creates one simple, printer-friendly heatmap.
- `tests/test_pipeline.py`: verifies file lengths, reshaping, backward
  alignment, error handling, leveling, and plotting.
- `requirements.txt`: NumPy and Matplotlib dependencies.

## Expected STM input

One completed scan is expected to provide:

```text
STMF1.hex   forward samples
STMB1.hex   backward samples in acquisition order
STMP1.txt   dimensions, completion counters, bias field, and current setting
```

The `.hex` files are not text files. They contain raw little-endian signed
16-bit values with no header. For `Nx` points and `Ny` lines, each direction
must contain exactly:

```text
Nx × Ny samples
2 × Nx × Ny bytes
```

The plotter reads the parameter file first, rejects incorrect binary lengths,
reshapes the values into `(Ny, Nx)`, and reverses each backward row into the
forward spatial orientation.

## Install

From the repository root:

```console
python -m pip install -r notunnelpy/requirements.txt
```

## Generate synthetic inputs

```console
python -m notunnelpy.generate_demo_data
```

The default command creates:

```text
notunnelpy/demo_output/STMF1.hex
notunnelpy/demo_output/STMB1.hex
notunnelpy/demo_output/STMP1.txt
```

By default, the generator creates an idealized atomic lattice. Each bright
site is a Gaussian peak representing an atom-scale feature. This tests
atomic-resolution plotting, but it is not a material-specific or
tunneling-current simulation. The forward and backward fixtures use the same
underlying lattice with independent low-level noise; their default systematic
offset is zero.

Choose a different fixture:

```console
python -m notunnelpy.generate_demo_data notunnelpy/demo_output --points 96 --lines 72 --pattern double-bump --noise 10 --overwrite
```

Available patterns are `atomic-lattice`, `flat`, `slope`, `bump`,
`double-bump`, and `checkerboard`.

## Plot the files

```console
python -m notunnelpy.plot_stm notunnelpy/demo_output
```

This creates `notunnelpy/demo_output/STM1-heatmap.png`: a single forward-scan
heatmap using a light blue palette that remains readable when printed.

Other views remain available as individual, uncluttered heatmaps:

```console
python -m notunnelpy.plot_stm notunnelpy/demo_output --view backward
python -m notunnelpy.plot_stm notunnelpy/demo_output --view average
python -m notunnelpy.plot_stm notunnelpy/demo_output --view difference
```

Because the supplied firmware currently has an unsafe backward-array index,
the first real-data version should support forward-only plotting:

```console
python -m notunnelpy.plot_stm path/to/real/scan --forward-only
```

Optional leveling is explicit and disabled by default:

```console
python -m notunnelpy.plot_stm notunnelpy/demo_output --level line
python -m notunnelpy.plot_stm notunnelpy/demo_output --level plane
```

Never describe controller counts as nanometers until a vertical-piezo
calibration has been measured.

## Run tests

```console
python -m unittest discover -s notunnelpy/tests -v
```

## Moving to `tunnelpy`

When real tunneling data exist, copy these into `tunnelpy/`:

```text
stm_io.py
plot_stm.py
requirements.txt
```

Keep `generate_demo_data.py` and `tests/` available for regression testing.
Before trusting real backward files, correct and test the Teensy
`DataArray1B` index. Also verify the byte order, file lengths, scan orientation,
and the meaning of the firmware's bias field against an actual completed scan.
