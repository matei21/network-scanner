import { useState } from "react";
import { BellRing, ChevronDown, ChevronUp } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";
import DiffDetails from "./DiffDetails";

// FR-13: warn after an upload / live scan when something NEW appeared since the previous scan.
export default function ChangeAlert({ changes }) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);
  if (!changes) return null;

  const devices = changes.devices_added || [];
  const ports = (changes.ports_opened || []).filter((p) => !devices.includes(p.ip));
  const problems = changes.new_findings || [];
  if (!devices.length && !ports.length && !problems.length) return null;

  const parts = [
    devices.length && `${devices.length} ${t(devices.length === 1 ? "alert_device_one" : "alert_devices")}`,
    ports.length && `${ports.length} ${t(ports.length === 1 ? "alert_port_one" : "alert_ports")}`,
    problems.length && `${problems.length} ${t(problems.length === 1 ? "alert_problem_one" : "alert_problems")}`,
  ].filter(Boolean);

  return (
    <div role="status" className="rounded-2xl border-2 border-amber-500 bg-amber-50 p-4 text-amber-950">
      <div className="flex items-start gap-3">
        <BellRing className="w-6 h-6 shrink-0 text-amber-700" aria-hidden />
        <div className="flex-1">
          <div className="font-semibold text-lg">{t("alert_title")}</div>
          <p className="mt-1">
            {t("alert_since")} <span className="font-medium break-all">{changes.compared_with}</span>: {parts.join(", ")}.
          </p>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="mt-2 inline-flex items-center gap-1 font-medium underline"
          >
            {open ? <ChevronUp className="w-4 h-4" aria-hidden /> : <ChevronDown className="w-4 h-4" aria-hidden />}
            {open ? t("alert_hide") : t("alert_show")}
          </button>
          {open && (
            <div className="mt-3 rounded-lg bg-white p-3">
              <DiffDetails diff={changes} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
