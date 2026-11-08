import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { apiFetch, getReportPdfUrl, httpError } from "../lib/api";
import { Eye, Download, ExternalLink, X, Loader2 } from "lucide-react";

const TEXT = {
  ro: {
    view: "Vezi raportul",
    loading: "Se pregateste raportul...",
    title: "Raport de securitate",
    download: "Descarca",
    newTab: "Deschide in tab nou",
    close: "Inchide",
    error: "Raportul nu a putut fi generat.",
  },
  en: {
    view: "View report",
    loading: "Preparing the report...",
    title: "Security report",
    download: "Download",
    newTab: "Open in new tab",
    close: "Close",
    error: "The report could not be generated.",
  },
};

function filenameFrom(header, fallback) {
  const m = /filename="?([^";]+)"?/i.exec(header || "");
  return m ? m[1] : fallback;
}

// Opens the PDF report in a viewer inside the app; download or open in a new tab from there.
export default function PdfDownload({ scanId }) {
  const { lang } = useLanguage();
  const l = TEXT[lang] || TEXT.ro;
  const [state, setState] = useState("idle"); // idle | loading | open | error
  const [error, setError] = useState("");
  const [file, setFile] = useState({ url: "", name: "" });
  const closeRef = useRef(null);

  useEffect(() => () => file.url && URL.revokeObjectURL(file.url), [file.url]);

  useEffect(() => {
    if (state !== "open") return;
    closeRef.current?.focus();
    const onKey = (e) => e.key === "Escape" && setState("idle");
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [state]);

  if (!scanId) return null;

  async function open() {
    setState("loading");
    setError("");
    try {
      const res = await apiFetch(`${getReportPdfUrl(scanId, lang)}&inline=true`);
      if (!res.ok) throw await httpError(res);
      const name = filenameFrom(res.headers.get("Content-Disposition"), `raport_securitate_${scanId}.pdf`);
      const blob = await res.blob();
      setFile({ url: URL.createObjectURL(new Blob([blob], { type: "application/pdf" })), name });
      setState("open");
    } catch (e) {
      setError(e.message || l.error);
      setState("error");
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={open}
        disabled={state === "loading"}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-700 text-white hover:bg-blue-800 text-base font-medium disabled:opacity-60"
      >
        {state === "loading" ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <Eye className="w-4 h-4" aria-hidden />}
        {state === "loading" ? l.loading : l.view}
      </button>
      {state === "error" && <p className="text-base text-red-700">{error || l.error}</p>}

      {state === "open" && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={l.title}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 sm:p-6"
          onClick={(e) => e.target === e.currentTarget && setState("idle")}
        >
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[92vh] flex flex-col overflow-hidden">
            <header className="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-gray-200">
              <div className="min-w-0 flex-1">
                <h2 className="font-semibold text-lg">{l.title}</h2>
                <p className="text-base text-gray-600 truncate" title={file.name}>{file.name}</p>
              </div>
              <a
                href={file.url}
                download={file.name}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-blue-700 text-white hover:bg-blue-800 text-base font-semibold"
              >
                <Download className="w-4 h-4" aria-hidden />
                {l.download}
              </a>
              <a
                href={file.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-300 hover:bg-gray-50 text-base"
              >
                <ExternalLink className="w-4 h-4" aria-hidden />
                {l.newTab}
              </a>
              <button
                ref={closeRef}
                type="button"
                onClick={() => setState("idle")}
                aria-label={l.close}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-300 hover:bg-gray-50 text-base"
              >
                <X className="w-4 h-4" aria-hidden />
                {l.close}
              </button>
            </header>
            <iframe title={l.title} src={file.url} className="flex-1 w-full bg-gray-100" />
          </div>
        </div>
      )}
    </div>
  );
}
