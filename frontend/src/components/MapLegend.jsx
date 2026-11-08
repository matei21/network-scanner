import { useLanguage } from "../i18n/LanguageContext";
import { deviceTypeLabel } from "../lib/findings";
import DeviceIcon from "./DeviceIcon";

const SEVERITY_LEGEND = [
  { key: "high",   bg: "var(--node-bg-high)",   ring: "var(--node-ring-high)" },
  { key: "medium", bg: "var(--node-bg-medium)", ring: "var(--node-ring-medium)" },
  { key: "low",    bg: "var(--node-bg-low)",    ring: "var(--node-ring-low)" },
  { key: "info",   bg: "var(--node-bg-info)",   ring: "var(--node-ring-info)" },
  { key: "safe",   bg: "var(--node-bg-safe)",   ring: "var(--node-ring-safe)" },
];

export default function MapLegend({ devices }) {
  const { t, lang } = useLanguage();

  const types = Array.from(
    new Set((devices || []).map((d) => d.type || "unknown"))
  );

  return (
    <div className="map-legend rounded-2xl p-5 border">
      <h3 className="font-bold text-lg mb-4">
        {lang === "ro" ? "Legenda" : "Legend"}
      </h3>

      {/* ROW 1 — severity: big dots with label underneath, horizontal */}
      <div className="mb-5">
        <div className="legend-label text-sm font-semibold mb-3">
          {lang === "ro" ? "Culori — gravitate" : "Colours — severity"}
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

      {/* ROW 2 — icons: big icons in a 3-column grid with label underneath */}
      <div>
        <div className="legend-label text-sm font-semibold mb-3">
          {lang === "ro" ? "Iconite — tip dispozitiv" : "Icons — device type"}
        </div>
                <div className="flex flex-wrap gap-4 justify-start">
          {types.map((type) => (
            <div key={type} className="flex flex-col items-center gap-2">
              <span
                className="icon-bubble inline-flex w-16 h-16 shrink-0 items-center justify-center rounded-full border-2"
                style={{ borderColor: "var(--border)" }}
              >
                <DeviceIcon type={type} size={56} />
              </span>
              <span className="legend-text text-sm text-center">
                {deviceTypeLabel(type, lang)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}