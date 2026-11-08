// Helpers over scan JSON. Pure functions; no React, no fetch.
// Contract lives at docs/api_contract.json.

const SEV_ORDER = { high: 0, medium: 1, low: 2, info: 3 };

export function flattenFindings(scan) {
  if (!scan?.devices) return [];
  const out = [];
  for (const d of scan.devices) {
    for (const f of d.findings || []) {
      out.push({ ...f, device: d });
    }
  }
  return out;
}

export function sortedBySeverity(findings) {
  return [...findings].sort((a, b) => {
    const s = (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9);
    if (s !== 0) return s;
    return (b.points || 0) - (a.points || 0);
  });
}

export function mostDangerous(scan) {
  const list = sortedBySeverity(flattenFindings(scan));
  return list[0] || null;
}

export function verdictFromScore(score) {
  if (score == null) return "error";
  if (score >= 70) return "safe";
  if (score >= 40) return "watch";
  return "at_risk";
}

// Backend-contract has no summary field — we derive it in the UI from the
// finding list so a grandparent-level reader still sees one plain sentence.
export function summarySentence(scan, lang) {
  if (!scan || scan.status === "error") {
    return lang === "ro"
      ? "Fisierul nu poate fi citit."
      : "The file cannot be read.";
  }
  const findings = flattenFindings(scan);
  if (findings.length === 0) {
    return lang === "ro"
      ? "Nu am gasit probleme importante."
      : "No important problems were found.";
  }
  const top = sortedBySeverity(findings)[0];
  const highCount = findings.filter((f) => f.severity === "high").length;
  if (lang === "ro") {
    const count = `${findings.length} ${findings.length === 1 ? "problema" : "probleme"}`;
    const severe =
      highCount > 0
        ? ` ${highCount} ${highCount === 1 ? "este grava" : "sunt grave"}.`
        : "";
    return `Reteaua ta are ${count}.${severe} Incepe cu ${top.code} pe ${top.ip}.`;
  }
  const count = `${findings.length} ${findings.length === 1 ? "problem" : "problems"}`;
  const severe = highCount > 0 ? ` ${highCount} serious.` : "";
  return `Your network has ${count}.${severe} Start with ${top.code} on ${top.ip}.`;
}

export function severityColorClasses(severity) {
  // Saturated tints that mirror the hero card's severity palette, so the
  // whole page reads at one intensity level (user feedback).
  switch (severity) {
    case "high":
      return {
        bg: "bg-red-200",
        border: "border-red-400",
        text: "text-risk-high",
        dot: "bg-risk-high",
      };
    case "medium":
      return {
        bg: "bg-amber-200",
        border: "border-amber-400",
        text: "text-risk-medium",
        dot: "bg-risk-medium",
      };
    case "low":
      return {
        bg: "bg-blue-200",
        border: "border-blue-400",
        text: "text-risk-low",
        dot: "bg-risk-low",
      };
    case "info":
    default:
      return {
        bg: "bg-gray-200",
        border: "border-gray-400",
        text: "text-risk-info",
        dot: "bg-risk-info",
      };
  }
}

// Hero card color: highest severity present in findings (not the raw score).
// If nothing at all → safe/green. Error state short-circuits.
export function heroVerdict(scan) {
  if (!scan || scan.status === "error") return "error";
  const findings = flattenFindings(scan);
  if (findings.some((f) => f.severity === "high")) return "at_risk";
  if (findings.some((f) => f.severity === "medium")) return "watch";
  if (findings.some((f) => f.severity === "low" || f.severity === "info"))
    return "watch";
  return "safe";
}

// The backend (ai/fingerprint.py) names some types differently from the UI.
const TYPE_ALIASES = { computer: "pc", smart_tv: "tv", smart_home: "iot" };

export function normalizeDeviceType(type) {
  return TYPE_ALIASES[type] || type || "unknown";
}

// Emoji fallback used if the PNG at /devices/<type>.png is missing.
export function deviceEmoji(type) {
  switch (normalizeDeviceType(type)) {
    case "router":
      return "🌐";
    case "camera":
      return "📹";
    case "printer":
      return "🖨️";
    case "tv":
      return "📺";
    case "pc":
    case "laptop":
      return "💻";
    case "phone":
      return "📱";
    case "iot":
      return "🔌";
    case "nas":
    case "server":
      return "🗄️";
    default:
      return "❓";
  }
}

// Returns the PNG path user drops into /public/devices/<name>.png.
// Keep names in sync with the user's icon set. pc + laptop share one icon
// (laptop.png); nas + server share one (nas.png).
export function deviceIconSrc(rawType) {
  const type = normalizeDeviceType(rawType);
  const name = (() => {
    switch (type) {
      case "router":
      case "camera":
      case "printer":
      case "tv":
      case "phone":
      case "iot":
      case "nas":
      case "unknown":
        return type;
      case "pc":
      case "laptop":
        return "laptop";
      case "server":
        return "nas";
      default:
        return "unknown";
    }
  })();
  return `/devices/${name}.png`;
}

// Back-compat alias used in older components.
export const deviceIcon = deviceEmoji;

// Human-readable device type label in RO / EN for the device cards.
export function deviceTypeLabel(type, lang) {
  const ro = {
    router: "Ruter",
    laptop: "Laptop",
    pc: "Computer",
    phone: "Telefon",
    tv: "Televizor",
    camera: "Camera",
    printer: "Imprimanta",
    iot: "Smart home",
    nas: "NAS",
    server: "Server",
    unknown: "Necunoscut",
  };
  const en = {
    router: "Router",
    laptop: "Laptop",
    pc: "PC",
    phone: "Phone",
    tv: "TV",
    camera: "Camera",
    printer: "Printer",
    iot: "Smart home",
    nas: "NAS",
    server: "Server",
    unknown: "Unknown device",
  };
  const dict = lang === "ro" ? ro : en;
  return dict[normalizeDeviceType(type)] || dict.unknown;
}
