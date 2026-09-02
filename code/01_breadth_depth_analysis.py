from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = ROOT / "data" / "derived" / "analytical_panel_2000_2024.csv"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

COUNTRIES = 19
BOOTSTRAP_REPLICATIONS = 20_000
BOOTSTRAP_SEED = 20260902
THRESHOLDS = {
    "primary": 0.0,
    "threshold_010": 0.001,
    "threshold_025": 0.0025,
}


def _safe_balance(positive_side: float, negative_side: float) -> float:
    denominator = positive_side + negative_side
    return (positive_side - negative_side) / denominator if denominator > 0 else np.nan


def _is_direction_reversal(country_balance: float, physical_balance: float) -> bool:
    """Return True only when the two balances have strictly opposite signs."""
    return bool(country_balance * physical_balance < 0)


def _concentration(values: pd.Series) -> dict[str, float]:
    values = values.loc[values > 0].astype(float).sort_values(ascending=False)
    total = float(values.sum())
    if total <= 0:
        return {
            "contributors": 0,
            "hhi": np.nan,
            "effective_contributors": np.nan,
            "top1_share": np.nan,
            "top3_share": np.nan,
        }
    weights = values / total
    hhi = float(np.square(weights).sum())
    return {
        "contributors": int(len(values)),
        "hhi": hhi,
        "effective_contributors": float(1 / hhi),
        "top1_share": float(weights.iloc[:1].sum()),
        "top3_share": float(weights.iloc[:3].sum()),
    }


def classify_changes(panel: pd.DataFrame, threshold: float) -> pd.DataFrame:
    frame = panel.copy()
    material = frame["fossil_change_twh"].abs() >= threshold * frame["prior_generation_twh"]
    if threshold == 0:
        material = frame["fossil_change_twh"].ne(0)
    frame["direction"] = np.select(
        [material & frame["fossil_change_twh"].lt(0), material & frame["fossil_change_twh"].gt(0)],
        ["reduction", "addition"],
        default="boundary",
    )
    frame["reduction_twh"] = np.where(frame["direction"].eq("reduction"), -frame["fossil_change_twh"], 0.0)
    frame["addition_twh"] = np.where(frame["direction"].eq("addition"), frame["fossil_change_twh"], 0.0)
    return frame


def summarize_group(group: pd.DataFrame) -> dict[str, float]:
    n_reduction = int(group["direction"].eq("reduction").sum())
    n_addition = int(group["direction"].eq("addition").sum())
    n_boundary = int(group["direction"].eq("boundary").sum())
    gross_reduction = float(group["reduction_twh"].sum())
    gross_addition = float(group["addition_twh"].sum())
    country_balance = _safe_balance(n_reduction, n_addition)
    physical_balance = _safe_balance(gross_reduction, gross_addition)
    net_contraction = gross_reduction - gross_addition
    observed_net = -float(group["fossil_change_twh"].sum())
    return {
        "observations": int(len(group)),
        "n_reduction": n_reduction,
        "n_addition": n_addition,
        "n_boundary": n_boundary,
        "country_balance": country_balance,
        "gross_reduction_twh": gross_reduction,
        "gross_addition_twh": gross_addition,
        "net_contraction_twh": net_contraction,
        "observed_net_contraction_twh": observed_net,
        "physical_balance": physical_balance,
        "scale_gap": country_balance - physical_balance,
        "direction_reversal": _is_direction_reversal(country_balance, physical_balance),
    }


