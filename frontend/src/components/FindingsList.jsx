import { useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { flattenFindings, sortedBySeverity, severityColorClasses } from "../lib/findings";
import DeviceIcon from "./DeviceIcon";
import { ChevronDown, ChevronUp, Flame } from "lucide-react";

function SeverityBadge({ severity }) {
  const { t } = useLanguage();
  const theme = severityColorClasses(severity);
  const label = t(`severity_${severity}`) || severity;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border ${theme.border} ${theme.bg} ${theme.text} text-sm font-medium`}
    >
      <span className={`w-2 h-2 rounded-full ${theme.dot}`} aria-hidden />
      {label}
    </span>
  );
}

function FindingItem({ finding, lang, expert, isTop }) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(isTop);
  const theme = severityColorClasses(finding.severity);
  const device = finding.device;
  const explanation =
    lang === "ro" ? finding.explanation_ro : finding.explanation_en;
  const steps = (lang === "ro" ? finding.fix_steps_ro : finding.fix_steps_en) || [];

  return (
    <article
      className={`rounded-xl border ${theme.border} ${theme.bg} p-4`}
      aria-labelledby={`f-${finding.code}-${device?.ip}-${finding.port}`}
    >
      <header className="flex flex-wrap items-center gap-3">
        <SeverityBadge severity={finding.severity} />
        <code
          id={`f-${finding.code}-${device?.ip}-${finding.port}`}
          className="font-mono text-sm px-2 py-0.5 bg-white border border-gray-200 rounded"
        >
          {finding.code}
        </code>
        <span className="text-sm text-gray-700 inline-flex items-center gap-1.5">
          <DeviceIcon type={device?.type} size={20} />
          {device?.hostname || device?.ip} · {t("finding_port")} {finding.port}
        </span>
        {isTop && (
          <span className="ml-auto inline-flex items-center gap-1 text-sm text-risk-high font-semibold">
            <Flame className="w-4 h-4" aria-hidden />
            {t("finding_most_dangerous")}
          </span>
        )}
      </header>

      <p className="mt-3 text-lg text-gray-900">{explanation}</p>

      {expert && finding.evidence && (
        <p className="mt-2 text-sm text-gray-600">
          <span className="font-semibold">{t("finding_evidence")}:</span>{" "}
          <span className="font-mono">{finding.evidence}</span>
          {finding.cis_control && (
            <span className="ml-3">· {finding.cis_control}</span>
          )}
          {finding.owasp_iot && (
            <span className="ml-3">· OWASP {finding.owasp_iot}</span>
          )}
        </p>
      )}

      {steps.length > 0 && (
        <>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="mt-3 inline-flex items-center gap-1 text-base font-semibold text-blue-700 hover:underline"
            aria-expanded={open}
          >
            {open ? (
              <>
                <ChevronUp className="w-5 h-5" aria-hidden />
                {t("finding_collapse")}
              </>
            ) : (
              <>
                <ChevronDown className="w-5 h-5" aria-hidden />
                {t("finding_expand")}
              </>
            )}
          </button>
          {open && (
            <div className="mt-3 bg-white rounded-lg border border-gray-200 p-3">
              <div className="font-semibold mb-2">{t("finding_fix_title")}</div>
              <ol className="list-decimal pl-6 space-y-1 text-base">
                {steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          )}
        </>
      )}
    </article>
  );
}

export default function FindingsList({ scan, expert }) {
  const { lang, t } = useLanguage();
  const sorted = sortedBySeverity(flattenFindings(scan));
  if (sorted.length === 0) {
    return (
      <div className="text-center py-10 text-gray-700">
        {t("verdict_safe_desc")}
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {sorted.map((f, i) => (
        <FindingItem
          key={`${f.code}-${f.device?.ip}-${f.port}-${i}`}
          finding={f}
          lang={lang}
          expert={expert}
          isTop={i === 0}
        />
      ))}
    </div>
  );
}
