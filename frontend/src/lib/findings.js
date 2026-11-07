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
  switch (severity) {
    case "high":
      return {
        bg: "bg-red-50",
        border: "border-red-300",
        text: "text-risk-high",
        dot: "bg-risk-high",
      };
    case "medium":
      return {
        bg: "bg-amber-50",
        border: "border-amber-300",
        text: "text-risk-medium",
        dot: "bg-risk-medium",
      };
    case "low":
      return {
        bg: "bg-blue-50",
        border: "border-blue-300",
        text: "text-risk-low",
        dot: "bg-risk-low",
      };
    case "info":
    default:
      return {
        bg: "bg-gray-50",
        border: "border-gray-300",
        text: "text-risk-info",
        dot: "bg-risk-info",
      };
  }
}

export function deviceIcon(type) {
  switch (type) {
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
