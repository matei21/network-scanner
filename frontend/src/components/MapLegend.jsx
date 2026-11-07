import { useLanguage } from "../i18n/LanguageContext";
import { deviceTypeLabel } from "../lib/findings";
import DeviceIcon from "./DeviceIcon";

const SEVERITY_LEGEND = [
  { key: "high",   bg: "rgba(248, 201, 201, 0.85)", ring: "#B91C1C" },
  { key: "medium", bg: "rgba(255, 224, 163, 0.85)", ring: "#B45309" },
  { key: "low",    bg: "rgba(191, 219, 254, 0.85)", ring: "#1D4ED8" },
  { key: "info",   bg: "rgba(229, 231, 235, 0.85)", ring: "#6B7280" },
  { key: "safe",   bg: "rgba(200, 230, 201, 0.85)", ring: "#2E7D32" },
];

export default function MapLegend({ devices }) {
  const { t, lang } = useLanguage();

  const types = Array.from(
    new Set((devices || []).map((d) => d.type || "unknown"))
  );

  return (
    <div
      className="rounded-2xl p-5 border"
      style={{
        background: "rgba(255, 255, 255, 0.75)",
        borderColor: "var(--border)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
      }}
    >
      <h3 className="font-bold text-lg mb-4">
        {lang === "ro" ? "Legenda" : "Legend"}
      </h3>

      {/* ROW 1 — severity: big dots with label underneath, horizontal */}
      <div className="mb-5">
        <div className="text-sm font-semibold mb-3" style={{ color: "var(--text-muted)" }}>
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
              <span className="text-sm font-semibold text-center">
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
        <div className="text-sm font-semibold mb-3" style={{ color: "var(--text-muted)" }}>
          {lang === "ro" ? "Iconite — tip dispozitiv" : "Icons — device type"}
        </div>
                <div className="flex flex-wrap gap-4 justify-start">
          {types.map((type) => (
            <div key={type} className="flex flex-col items-center gap-2">
              <span
                className="inline-flex w-16 h-16 shrink-0 items-center justify-center rounded-full bg-white border-2"
                style={{ borderColor: "var(--border)" }}
              >
                <DeviceIcon type={type} size={56} />
              </span>
              <span className="text-sm text-center">
                {deviceTypeLabel(type, lang)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}