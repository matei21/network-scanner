import { useRef, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { Upload, Radar } from "lucide-react";

export default function ScanControls({ onUpload, onLiveScan, busy }) {
  const { t } = useLanguage();
  const fileRef = useRef(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <input
        ref={fileRef}
        type="file"
        accept=".xml,text/xml"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onUpload?.(f);
          e.target.value = "";
        }}
      />
      <button
        type="button"
        disabled={busy}
        onClick={() => fileRef.current?.click()}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-700 text-white hover:bg-blue-800 disabled:opacity-50"
      >
        <Upload className="w-5 h-5" aria-hidden />
        {t("upload_button")}
      </button>

      <button
        type="button"
        disabled={busy}
        onClick={() => setConfirmOpen(true)}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-50"
      >
        <Radar className="w-5 h-5" aria-hidden />
        {t("scan_button")}
      </button>

      <span className="text-sm text-gray-600 basis-full sm:basis-auto">
        {t("upload_hint")}
      </span>

      {confirmOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="live-confirm-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setConfirmOpen(false);
          }}
        >
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl">
            <h2 id="live-confirm-title" className="text-xl font-semibold">
              {t("scan_confirm_title")}
            </h2>
            <p className="mt-2 text-gray-800">{t("scan_confirm_body")}</p>
            <div className="mt-5 flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setConfirmOpen(false)}
                className="px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50"
              >
                {t("scan_confirm_no")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setConfirmOpen(false);
                  onLiveScan?.();
                }}
                className="px-4 py-2 rounded-lg bg-red-700 text-white hover:bg-red-800"
              >
                {t("scan_confirm_yes")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
