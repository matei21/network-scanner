// API client. Defaults to MOCK mode so person C can develop without backend.
// Set VITE_USE_MOCK=0 in frontend/.env.local to hit the real backend once
// person B's FastAPI is up on :8000 (see vite.config.js proxy).
// The shape of each return value MUST match docs/api_contract.json.

import { mockScan, mockPerfect, mockBroken } from "../data/mockScan";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "0";

// Simulate a small delay so loading states are visible in mock mode.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function getLatestScan() {
  if (USE_MOCK) {
    await sleep(250);
    return mockScan;
  }
  const r = await fetch("/api/scan/latest");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function getScan(id) {
  if (USE_MOCK) {
    await sleep(150);
    if (id === "demo-after-fixes") return mockPerfect;
    if (id === "demo-broken") return mockBroken;
    return mockScan;
  }
  const r = await fetch(`/api/scan/${encodeURIComponent(id)}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
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
  const r = await fetch("/api/scan/upload", { method: "POST", body: fd });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function runLiveScan({ confirm }) {
  if (!confirm) throw new Error("Live scan requires explicit confirmation.");
  if (USE_MOCK) {
    await sleep(800);
    return mockScan;
  }
  const r = await fetch("/api/scan/live", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function getHistory() {
  if (USE_MOCK) {
    await sleep(150);
    return mockScan.history;
  }
  const r = await fetch("/api/scans/history");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function deleteHistory() {
  if (USE_MOCK) {
    await sleep(100);
    return { ok: true };
  }
  const r = await fetch("/api/scans/history", { method: "DELETE" });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function askAssistant(question, scanId, language) {
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
  const r = await fetch("/api/assistant/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, scan_id: scanId, language }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function getDetailedFix(findingCode, deviceIp, scanId, language = "ro") {
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
  const r = await fetch("/api/assistant/detailed-fix", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_code: findingCode, device_ip: deviceIp, scan_id: scanId, language }),
  });
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
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
