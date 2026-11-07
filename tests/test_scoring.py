from analyzer import catalog
from analyzer.models import Finding
from analyzer.privacy import mask_mac
from analyzer.scoring import network_score


def _f(code: str) -> Finding:
    e = catalog.get(code)
    return Finding(file="x.xml", ip="192.168.1.1", port=1, code=code, severity=e.severity, points=e.points)


def test_no_findings_is_100():
    assert network_score([]) == 100


def test_score_never_below_zero():
    assert network_score([_f("TELNET_OPEN")] * 10) == 0


def test_v2_score():
    codes = ["HTTP_ADMIN_CLEARTEXT", "UPNP_EXPOSED", "CAMERA_STREAM_EXPOSED",
             "HTTP_ADMIN_CLEARTEXT", "MQTT_EXPOSED"]
    assert network_score([_f(c) for c in codes]) == 40


def test_catalog_has_15_codes():
    assert len(catalog.CATALOG) == 15


def test_mask_mac():
    assert mask_mac("50:c7:bf:12:34:56") == "50:C7:**:**:**:**"
    assert mask_mac("") == ""
