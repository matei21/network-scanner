import { CheckCircle2, AlertTriangle, MonitorSmartphone, MonitorX, DoorOpen, DoorClosed, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";

// FR-10: the full difference between two scans, as lists (icon + text, never colour alone).
function Section({ icon: Icon, title, items, tone }) {
  if (!items.length) return null;
  return (
    <div>
      <div className={`flex items-center gap-2 font-semibold ${tone}`}>
        <Icon className="w-4 h-4 shrink-0" aria-hidden />
        {title} ({items.length})
      </div>
      <ul className="mt-1 ml-6 list-disc space-y-0.5 text-gray-800">
        {items.map((text) => (
          <li key={text} className="break-all">{text}</li>
        ))}
      </ul>
    </div>
  );
}

export default function DiffDetails({ diff }) {
  const { t } = useLanguage();
  if (!diff) return null;

  const finding = (f) => `${f.finding_code} - ${f.ip}${f.port != null ? `:${f.port}` : ""}`;
  const port = (p) => `${p.ip}:${p.port}/${p.protocol}${p.service ? ` (${p.service})` : ""}`;
  // A device that appeared or disappeared already explains its ports.
  const opened = (diff.ports_opened || []).filter((p) => !(diff.devices_added || []).includes(p.ip));
  const closed = (diff.ports_closed || []).filter((p) => !(diff.devices_removed || []).includes(p.ip));

  const sections = [
    { icon: CheckCircle2, title: t("diff_resolved"), items: (diff.resolved_findings || []).map(finding), tone: "text-risk-safe" },
    { icon: AlertTriangle, title: t("diff_new_findings"), items: (diff.new_findings || []).map(finding), tone: "text-risk-high" },
    { icon: MonitorSmartphone, title: t("diff_devices_added"), items: diff.devices_added || [], tone: "text-risk-medium" },
    { icon: MonitorX, title: t("diff_devices_removed"), items: diff.devices_removed || [], tone: "text-gray-700" },
    { icon: DoorOpen, title: t("diff_ports_opened"), items: opened.map(port), tone: "text-risk-medium" },
    { icon: DoorClosed, title: t("diff_ports_closed"), items: closed.map(port), tone: "text-risk-safe" },
  ];
  const nothing = sections.every((s) => !s.items.length);

  const delta = diff.old_score != null && diff.new_score != null ? diff.new_score - diff.old_score : null;
  const ScoreIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;

  return (
    <div className="space-y-3 text-base">
      {delta !== null && (
        <div className="flex items-center gap-2 font-semibold text-gray-800">
          <ScoreIcon className="w-4 h-4" aria-hidden />
          {t("diff_score")}: {diff.old_score} → {diff.new_score} ({delta > 0 ? `+${delta}` : delta})
        </div>
      )}
      {sections.map((s) => (
        <Section key={s.title} {...s} />
      ))}
      {nothing && <p className="text-gray-700">{t("diff_nothing")}</p>}
    </div>
  );
}
