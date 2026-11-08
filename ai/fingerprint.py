"""
Device fingerprinting: ghiceste tipul dispozitivului
din vendor (MAC OUI), hostname si serviciile detectate.
"""

DEVICE_SIGNATURES = {
    "router": {
        "vendors": [
            "tp-link", "netgear", "asus", "cisco", "linksys", "d-link",
            "huawei", "zte", "mikrotik", "ubiquiti", "tenda", "xiaomi",
            "mercusys", "draytek", "juniper", "aruba", "fortinet",
        ],
        "services": ["domain", "upnp"],
        "hostname_patterns": ["router", "gateway", "gw", "modem", "rt-", "dsl"],
        "icon": "\U0001f310",
        "label": {"ro": "Router", "en": "Router"},
    },
    "camera": {
        "vendors": [
            "hikvision", "dahua", "axis", "reolink", "wyze", "amcrest",
            "vivotek", "foscam", "annke", "ezviz", "eufy", "arlo",
            "ring", "nest", "unifi", "lorex",
        ],
        "services": ["rtsp"],
        "hostname_patterns": ["cam", "ipcam", "camera", "dvr", "nvr"],
        "icon": "\U0001f4f7",
        "label": {"ro": "Camera IP", "en": "IP Camera"},
    },
    "printer": {
        "vendors": [
            "hp", "hewlett", "canon", "epson", "brother", "lexmark",
            "xerox", "ricoh", "kyocera", "samsung", "konica",
        ],
        "services": ["jetdirect", "ipp", "printer"],
        "hostname_patterns": ["printer", "prn", "print", "laserjet", "deskjet", "officejet"],
        "icon": "\U0001f5a8️",
        "label": {"ro": "Imprimanta", "en": "Printer"},
    },
    "phone": {
        "vendors": [
            "samsung", "apple", "xiaomi", "huawei", "oneplus", "google",
            "oppo", "vivo", "realme", "motorola", "nokia", "sony",
            "lg", "zte", "honor",
        ],
        "services": [],
        "hostname_patterns": [
            "iphone", "galaxy", "pixel", "phone", "android",
            "redmi", "poco", "oneplus", "huawei",
        ],
        "icon": "\U0001f4f1",
        "label": {"ro": "Telefon", "en": "Phone"},
    },
    "smart_tv": {
        "vendors": ["samsung", "lg", "sony", "vizio", "tcl", "hisense", "philips"],
        "services": ["googlecast", "dial"],
        "hostname_patterns": [
            "tv", "smart-tv", "smarttv", "chromecast", "firestick",
            "fire-tv", "roku", "appletv", "android-tv",
        ],
        "icon": "\U0001f4fa",
        "label": {"ro": "Smart TV", "en": "Smart TV"},
    },
    "computer": {
        "vendors": [
            "dell", "lenovo", "hp", "hewlett", "asus", "acer", "apple",
            "msi", "gigabyte", "intel", "microsoft", "razer",
        ],
        "services": ["ms-wbt-server", "microsoft-ds"],
        "hostname_patterns": [
            "laptop", "desktop", "pc", "macbook", "imac", "workstation",
            "dell", "lenovo", "thinkpad",
        ],
        "icon": "\U0001f4bb",
        "label": {"ro": "Calculator", "en": "Computer"},
    },
    "smart_home": {
        "vendors": ["espressif", "tuya", "sonoff", "shelly", "ikea"],
        "services": ["mqtt", "coap"],
        "hostname_patterns": [
            "hub", "smart", "echo", "alexa", "nest", "homepod",
            "esp32", "esp8266", "tasmota", "shelly",
        ],
        "icon": "\U0001f3e0",
        "label": {"ro": "Dispozitiv Smart Home", "en": "Smart Home Device"},
    },
    "server": {
        "vendors": [],
        "services": ["mysql", "postgresql", "redis", "mongodb", "ssh", "ftp"],
        "hostname_patterns": ["srv", "server", "nas", "db", "web", "mail"],
        "icon": "\U0001f5a5️",
        "label": {"ro": "Server", "en": "Server"},
    },
}

# Prioritatea de matching: device-urile mai specifice au prioritate
# cand vendor-ul apare in mai multe categorii (ex: Samsung = phone si smart_tv)
PRIORITY_ORDER = [
    "camera", "printer", "smart_home", "smart_tv",
    "router", "server", "phone", "computer",
]


def guess_device_type(host):
    """
    Ghiceste tipul dispozitivului pe baza datelor din scan.

    Args:
        host: dict cu:
            - vendor (str): producatorul din MAC OUI, ex: "TP-Link"
            - hostname (str): hostname-ul, ex: "router.lan"
            - services (list[str]): serviciile detectate, ex: ["http", "domain", "upnp"]
            - is_gateway (bool): daca e gateway-ul retelei

    Returns:
        dict cu type, icon, label_ro, label_en
    """
    vendor = (host.get("vendor") or "").lower()
    hostname = (host.get("hostname") or "").lower()
    services = [s.lower() for s in host.get("services", [])]
    is_gateway = host.get("is_gateway", False)

    if is_gateway:
        sig = DEVICE_SIGNATURES["router"]
        return {
            "type": "router",
            "icon": sig["icon"],
            "label_ro": sig["label"]["ro"],
            "label_en": sig["label"]["en"],
        }

    scores = {}
    for device_type in PRIORITY_ORDER:
        sig = DEVICE_SIGNATURES[device_type]
        score = 0

        for v in sig.get("vendors", []):
            if v in vendor:
                score += 3
                break

        for s in sig.get("services", []):
            if s in services:
                score += 2
                break

        for p in sig.get("hostname_patterns", []):
            if p in hostname:
                score += 2
                break

        if score > 0:
            scores[device_type] = score

    if not scores:
        return {
            "type": "unknown",
            "icon": "❓",
            "label_ro": "Dispozitiv necunoscut",
            "label_en": "Unknown device",
        }

    # Samsung cu hostname "tv" = smart_tv, nu phone
    # Rezolvat prin priority order -- camera/printer/smart_tv au prioritate
    best_score = max(scores.values())
    for device_type in PRIORITY_ORDER:
        if scores.get(device_type) == best_score:
            sig = DEVICE_SIGNATURES[device_type]
            return {
                "type": device_type,
                "icon": sig["icon"],
                "label_ro": sig["label"]["ro"],
                "label_en": sig["label"]["en"],
            }

    # fallback (nu ar trebui sa ajunga aici)
    best = max(scores, key=scores.get)
    sig = DEVICE_SIGNATURES[best]
    return {
        "type": best,
        "icon": sig["icon"],
        "label_ro": sig["label"]["ro"],
        "label_en": sig["label"]["en"],
    }


def suggest_device_name(device: dict, language: str = "ro") -> str:
    """Generate a friendly suggested name like 'Camera de supraveghere Hikvision'."""
    device_type = device.get("type", "unknown")
    vendor = device.get("vendor", "")
    hostname = device.get("hostname", "")

    sig = DEVICE_SIGNATURES.get(device_type)
    if sig:
        label = sig["label"].get(language, sig["label"]["ro"])
    else:
        label = "Dispozitiv necunoscut" if language == "ro" else "Unknown device"

    vendor_short = vendor.split()[0] if vendor else ""
    if vendor_short and vendor_short.lower() not in label.lower():
        return f"{label} {vendor_short}"
    if hostname and hostname.lower() not in ("localhost", "") and len(hostname) < 30:
        return f"{label} ({hostname})"
    return label
