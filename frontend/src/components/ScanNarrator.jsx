import { useEffect, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { narrateScan } from "../lib/api";
import { BookOpen, Loader2 } from "lucide-react";

export default function ScanNarrator({ scanId }) {
  const { lang, t } = useLanguage();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!scanId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    narrateScan(scanId, lang)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(String(e.message || e)))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [scanId, lang]);

  if (!scanId || error) return null;

  if (loading) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-blue-600" aria-hidden />
        <span className="text-sm text-blue-700">
          {lang === "ro" ? "Se genereaza rezumatul..." : "Generating summary..."}
        </span>
      </div>
    );
  }

  if (!data?.narrative) return null;

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <BookOpen className="w-5 h-5 text-blue-700" aria-hidden />
        <h3 className="font-semibold text-blue-900">
          {lang === "ro" ? "Rezumatul retelei tale" : "Your network summary"}
        </h3>
      </div>
      <p className="text-base text-blue-900 whitespace-pre-line">{data.narrative}</p>
    </div>
  );
}
