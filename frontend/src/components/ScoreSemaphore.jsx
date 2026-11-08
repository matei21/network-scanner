import { useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { heroVerdict } from "../lib/findings";
import { CheckCircle2, AlertTriangle, ShieldAlert, Loader2, ChevronDown, ChevronUp, Scale } from "lucide-react";

const TEXT = {
  ro: {
    title: "Scor ponderat",
    vsOfficial: "oficial",
    intro:
      "Pleaca de la scorul oficial (100 minus punctele problemelor) si il ajusteaza dupa context: ce fel de dispozitiv e afectat, ce probleme se agraveaza reciproc si cat de raspandite sunt. Ajustarile sunt limitate la -30 / +10 puncte.",
    start: "Punct de plecare",
    official: "= scor oficial",
    total: "Scor ponderat",
    floor: "(nu coboara sub 0)",
    how: "Cum se calculeaza",
    rows: {
      findings: "Probleme gasite",
      device_weight: "Importanta dispozitivelor afectate",
      density: "Multe probleme pe acelasi dispozitiv",
      combo: "Combinatie periculoasa",
      systemic: "Probleme pe majoritatea dispozitivelor",
      gateway_high: "Problema grava pe router",
      cap: "Limita ajustarilor",
    },
    rules: [
      ["Importanta dispozitivului", "punctele unei probleme se inmultesc cu: router si camera x1.25, server x1.2, smart home x1.15, necunoscut x1.1, PC/telefon x1.0, imprimanta/TV x0.9."],
      ["Concentrare", "-3 pentru fiecare problema peste a 2-a pe acelasi dispozitiv (maxim -6 pe dispozitiv)."],
      ["Combinatii", "-8 pentru perechi care se agraveaza pe acelasi dispozitiv, ex: stream camera + parola admin necriptata (maxim -16)."],
      ["Raspandire", "-5 daca peste 60% din dispozitive (minim 3) au probleme."],
      ["Router", "-10 daca routerul are o problema de severitate mare."],
      ["Limita", "ajustarile totale sunt intre -30 si +10, ca scorul ponderat sa ramana comparabil cu cel oficial."],
    ],
  },
  en: {
    title: "Weighted score",
    vsOfficial: "official",
    intro:
      "Starts from the official score (100 minus the findings' points) and adjusts it for context: what kind of device is affected, which issues make each other worse and how widespread they are. Adjustments are limited to -30 / +10 points.",
    start: "Starting point",
    official: "= official score",
    total: "Weighted score",
    floor: "(never below 0)",
    how: "How it's calculated",
    rows: {
      findings: "Findings",
      device_weight: "Importance of affected devices",
      density: "Many issues on one device",
      combo: "Dangerous combination",
      systemic: "Issues on most devices",
      gateway_high: "Serious issue on the router",
      cap: "Adjustment limit",
    },
    rules: [
      ["Device importance", "a finding's points are multiplied by: router and camera x1.25, server x1.2, smart home x1.15, unknown x1.1, PC/phone x1.0, printer/TV x0.9."],
      ["Concentration", "-3 for every finding beyond the 2nd on the same device (at most -6 per device)."],
      ["Combinations", "-8 for pairs that worsen each other on the same device, e.g. camera stream + cleartext admin password (at most -16)."],
      ["Spread", "-5 if more than 60% of devices (at least 3) have issues."],
      ["Router", "-10 if the router has a high-severity finding."],
      ["Limit", "total adjustments stay between -30 and +10 so the weighted score stays comparable to the official one."],
    ],
  },
};

function scoreClass(s) {
  return s < 40 ? "wp-bad" : s < 70 ? "wp-warn" : "wp-good";
}

function Row({ label, delta, detail, strong }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 py-1.5 border-b wp-divider last:border-0">
      <span className={`text-sm min-w-0 ${strong ? "font-semibold" : ""}`}>{label}</span>
      <span className={`text-sm font-mono font-semibold tabular-nums text-right ${delta < 0 ? "wp-bad" : delta > 0 ? "wp-good" : ""}`}>
        {delta > 0 ? `+${delta}` : delta}
      </span>
      {detail && (
        <span className="col-span-2 text-xs wp-muted mt-0.5" style={{ overflowWrap: "anywhere" }}>
          {detail}
        </span>
      )}
    </div>
  );
}

