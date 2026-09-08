#!/usr/bin/env python3
"""Verify release checksums, row semantics, and central-prediction metrics."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "charge_radius_mtl_oof_rms": 0.014671871877824877,
    "be2_mtl_oof_rms": 0.1924778379947288,
    "charge_radius_stl_oof_rms": 0.07600884500180767,
    "be2_stl_oof_rms": 0.2955185541512647,
}


def rms(frame: pd.DataFrame, truth: str, prediction: str) -> float:
    residual = frame[prediction].to_numpy(float) - frame[truth].to_numpy(float)
    return float(np.sqrt(np.mean(residual**2)))


def verify_manifest() -> None:
    manifest = pd.read_csv(ROOT / "MANIFEST.csv")
    failures = []
    for row in manifest.itertuples(index=False):
        path = ROOT / row.path
        if not path.exists():
            failures.append(f"missing: {row.path}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != row.sha256:
            failures.append(f"checksum: {row.path}")
    if failures:
        raise RuntimeError("Manifest verification failed: " + ", ".join(failures))


def verify_livechart_be2_targets(be2_table: pd.DataFrame) -> None:
    """Check the 24 retained LiveChart targets against the intended branch."""
    nndc = pd.read_csv(ROOT / "inputs" / "nndc_adopted_be2.csv")
    nndc_keys = set(zip(nndc["z"], nndc["n"]))
    measured = be2_table[be2_table["training_measurement_e2_b2"].notna()].copy()
    livechart_targets = measured[
        ~pd.MultiIndex.from_frame(measured[["z", "n"]]).isin(nndc_keys)
    ]
    if len(livechart_targets) != 24:
        raise RuntimeError(
            f"Expected 24 LiveChart-derived B(E2) targets, found {len(livechart_targets)}."
        )
    if ((be2_table["z"] == 40) & (be2_table["n"] == 58)).any():
        raise RuntimeError("98Zr must be excluded from the derived B(E2) release.")

    gammas = pd.read_csv(ROOT / "inputs" / "iaea_livechart_gammas.csv")
    normalized_start_jp = gammas["start_level_jp"].str.replace(
        r"[()]", "", regex=True
    )
    candidates = gammas[
        normalized_start_jp.eq("2+")
        & gammas["end_level_jp"].eq("0+")
        & gammas["end_level_energy"].eq(0)
        & gammas["b_e2"].notna()
    ].copy()
    candidates = candidates.sort_values("start_level_energy").drop_duplicates(
        ["z", "n"], keep="first"
    )
    comparison = livechart_targets.merge(
        candidates[["z", "n", "b_e2"]], on=["z", "n"], how="left", validate="one_to_one"
    )
    if comparison["b_e2"].isna().any():
        missing = comparison.loc[comparison["b_e2"].isna(), ["z", "n"]].to_dict(
            "records"
        )
        raise RuntimeError(f"Missing LiveChart ground-state transitions: {missing}")
    converted = comparison["b_e2"] * 0.0594 * comparison["a"] ** (4.0 / 3.0) * 1.0e-4
    if not np.allclose(
        comparison["training_measurement_e2_b2"], converted, rtol=0.0, atol=1.0e-10
    ):
        bad = comparison.loc[
            ~np.isclose(
                comparison["training_measurement_e2_b2"],
                converted,
                rtol=0.0,
                atol=1.0e-10,
            ),
            ["z", "n"],
        ].to_dict("records")
        raise RuntimeError(f"LiveChart B(E2) branch/conversion mismatch: {bad}")


def main() -> None:
    verify_manifest()
    residuals = pd.read_csv(ROOT / "inputs" / "uncertainty_oof_residuals.csv")
    radius = residuals[residuals["observable"].eq("charge_radius")]
    be2 = residuals[residuals["observable"].eq("be2")]
    stl_radius = pd.read_csv(ROOT / "tables" / "stl_charge_radii_oof.csv")
    stl_be2 = pd.read_csv(ROOT / "tables" / "stl_be2_oof.csv")
    actual = {
        "charge_radius_mtl_oof_rms": rms(radius, "measurement", "oof_prediction"),
        "be2_mtl_oof_rms": rms(be2, "measurement", "oof_prediction"),
        "charge_radius_stl_oof_rms": rms(
            stl_radius, "measurement_fm", "stl_oof_prediction_fm"
        ),
        "be2_stl_oof_rms": rms(
            stl_be2, "measurement_e2_b2", "stl_oof_prediction_e2_b2"
        ),
    }
    for name, expected in EXPECTED.items():
        if not np.isclose(actual[name], expected, rtol=0.0, atol=1.0e-12):
            raise RuntimeError(f"{name}: expected {expected}, obtained {actual[name]}")

    radii = pd.read_csv(ROOT / "tables" / "nuclr_charge_radii.csv")
    be2_table = pd.read_csv(ROOT / "tables" / "nuclr_be2.csv")
    verify_livechart_be2_targets(be2_table)
    counts = {
        "charge_radius_rows": int(len(radii)),
        "charge_radius_measured_oof_rows": int(
            radii["nuclr_prediction_kind"].eq("measured_target_oof_4_models").sum()
        ),
        "charge_radius_open_rows": int(
            radii["nuclr_prediction_kind"].eq("unmeasured_target_40_models").sum()
        ),
        "be2_rows": int(len(be2_table)),
        "be2_measured_oof_rows": int(
            be2_table["nuclr_prediction_kind"].eq("measured_target_oof_4_models").sum()
        ),
        "be2_open_rows": int(
            be2_table["nuclr_prediction_kind"].eq("unmeasured_target_40_models").sum()
        ),
    }
    expected_counts = {
        "charge_radius_rows": 3231,
        "charge_radius_measured_oof_rows": 868,
        "charge_radius_open_rows": 2363,
        "be2_rows": 830,
        "be2_measured_oof_rows": 432,
        "be2_open_rows": 398,
    }
    if counts != expected_counts:
        raise RuntimeError(f"Prediction-kind counts changed: {counts}")

    valid_be2_support = be2_table["ground_state_spin"].eq(0) & be2_table[
        "ground_state_parity"
    ].eq(1)
    if not valid_be2_support.all():
        raise RuntimeError("B(E2) release contains nuclei without a 0+ ground state.")
    composition = {
        "even_even": int(((be2_table["z"] % 2 == 0) & (be2_table["n"] % 2 == 0)).sum()),
        "odd_odd": int(((be2_table["z"] % 2 == 1) & (be2_table["n"] % 2 == 1)).sum()),
    }
    if composition != {"even_even": 808, "odd_odd": 22}:
        raise RuntimeError(f"B(E2) support composition changed: {composition}")
    measured_be2 = be2_table[be2_table["training_measurement_e2_b2"].notna()]
    measured_composition = {
        "even_even": int(
            (measured_be2["z"].mod(2).eq(0) & measured_be2["n"].mod(2).eq(0)).sum()
        ),
        "odd_odd": int(
            (measured_be2["z"].mod(2).eq(1) & measured_be2["n"].mod(2).eq(1)).sum()
        ),
    }
    if measured_composition != {"even_even": 427, "odd_odd": 5}:
        raise RuntimeError(
            f"Measured B(E2) support composition changed: {measured_composition}"
        )
    even_even_measured = measured_be2[
        measured_be2["z"].mod(2).eq(0) & measured_be2["n"].mod(2).eq(0)
    ]

    def multiplicative_tail(frame: pd.DataFrame) -> float:
        ratio = frame["nuclr_prediction_e2_b2"] / frame["training_measurement_e2_b2"]
        return float(np.exp(np.quantile(np.abs(np.log(ratio)), 0.95)))

    tail_diagnostics = {
        "be2_all_432_multiplicative_95pct": multiplicative_tail(measured_be2),
        "be2_even_even_427_multiplicative_95pct": multiplicative_tail(
            even_even_measured
        ),
    }
    print(
        json.dumps(
            {
                "rms": actual,
                "counts": counts,
                "be2_composition": composition,
                "be2_measured_composition": measured_composition,
                "tail_diagnostics": tail_diagnostics,
            },
            indent=2,
        )
    )
    print("All release checks passed.")


if __name__ == "__main__":
    main()
