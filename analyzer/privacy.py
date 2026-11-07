"""Privacy helpers (NFR-02: MAC addresses masked in all output)."""

from __future__ import annotations


def mask_mac(mac: str) -> str:
    """'50:C7:BF:12:34:56' -> '50:C7:**:**:**:**'. Empty stays empty."""
    if not mac:
        return ""
    parts = mac.replace("-", ":").upper().split(":")
    if len(parts) != 6:
        return "**:**:**:**:**:**"
    return ":".join(parts[:2] + ["**"] * 4)
