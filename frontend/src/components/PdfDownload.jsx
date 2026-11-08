import { useLanguage } from "../i18n/LanguageContext";
import { getReportPdfUrl } from "../lib/api";
import { FileDown } from "lucide-react";

export default function PdfDownload({ scanId }) {
  const { lang } = useLanguage();
  if (!scanId) return null;

  const url = getReportPdfUrl(scanId, lang);
  const label = lang === "ro" ? "Descarca raport PDF" : "Download PDF report";

  return (
    <a
      href={url}
      download
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 text-white hover:bg-gray-900 text-sm font-medium"
    >
      <FileDown className="w-4 h-4" aria-hidden />
      {label}
    </a>
  );
}
