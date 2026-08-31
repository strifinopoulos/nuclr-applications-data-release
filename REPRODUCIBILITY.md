# Reproducing the Released Analysis

## Scope

This package reproduces the paper's post-hoc uncertainty analysis and chain
figures from frozen NuCLR predictions. It does not retrain NuCLR or regenerate
the neural-network checkpoints. The central predictions are treated as fixed
inputs, while the residual-scale gradient-boosted regressors are refitted.

## Environment

The release was verified with Python 3.9.12 and the exact package versions in
`requirements.txt`.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

On Linux or macOS, use `.venv/bin/python` instead.

## Uncertainty Analysis

First verify the release checksums, prediction semantics, and MTL/STL OOF RMS
values:

```bash
python scripts/verify_release.py
```

Run:

```bash
python scripts/reproduce_uncertainty.py
```

The script performs the following steps independently for charge radii and
`B(E2)`:

1. Reads the exact measured-target OOF centers and measurements from
   `inputs/uncertainty_oof_residuals.csv`.
2. Builds the 12 nuclear-structure features specified in the manuscript.
3. Uses the exact assignments in `splits/random_folds.csv` for five shuffled
   five-fold partitions.
4. Fits all 20 ordered training/calibration/test rotations per partition.
5. Gives each measured nucleus the median width from its 20 held-out-test fits
   and each open nucleus the median width from all 100 fits.
6. Recomputes the random-fold coverage and translated-grid local score.
7. Uses `splits/regional_folds.csv` to repeat the three-partition contiguous-
   region stress test.
8. Compares the results with `tables/uncertainty_validation.csv` and every
   released interval width. The command exits with an error on disagreement.

The generated files are written under `reproduced/`. Recomputing residuals from
the frozen measurement and OOF-prediction columns is intentional: it matches
the floating-point operation in the production analysis.

## Figures

Run:

```bash
python scripts/reproduce_figures.py
```

This regenerates the numerical content of the four isotopic-chain figure
families and the promethium panel from the released NuCLR, experimental, 5DCH,
and BSkG3 tables. Output filenames match the manuscript assets. Rendering is a
standalone public implementation and is not expected to be byte-for-byte
identical to the final journal-layout images.

## What Is and Is Not Verified

The package verifies the reported OOF central-prediction metrics by direct
calculation from the tables, the complete residual-scale interval procedure,
random-fold coverage, local calibration, regional stress tests, and plotted
data series. It does not reproduce the neural-network training that generated
the frozen NuCLR predictions. Consequently, it audits the paper from the OOF
prediction stage onward, not from raw nuclear tables to trained checkpoints.

Coverage claims are empirical and marginal over randomly held-out measured
nuclei. The conformal exchangeability condition is not established for open
nuclei outside measured support, and no nominal coverage is assigned there.
