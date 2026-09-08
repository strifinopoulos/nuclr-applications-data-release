#!/usr/bin/env python3
"""Regenerate the manuscript chain plots from the public release tables."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
COLORS = {
    "nuclr": "#d95f02",
    "5dch": "#2a9d8f",
    "bskg3": "#6c5ce7",
    "data": "#111111",
}

REFERENCE_N = {
    ("radii", 20): 24,
    ("radii", 28): 33,
    ("radii", 50): 70,
    ("radii", 62): 84,
    ("radii", 80): 113,
    ("radii", 82): 116,
    ("be2", 40): 54,
    ("be2", 50): 68,
    ("be2", 54): 74,
    ("be2", 62): 82,
    ("be2", 84): 118,
    ("be2", 90): 138,
    ("be2", 92): 142,
}


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "legend.fontsize": 6.8,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "axes.linewidth": 0.8,
            "savefig.dpi": 250,
        }
    )


def load_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    radii = pd.read_csv(ROOT / "tables" / "nuclr_charge_radii.csv")
    be2 = pd.read_csv(ROOT / "tables" / "nuclr_be2.csv")
    if not (be2["ground_state_spin"].eq(0) & be2["ground_state_parity"].eq(1)).all():
        raise RuntimeError("The released B(E2) table must contain only 0+ ground states.")
    d5 = pd.read_csv(ROOT / "models" / "5dch_predictions.csv")
    bskg3 = pd.read_csv(ROOT / "models" / "bskg3_predictions.csv")
    return radii, be2, d5, bskg3


def decorate(ax: plt.Axes) -> None:
    ax.grid(color="0.90", linewidth=0.45)
    ax.tick_params(direction="in", top=True, right=True)


def plot_chain(
    top: plt.Axes,
    delta: plt.Axes,
    data: pd.DataFrame,
    d5: pd.DataFrame,
    bskg3: pd.DataFrame,
    z: int,
    *,
    observable: str,
) -> None:
    if observable == "radii":
        prediction = "nuclr_prediction_fm"
        truth = "training_measurement_fm"
        truth_unc = "training_measurement_unc_fm"
        lower = "interval68_lower_fm"
        upper = "interval68_upper_fm"
        model_value = "charge_radius_fm"
        ylabel = r"$R_{\rm ch}$ [fm]"
        delta_ylabel = r"$\Delta R_{\rm ch}$ [fm]"
    else:
        prediction = "nuclr_prediction_e2_b2"
        truth = "training_measurement_e2_b2"
        truth_unc = "training_measurement_unc_e2_b2"
        lower = "interval68_lower_e2_b2"
        upper = "interval68_upper_e2_b2"
        model_value = "be2_down_e2_b2"
        ylabel = r"$B(E2)$ [$e^2{\rm b}^2$]"
        delta_ylabel = r"$\Delta B(E2)$"

    chain = data[data["z"].eq(z)].sort_values("n")
    measured = chain[chain[truth].notna()]
    open_points = chain[chain[truth].isna()]
    top.errorbar(
        measured["n"],
        measured[truth],
        yerr=measured[truth_unc].abs(),
        fmt="o",
        ms=3.0,
        color=COLORS["data"],
        capsize=1.7,
        lw=0.7,
        label="data",
        zorder=5,
    )
    top.errorbar(
        measured["n"],
        measured[prediction],
        yerr=np.vstack(
            [
                measured[prediction] - measured[lower],
                measured[upper] - measured[prediction],
            ]
        ),
        fmt="s",
        ms=2.8,
        color=COLORS["nuclr"],
        capsize=1.7,
        lw=0.75,
        label="NuCLR (OOF)",
        zorder=4,
    )
    top.errorbar(
        open_points["n"],
        open_points[prediction],
        yerr=np.vstack(
            [
                open_points[prediction] - open_points[lower],
                open_points[upper] - open_points[prediction],
            ]
        ),
        fmt="s",
        ms=3.0,
        mfc="white",
        mec=COLORS["nuclr"],
        ecolor=COLORS["nuclr"],
        capsize=1.7,
        lw=0.75,
        label="NuCLR (open)",
        zorder=3,
    )

    reference_n = REFERENCE_N[(observable, z)]
    reference_row = chain[chain["n"].eq(reference_n)]
    if len(reference_row) != 1:
        raise RuntimeError(f"Missing NuCLR reference N={reference_n} for Z={z}.")
    reference_prediction = float(reference_row[prediction].iloc[0])
    delta.plot(
        chain["n"],
        chain[prediction] - reference_prediction,
        color=COLORS["nuclr"],
        linewidth=1.15,
    )

    model_specs = [
        (d5, "5DCH", COLORS["5dch"], "--"),
        (bskg3, "BSkG3", COLORS["bskg3"], "-."),
    ]
    for model, label, color, linestyle in model_specs:
        model_chain = model[model["z"].eq(z) & model[model_value].notna()].sort_values("n")
        model_chain = model_chain[
            model_chain["n"].between(int(chain["n"].min()), int(chain["n"].max()))
        ]
        top.plot(
            model_chain["n"],
            model_chain[model_value],
            color=color,
            linestyle=linestyle,
            linewidth=1.0,
            label=label,
        )
        reference_value = np.interp(
            reference_n,
            model_chain["n"].to_numpy(float),
            model_chain[model_value].to_numpy(float),
        )
        delta.plot(
            model_chain["n"],
            model_chain[model_value] - reference_value,
            color=color,
            linestyle=linestyle,
            linewidth=0.95,
        )

    if observable == "radii":
        external = chain[chain["external_measurement_fm"].notna()]
        if len(external):
            top.errorbar(
                external["n"],
                external["external_measurement_fm"],
                yerr=external["external_measurement_unc_fm"],
                fmt="o",
                ms=3.0,
                color=COLORS["data"],
                capsize=1.7,
                lw=0.7,
                zorder=6,
            )

    symbol = str(chain["symbol"].dropna().iloc[0]) if len(chain) else f"Z={z}"
    top.set_title(f"{symbol} ($Z={z}$)")
    top.set_ylabel(ylabel)
    delta.set_ylabel(delta_ylabel)
    delta.set_xlabel(r"Neutron number $N$")
    delta.axhline(0.0, color="0.55", linewidth=0.55)
    delta.axvline(reference_n, color="0.60", linestyle=":", linewidth=0.65)
    delta.text(
        0.98,
        0.88,
        rf"$N_{{\rm ref}}={reference_n}$",
        transform=delta.transAxes,
        ha="right",
        va="top",
        color="0.40",
        fontsize=7.0,
    )
    decorate(top)
    decorate(delta)


def chain_figure(
    output: Path,
    data: pd.DataFrame,
    d5: pd.DataFrame,
    bskg3: pd.DataFrame,
    zs: list[int],
    *,
    observable: str,
    ncols: int,
) -> None:
    nrows = int(np.ceil(len(zs) / ncols))
    fig = plt.figure(figsize=(3.25 * ncols, 3.55 * nrows))
    outer = fig.add_gridspec(nrows, ncols, hspace=0.58, wspace=0.38)
    axes = []
    for index, z in enumerate(zs):
        row, col = divmod(index, ncols)
        inner = outer[row, col].subgridspec(2, 1, height_ratios=[3.0, 1.0], hspace=0.08)
        top = fig.add_subplot(inner[0])
        delta = fig.add_subplot(inner[1], sharex=top)
        plt.setp(top.get_xticklabels(), visible=False)
        plot_chain(top, delta, data, d5, bskg3, z, observable=observable)
        axes.append(top)
    for index in range(len(zs), nrows * ncols):
        row, col = divmod(index, ncols)
        blank = fig.add_subplot(outer[row, col])
        blank.axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=min(5, len(labels)),
        frameon=False,
        bbox_to_anchor=(0.5, 0.012),
    )
    bottom = 0.20 if nrows == 1 else 0.11
    fig.subplots_adjust(left=0.08, right=0.985, top=0.94, bottom=bottom)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def promethium_figure(output: Path, radii: pd.DataFrame, bskg3: pd.DataFrame) -> None:
    pm = radii[radii["z"].eq(61)].sort_values("n")
    shifts = pd.read_csv(ROOT / "tables" / "promethium_isotope_shifts.csv")
    reference_n = 86
    reference_radius = float(pm.loc[pm["n"].eq(reference_n), "nuclr_prediction_fm"].iloc[0])
    model = bskg3[bskg3["z"].eq(61) & bskg3["charge_radius_fm"].notna()].copy()
    model_ref = float(model.loc[model["n"].eq(reference_n), "charge_radius_fm"].iloc[0])
    model["aligned"] = np.sqrt(
        reference_radius**2 + model["charge_radius_fm"] ** 2 - model_ref**2
    )

    fig, ax = plt.subplots(figsize=(3.35, 3.0))
    ax.errorbar(
        pm["n"],
        pm["nuclr_prediction_fm"],
        yerr=pm["interval68_half_width_fm"],
        fmt="s",
        ms=3.0,
        mfc="white",
        mec=COLORS["nuclr"],
        ecolor=COLORS["nuclr"],
        capsize=1.8,
        lw=0.75,
        label="NuCLR (open)",
    )
    ax.plot(
        model["n"], model["aligned"], color=COLORS["bskg3"], linestyle="-.",
        linewidth=1.0, label="BSkG3 (aligned)"
    )
    lower = shifts["radius_aligned"] - shifts["radius_low"]
    upper = shifts["radius_high"] - shifts["radius_aligned"]
    ax.errorbar(
        shifts["n"],
        shifts["radius_aligned"],
        yerr=np.vstack([lower, upper]),
        fmt="o",
        ms=3.4,
        color=COLORS["data"],
        capsize=1.8,
        lw=0.75,
        label="isotope shifts (aligned)",
    )
    ax.axvline(reference_n, color="0.6", linestyle=":", linewidth=0.7)
    ax.set_title(r"Promethium ($Z=61$)")
    ax.set_xlabel(r"Neutron number $N$")
    ax.set_ylabel(r"$R_{\rm ch}$ [fm]")
    ax.legend(frameon=False)
    decorate(ax)
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reproduced" / "figures")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    style()
    radii, be2, d5, bskg3 = load_tables()
    chain_figure(
        args.output_dir / "paper_radii_main_gbm.png",
        radii, d5, bskg3, [28, 62, 82], observable="radii", ncols=3,
    )
    chain_figure(
        args.output_dir / "paper_be2_main_gbm_main_new.png",
        be2, d5, bskg3, [62, 84, 92], observable="be2", ncols=3,
    )
    chain_figure(
        args.output_dir / "appendix_radii_other_a_gbm.png",
        radii, d5, bskg3, [20, 50, 80], observable="radii", ncols=3,
    )
    chain_figure(
        args.output_dir / "appendix_be2_other_a_gbm_main_new.png",
        be2, d5, bskg3, [40, 50, 54, 90], observable="be2", ncols=2,
    )
    promethium_figure(
        args.output_dir / "radii_Pm_cv_uncertainty_gbm.png", radii, bskg3
    )
    print(f"Wrote five figure files to {args.output_dir}")


if __name__ == "__main__":
    main()
