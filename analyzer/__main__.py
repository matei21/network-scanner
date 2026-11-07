"""CLI: python -m analyzer <folder-or-file> --out results/

Writes findings.csv and scores.csv for a whole folder in one command (FR-15).
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="analyzer", description="Analyze nmap XML scan files.")
    ap.add_argument("input", type=Path, help="folder with *.xml files, or a single .xml file")
    ap.add_argument("--out", type=Path, default=Path("results"), help="output folder for CSV files")
    args = ap.parse_args(argv)

    # TODO(A):
    #  results = service.analyze_folder(args.input)  (or analyze_file for a single file)
    #  export.write_findings_csv(results, args.out / "findings.csv")
    #  export.write_scores_csv(results, args.out / "scores.csv")
    #  print a short summary (files, findings, errors)
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
