import { useLanguage } from "../i18n/LanguageContext";
import { heroVerdict } from "../lib/findings";
import { CheckCircle2, AlertTriangle, ShieldAlert, Loader2 } from "lucide-react";

// Big traffic-light score. Color + icon + word label — color is never the
// only signal (NFR-08).
export default function ScoreSemaphore({ score, scan, loading }) {
  const { t } = useLanguage();
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
    safe: {
      ring: "ring-green-500",
      text: "text-risk-safe",
      bg: "bg-green-50",
      Icon: CheckCircle2,
      label: t("verdict_safe"),
      desc: t("verdict_safe_desc"),
    },
    watch: {
      ring: "ring-amber-500",
      text: "text-risk-medium",
      bg: "bg-amber-50",
      Icon: AlertTriangle,
      label: t("verdict_watch"),
      desc: t("verdict_watch_desc"),
    },
    at_risk: {
      ring: "ring-red-500",
      text: "text-risk-high",
      bg: "bg-red-50",
      Icon: ShieldAlert,
      label: t("verdict_at_risk"),
      desc: t("verdict_at_risk_desc"),
    },
    error: {
      ring: "ring-gray-500",
      text: "text-risk-info",
      bg: "bg-gray-50",
      Icon: AlertTriangle,
      label: "—",
      desc: "",
    },
  }[verdict];

  const { Icon } = theme;

  return (
    <div
      className="hero-card relative p-6 rounded-2xl"
      data-verdict={verdict}
      role="status"
      aria-label={`${t("score_label")}: ${score ?? "N/A"} ${t("score_of_100")}. ${theme.label}. ${theme.desc}`}
    >
      <div className="flex items-center gap-6">
        <div
          className={`score-disc w-32 h-32 shrink-0 rounded-full ring-8 ${theme.ring} flex flex-col items-center justify-center`}
        >
          <span className={`text-5xl font-bold tabular-nums ${theme.text}`}>
            {score ?? "—"}
          </span>
          <span className="text-xs text-gray-600">{t("score_of_100")}</span>
        </div>
        <div className="min-w-0">
          <div className={`flex items-center gap-2 ${theme.text}`}>
            <Icon className="w-7 h-7" aria-hidden />
            <span className="text-2xl font-semibold">{theme.label}</span>
          </div>
          <p className="mt-2 text-lg">{theme.desc}</p>
        </div>
      </div>
    </div>
  );
}
