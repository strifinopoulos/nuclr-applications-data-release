# NuCLR Applications Data

Data release for *Learning Nuclear Structure with AI: Radii and Collectivity*.

This repository contains the frozen data and predictions, the exact
uncertainty-analysis splits, and the scripts used to reproduce the reported
post-hoc interval diagnostics and chain figures. It starts from frozen NuCLR
OOF predictions and does not reproduce neural-network training or checkpoints.

## Contents

| Path | Description |
|---|---|
| `tables/nuclr_charge_radii.csv` | NuCLR charge-radius predictions for 3,231 nuclei, adopted training measurements, external calcium measurements, and 68%/95% interval columns. |
| `tables/nuclr_be2.csv` | NuCLR downward `B(E2; 2+ -> 0+)` predictions for 830 nuclei with a `0+` ground state (808 even-even and 22 odd-odd), with measurements and interval columns. |
| `tables/stl_charge_radii_oof.csv` | Measured-target OOF predictions from the target-only radius reference campaign. |
| `tables/stl_be2_oof.csv` | Measured-target OOF predictions from the target-only `B(E2)` reference campaign. |
| `tables/promethium_isotope_shifts.csv` | Published `143-147Pm` isotope shifts and the aligned NuCLR comparison used in the supplement. |
| `tables/uncertainty_validation.csv` | Aggregate random-fold and contiguous-region interval diagnostics reported in Table S1. |
| `models/5dch_predictions.csv` | Standardized 5DCH charge-radius and downward-`B(E2)` predictions. |
| `models/bskg3_predictions.csv` | Standardized BSkG3 charge radii, deformations, and derived downward-`B(E2)` values. |
| `inputs/` | Frozen input tables used by the campaigns. |
| `inputs/uncertainty_oof_residuals.csv` | Exact measured-target OOF centers and measurements used to fit the residual-scale models. |
| `splits/random_folds.csv` | Exact five repeated random five-fold assignments. |
| `splits/regional_folds.csv` | Exact three repeated regional five-fold assignments. |
| `scripts/reproduce_uncertainty.py` | Refits the interval GBMs and verifies widths and diagnostics. |
| `scripts/reproduce_figures.py` | Recreates the manuscript chain-plot data series. |
| `scripts/verify_release.py` | Verifies checksums, row semantics, and MTL/STL OOF RMS values. |
| `MANIFEST.csv` | Row counts, byte sizes, and SHA-256 checksums. |

## Prediction Semantics

For measured targets, `nuclr_prediction_kind` is
`measured_target_oof_4_models`: the central value is the mean of the four
models whose target fold excluded that nucleus. For unmeasured targets it is
`unmeasured_target_40_models`: the central value is the mean of all 40 models.

The 68% intervals are the ones shown in the figures. The 95% columns are
included for completeness and for the validation results in Table S1. For
measured targets, the intervals are cross-fitted and their marginal coverage
is tested empirically. For unmeasured targets, the widths transfer the OOF
residual scale learned at measured nuclei with similar structural features;
they are not assigned nominal coverage. `B(E2)` lower endpoints are intersected
with the physical support `B(E2) >= 0`.

The released measured `B(E2)` set contains 432 nuclei with a `0+` ground state:
427 even-even nuclei and five odd-odd nuclei. The released prediction grid contains
no odd-A, `1/2+` rows because those rows do not represent a
`B(E2; 2+ -> 0+)` transition.

The frozen campaign used an additional `98Zr` target whose LiveChart extraction
selected the branch to an excited `0+` state rather than the ground-state
branch. Because the released ensemble was not retrained after that source issue
was identified, `98Zr` is excluded from the derived prediction, residual,
validation-split, STL-comparison, and figure tables. The complete frozen
LiveChart source extract remains in `inputs/iaea_livechart_gammas.csv`.

`nuclr_seed_std_*` records the spread of the corresponding central-prediction
ensemble. It is diagnostic information and is not added to the calibrated
interval half-width.

## Measurements and Units

- Charge radii are in fm.
- `B(E2)` values are downward transition strengths in `e^2 b^2`.
- `training_measurement_*` contains the target table used by NuCLR.
- The six calcium measurements in `external_measurement_*` were absent from
  the frozen training table and are retained separately as external data.
- The frozen sources do not report a usable uncertainty for 26 of the 432
  measured `B(E2)` targets; their `training_measurement_unc_e2_b2` fields are
  therefore blank. Source values are retained as reported rather than removed
  by an undocumented plausibility filter.
- Blank CSV fields mean that the quantity is unavailable for that nucleus.

See [SOURCES.md](SOURCES.md) for provenance, conversions, and citations.

## Reproduction

Install the pinned dependencies and run:

```bash
python -m pip install -r requirements.txt
python scripts/verify_release.py
python scripts/reproduce_uncertainty.py
python scripts/reproduce_figures.py --output-dir reproduced/figures
```

The uncertainty script refits the residual-scale GBMs and checks the reported
coverage diagnostics and released interval widths using the frozen NuCLR OOF
predictions in this repository.

The interval reproduction uses the exact assignments in
`splits/random_folds.csv` and `splits/regional_folds.csv`. It evaluates all 20
ordered calibration/test rotations in each of five random partitions. Measured
nuclei receive the median width from their 20 held-out-test fits; unmeasured
nuclei receive the median width from all 100 fits. The script checks the
released widths, random-fold coverage, local calibration, and regional
diagnostics against `tables/uncertainty_validation.csv`.

### Figure outputs

The figure script reproduces the numerical content of the current manuscript
chain plots and writes these standalone PNGs:

| Output | Chains | Reference neutron numbers |
|---|---|---|
| `paper_radii_main_gbm.png` | Ni, Sm, Pb | 33, 84, 116 |
| `paper_be2_main_gbm_main_new.png` | Sm, Po, U | 82, 118, 142 |
| `appendix_radii_other_a_gbm.png` | Ca, Sn, Hg | 24, 70, 113 |
| `appendix_be2_other_a_gbm_main_new.png` | Zr, Sn, Xe, Th | 54, 68, 74, 138 |
| `radii_Pm_cv_uncertainty_gbm.png` | Pm | 86 |

For each lower chain panel, the reference is the central measured isotope.
NuCLR, 5DCH, and BSkG3 are each subtracted by their own value at the same
`N_ref`; a baseline value is linearly interpolated when that isotope is not
tabulated. Nuclear-model curves are restricted to the released NuCLR chain
range. Filled NuCLR squares are measured-target OOF predictions, open squares
are full-ensemble predictions at unmeasured targets, and the error bars are the
released 68% intervals. The Pm panel instead aligns the isotope-shift data and
BSkG3 curve at `N_ref = 86`.

The generated files reproduce the plotted data and reference convention.
Fonts and rasterization can vary slightly with the local Matplotlib version.

## Citation

Cite this repository using [CITATION.cff](CITATION.cff) and cite the original
experimental and nuclear-model sources listed in [SOURCES.md](SOURCES.md).
