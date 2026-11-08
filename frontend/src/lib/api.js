// API client. Defaults to MOCK mode so person C can develop without backend.
// Set VITE_USE_MOCK=0 in frontend/.env.local to hit the real backend once
// person B's FastAPI is up on :8000 (see vite.config.js proxy).
// The shape of each return value MUST match docs/api_contract.json.

import { mockScan, mockPerfect, mockBroken } from "../data/mockScan";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "0";

// Simulate a small delay so loading states are visible in mock mode.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// The backend answers every message (errors, guardrail refusals) in the UI's language (NFR-09).
let apiLanguage = "ro";
export function setApiLanguage(lang) {
  apiLanguage = lang === "en" ? "en" : "ro";
}

export function apiFetch(url, options = {}) {
  return fetch(url, { ...options, headers: { ...options.headers, "Accept-Language": apiLanguage } });
}

// FastAPI puts the reason in {"detail": ...} (e.g. why the guardrail refused a scan); show it, not just the code.
export async function httpError(r) {
  let message = `HTTP ${r.status}`;
  try {
    const body = await r.json();
    if (typeof body?.detail === "string") message = body.detail;
  } catch {
    // not JSON
  }
  const err = new Error(message);
  err.status = r.status;
  return err;
}

export async function getLatestScan() {
  if (USE_MOCK) {
    await sleep(250);
    return mockScan;
  }
  const r = await apiFetch("/api/scan/latest");
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function getScan(id) {
  if (USE_MOCK) {
    await sleep(150);
    if (id === "demo-after-fixes") return mockPerfect;
    if (id === "demo-broken") return mockBroken;
    return mockScan;
  }
  const r = await apiFetch(`/api/scan/${encodeURIComponent(id)}`);
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function uploadXml(file) {
  if (USE_MOCK) {
    await sleep(400);
    if (file?.name?.toLowerCase().includes("broken")) return mockBroken;
    if (file?.name?.toLowerCase().includes("after")) return mockPerfect;
    return mockScan;
  }
  const fd = new FormData();
  fd.append("file", file);
  const r = await apiFetch("/api/scan/upload", { method: "POST", body: fd });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

// Live scan = background job: preview (what & where, no scan) -> start -> poll -> done / cancel.
let mockPolls = 0;

export async function getLiveScanPreview() {
  if (USE_MOCK) {
    await sleep(200);
    return { allowed: true, target: "192.168.1.0/24", ssid: "RSH-demo", subnet: "192.168.1.0/24", reason: "" };
  }
  const r = await apiFetch("/api/scan/live/preview");
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function startLiveScan() {
  if (USE_MOCK) {
    mockPolls = 0;
    return { job_id: "mock", status: "running", phase: "discovery", percent: 0 };
  }
  const r = await apiFetch("/api/scan/live", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true }),
  });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function getLiveScan(jobId) {
  if (USE_MOCK) {
    mockPolls += 1;
    const percent = Math.min(100, mockPolls * 20);
    return percent < 100
      ? { job_id: jobId, status: "running", phase: "tcp", percent, remaining: "0:00:10" }
      : { job_id: jobId, status: "done", percent: 100, result: mockScan };
  }
  const r = await apiFetch(`/api/scan/live/${encodeURIComponent(jobId)}`);
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function cancelLiveScan(jobId) {
  if (USE_MOCK) return { job_id: jobId, status: "cancelled" };
  const r = await apiFetch(`/api/scan/live/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function getHistory() {
  if (USE_MOCK) {
    await sleep(150);
    return mockScan.history;
  }
  const r = await apiFetch("/api/scans/history");
  if (!r.ok) throw await httpError(r);
  return r.json();
}

// FR-10: everything that changed between two scans (devices, ports, findings, score).
export async function getDiff(oldScanId, newScanId) {
  if (USE_MOCK) {
    await sleep(150);
    return {
      old_scan_id: oldScanId, new_scan_id: newScanId, old_score: 60, new_score: 100,
      resolved_findings: [{ ip: "192.168.1.30", port: 23, finding_code: "TELNET_OPEN" }],
      new_findings: [], devices_added: [], devices_removed: [],
      ports_opened: [{ ip: "192.168.1.1", port: 443, protocol: "tcp", service: "https" }],
      ports_closed: [{ ip: "192.168.1.30", port: 23, protocol: "tcp", service: "telnet" }],
    };
  }
  const r = await apiFetch(`/api/diff/${encodeURIComponent(oldScanId)}/${encodeURIComponent(newScanId)}`);
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function deleteHistory() {
  if (USE_MOCK) {
    await sleep(100);
    return { ok: true };
  }
  const r = await apiFetch("/api/scans/history", { method: "DELETE" });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function askAssistant(question, scanId, language, expert = false, allowWeb = false) {
  if (USE_MOCK) {
    await sleep(400);
    return {
      answer:
        language === "en"
          ? "The most dangerous issue is CAMERA_STREAM_EXPOSED on 192.168.1.40 (Hikvision camera). Start here: disable RTSP from the camera app."
          : "Cea mai periculoasa problema este CAMERA_STREAM_EXPOSED pe 192.168.1.40 (camera Hikvision). Incepe cu aceasta: dezactiveaza RTSP din aplicatia camerei.",
      cites: [{ ip: "192.168.1.40", port: 554, code: "CAMERA_STREAM_EXPOSED" }],
    };
  }
  const r = await apiFetch("/api/assistant/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, scan_id: scanId, language, expert, allow_web: allowWeb }),
  });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function getDetailedFix(findingCode, deviceIp, scanId, language = "ro", expert = false) {
  if (USE_MOCK) {
    await sleep(500);
    return {
      fix_text: "1. Deschide setarile camerei in browser (192.168.1.40)\n2. Cauta Settings > Network > RTSP\n3. Activeaza Authentication\n4. Seteaza o parola puternica\n5. Verifica ca streamul nu e vizibil fara parola",
      source: "template",
      search_results: [{ title: "How to secure Hikvision camera RTSP", body: "Step by step guide...", href: "https://example.com" }],
      generic_advice: "Deschide aplicatia camerei sau acceseaz-o prin browser...",
      template_steps: ["Deschide setarile camerei", "Activeaza Authentication"],
    };
  }
  const r = await apiFetch("/api/assistant/detailed-fix", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_code: findingCode, device_ip: deviceIp, scan_id: scanId, language, expert }),
  });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function getDeviceNames() {
  if (USE_MOCK) {
    await sleep(100);
    return {
      "192.168.1.1": { custom_name: "Routerul WiFi", suggested_name: "Router TP-Link" },
      "192.168.1.40": { custom_name: "Camera din sufragerie", suggested_name: "Camera IP Hikvision" },
    };
  }
  const r = await apiFetch("/api/device-names");
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function saveDeviceName(ip, customName, suggestedName) {
  if (USE_MOCK) {
    await sleep(100);
    return { ok: true };
  }
  const r = await apiFetch("/api/device-names", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ip, custom_name: customName, suggested_name: suggestedName }),
  });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function suggestDeviceNames(scanId, language = "ro") {
  if (USE_MOCK) {
    await sleep(200);
    return {
      "192.168.1.1": "Router TP-Link",
      "192.168.1.40": "Camera IP Hikvision",
      "192.168.1.100": "Calculator",
      "192.168.1.50": "Dispozitiv necunoscut",
    };
  }
  const r = await apiFetch(`/api/device-names/suggest/${encodeURIComponent(scanId)}?language=${language}`);
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function narrateDiff(oldScanId, newScanId, language = "ro") {
  if (USE_MOCK) {
    await sleep(300);
    return {
      narrative: language === "en"
        ? "Security score improved from 35 to 55 (+20 points).\n\n1 resolved issue:\n  - CAMERA_STREAM_EXPOSED on 192.168.1.40 (port 554)\n\n1 new device: 192.168.1.50"
        : "Scorul de securitate a crescut de la 35 la 55 (+20 puncte).\n\n1 problema rezolvata:\n  - CAMERA_STREAM_EXPOSED pe 192.168.1.40 (port 554)\n\n1 dispozitiv nou: 192.168.1.50",
      old_score: 35, new_score: 55,
      resolved_count: 1, new_count: 0,
      devices_added_count: 1, devices_removed_count: 0,
    };
  }
  const r = await apiFetch(`/api/assistant/narrate-diff/${encodeURIComponent(oldScanId)}/${encodeURIComponent(newScanId)}?language=${language}`);
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function narrateDiffVsPrevious(scanId, language = "ro") {
  if (USE_MOCK) {
    await sleep(300);
    return {
      narrative: language === "en"
        ? "Security score improved from 35 to 55 (+20 points).\n\n1 resolved issue:\n  - CAMERA_STREAM_EXPOSED on 192.168.1.40 (port 554)"
        : "Scorul de securitate a crescut de la 35 la 55 (+20 puncte).\n\n1 problema rezolvata:\n  - CAMERA_STREAM_EXPOSED pe 192.168.1.40 (port 554)",
      old_score: 35, new_score: 55,
      resolved_count: 1, new_count: 0,
      devices_added_count: 0, devices_removed_count: 0,
    };
  }
  const r = await apiFetch(`/api/assistant/narrate-diff-latest/${encodeURIComponent(scanId)}?language=${language}`);
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export function getReportPdfUrl(scanId, language = "ro") {
  if (scanId) return `/api/report/pdf/${encodeURIComponent(scanId)}?language=${language}`;
  return `/api/report/pdf?language=${language}`;
}

export async function getAISettings() {
  if (USE_MOCK) {
    await sleep(100);
    return { provider: "local", has_groq_key: false };
  }
  const r = await apiFetch("/api/settings/ai");
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function updateAISettings(provider, groqApiKey) {
  if (USE_MOCK) {
    await sleep(100);
    return { provider, has_groq_key: !!groqApiKey };
  }
  const body = { provider };
  if (groqApiKey !== undefined) body.groq_api_key = groqApiKey;
  const r = await apiFetch("/api/settings/ai", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function getFixInfo(findingCode, ip, port, language = "ro", scanId) {
  if (USE_MOCK) {
    await sleep(200);
    const mockCommands = {
      TELNET_OPEN: { fix_type: "powershell", command: "Disable-WindowsOptionalFeature -Online -FeatureName TelnetClient -NoRestart", explanation: "Disables the Telnet component from Windows.", requires_admin: true },
      CAMERA_STREAM_EXPOSED: { fix_type: "portal", portal_url: `http://${ip}`, explanation: "Opens the camera panel. Disable open RTSP or set a password.", requires_admin: false },
    };
    return mockCommands[findingCode] || { fix_type: "powershell", command: `New-NetFirewallRule -DisplayName 'Block port ${port}' -Direction Inbound -Action Block -Protocol TCP -LocalPort ${port}`, explanation: `Blocks port ${port}`, requires_admin: true };
  }
  const r = await apiFetch("/api/fix/info", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_code: findingCode, ip, port, language, scan_id: scanId }),
  });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function executeFix(findingCode, ip, port, language = "ro", scanId) {
  if (USE_MOCK) {
    await sleep(1000);
    return { status: "remote", executed: false, message: "Mock mode: nothing runs." };
  }
  const r = await apiFetch("/api/fix/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_code: findingCode, ip, port, language, scan_id: scanId }),
  });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

