# Fossil-Power Contraction across G20 Electricity Systems

[![Reproducibility](https://img.shields.io/badge/reproducibility-verified-188977)](verification/verification_report.json)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB)](environment.yml)
[![License: MIT](https://img.shields.io/badge/code%20license-MIT-yellow.svg)](LICENSE)

This repository contains the data, analysis code, machine-readable outputs,
figures, robustness diagnostics, and verification records for:

> Küçükoğlu, S. *Fossil-Power Contraction across G20 Electricity Systems:
> National Breadth, Physical Depth, and Contribution Concentration*.

The study examines all 19 country members of the G20 over 2000–2024. It
distinguishes the national breadth of fossil-power contraction from its physical
depth in TWh and evaluates how the concentration of country contributions can
produce disagreement between these two assessments. The evidence is descriptive
and decompositional; it does not identify causal effects or policy mechanisms.

## Reproduce the results

Create the environment and run the analysis from the included checksum-verified
derived panel:

```bash
conda env create -f environment.yml
conda run -n g20-fossil-contraction-repro python code/run_all.py
```

Alternatively, with Python 3.12:

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python code/run_all.py
```

To retrieve the two public OWID files, verify their frozen checksums, and rebuild
the analytical panel before reproducing all outputs:

```bash
python code/run_all.py --rebuild-panel
```

The checksum gate stops if a live public source has changed. The included
derived panel therefore remains the stable entry point for exact reproduction.

## Repository contents

| Path | Contents |
| --- | --- |
| `data/derived/` | Balanced analytical panel and data dictionary |
| `data/raw/` | Instructions for checksum-locked source retrieval; raw files are excluded from Git |
| `results/` | Annual and five-year breadth–depth outputs, country contributions, bootstrap results, LOCO diagnostics, and headline estimates |
| `figures/` | Publication-quality PNG and editable SVG figures |
| `code/` | Source reconstruction, analysis, one-command runner, and verification scripts |
| `verification/` | Source lineage, checksums, and a machine-readable result audit |

## Output-to-manuscript map

| Manuscript element | Authoritative file |
| --- | --- |
| Full-period headline results | `results/headline_results.json` |
| Annual balances and direction reversals | `results/annual_breadth_depth.csv` |
| Five-year summaries and threshold sensitivities | `results/period_breadth_depth.csv` |
| Country contributions and concentration | `results/country_contributions.csv` |
| Country-cluster bootstrap intervals | `results/bootstrap_intervals.csv` |
| All 20,000 bootstrap draws | `results/bootstrap_20000.csv` |
| Leave-one-country-out diagnostics | `results/leave_one_country_out.csv` |
| Validation identities | `results/validation_report.json` and `verification/verification_report.json` |

## Frozen source and analytical scope

The source is the publicly available [Our World in Data Energy dataset](https://github.com/owid/energy-data)
and its codebook, frozen on 1 September 2026. Exact SHA-256 identifiers and
provider lineage are recorded in [`verification/source_manifest.md`](verification/source_manifest.md).
The derived panel's checksum is:

```text
7b80e29507cf5201b6b358bebd0ccdfdcbbe4396ae5dca15aeea559200204cce  data/derived/analytical_panel_2000_2024.csv
```

The analytical population is 19 G20 country members. The European Union and
African Union are not treated as country observations. The primary period is
2000–2024, with 1999 used only as a lag buffer when the panel is reconstructed.

## Verification gate

`code/02_verify.py` checks the panel checksum and structure, the 174 reduction
and 301 addition observations, full-period country and physical balances, the
three annual direction reversals, flow magnitudes, concentration results,
China's addition share, the strict sign-opposition definition of direction
reversal, and the bootstrap seed and replication count. A failed check
terminates the workflow with a non-zero exit status. The workflow also refreshes
`verification/SHA256SUMS.txt` after every successful run.

No restricted, confidential, or personal data are included.

## Citation and licensing

Please cite the manuscript and this repository. Machine-readable citation
metadata are in [`CITATION.cff`](CITATION.cff). Analysis code is released under
the [MIT License](LICENSE). Source and derived data retain upstream attribution
and reuse conditions; see [`LICENSES.md`](LICENSES.md).
