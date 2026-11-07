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

export async function askAssistant(question, scanId) {
  if (USE_MOCK) {
    await sleep(400);
    return {
      answer:
        "Cea mai periculoasa problema este CAMERA_STREAM_EXPOSED pe 192.168.1.40 (camera Hikvision). Incepe cu aceasta: dezactiveaza RTSP din aplicatia camerei.",
      cites: [{ ip: "192.168.1.40", port: 554, code: "CAMERA_STREAM_EXPOSED" }],
    };
  }
  const r = await fetch("/api/assistant/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, scan_id: scanId }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
