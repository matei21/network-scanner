"""
Test rapid pentru modulul AI.
Ruleaza: python -m ai.test_ai
"""

from ai.templates import get_template, get_all_finding_codes, FINDING_TEMPLATES
from ai.fingerprint import guess_device_type
from ai.ai_service import AIService, build_scan_context, Chatbot
from ai.assistant import Assistant, enrich_scan_data, enrich_findings_list


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


def test_enrich_scan_data():
    print("=" * 60)
    print("TEST 5: Enrich scan data (fingerprint + templates)")
    print("=" * 60)

    mock_scan = {
        "score": 40,
        "devices": [
            {
                "ip": "192.168.1.1",
                "vendor": "TP-Link",
                "hostname": "router.lan",
                "is_gateway": True,
                "open_ports": [
                    {"port": 80, "service": "http"},
                    {"port": 1900, "service": "upnp"},
                ],
                "findings": [
                    {"code": "HTTP_ADMIN_CLEARTEXT", "port": 80},
                    {"code": "UPNP_EXPOSED", "port": 1900},
                ],
            },
            {
                "ip": "192.168.1.40",
                "vendor": "Hikvision",
                "hostname": "ipcam",
                "open_ports": [
                    {"port": 554, "service": "rtsp"},
                ],
                "findings": [
                    {"code": "CAMERA_STREAM_EXPOSED", "port": 554},
                ],
            },
        ],
    }

    enriched = enrich_scan_data(mock_scan)

    # Check fingerprinting
    d1 = enriched["devices"][0]
    assert d1["type"] == "router", f"Expected router, got {d1['type']}"
    print(f"  OK: {d1['ip']} -> {d1['type_label_en']}")

    d2 = enriched["devices"][1]
    assert d2["type"] == "camera", f"Expected camera, got {d2['type']}"
    print(f"  OK: {d2['ip']} -> {d2['type_label_en']}")

    # Check template enrichment
    f1 = d1["findings"][0]
    assert "explanation_ro" in f1, "Missing explanation_ro"
    assert "fix_steps_en" in f1, "Missing fix_steps_en"
    assert "cis_control" in f1, "Missing cis_control"
    print(f"  OK: {f1['code']} has explanation_ro, fix_steps_en, cis_control")

    f2 = d2["findings"][0]
    assert "owasp_iot" in f2, "Missing owasp_iot"
    assert "Privacy" in f2["owasp_iot"], f"Expected Privacy in OWASP, got {f2['owasp_iot']}"
    print(f"  OK: {f2['code']} OWASP = {f2['owasp_iot']}")

    print("  PASSED\n")


def test_enrich_findings_list():
    print("=" * 60)
    print("TEST 6: Enrich findings list (flat)")
    print("=" * 60)

    findings = [
        {"code": "TELNET_OPEN", "ip": "192.168.1.1", "port": 23},
        {"code": "DB_EXPOSED", "ip": "192.168.1.40", "port": 3306},
        {"code": "SSH_OPEN", "ip": "192.168.1.20", "port": 22},
    ]

    enriched = enrich_findings_list(findings)

    for f in enriched:
        assert f"explanation_ro" in f, f"Missing explanation_ro for {f['code']}"
        assert f"explanation_en" in f, f"Missing explanation_en for {f['code']}"
        assert "fix_steps_ro" in f, f"Missing fix_steps_ro for {f['code']}"
        assert "severity" in f, f"Missing severity for {f['code']}"
        assert "points" in f, f"Missing points for {f['code']}"
        print(f"  OK: {f['code']} -> severity={f['severity']}, "
              f"points={f['points']}, "
              f"fix_steps={len(f['fix_steps_ro'])} steps")

    assert enriched[0]["points"] == 20  # TELNET
    assert enriched[1]["points"] == 20  # DB
    assert enriched[2]["points"] == 0   # SSH
    print("  PASSED\n")


def test_assistant_template_mode():
    print("=" * 60)
    print("TEST 7: Assistant Q&A (template fallback)")
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
                "open_ports": [80],
            },
        ],
        "findings": [
            {"code": "HTTP_ADMIN_CLEARTEXT", "ip": "192.168.1.1",
             "port": 80, "severity": "medium"},
        ],
    }

    assistant = Assistant(mock_scan, enable_cloud=False, enable_local=False)

    # Status
    status = assistant.status
    assert status["template"] is True
    print(f"  Status: cloud={status['cloud']}, local={status['local']}, template={status['template']}")

    # Explain
    result = assistant.explain(
        "HTTP_ADMIN_CLEARTEXT",
        {"ip": "192.168.1.1", "vendor": "TP-Link", "hostname": "router.lan",
         "type": "router", "port": 80, "service": "http"},
        language="ro",
    )
    assert result["source"] == "template"
    assert len(result["fix_steps"]) >= 2
    print(f"  Explain source: {result['source']}, fix_steps: {len(result['fix_steps'])}")

    # Get fix
    fix = assistant.get_fix(
        "HTTP_ADMIN_CLEARTEXT",
        {"ip": "192.168.1.1", "vendor": "TP-Link", "port": 80, "service": "http"},
        language="en",
    )
    assert fix["source"] == "template"
    print(f"  Fix source: {fix['source']}, steps: {len(fix['steps'])}")

    # Reset
    assistant.reset()
    assert len(assistant.chatbot.history) == 0
    print("  Reset: OK")

    print("  PASSED\n")


if __name__ == "__main__":
    test_templates()
    test_fingerprinting()
    test_ai_service_template_fallback()
    test_chatbot_context()
    test_enrich_scan_data()
    test_enrich_findings_list()
    test_assistant_template_mode()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