function WeightedScorePanel({ customRisk, officialScore, lang }) {
  const [open, setOpen] = useState(false);
  const [showRules, setShowRules] = useState(false);
  if (!customRisk || !Array.isArray(customRisk.breakdown)) return null;

  const l = TEXT[lang] || TEXT.ro;
  const { score, breakdown } = customRisk;
  const findings = breakdown.find((b) => b.key === "findings");
  const adjustments = breakdown.filter((b) => b.key !== "findings");
  const official = 100 + (findings?.delta || 0);

  return (
    <div className="mt-3 min-w-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-left"
        aria-expanded={open}
      >
        <Scale className="w-4 h-4 shrink-0" aria-hidden />
        <span className="font-medium">{l.title}:</span>
        <span className={`text-lg font-bold tabular-nums ${scoreClass(score)}`}>{score}/100</span>
        {officialScore != null && (
          <span className="text-xs wp-muted">
            ({l.vsOfficial} {officialScore})
          </span>
        )}
        {open ? <ChevronUp className="w-4 h-4" aria-hidden /> : <ChevronDown className="w-4 h-4" aria-hidden />}
      </button>

      {open && (
        <div className="weighted-panel mt-2 w-full max-w-lg rounded-lg border p-3">
          <p className="text-xs wp-muted mb-2" style={{ overflowWrap: "anywhere" }}>{l.intro}</p>

          <Row label={l.start} delta={100} />
          {findings && (
            <Row label={`${l.rows.findings} (${findings.detail})`} delta={findings.delta} />
          )}
          <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 py-1.5 border-b wp-divider">
            <span className="text-sm wp-muted">{l.official}</span>
            <span className="text-sm font-mono tabular-nums text-right">{Math.max(0, official)}</span>
          </div>
          {adjustments.map((b, i) => (
            <Row key={i} label={l.rows[b.key] || b.key} delta={b.delta} detail={b.key === "cap" ? null : b.detail} />
          ))}
          <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 pt-2 mt-1 border-t-2 wp-divider">
            <span className="text-sm font-semibold">
              {l.total} {customRisk.raw < 0 && <span className="text-xs font-normal wp-muted">{l.floor}</span>}
            </span>
            <span className={`text-sm font-bold tabular-nums text-right ${scoreClass(score)}`}>{score}/100</span>
          </div>

          <button
            type="button"
            onClick={() => setShowRules((v) => !v)}
            className="mt-3 inline-flex items-center gap-1 text-xs font-medium underline-offset-2 hover:underline"
            aria-expanded={showRules}
          >
            {showRules ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {l.how}
          </button>
          {showRules && (
            <ul className="mt-1.5 space-y-1 text-xs">
              {l.rules.map(([name, rule]) => (
                <li key={name} style={{ overflowWrap: "anywhere" }}>
                  <span className="font-semibold">{name}:</span> <span className="wp-muted">{rule}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default function ScoreSemaphore({ score, scan, loading }) {
  const { t, lang } = useLanguage();
  const verdict = heroVerdict(scan);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-10 bg-white rounded-2xl border border-gray-200">
        <Loader2 className="w-10 h-10 animate-spin text-gray-500" aria-hidden />
        <span className="ml-3 text-lg">{t("loading")}</span>
      </div>
    );
  }

  const theme = {
    safe: { ring: "ring-green-500", text: "text-risk-safe", Icon: CheckCircle2, label: t("verdict_safe"), desc: t("verdict_safe_desc") },
    watch: { ring: "ring-amber-500", text: "text-risk-medium", Icon: AlertTriangle, label: t("verdict_watch"), desc: t("verdict_watch_desc") },
    at_risk: { ring: "ring-red-500", text: "text-risk-high", Icon: ShieldAlert, label: t("verdict_at_risk"), desc: t("verdict_at_risk_desc") },
    error: { ring: "ring-gray-500", text: "text-risk-info", Icon: AlertTriangle, label: "—", desc: "" },
  }[verdict];

  const { Icon } = theme;

  return (
    <div
      className="hero-card relative p-6 rounded-2xl"
      data-verdict={verdict}
      role="status"
      aria-label={`${t("score_label")}: ${score ?? "N/A"} ${t("score_of_100")}. ${theme.label}. ${theme.desc}`}
    >
      <div className="flex flex-wrap sm:flex-nowrap items-start sm:items-center gap-6">
        <div
          className={`score-disc w-32 h-32 shrink-0 rounded-full ring-8 ${theme.ring} flex flex-col items-center justify-center`}
        >
          <span className={`text-5xl font-bold tabular-nums ${theme.text}`}>{score ?? "—"}</span>
          <span className="text-xs text-gray-600">{t("score_of_100")}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className={`flex items-center gap-2 ${theme.text}`}>
            <Icon className="w-7 h-7 shrink-0" aria-hidden />
            <span className="text-2xl font-semibold">{theme.label}</span>
          </div>
          <p className="mt-2 text-lg">{theme.desc}</p>
          <WeightedScorePanel customRisk={scan?.custom_risk_score} officialScore={score} lang={lang} />
        </div>
      </div>
    </div>
  );
}
