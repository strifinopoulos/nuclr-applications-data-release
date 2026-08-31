# NuCLR Applications Data

Data release for *Learning Nuclear Structure with AI: Radii and Collectivity*.

This repository is private staging material. It is intended to be made public
with the manuscript submission. It contains data tables only; model-training
and figure-generation code are maintained separately.

## Contents

| Path | Description |
|---|---|
| `tables/nuclr_charge_radii.csv` | NuCLR charge-radius predictions for 3,231 nuclei, adopted training measurements, external calcium measurements, and 68%/95% interval columns. |
| `tables/nuclr_be2.csv` | NuCLR downward `B(E2; 2+ -> 0+)` predictions for the 991 nuclei in the prediction table with a `0+` ground state, with measurements and interval columns. |
| `tables/stl_charge_radii_oof.csv` | Measured-target OOF predictions from the target-only radius reference campaign. |
| `tables/stl_be2_oof.csv` | Measured-target OOF predictions from the target-only `B(E2)` reference campaign. |
| `tables/promethium_isotope_shifts.csv` | Published `143-147Pm` isotope shifts and the aligned NuCLR comparison used in the supplement. |
| `tables/uncertainty_validation.csv` | Aggregate random-fold and contiguous-region interval diagnostics reported in Table S1. |
| `models/5dch_predictions.csv` | Standardized 5DCH charge-radius and downward-`B(E2)` predictions. |
| `models/bskg3_predictions.csv` | Standardized BSkG3 charge radii, deformations, and derived downward-`B(E2)` values. |
| `inputs/` | Frozen input tables used by the campaigns. |
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

`nuclr_seed_std_*` records the spread of the corresponding central-prediction
ensemble. It is diagnostic information and is not added to the calibrated
interval half-width.

## Measurements and Units

- Charge radii are in fm.
- `B(E2)` values are downward transition strengths in `e^2 b^2`.
- `training_measurement_*` contains the target table used by NuCLR.
- The six calcium measurements in `external_measurement_*` were absent from
  the frozen training table and are retained separately as external data.
- Blank CSV fields mean that the quantity is unavailable for that nucleus.

See [SOURCES.md](SOURCES.md) for provenance, conversions, and citations.

## Citation

Until the accompanying paper has a final citation or DOI, cite this repository
using [CITATION.cff](CITATION.cff) and cite the original experimental and
nuclear-model sources listed in [SOURCES.md](SOURCES.md).

