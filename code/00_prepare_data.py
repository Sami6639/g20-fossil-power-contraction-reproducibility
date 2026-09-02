"""Retrieve, checksum, and reconstruct the frozen analytical panel."""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
SOURCE_URL = "https://owid-public.owid.io/data/energy/owid-energy-data.csv"
CODEBOOK_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-codebook.csv"
SOURCE_SHA256 = "77b3db513f02f5fffb69fe02832907ce70b01d3906fc2c5dd40fa47e3ee7d0f3"
CODEBOOK_SHA256 = "3cc9b7db0d921496e2988568ce3aee5ed41f50431dd234a0663b5f0a4b2e32bb"
DERIVED_SHA256 = "7b80e29507cf5201b6b358bebd0ccdfdcbbe4396ae5dca15aeea559200204cce"

COUNTRIES = {
    "ARG": "Argentina", "AUS": "Australia", "BRA": "Brazil", "CAN": "Canada",
    "CHN": "China", "FRA": "France", "DEU": "Germany", "IND": "India",
    "IDN": "Indonesia", "ITA": "Italy", "JPN": "Japan", "KOR": "South Korea",
    "MEX": "Mexico", "RUS": "Russia", "SAU": "Saudi Arabia",
    "ZAF": "South Africa", "TUR": "Türkiye", "GBR": "United Kingdom",
    "USA": "United States",
}

KEEP_COLUMNS = [
    "country", "year", "iso_code", "renewables_electricity", "fossil_electricity",
    "electricity_generation", "electricity_demand", "fossil_share_elec",
    "net_elec_imports_share_demand", "wind_electricity", "solar_electricity",
    "nuclear_electricity",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_verified(url: str, destination: Path, expected: str) -> None:
    if destination.exists() and sha256(destination) == expected:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as out:
        while block := response.read(1024 * 1024):
            out.write(block)
    observed = sha256(temporary)
    if observed != expected:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"Checksum mismatch for {url}. Expected {expected}, observed {observed}. "
            "The live public source may have changed; see verification/source_manifest.md."
        )
    temporary.replace(destination)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)
    source = RAW / "owid-energy-data.csv"
    codebook = RAW / "owid-energy-codebook.csv"
    download_verified(SOURCE_URL, source, SOURCE_SHA256)
    download_verified(CODEBOOK_URL, codebook, CODEBOOK_SHA256)

    full = pd.read_csv(source, usecols=KEEP_COLUMNS)
    lagged = full.loc[
        full["iso_code"].isin(COUNTRIES) & full["year"].between(1999, 2024), KEEP_COLUMNS
    ].copy()
    lagged["country_source"] = lagged["country"]
    lagged["country"] = lagged["iso_code"].map(COUNTRIES)
    lagged = lagged.sort_values(["iso_code", "year"]).reset_index(drop=True)

    if lagged.groupby("iso_code")["year"].nunique().ne(26).any():
        raise RuntimeError("The 1999–2024 lag-buffer panel is not balanced for all 19 countries.")
    required = ["renewables_electricity", "fossil_electricity", "electricity_generation"]
    if lagged[required].isna().any().any():
        raise RuntimeError("Primary electricity variables contain missing observations.")

    groups = lagged.groupby("iso_code", sort=False)
    lagged["renewables_change_twh"] = groups["renewables_electricity"].diff()
    lagged["fossil_change_twh"] = groups["fossil_electricity"].diff()
    lagged["prior_generation_twh"] = groups["electricity_generation"].shift(1)
    lagged["electricity_demand_growth_pct"] = groups["electricity_demand"].pct_change(fill_method=None) * 100
    lagged["wind_solar_share_elec"] = (
        (lagged["wind_electricity"].fillna(0) + lagged["solar_electricity"].fillna(0))
        / lagged["electricity_generation"] * 100
    )
    lagged["nuclear_share_elec"] = (
        lagged["nuclear_electricity"].fillna(0) / lagged["electricity_generation"] * 100
    )
    panel = lagged.loc[lagged["year"].between(2000, 2024)].copy()
    output = DERIVED / "analytical_panel_2000_2024.csv"
    panel.to_csv(output, index=False, float_format="%.10g")
    if sha256(output) != DERIVED_SHA256:
        raise RuntimeError("The reconstructed analytical panel does not match the frozen panel checksum.")
    print(f"Verified analytical panel: {output}")


if __name__ == "__main__":
    main()

