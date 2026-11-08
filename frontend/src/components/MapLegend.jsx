import { useLanguage } from "../i18n/LanguageContext";
import { deviceTypeLabel, normalizeDeviceType } from "../lib/findings";
import DeviceIcon from "./DeviceIcon";

const SEVERITY_LEGEND = [
  { key: "high",   bg: "var(--node-bg-high)",   ring: "var(--node-ring-high)" },
  { key: "medium", bg: "var(--node-bg-medium)", ring: "var(--node-ring-medium)" },
  { key: "low",    bg: "var(--node-bg-low)",    ring: "var(--node-ring-low)" },
  { key: "info",   bg: "var(--node-bg-info)",   ring: "var(--node-ring-info)" },
  { key: "safe",   bg: "var(--node-bg-safe)",   ring: "var(--node-ring-safe)" },
];

// Only the types the backend can recognise (ai/fingerprint.py). It never
// reports "laptop" (nmap cannot tell a laptop from a PC) or "nas".
const ALL_TYPES = ["router", "pc", "phone", "tv", "camera", "printer", "iot", "server", "unknown"];

export default function MapLegend({ devices }) {
  const { t, lang } = useLanguage();

  // Every device type is listed; the ones in this network are bold and full colour.
  // Types the UI has no name for count as "unknown", so each type appears once.
  const present = new Set(
    (devices || []).map((d) => {
      const type = { laptop: "pc", nas: "server" }[normalizeDeviceType(d.type)] || normalizeDeviceType(d.type);
      return ALL_TYPES.includes(type) ? type : "unknown";
    })
  );
  const types = ALL_TYPES;

  return (
    <div className="map-legend rounded-2xl p-5 border">
      <h3 className="font-bold text-lg mb-4">
        {lang === "ro" ? "Legenda" : "Legend"}
      </h3>

      {/* ROW 1 - severity: big dots with label underneath, horizontal */}
      <div className="mb-5">
        <div className="legend-label text-sm font-semibold mb-3">
          {lang === "ro" ? "Culori - gravitate" : "Colours - severity"}
        </div>
        <div className="flex flex-wrap gap-4 justify-start">
          {SEVERITY_LEGEND.map((s) => (
            <div key={s.key} className="flex flex-col items-center gap-2 min-w-[72px]">
              <span
                className="inline-block w-12 h-12 rounded-full border-4"
                style={{ background: s.bg, borderColor: s.ring }}
                aria-hidden
              />
              <span className="legend-text text-sm font-semibold text-center">
                {s.key === "safe"
                  ? (lang === "ro" ? "Fara probleme" : "No problems")
                  : t(`severity_${s.key}`)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ROW 2 - icons: big icons in a 3-column grid with label underneath */}
      <div>
        <div className="legend-label text-sm font-semibold mb-3">
          {lang === "ro" ? "Iconite - tip dispozitiv" : "Icons - device type"}
        </div>
                <div className="flex flex-wrap gap-4 justify-start">
          {types.map((type) => {
            const here = present.has(type);
            return (
              <div key={type} className={`flex flex-col items-center gap-2 ${here ? "" : "legend-absent"}`}>
                <span
                  className="icon-bubble inline-flex w-16 h-16 shrink-0 items-center justify-center rounded-full"
                  style={{
                    border: here ? "3px solid var(--border-strong)" : "2px solid var(--border)",
                  }}
                >
                  <DeviceIcon type={type} size={56} />
                </span>
                <span className={`legend-text text-sm text-center ${here ? "font-bold" : ""}`}>
                  {deviceTypeLabel(type, lang)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}