import { useLanguage } from "../i18n/LanguageContext";
import { Trash2 } from "lucide-react";

function Sparkline({ points }) {
  // Tiny SVG line chart of scores over time. Points are {date, score}.
  if (!points || points.length === 0) return null;
  const w = 320;
  const h = 100;
  const pad = 8;
  const xs = points.map((_, i) =>
    pad + (i * (w - pad * 2)) / Math.max(1, points.length - 1)
  );
  const ys = points.map(
    (p) => h - pad - ((p.score ?? 0) / 100) * (h - pad * 2)
  );
  const d = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x} ${ys[i]}`).join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="w-full max-w-md h-28"
      role="img"
      aria-label="Score trend"
    >
      <rect x="0" y="0" width={w} height={h} fill="#f9fafb" rx="8" />
      <line
        x1={pad}
        x2={w - pad}
        y1={h - pad - (70 / 100) * (h - pad * 2)}
        y2={h - pad - (70 / 100) * (h - pad * 2)}
        stroke="#86efac"
        strokeDasharray="3 3"
      />
      <path d={d} fill="none" stroke="#1d4ed8" strokeWidth="2" />
      {xs.map((x, i) => (
        <g key={i}>
          <circle cx={x} cy={ys[i]} r="3.5" fill="#1d4ed8" />
          <text
            x={x}
            y={h - 1}
            textAnchor="middle"
            fontSize="9"
            fill="#4b5563"
          >
            {points[i].date?.slice(5)}
          </text>
          <text
            x={x}
            y={ys[i] - 6}
            textAnchor="middle"
            fontSize="10"
            fill="#111827"
            fontWeight="600"
          >
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
        <h3 className="font-semibold mb-2">{t("history_score_trend")}</h3>
        <Sparkline points={history} />
      </section>

      <section>
        <h3 className="font-semibold mb-2">{t("history_title")}</h3>
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
          className="inline-flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg text-gray-800 hover:bg-gray-50"
        >
          <Trash2 className="w-4 h-4" aria-hidden />
          {t("history_delete")}
        </button>
      </div>
    </div>
  );
}
