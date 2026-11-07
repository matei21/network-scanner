import { useMemo, useState } from "react";
import DeviceIcon from "./DeviceIcon";
import DeviceDetailModal from "./DeviceDetailModal";
import { useLanguage } from "../i18n/LanguageContext";
import { deviceTypeLabel } from "../lib/findings";

// Dedupe devices by ip+mac (backend sometimes emits one row per findings
// group) so each node appears once on the map.
function dedupe(devices) {
  const seen = new Map();
  for (const d of devices || []) {
    const key = `${d.ip}|${d.mac || ""}`;
    const prev = seen.get(key);
    if (prev) {
      const portKey = (p) => `${p.protocol}/${p.port}`;
      const existing = new Set((prev.open_ports || []).map(portKey));
      for (const p of d.open_ports || []) {
        if (!existing.has(portKey(p))) prev.open_ports.push(p);
      }
      prev.findings = [...(prev.findings || []), ...(d.findings || [])];
    } else {
      seen.set(key, {
        ...d,
        open_ports: [...(d.open_ports || [])],
        findings: [...(d.findings || [])],
      });
    }
  }
  return Array.from(seen.values());
}

function highestSeverity(findings) {
  if (!findings?.length) return null;
  if (findings.some((f) => f.severity === "high")) return "high";
  if (findings.some((f) => f.severity === "medium")) return "medium";
  if (findings.some((f) => f.severity === "low")) return "low";
  return "info";
}

const SEVERITY_RING = {
  high: "#B91C1C",
  medium: "#B45309",
  low: "#1D4ED8",
  info: "#6B7280",
};

const SEVERITY_BG = {
  high: "rgba(248, 201, 201, 0.85)",
  medium: "rgba(255, 224, 163, 0.85)",
  low: "rgba(191, 219, 254, 0.85)",
  info: "rgba(229, 231, 235, 0.85)",
};

export default function NetworkMap({ devices }) {
  const { t, lang } = useLanguage();
  const [selected, setSelected] = useState(null);
  const nodes = useMemo(() => dedupe(devices || []), [devices]);

  // Pick first router as hub; if none, first device.
  const { hub, others } = useMemo(() => {
    const list = [...nodes];
    const routerIdx = list.findIndex((d) => d.type === "router");
    const hubIdx = routerIdx >= 0 ? routerIdx : 0;
    const h = list[hubIdx];
    const o = list.filter((_, i) => i !== hubIdx);
    return { hub: h, others: o };
  }, [nodes]);

  if (!nodes.length) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-6 text-center text-gray-700">
        {lang === "ro"
          ? "Niciun dispozitiv detectat inca."
          : "No devices detected yet."}
      </div>
    );
  }

  // Layout maths: hub at center, others on a circle around it. On narrow
  // screens the circle shrinks; icons stay 64 px minimum.
  const vbW = 720;
  const vbH = 440;
  const cx = vbW / 2;
  const cy = vbH / 2;
  const radius = Math.min(vbW, vbH) * 0.25;

  const positioned = others.map((d, i) => {
    const angle = (i / Math.max(1, others.length)) * Math.PI * 2 - Math.PI / 2;
    return {
      device: d,
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
    };
  });

  return (
    <>
      <div className="network-map rounded-2xl border border-gray-200 p-4 relative overflow-hidden">
        <div className="relative z-10 flex items-baseline justify-between mb-2">
          <h3 className="font-bold text-lg">
            {lang === "ro" ? "Harta retelei" : "Network map"}
          </h3>
          <span className="text-sm text-gray-600">
            {lang === "ro"
              ? "Apasa pe un dispozitiv pentru detalii"
              : "Click a device for details"}
          </span>
        </div>

        <div className="relative z-10 w-full" style={{ aspectRatio: `${vbW} / ${vbH}` }}>
          {/* SVG layer draws the connection lines underneath */}
          <svg
            viewBox={`0 0 ${vbW} ${vbH}`}
            preserveAspectRatio="xMidYMid meet"
            className="absolute inset-0 w-full h-full"
            aria-hidden
          >
            {positioned.map((p, i) => {
              const sev = highestSeverity(p.device.findings);
              const stroke = sev ? SEVERITY_RING[sev] : "var(--border)";
              return (
                <line
                  key={i}
                  x1={cx}
                  y1={cy}
                  x2={p.x}
                  y2={p.y}
                  stroke={stroke}
                  strokeWidth={sev === "high" ? 2.5 : 1.5}
                  strokeOpacity={sev ? 0.55 : 0.35}
                  strokeDasharray={sev ? "0" : "4 4"}
                />
              );
            })}
          </svg>

          {/* Hub node (router) */}
          {hub && (
            <NodeButton
              device={hub}
              xPct={50}
              yPct={50}
              label={deviceTypeLabel(hub.type, lang)}
              size={96}
              isHub
              onClick={() => setSelected(hub)}
            />
          )}

          {/* Other devices around the hub */}
          {positioned.map(({ device, x, y }) => (
            <NodeButton
              key={`${device.ip}|${device.mac || ""}`}
              device={device}
              xPct={(x / vbW) * 100}
              yPct={(y / vbH) * 100}
              label={deviceTypeLabel(device.type, lang)}
              size={76}
              onClick={() => setSelected(device)}
            />
          ))}
        </div>
      </div>

      {selected && (
        <DeviceDetailModal device={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}

function NodeButton({ device, xPct, yPct, label, size, isHub, onClick }) {
  const sev = highestSeverity(device.findings);
  const bg = sev ? SEVERITY_BG[sev] : "rgba(200, 230, 201, 0.85)";
  const ring = sev ? SEVERITY_RING[sev] : "var(--border-strong)";
  const count = device.findings?.length || 0;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`${label} ${device.hostname || device.ip} - ${count} ${
        count === 1 ? "problem" : "problems"
      }`}
      className="absolute flex flex-col items-center gap-1 -translate-x-1/2 -translate-y-1/2 group"
      style={{ left: `${xPct}%`, top: `${yPct}%` }}
    >
      <span
        className="rounded-full flex items-center justify-center overflow-hidden transition shadow-md group-hover:shadow-lg group-hover:scale-105"
        style={{
          width: size,
          height: size,
          border: `3px solid ${ring}`,
          backgroundColor: bg,
        }}
      >
        <DeviceIcon type={device.type} size={size - 10} />
      </span>
      <span
        className="text-xs font-semibold whitespace-nowrap max-w-[120px] truncate px-2 py-0.5 rounded-md"
        style={{
          fontSize: "0.75rem",
          backgroundColor: "rgba(255, 255, 255, 0.75)",
          color: "#1A2E1E",
        }}
      >
        {device.hostname || device.ip}
      </span>
      {isHub && (
        <span
          className="text-[10px] uppercase tracking-wider px-1.5 rounded"
          style={{
            background: "var(--accent-soft)",
            color: "var(--accent-dark)",
          }}
        >
          {label}
        </span>
      )}
    </button>
  );
}
