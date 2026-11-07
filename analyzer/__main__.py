"""CLI: python -m analyzer <folder-or-file> --out results/

Writes findings.csv and scores.csv for a whole folder in one command (FR-15).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import export, service


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="analyzer", description="Analyze nmap XML scan files.")
    ap.add_argument("input", type=Path, help="folder with *.xml files, or a single .xml file")
    ap.add_argument("--out", type=Path, default=Path("results"), help="output folder for CSV files")
    args = ap.parse_args(argv)

    try:
        results = service.analyze_folder(args.input)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if not results:
        print(f"No .xml files found in {args.input}", file=sys.stderr)
        return 2

    findings_path = args.out / "findings.csv"
    scores_path = args.out / "scores.csv"
    export.write_findings_csv(results, findings_path)
    export.write_scores_csv(results, scores_path)

    print(f"{'file':<32} {'score':>6}  findings")
    for r in results:
        if r.error:
            print(f"{r.file:<32} {'ERROR':>6}  {r.error}")
        else:
            print(f"{r.file:<32} {r.score:>6}  {len(r.findings)}")

    total = sum(len(r.findings) for r in results)
    errors = sum(1 for r in results if r.error)
    print(f"\n{len(results)} files, {total} findings, {errors} unreadable")
    print(f"Wrote {findings_path} and {scores_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
