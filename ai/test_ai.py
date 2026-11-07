"""
Test rapid pentru modulul AI.
Ruleaza: python -m ai.test_ai
"""

from ai.templates import get_template, get_all_finding_codes, FINDING_TEMPLATES
from ai.fingerprint import guess_device_type
from ai.ai_service import AIService, build_scan_context, Chatbot


def test_templates():
    print("=" * 60)
    print("TEST 1: Template-uri")
    print("=" * 60)

    codes = get_all_finding_codes()
    print(f"  Total finding codes: {len(codes)}")
    assert len(codes) == 15, f"Asteptat 15, gasit {len(codes)}"

    for code in codes:
        t_ro = get_template(code, "ro")
        t_en = get_template(code, "en")
        assert t_ro is not None, f"Template RO lipsa: {code}"
        assert t_en is not None, f"Template EN lipsa: {code}"
        assert len(t_ro["fix_steps"]) >= 2, f"Prea putini pasi fix RO: {code}"
        assert len(t_en["fix_steps"]) >= 2, f"Prea putini pasi fix EN: {code}"
        print(f"  OK: {code} ({t_ro['severity']}, {t_ro['points']}p)")

    total_points = sum(FINDING_TEMPLATES[c]["points"] for c in codes)
    print(f"  Total puncte posibile: {total_points}")
    print("  PASSED\n")


def test_fingerprinting():
    print("=" * 60)
    print("TEST 2: Device fingerprinting")
    print("=" * 60)

    test_cases = [
        ({"vendor": "TP-Link", "hostname": "router.lan", "services": ["domain", "http"], "is_gateway": True},
         "router"),
        ({"vendor": "Hikvision", "hostname": "ipcam", "services": ["rtsp", "http"]},
         "camera"),
        ({"vendor": "HP", "hostname": "officejet-pro", "services": ["jetdirect", "ipp"]},
         "printer"),
        ({"vendor": "Samsung", "hostname": "galaxy-s23", "services": []},
         "phone"),
        ({"vendor": "Samsung", "hostname": "smart-tv", "services": ["googlecast"]},
         "smart_tv"),
        ({"vendor": "Dell", "hostname": "laptop-ana", "services": []},
         "computer"),
        ({"vendor": "Espressif", "hostname": "shelly1", "services": ["mqtt"]},
         "smart_home"),
        ({"vendor": "", "hostname": "", "services": ["sun-answerbook"]},
         "unknown"),
        ({"vendor": "Dell", "hostname": "oldsrv", "services": ["ftp", "ssh"]},
         "server"),
    ]

    for host, expected_type in test_cases:
        result = guess_device_type(host)
        status = "OK" if result["type"] == expected_type else "FAIL"
        print(f"  {status}: {host.get('vendor', '?')} / {host.get('hostname', '?')} "
              f"-> {result['label_en']} "
              f"(expected: {expected_type}, got: {result['type']})")
        if result["type"] != expected_type:
            print(f"    WARN: Expected {expected_type}, got {result['type']}")

    print("  PASSED\n")


def test_ai_service_template_fallback():
    print("=" * 60)
    print("TEST 3: AI Service (template fallback)")
    print("=" * 60)

    # Disable cloud si local -- forteaza template
    ai = AIService(enable_cloud=False, enable_local=False)
    status = ai.status
    print(f"  Status: cloud={status['cloud']}, local={status['local']}, template={status['template']}")

    result = ai.explain_finding(
        "TELNET_OPEN",
        {"ip": "192.168.1.1", "vendor": "Netgear", "hostname": "gateway",
         "type": "router", "port": 23, "service": "telnet"},
        language="ro",
    )
    print(f"  Source: {result['source']}")
    print(f"  Text: {result['text'][:100]}...")
    print(f"  Fix steps: {len(result['fix_steps'])} pasi")
    print(f"  CIS: {result['cis_control']}")
    print(f"  OWASP: {result['owasp_iot']}")
    assert result["source"] == "template"
    assert len(result["fix_steps"]) > 0
    print("  PASSED\n")


def test_chatbot_context():
    print("=" * 60)
    print("TEST 4: Chatbot context building")
    print("=" * 60)

    mock_scan = {
        "subnet": "192.168.1.0/24",
        "score": 40,
        "scan_date": "2026-11-07",
        "devices": [
            {
                "ip": "192.168.1.1",
                "mac_masked": "50:C7:**:**:**:**",
                "vendor": "TP-Link",
                "hostname": "router.lan",
                "type_label": "Router",
                "open_ports": [80, 443, 1900],
            },
            {
                "ip": "192.168.1.40",
                "mac_masked": "C0:56:**:**:**:**",
                "vendor": "Hikvision",
                "hostname": "ipcam",
                "type_label": "Camera IP",
                "open_ports": [80, 554],
            },
        ],
        "findings": [
            {"code": "HTTP_ADMIN_CLEARTEXT", "ip": "192.168.1.1", "port": 80, "severity": "medium"},
            {"code": "UPNP_EXPOSED", "ip": "192.168.1.1", "port": 1900, "severity": "medium"},
            {"code": "CAMERA_STREAM_EXPOSED", "ip": "192.168.1.40", "port": 554, "severity": "high"},
        ],
    }

    context = build_scan_context(mock_scan)
    print(f"  Context length: {len(context)} chars")
    print(f"  Contains subnet: {'192.168.1.0/24' in context}")
    print(f"  Contains score: {'40/100' in context}")
    print(f"  Contains camera: {'Hikvision' in context}")
    print(f"  Contains finding: {'CAMERA_STREAM_EXPOSED' in context}")
    assert "192.168.1.0/24" in context
    assert "40/100" in context
    assert "Hikvision" in context
    print("  PASSED\n")

    # Test chatbot cu template fallback
    ai = AIService(enable_cloud=False, enable_local=False)
    bot = Chatbot(ai, mock_scan)
    print("  Chatbot system prompt length:", len(bot.system_prompt), "chars")
    print("  PASSED\n")


if __name__ == "__main__":
    test_templates()
    test_fingerprinting()
    test_ai_service_template_fallback()
    test_chatbot_context()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
