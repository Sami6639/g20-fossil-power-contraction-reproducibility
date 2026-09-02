# Source manifest

## Frozen analytical source

| Item | Freeze date | Public location | SHA-256 |
| --- | --- | --- | --- |
| OWID Energy dataset (`owid-energy-data.csv`) | 1 September 2026 | <https://owid-public.owid.io/data/energy/owid-energy-data.csv> | `77b3db513f02f5fffb69fe02832907ce70b01d3906fc2c5dd40fa47e3ee7d0f3` |
| OWID Energy codebook (`owid-energy-codebook.csv`) | 1 September 2026 | <https://github.com/owid/energy-data/blob/master/owid-energy-codebook.csv> | `3cc9b7db0d921496e2988568ce3aee5ed41f50431dd234a0663b5f0a4b2e32bb` |
| Derived analytical panel (`analytical_panel_2000_2024.csv`) | 2 September 2026 | Included in this repository | `7b80e29507cf5201b6b358bebd0ccdfdcbbe4396ae5dca15aeea559200204cce` |

The source and codebook hashes were reverified when the reproducibility archive
was assembled. If a live public file has subsequently changed, the checksum
gate will stop rather than silently substitute a different data vintage.

## Provider lineage

The frozen OWID codebook identifies the electricity series used in the study as
harmonized from Ember's Yearly Electricity Data and the Energy Institute
Statistical Review of World Energy. The codebook is the authoritative record of
field definitions, units, processing notes, and provider lineage.

## Population and period

The population comprises the 19 country members of the G20. The European Union
and African Union are excluded because they are supranational members rather
than country-level observational units. The analytical period is 2000–2024;
1999 is used only to construct the 2000 annual change. The balanced panel
contains 475 country-years.