// Re-check one port after a fix; the backend saves the result as a new history entry.
export async function verifyFix(scanId, findingCode, ip, port) {
  const r = await apiFetch("/api/fix/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scan_id: scanId, finding_code: findingCode, ip, port, confirm: true }),
  });
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function getFixResult(runId) {
  const r = await apiFetch(`/api/fix/result/${encodeURIComponent(runId)}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function narrateScan(scanId, language = "ro") {
  if (USE_MOCK) {
    await sleep(300);
    return {
      narrative:
        "Reteaua ta are 4 dispozitive si un scor de securitate de 40/100.\nAm gasit 5 probleme de securitate (2 critice).\n\nCele mai grave probleme:\n  - camera de supraveghere (192.168.1.40): Camera video transmite imagini accesibile oricui din retea.\n\nRecomandare: incepe cu CAMERA_STREAM_EXPOSED pe 192.168.1.40 -- aceasta e cea mai urgenta.",
      total_devices: 4,
      total_findings: 5,
      high_count: 2,
      medium_count: 3,
      score: 40,
    };
  }
  const url = scanId
    ? `/api/assistant/narrate/${encodeURIComponent(scanId)}?language=${language}`
    : `/api/assistant/narrate?language=${language}`;
  const r = await apiFetch(url);
  if (!r.ok) throw await httpError(r);
  return r.json();
}
