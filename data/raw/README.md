# Frozen raw source files

The complete workflow can retrieve the public OWID Energy dataset and codebook
when `python code/run_all.py --rebuild-panel` is used. Raw files are accepted
only if their SHA-256 checksums match the frozen 1 September 2026 source listed
in `verification/source_manifest.md`. Raw files remain local and are excluded
from Git. The verified derived analytical panel is included in `data/derived/`.

