import { useEffect, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import {
  deviceTypeLabel,
  severityColorClasses,
  sortedBySeverity,
} from "../lib/findings";
import DeviceIcon from "./DeviceIcon";
import { X, ChevronDown, ChevronUp, Flame } from "lucide-react";

// Flashcard opened when a device is clicked on the NetworkMap.
export default function DeviceDetailModal({ device, onClose }) {
  const { t, lang } = useLanguage();
  const [openStep, setOpenStep] = useState(null);

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose?.();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!device) return null;
    const verdict = (() => {
    const f = device.findings || [];
    if (f.some((x) => x.severity === "high")) return "at_risk";
    if (f.some((x) => x.severity === "medium")) return "watch";
    if (f.some((x) => x.severity === "low")) return "attention";
    if (f.some((x) => x.severity === "info")) return "info";
    return "safe";
  })();
  const findings = sortedBySeverity(device.findings || []);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="device-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div className="device-modal rounded-2xl max-w-lg w-full p-6 shadow-xl max-h-[85vh] overflow-y-auto" data-verdict={verdict}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-4 min-w-0">
            <div
              className="w-20 h-20 shrink-0 rounded-full border-2 flex items-center justify-center overflow-hidden"
              style={{
                borderColor: {
                  at_risk: "#B91C1C",
                  watch: "#B45309",
                  attention: "#1D4ED8",
                  info: "#6B7280",
                  safe: "#2E7D32",
                }[verdict] || "var(--border)",
                backgroundColor: {
                  at_risk: "rgba(248, 201, 201, 0.85)",
                  watch: "rgba(255, 224, 163, 0.85)",
                  attention: "rgba(191, 219, 254, 0.85)",
                  info: "rgba(229, 231, 235, 0.85)",
                  safe: "rgba(200, 230, 201, 0.85)",
                }[verdict] || "rgba(255, 255, 255, 0.95)",
              }}
            >
              <DeviceIcon type={device.type} size={76} />
            </div>
            <div className="min-w-0">
              <h2
                id="device-modal-title"
                className="text-xl font-bold leading-tight"
              >
                {device.hostname || t("no_hostname")}
              </h2>
              <span
                className="inline-block mt-1 text-xs px-2 py-0.5 rounded-full"
                style={{
                  background: "var(--accent-soft)",
                  color: "var(--accent-dark)",
                }}
              >
                {deviceTypeLabel(device.type, lang)}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onClose?.()}
            aria-label={lang === "ro" ? "Inchide" : "Close"}
            className="p-1 rounded-lg hover:bg-gray-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-600">IP</dt>
          <dd className="font-mono">{device.ip}</dd>
          <dt className="text-gray-600">MAC</dt>
          <dd className="font-mono">{device.mac || t("no_mac")}</dd>
          <dt className="text-gray-600">{lang === "ro" ? "Producator" : "Vendor"}</dt>
          <dd>{device.vendor || t("no_vendor")}</dd>
          <dt className="text-gray-600">{t("open_ports")}</dt>
          <dd>{device.open_ports?.length || 0}</dd>
        </dl>

        {device.open_ports?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {device.open_ports.map((p) => (
              <span
                key={`${p.protocol}/${p.port}`}
                className="text-xs px-2 py-0.5 bg-gray-100 rounded border border-gray-200 tabular-nums"
                title={[p.service, p.product, p.version].filter(Boolean).join(" ")}
              >
                {p.port}/{p.protocol}
                {p.service ? ` · ${p.service}` : ""}
              </span>
            ))}
          </div>
        )}

        {findings.length > 0 ? (
          <div className="mt-5">
            <h3 className="font-bold text-lg mb-2">
              {findings.length} {t("findings_count")}
            </h3>
            <div className="space-y-2">
              {findings.map((f, i) => {
                const theme = severityColorClasses(f.severity);
                const key = `${f.code}-${i}`;
                const open = openStep === key;
                const explanation =
                  lang === "ro" ? f.explanation_ro : f.explanation_en;
                const steps =
                  (lang === "ro" ? f.fix_steps_ro : f.fix_steps_en) || [];
                return (
                  <div
                    key={key}
                    className={`rounded-lg border ${theme.border} ${theme.bg} p-3`}
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      {i === 0 && (
                        <Flame
                          className="w-4 h-4 text-risk-high"
                          aria-label={t("finding_most_dangerous")}
                        />
                      )}
                      <code className="font-mono text-xs px-1.5 py-0.5 bg-white border border-gray-200 rounded">
                        {f.code}
                      </code>
                      <span className={`text-sm font-semibold ${theme.text}`}>
                        {t(`severity_${f.severity}`)}
                      </span>
                      <span className="text-xs text-gray-600 ml-auto">
                        {t("finding_port")} {f.port}
                      </span>
                    </div>
                    <p className="mt-2 text-base">{explanation}</p>
                    {steps.length > 0 && (
                      <>
                        <button
                          type="button"
                          onClick={() => setOpenStep(open ? null : key)}
                          aria-expanded={open}
                          className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-blue-700 hover:underline"
                        >
                          {open ? (
                            <>
                              <ChevronUp className="w-4 h-4" />
                              {t("finding_collapse")}
                            </>
                          ) : (
                            <>
                              <ChevronDown className="w-4 h-4" />
                              {t("finding_expand")}
                            </>
                          )}
                        </button>
                        {open && (
                          <ol className="mt-2 list-decimal pl-6 space-y-1 text-sm bg-white/50 rounded p-2">
                            {steps.map((s, j) => (
                              <li key={j}>{s}</li>
                            ))}
                          </ol>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <p className="mt-5 text-gray-700">
            {lang === "ro"
              ? "Niciun risc identificat pentru acest dispozitiv."
              : "No risks found for this device."}
          </p>
        )}
      </div>
    </div>
  );
}
