import { useLanguage } from "../i18n/LanguageContext";
import { AlertOctagon, Trash2 } from "lucide-react";

function Sparkline({ points }) {
  // Score trend chart — larger, white-on-green palette (user feedback).
  if (!points || points.length === 0) return null;
  const w = 720;
  const h = 240;
  const padX = 60; // room for half a date label at both ends
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
          <stop offset="0%" stopColor="#3F6B4E" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#3F6B4E" stopOpacity="0.05" />
        </linearGradient>
      </defs>
      {/* Card background: white */}
      <rect x="0" y="0" width={w} height={h} fill="#FFFFFF" rx="16" />
      {/* 70-line threshold (safe score) */}
      <line
        x1={padX}
        x2={w - padX}
        y1={h - padY - (70 / 100) * (h - padY * 2)}
        y2={h - padY - (70 / 100) * (h - padY * 2)}
        stroke="#86B49A"
        strokeDasharray="4 4"
        strokeWidth="1.5"
      />
      <text x={w - padX - 2} y={h - padY - (70 / 100) * (h - padY * 2) - 6}
        fontSize="12" fill="#3F6B4E" textAnchor="end" fontWeight="600">
        70
      </text>
      {/* Area under curve */}
      <path d={area} fill="url(#trendFill)" />
      {/* Line */}
      <path d={line} fill="none" stroke="#3F6B4E" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      {/* Points + labels */}
      {xs.map((x, i) => (
        <g key={i}>
          <circle cx={x} cy={ys[i]} r="6" fill="#FFFFFF" stroke="#3F6B4E" strokeWidth="3" />
          <text x={x} y={h - 10} textAnchor="middle" fontSize="13" fill="#3F6B4E" fontWeight="600">
            {points[i].date?.slice(5)}
          </text>
          <text x={x} y={ys[i] - 14} textAnchor="middle" fontSize="18" fill="#1F3A2A" fontWeight="700">
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
        <Sparkline points={history.filter((h) => h.status !== "error")} />
      </section>

      <section>
        <h3 className="on-video font-semibold mb-2 text-xl">{t("history_title")}</h3>
        <div className="overflow-x-auto border border-gray-200 rounded-xl bg-white">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200 text-gray-700">
              <tr>
                <th scope="col" className="p-3 font-semibold">{t("history_col_file")}</th>
                <th scope="col" className="p-3 font-semibold">{t("history_col_date")}</th>
                <th scope="col" className="p-3 font-semibold text-right">{t("history_col_findings")}</th>
                <th scope="col" className="p-3 font-semibold text-right">{t("history_col_score")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {history
                .slice()
                .reverse()
                .map((h) => {
                  const unreadable = h.status === "error";
                  return (
                    <tr key={h.scan_id}>
                      <td className="p-3 font-medium break-all">{h.file}</td>
                      <td className="p-3 tabular-nums whitespace-nowrap">{h.date}</td>
                      <td className="p-3 text-right tabular-nums whitespace-nowrap">
                        {unreadable
                          ? "-"
                          : `${h.findings_count} ${h.findings_count === 1 ? t("finding_count_one") : t("findings_count")}`}
                      </td>
                      <td className="p-3 text-right font-semibold tabular-nums whitespace-nowrap">
                        {unreadable ? (
                          <span className="inline-flex items-center gap-1 text-risk-high">
                            <AlertOctagon className="w-4 h-4" aria-hidden />
                            {t("history_unreadable")}
                          </span>
                        ) : (
                          h.score
                        )}
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
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
