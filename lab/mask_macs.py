"""Mask MAC addresses inside nmap XML scan files (NFR-02: MACs are personal data).

    python lab/mask_macs.py data/lab            # every .xml in the folder
    python lab/mask_macs.py data/lab/scan.xml   # one file
    python lab/mask_macs.py --check data/lab    # only report, change nothing (exit 1 if unmasked)

Only the MAC value of <address addrtype="mac" .../> changes:
    1C:1B:B5:D7:04:42  ->  1C:1B:**:**:**:**     (same format the tool shows)
The vendor and everything else stay byte-for-byte the same, so findings and
scores do not change. Running it twice is safe (already masked = no change).

Do not use it on the official Validation / Test Set files.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# A full MAC (six hex pairs) inside an nmap <address ... addrtype="mac"> element.
# Matches attribute order addr-then-addrtype (what nmap writes) and the reverse.
_ADDR_FIRST = re.compile(
    r'(<address\b[^>]*?\baddr=")([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})[:-](?:[0-9A-Fa-f]{2}[:-]){3}[0-9A-Fa-f]{2}'
    r'("[^>]*?\baddrtype="mac")'
)
_TYPE_FIRST = re.compile(
    r'(<address\b[^>]*?\baddrtype="mac"[^>]*?\baddr=")([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})[:-](?:[0-9A-Fa-f]{2}[:-]){3}[0-9A-Fa-f]{2}(")'
)

# Any full MAC anywhere in the text (used by --check and by the privacy test).
FULL_MAC = re.compile(r"(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f:])")


def _masked(m: re.Match) -> str:
    first_two = m.group(2).replace("-", ":").upper()
    return f"{m.group(1)}{first_two}:**:**:**:**{m.group(3)}"


def mask_text(text: str) -> str:
    text = _ADDR_FIRST.sub(_masked, text)
    return _TYPE_FIRST.sub(_masked, text)


def mask_file(path: Path) -> int:
    """Mask one file in place. Returns how many MACs were masked."""
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    new = mask_text(text)
    count = len(FULL_MAC.findall(text)) - len(FULL_MAC.findall(new))
    if new != text:
        # Keep the original line endings: write bytes, not text mode.
        path.write_bytes(new.encode("utf-8"))
    return count


def xml_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(p for p in target.iterdir() if p.is_file() and p.suffix.lower() == ".xml")


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    paths = [Path(a) for a in argv if a != "--check"]
    if not paths:
        print(__doc__)
        return 2

    problems = 0
    for target in paths:
        if not target.exists():
            print(f"not found: {target}")
            return 2
        for f in xml_files(target):
            if check_only:
                left = FULL_MAC.findall(f.read_text(encoding="utf-8"))
                if left:
                    problems += 1
                    print(f"UNMASKED  {f}: {len(left)} full MAC address(es)")
                else:
                    print(f"ok        {f}")
            else:
                n = mask_file(f)
                print(f"{'masked' if n else 'ok    '}  {f}" + (f": {n} MAC(s)" if n else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
