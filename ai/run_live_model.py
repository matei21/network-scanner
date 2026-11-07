"""
Test live: verifica ca modelul Qwen 2.5 3B ruleaza si raspunde la prompt-uri.
Ruleaza: python -m ai.test_live_model
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import time
from ai.ai_service import AIService, LocalLLM
from ai.assistant import Assistant

print("=" * 60)
print("TEST LIVE: Qwen 2.5 3B Instruct")
print("=" * 60)

# Test 1: Verifica ca modelul se incarca
print("\n[1] Incarc modelul local...")
t0 = time.time()
ai = AIService(enable_cloud=False, enable_local=True)
t1 = time.time()
print(f"    Incarcat in {t1 - t0:.1f}s")
print(f"    Status: {ai.status}")
assert ai.status["local"] is True, "Modelul local nu s-a incarcat!"
print("    OK\n")

# Test 2: Intrebare simpla directa
print("[2] Intrebare simpla la model...")
t0 = time.time()
result = ai.chat(
    system_prompt="Raspunde in romana, maxim 2 propozitii.",
    user_message="Ce este un port deschis intr-o retea de calculatoare?",
)
t1 = time.time()
print(f"    Source: {result['source']}")
print(f"    Timp: {t1 - t0:.1f}s")
print(f"    Raspuns: {result['text'][:300]}")
assert result["source"] == "local", f"Expected local, got {result['source']}"
assert len(result["text"]) > 20, "Raspuns prea scurt"
print("    OK\n")

# Test 3: Assistant.ask() cu date de scan
print("[3] Assistant.ask() cu scan data...")
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

assistant = Assistant(mock_scan, enable_cloud=False, enable_local=True)
print(f"    Status: {assistant.status}")

t0 = time.time()
answer = assistant.ask("Ce dispozitiv e cel mai periculos din reteaua mea?")
t1 = time.time()
print(f"    Source: {answer['source']}")
print(f"    Timp: {t1 - t0:.1f}s")
print(f"    Raspuns: {answer['text'][:400]}")
assert answer["source"] == "local"
print("    OK\n")

# Test 4: Explain finding cu model
print("[4] Explain finding personalizat...")
t0 = time.time()
explanation = assistant.explain(
    "CAMERA_STREAM_EXPOSED",
    {"ip": "192.168.1.40", "vendor": "Hikvision", "hostname": "ipcam",
     "type": "camera", "port": 554, "service": "rtsp"},
    language="ro",
)
t1 = time.time()
print(f"    Source: {explanation['source']}")
print(f"    Timp: {t1 - t0:.1f}s")
print(f"    Text: {explanation['text'][:300]}")
print(f"    Fix steps: {len(explanation['fix_steps'])} pasi")
print(f"    CIS: {explanation['cis_control']}")
print("    OK\n")

# Test 5: Follow-up (conversatie)
print("[5] Follow-up conversational...")
t0 = time.time()
answer2 = assistant.ask("Si cum rezolv problema cu camera?")
t1 = time.time()
print(f"    Source: {answer2['source']}")
print(f"    Timp: {t1 - t0:.1f}s")
print(f"    Raspuns: {answer2['text'][:400]}")
print("    OK\n")

print("=" * 60)
print("ALL LIVE TESTS PASSED")
print("=" * 60)
