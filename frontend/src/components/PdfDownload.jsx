import { useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { getReportPdfUrl } from "../lib/api";
import { FileDown, Loader2 } from "lucide-react";

export default function PdfDownload({ scanId }) {
  const { lang } = useLanguage();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!scanId) return null;

  async function handleDownload() {
    setLoading(true);
    setError(null);
    try {
      const url = getReportPdfUrl(scanId, lang);
      const res = await fetch(url);
      if (!res.ok) {
        const text = await res.text().catch(() => `HTTP ${res.status}`);
        throw new Error(text.slice(0, 120));
      }
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `network_report_${scanId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (e) {
      setError(e.message || "Download failed");
    } finally {
      setLoading(false);
    }
  }

  const label = lang === "ro" ? "Descarca raport PDF" : "Download PDF report";

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={handleDownload}
        disabled={loading}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 text-white hover:bg-gray-900 text-sm font-medium disabled:opacity-60"
      >
        {loading
          ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
          : <FileDown className="w-4 h-4" aria-hidden />
        }
        {label}
      </button>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
