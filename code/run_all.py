"""Run the complete reproducibility workflow."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(script: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "code" / script)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rebuild-panel",
        action="store_true",
        help="Download checksum-locked OWID files and reconstruct the derived panel.",
    )
    args = parser.parse_args()
    if args.rebuild_panel:
        run("00_prepare_data.py")
    run("01_breadth_depth_analysis.py")
    run("02_verify.py")


if __name__ == "__main__":
    main()

