"""Live scan from the command line, with the same guardrail as the API.

    python -m backend.scan                           # shows your network, refuses (no --confirm)
    python -m backend.scan --confirm                 # scans the subnet you are connected to
    python -m backend.scan --target 8.8.8.8 --confirm        # refused: public IP
    python -m backend.scan --target 192.168.1.0/24 --confirm # refused if not your network

Run the confirmed scan in a terminal opened "as administrator" (nmap -sS / -sU).
Exit codes: 0 scan done, 2 refused by the guardrail, 1 scan failed.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from analyzer import export
from analyzer.service import analyze_file

from .app.guardrails import build_allowlist, detect_network, validate_scan_target
from .app.scanner import run_nmap_scan


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m backend.scan", description="Guarded live network scan.")
    ap.add_argument("--target", help="IPv4 address or subnet (default: the subnet you are connected to)")
    ap.add_argument("--confirm", action="store_true", help="required: confirm you own this network")
    ap.add_argument("--out", type=Path, default=Path("results") / "live",
                    help="folder for findings.csv / scores.csv (default: results/live)")
    args = ap.parse_args(argv)

    net = detect_network()
    if net.get("subnet"):
        print(f"Your network: {net['subnet']} (interface {net.get('interface')}, gateway {net.get('gateway')})")
    else:
        print("Your network: not detected")

    allowlist = build_allowlist(net.get("subnet"))
    target = args.target or net.get("subnet") or ""
    check = validate_scan_target(target, allowlist=allowlist, confirmed=args.confirm)
    if not check["allowed"]:
        print(f"REFUSED: {check['reason']}")
        return 2

    print(f"OK: {check['reason']} Scanning (max 100 packets/s, this can take a few minutes)...")
    xml_path = Path("scans") / f"cli_{uuid.uuid4().hex}" / "live_scan.xml"
    scan = run_nmap_scan(str(target), str(xml_path))
    if not scan.get("success"):
        print(f"Scan failed: {scan.get('error') or scan.get('stderr') or 'nmap returned an error'}")
        return 1

    result = analyze_file(xml_path)
    if result.error:
        print(f"Scan output could not be read: {result.error}")
        return 1

    export.write_findings_csv([result], args.out / "findings.csv")
    export.write_scores_csv([result], args.out / "scores.csv")
    print(f"Score: {result.score}  |  devices: {len(result.devices)}  |  findings: {len(result.findings)}")
    for f in result.findings:
        print(f"  {f.severity:<6} {f.code:<22} {f.ip}:{'' if f.port is None else f.port}")
    print(f"Saved {xml_path} and {args.out / 'findings.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
