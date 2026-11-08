import { useState, useEffect } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { flattenFindings, sortedBySeverity, severityColorClasses } from "../lib/findings";
import { getFixInfo, executeFix, getFixResult, getDetailedFix } from "../lib/api";
import DeviceIcon from "./DeviceIcon";
import { ChevronDown, ChevronUp, Flame, AlertOctagon, Terminal, ExternalLink, CheckCircle2, Loader2, XCircle, ShieldCheck, Search, Monitor, Router, Copy, Check } from "lucide-react";

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

const FIX_TEXT = {
  ro: {
    here: "Pe acest calculator",
    on: "Se rezolva pe",
    where: "Unde gasesti setarea",
    run: "Rezolva automat (admin)",
    asking: "Aproba cererea Windows (UAC) ca sa continue...",
    running: "Se executa in fereastra PowerShell...",
    done: "Rezolvat. Fa o scanare noua ca sa confirmi.",
    failed: "Comanda nu a reusit.",
    openPanel: "Deschide panoul",
    guide: "Pasi exacti pentru",
    guideLoading: "Agentii cauta pasii pentru dispozitivul tau...",
    vector: "Vector de atac",
    cmdHere: "Comanda care va rula (PowerShell, administrator)",
    cmdRemote: (ip) => `Daca ${ip} este un PC Windows, ruleaza pe el (PowerShell ca administrator):`,
    whyNot: "Comenzile schimba doar calculatorul pe care ruleaza, asa ca aplicatia nu ruleaza nimic aici pentru o problema de pe alt dispozitiv.",
    parts: "Ce face fiecare parte",
    copy: "Copiaza",
    copied: "Copiat",
    output: "Rezultat",
    sources: "Surse",
    webNote: "Pasi gasiti pe internet, NU in scanul tau. Verifica sursele.",
  },
  en: {
    here: "On this computer",
    on: "Fixed on",
    where: "Where to find the setting",
    run: "Auto-fix (admin)",
    asking: "Approve the Windows (UAC) prompt to continue...",
    running: "Running in the PowerShell window...",
    done: "Fixed. Run a new scan to confirm.",
    failed: "The command did not succeed.",
    openPanel: "Open the panel",
    guide: "Exact steps for",
    guideLoading: "The agents are looking up steps for your device...",
    vector: "Attack vector",
    cmdHere: "Command that will run (PowerShell, administrator)",
    cmdRemote: (ip) => `If ${ip} is a Windows PC, run this on it (PowerShell as administrator):`,
    whyNot: "Commands only change the computer they run on, so the app runs nothing here for an issue on another device.",
    parts: "What each part does",
    copy: "Copy",
    copied: "Copied",
    output: "Output",
    sources: "Sources",
    webNote: "Steps found on the internet, NOT in your scan. Check the sources.",
  },
};

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function FixPanel({ finding, lang, expert, scanId }) {
  const device = finding.device || {};
  const L = FIX_TEXT[lang] || FIX_TEXT.ro;
  const [info, setInfo] = useState(null);
  const [run, setRun] = useState({ state: "idle" });
  const [guide, setGuide] = useState({ state: "idle" });
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!finding.code || !device.ip) return;
    let cancelled = false;
    getFixInfo(finding.code, device.ip, finding.port, lang, scanId)
      .then((r) => !cancelled && setInfo(r))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [finding.code, device.ip, finding.port, lang, scanId]);

  // The elevated window writes its result to a file; poll until it finishes.
  useEffect(() => {
    if (run.state !== "running" || !run.runId) return;
    let stopped = false;
    let timer;
    const started = Date.now();
    async function tick() {
      if (stopped) return;
      try {
        const r = await getFixResult(run.runId);
        if (r.status === "done") {
          setRun({ state: r.ok ? "done" : "failed", output: r.output });
          return;
        }
      } catch {
        /* backend busy: try again */
      }
      if (Date.now() - started > 330000) {
        setRun({ state: "failed", output: "" });
        return;
      }
      timer = setTimeout(tick, 2000);
    }
    timer = setTimeout(tick, 2000);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [run.state, run.runId]);

  if (!info) return null;

  async function runFix() {
    setRun({ state: "asking" });
    try {
      const r = await executeFix(finding.code, device.ip, finding.port, lang, scanId);
      if (r.status === "elevated") setRun({ state: "running", runId: r.run_id });
      else setRun({ state: r.status === "denied" ? "denied" : "error", output: r.message });
    } catch (e) {
      setRun({ state: "error", output: String(e.message || e) });
    }
  }

  async function loadGuide() {
    setGuide({ state: "loading" });
    try {
      const r = await getDetailedFix(finding.code, device.ip, scanId, lang, expert);
      setGuide({ state: "done", ...r });
    } catch (e) {
      setGuide({ state: "error", message: String(e.message || e) });
    }
  }

  function copy() {
    navigator.clipboard?.writeText(info.command).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  const isHere = info.target === "this_pc";
  const deviceName = [device.vendor, info.device?.label].filter(Boolean).join(" ") || device.ip;
  const busy = run.state === "asking" || run.state === "running";
  const guideAgents = (guide.agents || []).filter((a) => expert || a.agent === "advisor");

  return (
    <div className="mt-3 rounded-lg border border-gray-200 bg-white p-3 space-y-2 min-w-0">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
            isHere ? "border-green-300 bg-green-50 text-green-800" : "border-blue-300 bg-blue-50 text-blue-800"
          }`}
        >
          {isHere ? <Monitor className="w-3.5 h-3.5" aria-hidden /> : <Router className="w-3.5 h-3.5" aria-hidden />}
          {isHere ? L.here : `${L.on}: ${deviceName} (${device.ip})`}
        </span>
      </div>

      <p className="text-sm text-gray-900" style={{ overflowWrap: "anywhere" }}>{info.explanation}</p>
      {!isHere && info.menu_hint && (
        <p className="text-sm text-gray-700" style={{ overflowWrap: "anywhere" }}>
          <span className="font-semibold">{L.where}:</span> {info.menu_hint}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {info.can_run && (
          <button
            type="button"
            onClick={runFix}
            disabled={busy || run.state === "done"}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-white bg-blue-700 hover:bg-blue-800 disabled:opacity-60"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <ShieldCheck className="w-4 h-4" aria-hidden />}
            {L.run}
          </button>
        )}
        {info.portal_url && (
          <a
            href={info.portal_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-white bg-emerald-700 hover:bg-emerald-800"
          >
            <ExternalLink className="w-4 h-4" aria-hidden />
            {L.openPanel} ({hostOf(info.portal_url)})
          </a>
        )}
        {!isHere && (
          <button
            type="button"
            onClick={loadGuide}
            disabled={guide.state === "loading"}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-300 hover:bg-gray-50 disabled:opacity-60"
          >
            {guide.state === "loading" ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <Search className="w-4 h-4" aria-hidden />}
            {L.guide} {device.vendor || deviceName}
          </button>
        )}
      </div>

      {run.state !== "idle" && (
        <div
          className={`rounded-md p-2 text-sm ${
            run.state === "done" ? "bg-green-50 text-green-900" : ["failed", "error", "denied"].includes(run.state) ? "bg-red-50 text-red-900" : "bg-blue-50 text-blue-900"
          }`}
          role="status"
        >
          <div className="flex items-center gap-1.5">
            {run.state === "done" ? <CheckCircle2 className="w-4 h-4" aria-hidden /> : busy ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <XCircle className="w-4 h-4" aria-hidden />}
            <span>
              {run.state === "asking" ? L.asking : run.state === "running" ? L.running : run.state === "done" ? L.done : run.state === "failed" ? L.failed : run.output}
            </span>
          </div>
          {run.output && ["done", "failed"].includes(run.state) && (expert || run.state === "failed") && (
            <pre className="mt-1.5 text-xs font-mono whitespace-pre-wrap" style={{ overflowWrap: "anywhere" }}>
              {expert ? run.output : run.output.split("\n")[0]}
            </pre>
          )}
        </div>
      )}

      {guide.state === "loading" && <p className="text-sm text-gray-600">{L.guideLoading}</p>}
      {guide.state === "error" && <p className="text-sm text-red-700">{guide.message}</p>}
      {guide.state === "done" && (
        <div className="space-y-2">
          <p className="flex items-start gap-1.5 rounded-md border border-amber-300 bg-amber-50 p-2 text-base text-amber-900" role="note">
            <AlertOctagon className="w-4 h-4 shrink-0 mt-1" aria-hidden />
            {L.webNote}
          </p>
          {guideAgents.map((a, i) => (
            <div key={i} className="rounded-md border border-gray-200 p-2">
              <div className="text-xs font-semibold text-gray-600">{a.name} · {a.role}</div>
              <div className="mt-1 text-sm whitespace-pre-line" style={{ overflowWrap: "anywhere" }}>{a.text}</div>
            </div>
          ))}
          {guide.search_results?.length > 0 && (
            <div className="text-xs">
              <span className="font-semibold">{L.sources}:</span>{" "}
              {guide.search_results.map((s, i) => (
                <a key={i} href={s.href} target="_blank" rel="noopener noreferrer" className="text-blue-700 hover:underline mr-2" title={s.title}>
                  [{i + 1}] {hostOf(s.href)}
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {expert && (
        <div className="space-y-2 pt-1 border-t border-gray-200">
          {info.explanation_expert && (
            <p className="text-sm" style={{ overflowWrap: "anywhere" }}>
              <span className="font-semibold">{L.vector}:</span> {info.explanation_expert}
            </p>
          )}
          {info.command && (
            <div className="rounded-md bg-gray-900 p-2.5 min-w-0">
              <div className="flex items-center gap-2 text-xs text-gray-300 mb-1.5">
                <Terminal className="w-3.5 h-3.5 shrink-0" aria-hidden />
                <span className="min-w-0" style={{ overflowWrap: "anywhere" }}>{isHere ? L.cmdHere : L.cmdRemote(device.ip)}</span>
                <button type="button" onClick={copy} className="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-700 text-gray-100 hover:bg-gray-600 shrink-0">
                  {copied ? <Check className="w-3 h-3" aria-hidden /> : <Copy className="w-3 h-3" aria-hidden />}
                  {copied ? L.copied : L.copy}
                </button>
              </div>
              <code className="block text-xs font-mono text-green-200 whitespace-pre-wrap" style={{ overflowWrap: "anywhere" }}>
                {info.command}
              </code>
            </div>
          )}
          {info.command_parts?.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-600 mb-1">{L.parts}</div>
              <ol className="space-y-1.5 text-xs list-decimal pl-5">
                {info.command_parts.map((p, i) => (
                  <li key={i} className="min-w-0">
                    <code className="font-mono text-[11px] bg-gray-100 rounded px-1 py-0.5" style={{ overflowWrap: "anywhere" }}>{p.cmd}</code>
                    <div className="text-gray-700 mt-0.5">{p.meaning}</div>
                  </li>
                ))}
              </ol>
            </div>
          )}
          {!isHere && info.command && <p className="text-xs text-gray-600">{L.whyNot}</p>}
        </div>
      )}
    </div>
  );
}

function FindingItem({ finding, lang, expert, isTop, scanId }) {
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
        <span className="text-base text-gray-700 inline-flex flex-wrap items-center gap-x-1.5">
          <DeviceIcon type={device?.type} size={20} />
          {(device?.[`type_label_${lang}`] || device?.type) && (
            <span className="font-semibold">{device[`type_label_${lang}`] || device.type}</span>
          )}
          <span>{device?.hostname || device?.ip}</span>
          {device?.hostname && <span className="text-gray-600">({device.ip})</span>}
          {finding.port != null && <span>· {t("finding_port")} {finding.port}</span>}
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
          <p className="text-base text-amber-900">{riskScenario}</p>
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

      <FixPanel finding={finding} lang={lang} expert={expert} scanId={scanId} />
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
          scanId={scan?.scan_id}
        />
      ))}
    </div>
  );
}