def annual_summary(frame: pd.DataFrame, specification: str) -> pd.DataFrame:
    rows = []
    for year, group in frame.groupby("year", sort=True):
        row = {"specification": specification, "year": int(year), **summarize_group(group)}
        for flow, column in [("reduction", "reduction_twh"), ("addition", "addition_twh")]:
            metrics = _concentration(group[column])
            row.update({f"{flow}_{key}": value for key, value in metrics.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def period_summary(frame: pd.DataFrame, specification: str) -> pd.DataFrame:
    out = frame.copy()
    out["period"] = pd.cut(
        out["year"],
        bins=[1999, 2004, 2009, 2014, 2019, 2024],
        labels=["2000–2004", "2005–2009", "2010–2014", "2015–2019", "2020–2024"],
    )
    rows = []
    for period, group in out.groupby("period", observed=True, sort=True):
        row = {"specification": specification, "period": str(period), **summarize_group(group)}
        for flow, column in [("reduction", "reduction_twh"), ("addition", "addition_twh")]:
            country_totals = group.groupby("iso_code")[column].sum()
            metrics = _concentration(country_totals)
            row.update({f"{flow}_{key}": value for key, value in metrics.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def country_contributions(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (country, iso_code), group in frame.groupby(["country", "iso_code"], sort=True):
        reduction = float(group["reduction_twh"].sum())
        addition = float(group["addition_twh"].sum())
        rows.append(
            {
                "country": country,
                "iso_code": iso_code,
                "years_reduction": int(group["direction"].eq("reduction").sum()),
                "years_addition": int(group["direction"].eq("addition").sum()),
                "years_boundary": int(group["direction"].eq("boundary").sum()),
                "gross_reduction_twh": reduction,
                "gross_addition_twh": addition,
                "net_contraction_twh": reduction - addition,
            }
        )
    result = pd.DataFrame(rows)
    result["reduction_share"] = result["gross_reduction_twh"] / result["gross_reduction_twh"].sum()
    result["addition_share"] = result["gross_addition_twh"] / result["gross_addition_twh"].sum()
    return result.sort_values("net_contraction_twh", ascending=False).reset_index(drop=True)


def bootstrap_full_period(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    country_frames = {iso: group.copy() for iso, group in frame.groupby("iso_code", sort=True)}
    iso_codes = list(country_frames)
    country_stats = []
    for iso in iso_codes:
        group = country_frames[iso]
        country_stats.append(
            [
                group["direction"].eq("reduction").sum(),
                group["direction"].eq("addition").sum(),
                group["reduction_twh"].sum(),
                group["addition_twh"].sum(),
            ]
        )
    stats = np.asarray(country_stats, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.multinomial(COUNTRIES, [1 / COUNTRIES] * COUNTRIES, size=BOOTSTRAP_REPLICATIONS)
    totals = draws @ stats
    country_balance = (totals[:, 0] - totals[:, 1]) / (totals[:, 0] + totals[:, 1])
    physical_balance = (totals[:, 2] - totals[:, 3]) / (totals[:, 2] + totals[:, 3])
    bootstrap = pd.DataFrame(
        {
            "replication": np.arange(1, BOOTSTRAP_REPLICATIONS + 1),
            "country_balance": country_balance,
            "physical_balance": physical_balance,
            "scale_gap": country_balance - physical_balance,
            "direction_reversal": country_balance * physical_balance < 0,
        }
    )
    intervals = []
    for metric in ["country_balance", "physical_balance", "scale_gap"]:
        intervals.append(
            {
                "metric": metric,
                "estimate": summarize_group(frame)[metric],
                "ci_low": float(bootstrap[metric].quantile(0.025)),
                "ci_high": float(bootstrap[metric].quantile(0.975)),
                "replications": BOOTSTRAP_REPLICATIONS,
                "seed": BOOTSTRAP_SEED,
            }
        )
    intervals.append(
        {
            "metric": "direction_reversal_probability",
            "estimate": float(bootstrap["direction_reversal"].mean()),
            "ci_low": np.nan,
            "ci_high": np.nan,
            "replications": BOOTSTRAP_REPLICATIONS,
            "seed": BOOTSTRAP_SEED,
        }
    )
    return bootstrap, pd.DataFrame(intervals)


def leave_one_country_out(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for iso_code, country in frame[["iso_code", "country"]].drop_duplicates().itertuples(index=False):
        sample = frame.loc[frame["iso_code"].ne(iso_code)]
        rows.append({"omitted_country": country, "omitted_iso_code": iso_code, **summarize_group(sample)})
    return pd.DataFrame(rows)


def validate(panel: pd.DataFrame, annual: pd.DataFrame) -> dict[str, object]:
    checks = {
        "rows_475": bool(len(panel) == 475),
        "countries_19": bool(panel["iso_code"].nunique() == 19),
        "years_2000_2024": bool((int(panel["year"].min()), int(panel["year"].max())) == (2000, 2024)),
        "balanced_panel": bool(panel.groupby("iso_code")["year"].nunique().eq(25).all()),
        "core_complete": bool(not panel[["fossil_electricity", "fossil_change_twh", "prior_generation_twh"]].isna().any().any()),
        "annual_counts_reconcile": bool(annual[["n_reduction", "n_addition", "n_boundary"]].sum(axis=1).eq(19).all()),
        "balances_bounded": bool(annual[["country_balance", "physical_balance"]].abs().le(1 + 1e-12).all().all()),
        "flow_identity": bool(np.allclose(
            annual["net_contraction_twh"], annual["observed_net_contraction_twh"], atol=1e-6
        )),
    }
    checks["all_pass"] = all(checks.values())
    return checks


def make_figures(annual: pd.DataFrame, countries: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "svg.hashsalt": "g20-fossil-contraction-20260902",
        }
    )

    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    ax.axhline(0, color="#777777", linewidth=0.8)
    ax.plot(annual["year"], annual["country_balance"], marker="o", color="#2E6F9E", label="Equal-country balance")
    ax.plot(annual["year"], annual["physical_balance"], marker="s", color="#C05A3D", label="Physical-volume balance")
    ax.set_ylabel("Normalized balance (contraction +1; expansion −1)")
    ax.set_xlabel("")
    ax.legend(frameon=False, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "figure_1_country_vs_physical_balance.png", dpi=300)
    fig.savefig(FIGURES / "figure_1_country_vs_physical_balance.svg", metadata={"Date": None})
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.axvline(0, color="#999999", linewidth=0.8)
    ax.plot([-1, 1], [-1, 1], linestyle="--", color="#BBBBBB", linewidth=1)
    ax.scatter(annual["country_balance"], annual["physical_balance"], color="#3B7A57", s=38)
    label_years = {2000, 2013, 2018, 2020, 2023}
    for row in annual.loc[annual["year"].isin(label_years)].itertuples(index=False):
        ax.annotate(str(row.year), (row.country_balance, row.physical_balance), xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_xlabel("Equal-country balance")
    ax.set_ylabel("Physical-volume balance")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "figure_2_scale_alignment.png", dpi=300)
    fig.savefig(FIGURES / "figure_2_scale_alignment.svg", metadata={"Date": None})
    plt.close(fig)

    plot = countries.sort_values("net_contraction_twh")
    colors = np.where(plot["net_contraction_twh"].ge(0), "#188977", "#B64A55")
    fig, ax = plt.subplots(figsize=(8.5, 7.0))
    ax.barh(plot["country"], plot["net_contraction_twh"], color=colors)
    ax.axvline(0, color="#666666", linewidth=0.8)
    ax.set_xlabel("Cumulative net fossil-power contraction, 2000–2024 (TWh)")
    ax.set_ylabel("")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "figure_3_country_net_contributions.png", dpi=300)
    fig.savefig(FIGURES / "figure_3_country_net_contributions.svg", metadata={"Date": None})
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(PANEL_PATH)

    annual_frames = []
    period_frames = []
    classified = {}
    for specification, threshold in THRESHOLDS.items():
        frame = classify_changes(panel, threshold)
        classified[specification] = frame
        annual_frames.append(annual_summary(frame, specification))
        period_frames.append(period_summary(frame, specification))

    annual = pd.concat(annual_frames, ignore_index=True)
    periods = pd.concat(period_frames, ignore_index=True)
    primary = classified["primary"]
    countries = country_contributions(primary)
    bootstrap, intervals = bootstrap_full_period(primary)
    loco = leave_one_country_out(primary)

    annual.to_csv(RESULTS / "annual_breadth_depth.csv", index=False, float_format="%.10g")
    periods.to_csv(RESULTS / "period_breadth_depth.csv", index=False, float_format="%.10g")
    countries.to_csv(RESULTS / "country_contributions.csv", index=False, float_format="%.10g")
    bootstrap.to_csv(RESULTS / "bootstrap_20000.csv", index=False, float_format="%.10g")
    intervals.to_csv(RESULTS / "bootstrap_intervals.csv", index=False, float_format="%.10g")
    loco.to_csv(RESULTS / "leave_one_country_out.csv", index=False, float_format="%.10g")

    primary_annual = annual.loc[annual["specification"].eq("primary")].copy()
    full_period = summarize_group(primary)
    for flow, column in [("reduction", "reduction_twh"), ("addition", "addition_twh")]:
        country_totals = primary.groupby("iso_code")[column].sum()
        full_period.update({f"{flow}_{key}": value for key, value in _concentration(country_totals).items()})
    full_period.update(
        {
            "annual_direction_reversal_years": int(primary_annual["direction_reversal"].sum()),
            "annual_alignment_years": int((~primary_annual["direction_reversal"]).sum()),
            "annual_scale_gap_mean": float(primary_annual["scale_gap"].mean()),
            "annual_scale_gap_median": float(primary_annual["scale_gap"].median()),
            "annual_scale_gap_mean_absolute": float(primary_annual["scale_gap"].abs().mean()),
            "country_physical_balance_correlation": float(
                primary_annual["country_balance"].corr(primary_annual["physical_balance"])
            ),
        }
    )
    with (RESULTS / "headline_results.json").open("w", encoding="utf-8") as handle:
        json.dump(full_period, handle, indent=2, ensure_ascii=False)

    checks = validate(panel, primary_annual)
    with (RESULTS / "validation_report.json").open("w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)
    if not checks["all_pass"]:
        raise RuntimeError(f"Validation failure: {checks}")

    make_figures(primary_annual, countries)
    print(json.dumps(full_period, indent=2, ensure_ascii=False))
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
