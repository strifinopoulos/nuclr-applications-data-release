#!/usr/bin/env python3
"""Reproduce the post-hoc NuCLR interval analysis from frozen predictions.

This script does not train NuCLR. It fits the residual-scale GBMs described in
the paper, applies the frozen random and regional splits, reconstructs the
released interval widths, and checks the reported diagnostics.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor


ROOT = Path(__file__).resolve().parents[1]
MAGIC = np.array([2, 8, 20, 28, 50, 82, 126, 184], dtype=float)

CONFIG = {
    "charge_radius": {
        "table": ROOT / "tables" / "nuclr_charge_radii.csv",
        "truth": "training_measurement_fm",
        "prediction": "nuclr_prediction_fm",
        "released68": "interval68_half_width_fm",
        "released95": "interval95_half_width_fm",
    },
    "be2": {
        "table": ROOT / "tables" / "nuclr_be2.csv",
        "truth": "training_measurement_e2_b2",
        "prediction": "nuclr_prediction_e2_b2",
        "released68": "interval68_half_width_e2_b2",
        "released95": "interval95_half_width_e2_b2",
    },
}


def z_stable(a: np.ndarray) -> np.ndarray:
    return a / (1.98 + 0.0155 * np.cbrt(a) ** 2)


def structure_features(z: np.ndarray, n: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=float)
    n = np.asarray(n, dtype=float)
    a = z + n
    dz_magic = np.min(np.abs(z[:, None] - MAGIC[None, :]), axis=1)
    dn_magic = np.min(np.abs(n[:, None] - MAGIC[None, :]), axis=1)
    return np.stack(
        [
            z / 100,
            n / 150,
            a / 250,
            z % 2,
            n % 2,
            (z % 2) * (n % 2),
            np.abs(n - z) / a,
            (n - z) / 50,
            dz_magic / 20,
            dn_magic / 20,
            np.minimum(dz_magic, dn_magic) / 20,
            (z - z_stable(a)) / 10,
        ],
        axis=1,
    )


def finite_sample_quantile(scores: np.ndarray, level: float) -> float:
    ordered = np.sort(np.asarray(scores, dtype=float))
    rank = int(math.ceil((len(ordered) + 1) * level))
    if rank > len(ordered):
        raise ValueError(
            f"Calibration fold of size {len(ordered)} cannot resolve level {level}."
        )
    return float(ordered[rank - 1])


def grid_miscalibration(
    z: np.ndarray,
    n: np.ndarray,
    residual: np.ndarray,
    width: np.ndarray,
    *,
    cell_size: int = 8,
    min_cell: int = 8,
) -> float:
    translated_scores = []
    for offset_z in range(cell_size):
        for offset_n in range(cell_size):
            cell_coverages = []
            for z0 in range(-offset_z, 122, cell_size):
                for n0 in range(-offset_n, 182, cell_size):
                    mask = (
                        (z >= z0)
                        & (z < z0 + cell_size)
                        & (n >= n0)
                        & (n < n0 + cell_size)
                    )
                    if mask.sum() >= min_cell:
                        cell_coverages.append(
                            np.mean(np.abs(residual[mask]) <= width[mask])
                        )
            if cell_coverages:
                translated_scores.append(
                    np.sqrt(
                        np.mean((np.asarray(cell_coverages, dtype=float) - 0.68) ** 2)
                    )
                )
    return float(np.mean(translated_scores))


def load_folds(observable: str, mode: str, measured: pd.DataFrame) -> dict[int, np.ndarray]:
    path = ROOT / "splits" / f"{mode}_folds.csv"
    splits = pd.read_csv(path)
    splits = splits[splits["observable"].eq(observable)].copy()
    keys = measured[["z", "n"]].copy()
    result = {}
    for seed, part in splits.groupby("partition_seed"):
        merged = keys.merge(
            part[["z", "n", "fold"]],
            on=["z", "n"],
            how="left",
            validate="one_to_one",
        )
        if merged["fold"].isna().any():
            raise RuntimeError(f"Missing {mode} fold assignments for {observable}.")
        result[int(seed)] = merged["fold"].to_numpy(dtype=int)
    return result


def fit_scale(
    x: np.ndarray,
    residual: np.ndarray,
    train_idx: np.ndarray,
    random_state: int,
) -> GradientBoostingRegressor:
    rms = float(np.sqrt(np.mean(residual**2)))
    residual_floor = max(rms * 1.0e-4, 1.0e-12)
    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=2,
        learning_rate=0.05,
        subsample=0.8,
        random_state=random_state,
    )
    model.fit(
        x[train_idx],
        np.log(np.maximum(np.abs(residual[train_idx]), residual_floor)),
    )
    return model


def reconstruct_random_intervals(
    observable: str,
    full: pd.DataFrame,
    measured: pd.DataFrame,
    measured_full_idx: np.ndarray,
    residual: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict]:
    x_measured = structure_features(measured["z"], measured["n"])
    x_full = structure_features(full["z"], full["n"])
    folds = load_folds(observable, "random", measured)
    all_widths68 = []
    all_widths95 = []
    heldout68 = [[] for _ in range(len(measured))]
    heldout95 = [[] for _ in range(len(measured))]
    local_scores = []

    for seed, fold in sorted(folds.items()):
        cyclic_width68 = np.full(len(measured), np.nan)
        for test_fold in range(5):
            for cal_fold in range(5):
                if cal_fold == test_fold:
                    continue
                train_idx = np.flatnonzero((fold != test_fold) & (fold != cal_fold))
                cal_idx = np.flatnonzero(fold == cal_fold)
                test_idx = np.flatnonzero(fold == test_fold)
                random_state = seed * 1000 + test_fold * 100 + cal_fold * 10 + 2
                model = fit_scale(x_measured, residual, train_idx, random_state)
                cal_scale = np.exp(model.predict(x_measured[cal_idx]))
                cal_score = np.abs(residual[cal_idx]) / np.maximum(cal_scale, 1e-12)
                q68 = finite_sample_quantile(cal_score, 0.68)
                q95 = finite_sample_quantile(cal_score, 0.95)
                full_scale = np.exp(model.predict(x_full))
                width68 = q68 * full_scale
                width95 = q95 * full_scale
                all_widths68.append(width68)
                all_widths95.append(width95)
                for row, value68, value95 in zip(
                    test_idx,
                    width68[measured_full_idx[test_idx]],
                    width95[measured_full_idx[test_idx]],
                ):
                    heldout68[int(row)].append(float(value68))
                    heldout95[int(row)].append(float(value95))
                if cal_fold == (test_fold + 1) % 5:
                    cyclic_width68[test_idx] = width68[measured_full_idx[test_idx]]
        if np.isnan(cyclic_width68).any():
            raise RuntimeError(f"Incomplete cyclic prediction set for {observable}, seed {seed}.")
        local_scores.append(
            grid_miscalibration(
                measured["z"].to_numpy(int),
                measured["n"].to_numpy(int),
                residual,
                cyclic_width68,
            )
        )

    result68 = np.median(np.vstack(all_widths68), axis=0)
    result95 = np.median(np.vstack(all_widths95), axis=0)
    for row, full_idx in enumerate(measured_full_idx):
        if len(heldout68[row]) != 20 or len(heldout95[row]) != 20:
            raise RuntimeError(f"Expected 20 held-out widths for {observable} row {row}.")
        result68[full_idx] = np.median(heldout68[row])
        result95[full_idx] = np.median(heldout95[row])

    measured68 = result68[measured_full_idx]
    measured95 = result95[measured_full_idx]
    diagnostics = {
        "random_coverage68": float(np.mean(np.abs(residual) <= measured68)),
        "random_coverage95": float(np.mean(np.abs(residual) <= measured95)),
        "local_score68": float(np.mean(local_scores)),
        "local_score68_partition_sd": float(np.std(local_scores, ddof=1)),
    }
    return result68, result95, diagnostics


def regional_diagnostics(
    observable: str,
    measured: pd.DataFrame,
    residual: np.ndarray,
) -> dict:
    x = structure_features(measured["z"], measured["n"])
    folds = load_folds(observable, "regional", measured)
    coverage68 = []
    coverage95 = []

    for seed, fold in sorted(folds.items()):
        widths68 = np.full(len(measured), np.nan)
        widths95 = np.full(len(measured), np.nan)
        for test_fold in range(5):
            cal_fold = (test_fold + 1) % 5
            train_idx = np.flatnonzero((fold != test_fold) & (fold != cal_fold))
            cal_idx = np.flatnonzero(fold == cal_fold)
            test_idx = np.flatnonzero(fold == test_fold)
            random_state = seed * 1000 + test_fold * 100 + cal_fold * 10 + 2
            model = fit_scale(x, residual, train_idx, random_state)
            cal_scale = np.exp(model.predict(x[cal_idx]))
            cal_score = np.abs(residual[cal_idx]) / np.maximum(cal_scale, 1e-12)
            widths68[test_idx] = finite_sample_quantile(cal_score, 0.68) * np.exp(
                model.predict(x[test_idx])
            )
            widths95[test_idx] = finite_sample_quantile(cal_score, 0.95) * np.exp(
                model.predict(x[test_idx])
            )
        coverage68.append(float(np.mean(np.abs(residual) <= widths68)))
        coverage95.append(float(np.mean(np.abs(residual) <= widths95)))

    return {
        "regional_coverage68": float(np.mean(coverage68)),
        "regional_coverage68_partition_sd": float(np.std(coverage68, ddof=1)),
        "regional_coverage95": float(np.mean(coverage95)),
        "regional_coverage95_partition_sd": float(np.std(coverage95, ddof=1)),
    }


def reproduce_observable(observable: str, output_dir: Path) -> dict:
    cfg = CONFIG[observable]
    full = pd.read_csv(cfg["table"])
    residual_table = pd.read_csv(ROOT / "inputs" / "uncertainty_oof_residuals.csv")
    measured = residual_table[residual_table["observable"].eq(observable)].copy()
    measured = measured.reset_index(drop=True)
    indexed_full = full.reset_index(names="full_index")
    measured_keys = measured[["z", "n"]].merge(
        indexed_full[["z", "n", "full_index"]],
        on=["z", "n"],
        how="left",
        validate="one_to_one",
    )
    if measured_keys["full_index"].isna().any():
        raise RuntimeError(f"Missing released rows for {observable} OOF residuals.")
    measured_full_idx = measured_keys["full_index"].to_numpy(dtype=int)
    # Recompute after parsing the two frozen columns, matching the production
    # script's floating-point operation exactly.
    residual = (
        measured["oof_prediction"].to_numpy(float)
        - measured["measurement"].to_numpy(float)
    )

    width68, width95, diagnostics = reconstruct_random_intervals(
        observable, full, measured, measured_full_idx, residual
    )
    diagnostics.update(regional_diagnostics(observable, measured, residual))
    diagnostics["observable"] = observable
    diagnostics["n_measured"] = int(len(measured))
    diagnostics["random_coverage68_binomial_se"] = math.sqrt(
        diagnostics["random_coverage68"]
        * (1.0 - diagnostics["random_coverage68"])
        / len(measured)
    )
    diagnostics["random_coverage95_binomial_se"] = math.sqrt(
        diagnostics["random_coverage95"]
        * (1.0 - diagnostics["random_coverage95"])
        / len(measured)
    )
    diagnostics["max_abs_difference_from_released_width68"] = float(
        np.max(np.abs(width68 - full[cfg["released68"]].to_numpy(float)))
    )
    diagnostics["max_abs_difference_from_released_width95"] = float(
        np.max(np.abs(width95 - full[cfg["released95"]].to_numpy(float)))
    )

    reproduced = full[["z", "n", cfg["prediction"], cfg["truth"]]].copy()
    reproduced["reproduced_interval68_half_width"] = width68
    reproduced["reproduced_interval95_half_width"] = width95
    reproduced.to_csv(output_dir / f"{observable}_reproduced_intervals.csv", index=False)
    return diagnostics


def verify_metrics(results: pd.DataFrame) -> None:
    expected = pd.read_csv(ROOT / "tables" / "uncertainty_validation.csv")
    numeric = [column for column in expected.columns if column not in {"observable"}]
    merged = expected.merge(results, on="observable", suffixes=("_expected", "_actual"))
    failures = []
    for column in numeric:
        expected_values = merged[f"{column}_expected"].to_numpy(float)
        actual_values = merged[f"{column}_actual"].to_numpy(float)
        difference = np.abs(expected_values - actual_values)
        tolerance = 5.0e-5
        if np.any(difference > tolerance):
            failures.append(
                f"{column}: max difference {difference.max():.6g} exceeds {tolerance}"
            )
    for level in (68, 95):
        column = f"max_abs_difference_from_released_width{level}"
        if (results[column] > 5.0e-7).any():
            failures.append(
                f"released {level}% widths: max difference {results[column].max():.6g}"
            )
    if failures:
        raise RuntimeError("Reproduction checks failed:\n- " + "\n- ".join(failures))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reproduced",
        help="Directory for regenerated intervals and diagnostics.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        reproduce_observable(observable, args.output_dir)
        for observable in CONFIG
    ]
    results = pd.DataFrame(rows)
    verify_metrics(results)
    results.to_csv(args.output_dir / "uncertainty_validation_reproduced.csv", index=False)
    (args.output_dir / "uncertainty_validation_reproduced.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8"
    )
    print(results.to_string(index=False))
    print("All uncertainty reproduction checks passed.")


if __name__ == "__main__":
    main()
