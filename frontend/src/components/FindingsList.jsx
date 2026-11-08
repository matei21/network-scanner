import { useState, useEffect } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { flattenFindings, sortedBySeverity, severityColorClasses } from "../lib/findings";
import { getFixInfo, executeFix } from "../lib/api";
import DeviceIcon from "./DeviceIcon";
import { ChevronDown, ChevronUp, Flame, AlertOctagon, Terminal, ExternalLink, Play, CheckCircle2, Loader2, XCircle } from "lucide-react";

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

function FixButton({ findingCode, ip, port, lang }) {
  const [fixInfo, setFixInfo] = useState(null);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!findingCode || !ip) return;
    getFixInfo(findingCode, ip, port, lang).then(setFixInfo).catch(() => {});
  }, [findingCode, ip, port, lang]);

  if (!fixInfo) return null;

  async function handleExecute() {
    setStatus("running");
    try {
      const res = await executeFix(findingCode, ip, port, lang);
      setResult(res);
      setStatus(res.status === "success" ? "done" : "error");
    } catch (e) {
      setResult({ message: String(e.message || e) });
      setStatus("error");
    }
  }

  function handlePortal() {
    if (fixInfo.portal_url) window.open(fixInfo.portal_url, "_blank");
  }

  const isPortal = fixInfo.fix_type === "portal";
  const btnLabel = {
    idle: isPortal ? (lang === "ro" ? "Deschide panoul" : "Open panel") : (lang === "ro" ? "Rezolva automat" : "Auto-fix"),
    running: lang === "ro" ? "Se executa..." : "Running...",
    done: lang === "ro" ? "Rezolvat!" : "Fixed!",
    error: lang === "ro" ? "Eroare" : "Error",
  };
  const StatusIcon = { idle: isPortal ? ExternalLink : Play, running: Loader2, done: CheckCircle2, error: XCircle }[status];

  return (
    <div className="mt-3 bg-gray-900 rounded-lg p-3 text-white">
      {!isPortal && fixInfo.command && (
        <div className="mb-2">
          <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-1">
            <Terminal className="w-3.5 h-3.5" aria-hidden />
            PowerShell {fixInfo.requires_admin ? "(Admin)" : ""}
          </div>
          <code className="block text-sm font-mono bg-gray-800 rounded px-2 py-1.5 overflow-x-auto whitespace-pre-wrap break-all">
            {fixInfo.command}
          </code>
        </div>
      )}
      <p className="text-sm text-gray-300 mb-2">{fixInfo.explanation}</p>
      <button
        type="button"
        onClick={isPortal ? handlePortal : handleExecute}
        disabled={status === "running" || status === "done"}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium ${
          status === "done" ? "bg-green-600" : status === "error" ? "bg-red-600" : "bg-blue-600 hover:bg-blue-700"
        } disabled:opacity-60`}
      >
        <StatusIcon className={`w-4 h-4 ${status === "running" ? "animate-spin" : ""}`} aria-hidden />
        {btnLabel[status]}
      </button>
      {result?.stdout && <pre className="mt-2 text-xs text-green-300 font-mono whitespace-pre-wrap">{result.stdout}</pre>}
      {result?.stderr && <pre className="mt-2 text-xs text-red-300 font-mono whitespace-pre-wrap">{result.stderr}</pre>}
      {result?.message && status === "error" && <p className="mt-1 text-xs text-red-300">{result.message}</p>}
    </div>
  );
}


function FindingItem({ finding, lang, expert, isTop }) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(isTop);
  const theme = severityColorClasses(finding.severity);
  const device = finding.device;
  const explanation =
    lang === "ro" ? finding.explanation_ro : finding.explanation_en;
  const riskScenario =
    lang === "ro" ? finding.risk_scenario_ro : finding.risk_scenario_en;
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

      {riskScenario && (
        <div className="mt-2 flex gap-2 items-start bg-amber-50 border border-amber-200 rounded-lg p-3">
          <AlertOctagon className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" aria-hidden />
          <p className="text-sm text-amber-900">{riskScenario}</p>
        </div>
      )}

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

      <FixButton
        findingCode={finding.code}
        ip={device?.ip}
        port={finding.port}
        lang={lang}
      />
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
