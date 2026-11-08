import { useEffect, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { narrateDiffVsPrevious } from "../lib/api";
import { GitCompareArrows, Loader2, TrendingUp, TrendingDown, Minus } from "lucide-react";

export default function DiffNarrator({ scanId }) {
  const { lang } = useLanguage();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [noPrev, setNoPrev] = useState(false);

  useEffect(() => {
    if (!scanId) return;
    let cancelled = false;
    setLoading(true);
    setNoPrev(false);
    narrateDiffVsPrevious(scanId, lang)
      .then((d) => !cancelled && setData(d))
      .catch((e) => {
        if (!cancelled) {
          if (e.status === 404 || String(e.message || e).includes("404")) setNoPrev(true);
          setData(null);
        }
      })
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [scanId, lang]);

  if (!scanId || noPrev) return null;

  if (loading) {
    return (
      <div className="bg-purple-50 border border-purple-200 rounded-2xl p-4 flex items-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-purple-600" aria-hidden />
        <span className="text-sm text-purple-700">
          {lang === "ro" ? "Se compara cu scanul anterior..." : "Comparing with previous scan..."}
        </span>
      </div>
    );
  }

  if (!data?.narrative) return null;

  const delta = (data.new_score ?? 0) - (data.old_score ?? 0);
  const TrendIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;
  const trendColor = delta > 0 ? "text-green-700" : delta < 0 ? "text-red-700" : "text-gray-600";

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <GitCompareArrows className="w-5 h-5 text-purple-700" aria-hidden />
        <h3 className="font-semibold text-purple-900">
          {lang === "ro" ? "Comparatie cu scanul anterior" : "Comparison with previous scan"}
        </h3>
        <TrendIcon className={`w-5 h-5 ${trendColor}`} aria-hidden />
      </div>
      <p className="text-base text-purple-900 whitespace-pre-line">{data.narrative}</p>
    </div>
  );
}
