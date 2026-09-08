# Data Sources and Conventions

## Nuclear-Data Inputs

- `inputs/iaea_livechart_ground_states.csv` and
  `inputs/iaea_livechart_gammas.csv` are frozen extracts from the
  [IAEA LiveChart](https://www-nds.iaea.org/relnsd/vcharthtml/VChartHTML.html).
  The extraction dates are retained in the CSV columns.
- `inputs/ame2020.csv` is the AME2020 mass evaluation. Cite W. J. Huang et
  al., *Chinese Physics C* **45**, 030002 (2021),
  [doi:10.1088/1674-1137/abddb0](https://doi.org/10.1088/1674-1137/abddb0),
  and M. Wang et al., *Chinese Physics C* **45**, 030003 (2021),
  [doi:10.1088/1674-1137/abddaf](https://doi.org/10.1088/1674-1137/abddaf).
  Entries marked as systematic estimates are retained in the auxiliary tasks.
- `inputs/nndc_adopted_be2.csv` contains the adopted first-`2+` transition
  table used in the campaign. Cite B. Pritychenko et al., *Atomic Data and
  Nuclear Data Tables* **107**, 1 (2016),
  [doi:10.1016/j.adt.2015.10.001](https://doi.org/10.1016/j.adt.2015.10.001).
  The frozen source encodes the `146Sm` lower uncertainty with a minus sign;
  the standardized `training_measurement_unc_e2_b2` column reports its
  positive magnitude.
  For the 408 retained nuclei covered by this table, the tabulated upward
  strengths and uncertainties are divided by five to obtain downward
  `B(E2; 2+ -> 0+)` values.
- The remaining 24 released targets use the transition from the lowest listed
  first-`2+` level (including tentative `(2+)` assignments) to the `0+` ground
  state (`end_level_energy = 0`) in `inputs/iaea_livechart_gammas.csv`.
  LiveChart strengths in Weisskopf units are converted with
  `B(E2) [e^2 b^2] = B(E2) [W.u.] * 0.0594 * A^(4/3) * 1e-4`.
  The complete released target set contains 427 even-even and five odd-odd
  nuclei, all with `0+` ground states.
  `98Zr` is retained in the frozen LiveChart extract but excluded from the
  derived release tables because the frozen ensemble had been fine-tuned using
  its branch to an excited `0+` state rather than its ground-state branch.

## External Measurements

- The calcium table combines R. F. Garcia Ruiz et al., *Nature Physics* **12**,
  594 (2016), [doi:10.1038/nphys3645](https://doi.org/10.1038/nphys3645), and
  A. J. Miller et al., *Nature Physics* **15**, 432 (2019),
  [doi:10.1038/s41567-019-0416-9](https://doi.org/10.1038/s41567-019-0416-9).
  The source DOI is repeated on each CSV row.
- The promethium isotope shifts are from D. Studer et al., *European Physical
  Journal A* **56**, 69 (2020),
  [doi:10.1140/epja/s10050-020-00061-8](https://doi.org/10.1140/epja/s10050-020-00061-8).
  Absolute radii in the comparison table use the NuCLR `147Pm` prediction as a
  common anchor; the experimental observable is the isotope shift.

## Nuclear-Model Predictions

- `models/5dch_predictions.csv` is standardized from the table accompanying
  J.-P. Delaroche et al., *Physical Review C* **81**, 014303 (2010),
  [doi:10.1103/PhysRevC.81.014303](https://doi.org/10.1103/PhysRevC.81.014303),
  distributed through the
  [AMEDEE database](https://www-phynu.cea.fr/science_en_ligne/carte_potentiels_microscopiques/carte_potentiel_nucleaire_eng.htm).
  The source `B(E2; 2+ -> 0+)` column is numerically in `e^2 fm^4` and is
  multiplied by `1e-4` to obtain `e^2 b^2`.
- `models/bskg3_predictions.csv` is standardized from the supplemental table
  accompanying G. Grams et al., *European Physical Journal A* **59**, 270
  (2023),
  [doi:10.1140/epja/s10050-023-01158-6](https://doi.org/10.1140/epja/s10050-023-01158-6).
  Charge radii are direct table entries. The downward `B(E2; 2+ -> 0+)` values
  are computed directly from the tabulated `beta2` using the rigid-rotor
  relation stated in the manuscript; they are not transcribed from a source
  transition-strength table.

## NuCLR Tables

The NuCLR tables contain the predictions used in the manuscript, including the
structure-dependent gradient-boosted residual-scale intervals. The central
predictions and interval semantics are defined in the manuscript and summarized
in `README.md`. The target-only STL tables are reference OOF campaigns; the
`B(E2)` STL campaign predates the final stratified, weighted MTL protocol and is
not a strictly matched ablation.
