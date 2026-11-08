import { useLanguage } from "../i18n/LanguageContext";
import { Trash2 } from "lucide-react";

function Sparkline({ points }) {
  // Score trend chart — larger, white-on-green palette (user feedback).
  if (!points || points.length === 0) return null;
  const w = 720;
  const h = 240;
  const padX = 36;
  const padY = 42;
  const xs = points.map((_, i) =>
    padX + (i * (w - padX * 2)) / Math.max(1, points.length - 1)
  );
  const ys = points.map(
    (p) => h - padY - ((p.score ?? 0) / 100) * (h - padY * 2)
  );
  const line = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x} ${ys[i]}`).join(" ");
  const area = `${line} L ${xs[xs.length - 1]} ${h - padY} L ${xs[0]} ${h - padY} Z`;

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="w-full h-auto"
      role="img"
      aria-label="Score trend"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="var(--chart-line)" stopOpacity="0.6" />
          <stop offset="100%" stopColor="var(--chart-line)" stopOpacity="0.05" />
        </linearGradient>
      </defs>
      {/* Card background: white */}
      <rect x="0" y="0" width={w} height={h} fill="var(--chart-bg)" rx="16" />
      {/* 70-line threshold (safe score) */}
      <line
        x1={padX}
        x2={w - padX}
        y1={h - padY - (70 / 100) * (h - padY * 2)}
        y2={h - padY - (70 / 100) * (h - padY * 2)}
        stroke="var(--chart-dashed)"
        strokeDasharray="4 4"
        strokeWidth="1.5"
      />
      <text x={w - padX - 2} y={h - padY - (70 / 100) * (h - padY * 2) - 6}
        fontSize="12" fill="var(--chart-line)" textAnchor="end" fontWeight="600">
        70
      </text>
      {/* Area under curve */}
      <path d={area} fill="url(#trendFill)" />
      {/* Line */}
      <path d={line} fill="none" stroke="var(--chart-line)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      {/* Points + labels */}
      {xs.map((x, i) => (
        <g key={i}>
          <circle cx={x} cy={ys[i]} r="6" fill="var(--chart-point-fill)" stroke="var(--chart-line)" strokeWidth="3" />
          <text x={x} y={h - 10} textAnchor="middle" fontSize="13" fill="var(--chart-label-date)" fontWeight="600">
            {points[i].date?.slice(5)}
          </text>
          <text x={x} y={ys[i] - 14} textAnchor="middle" fontSize="18" fill="var(--chart-label-score)" fontWeight="700">
            {points[i].score}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default function HistoryView({ scan, onDelete }) {
  const { t } = useLanguage();
  const history = scan?.history || [];

  if (history.length === 0) {
    return <div className="text-gray-700">{t("history_empty")}</div>;
  }

  return (
    <div className="space-y-6">
      <section>
        <h3 className="on-video font-semibold mb-2 text-xl">{t("history_score_trend")}</h3>
        <Sparkline points={history} />
      </section>

      <section>
        <h3 className="on-video font-semibold mb-2 text-xl">{t("history_title")}</h3>
        <ul className="divide-y border border-gray-200 rounded-xl bg-white">
          {history
            .slice()
            .reverse()
            .map((h) => (
              <li
                key={h.scan_id}
                className="p-3 flex items-center justify-between"
              >
                <span className="tabular-nums">{h.date}</span>
                <span className="text-sm text-gray-600">
                  {h.findings_count} {t("findings_count")}
                </span>
                <span className="font-semibold tabular-nums">{h.score}</span>
              </li>
            ))}
        </ul>
      </section>

      <div>
        <button
          type="button"
          onClick={() => {
            if (window.confirm(t("history_delete_confirm"))) onDelete?.();
          }}
          className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-800 hover:bg-gray-50"
        >
          <Trash2 className="w-4 h-4" aria-hidden />
          {t("history_delete")}
        </button>
      </div>
    </div>
  );
}
