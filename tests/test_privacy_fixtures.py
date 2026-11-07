"""Privacy safety net (NFR-02): our own lab scans in the repo must not contain full MACs.

If this fails, mask the file before committing:
    python lab/mask_macs.py data/lab
The official Validation / Test Set files are not checked (organisers' data, kept unchanged).
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LAB_SCANS = ROOT / "data" / "lab"

_spec = importlib.util.spec_from_file_location("mask_macs", ROOT / "lab" / "mask_macs.py")
mask_macs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mask_macs)


def _lab_files():
    return sorted(LAB_SCANS.glob("*.xml")) if LAB_SCANS.is_dir() else []


@pytest.mark.parametrize("path", _lab_files(), ids=lambda p: p.name)
def test_lab_scan_has_no_full_mac(path):
    found = mask_macs.FULL_MAC.findall(path.read_text(encoding="utf-8"))
    assert not found, (
        f"{path.name} contains {len(found)} unmasked MAC address(es). "
        "Run: python lab/mask_macs.py data/lab"
    )


def test_masking_keeps_everything_else():
    xml = ('<address addr="10.74.130.9" addrtype="ipv4"/>\n'
           '<address addr="1c-1b-b5-d7-04-42" addrtype="mac" vendor="Intel Corporate"/>\n'
           '<address addrtype="mac" addr="AE:B3:1B:77:8A:1C"/>\n'
           '<elem key="title">Admin 12:34:56:78:9a:bc</elem>\n')
    out = mask_macs.mask_text(xml)
    assert '<address addr="10.74.130.9" addrtype="ipv4"/>' in out
    assert '<address addr="1C:1B:**:**:**:**" addrtype="mac" vendor="Intel Corporate"/>' in out
    assert '<address addrtype="mac" addr="AE:B3:**:**:**:**"/>' in out
    assert "Admin 12:34:56:78:9a:bc" in out          # only <address> MACs are touched
    assert mask_macs.mask_text(out) == out          # running twice changes nothing


def test_masked_mac_still_works_in_the_analyzer():
    from analyzer.privacy import mask_mac
    assert mask_mac("1C:1B:**:**:**:**") == "1C:1B:**:**:**:**"
