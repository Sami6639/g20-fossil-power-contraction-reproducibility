"""Verify data integrity, analytical identities, and manuscript headline results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "derived" / "analytical_panel_2000_2024.csv"
EXPECTED_PANEL_SHA256 = "7b80e29507cf5201b6b358bebd0ccdfdcbbe4396ae5dca15aeea559200204cce"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(value: float, expected: float, tolerance: float = 1e-9) -> bool:
    return bool(np.isclose(value, expected, atol=tolerance, rtol=0))


def write_checksum_manifest() -> None:
    """Write stable SHA-256 identifiers for every tracked package file."""
    destination = ROOT / "verification" / "SHA256SUMS.txt"
    files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and path != destination
    ]
    lines = [f"{sha256(path)}  ./{path.relative_to(ROOT).as_posix()}" for path in sorted(files)]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    panel = pd.read_csv(PANEL)
    headline = json.loads((ROOT / "results" / "headline_results.json").read_text(encoding="utf-8"))
    annual = pd.read_csv(ROOT / "results" / "annual_breadth_depth.csv")
    primary = annual.loc[annual["specification"].eq("primary")]
    periods = pd.read_csv(ROOT / "results" / "period_breadth_depth.csv")
    bootstrap_draws = pd.read_csv(ROOT / "results" / "bootstrap_20000.csv")
    bootstrap = pd.read_csv(ROOT / "results" / "bootstrap_intervals.csv").set_index("metric")
    countries = pd.read_csv(ROOT / "results" / "country_contributions.csv")
    threshold_boundary = periods.loc[
        periods["specification"].eq("threshold_010")
        & periods["period"].eq("2015–2019")
    ].iloc[0]

    checks = {
        "derived_panel_sha256": sha256(PANEL) == EXPECTED_PANEL_SHA256,
        "rows_475": len(panel) == 475,
        "countries_19": panel["iso_code"].nunique() == 19,
        "years_2000_2024": (int(panel["year"].min()), int(panel["year"].max())) == (2000, 2024),
        "balanced_panel": panel.groupby("iso_code")["year"].nunique().eq(25).all(),
        "reductions_174": headline["n_reduction"] == 174,
        "additions_301": headline["n_addition"] == 301,
        "country_balance": close(headline["country_balance"], -0.2673684210526316),
        "physical_balance": close(headline["physical_balance"], -0.5187043500594051),
        "scale_gap": close(headline["scale_gap"], 0.2513359290067735),
        "gross_reductions": close(headline["gross_reduction_twh"], 3287.4658050116595, 1e-6),
        "gross_additions": close(headline["gross_addition_twh"], 10373.43391605344, 1e-6),
        "annual_reversals_2013_2018_2023": primary.loc[primary["direction_reversal"], "year"].tolist() == [2013, 2018, 2023],
        "annual_reversal_definition_strict": annual["direction_reversal"].eq(
            annual["country_balance"].mul(annual["physical_balance"]).lt(0)
        ).all(),
        "period_reversal_definition_strict": periods["direction_reversal"].eq(
            periods["country_balance"].mul(periods["physical_balance"]).lt(0)
        ).all(),
        "bootstrap_reversal_definition_strict": bootstrap_draws["direction_reversal"].eq(
            bootstrap_draws["country_balance"].mul(bootstrap_draws["physical_balance"]).lt(0)
        ).all(),
        "zero_balance_is_not_reversal": close(float(threshold_boundary["country_balance"]), 0.0)
        and not bool(threshold_boundary["direction_reversal"]),
        "addition_hhi": close(headline["addition_hhi"], 0.29110951437666127),
        "reduction_hhi": close(headline["reduction_hhi"], 0.13640777977559154),
        "china_addition_share": close(float(countries.loc[countries["iso_code"].eq("CHN"), "addition_share"].iloc[0]), 0.5142850262, 1e-9),
        "bootstrap_replications": bootstrap["replications"].eq(20000).all(),
        "bootstrap_seed": bootstrap["seed"].eq(20260902).all(),
    }
    checks = {key: bool(value) for key, value in checks.items()}
    checks["all_pass"] = all(checks.values())
    destination = ROOT / "verification" / "verification_report.json"
    destination.write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    write_checksum_manifest()
    print(json.dumps(checks, indent=2))
    if not checks["all_pass"]:
        raise RuntimeError("One or more reproducibility checks failed.")


if __name__ == "__main__":
    main()
