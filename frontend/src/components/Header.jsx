import { useRef, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { Leaf, Languages, Eye, EyeOff, Upload, Radar } from "lucide-react";

// Full top menu bar: logo, nav tabs, upload/scan actions, mode + lang toggles.
// All collapses gracefully with flex-wrap on narrow screens.
export default function Header({
  expert,
  onToggleExpert,
  tab,
  onTabChange,
  tabs,
  onUpload,
  onLiveScan,
  busy,
}) {
  const { t, toggle } = useLanguage();
  const fileRef = useRef(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <>
      <header className="app-menubar">
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex items-center gap-4 flex-nowrap">
          <div className="flex items-center gap-2 min-w-0">
            <Leaf className="w-6 h-6 text-blue-700" aria-hidden />
            <span className="font-bold text-lg leading-tight whitespace-nowrap">
              {t("app_title")}
            </span>
          </div>

          <nav
            role="tablist"
            aria-label={t("app_title")}
            className="flex items-center gap-0.5 overflow-x-auto"
          >
            {tabs.map((item) => {
              const selected = item.id === tab;
              return (
                <button
                  key={item.id}
                  role="tab"
                  aria-selected={selected}
                  tabIndex={selected ? 0 : -1}
                  onClick={() => onTabChange(item.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-semibold whitespace-nowrap transition ${
                    selected
                      ? "bg-blue-700 text-white"
                      : "text-gray-800 hover:bg-gray-50"
                  }`}
                >
                  {item.label}
                  {typeof item.count === "number" && (
                    <span className="tab-count ml-1.5 inline-flex items-center justify-center text-xs font-bold px-1.5 min-w-5 rounded-full">
                      {item.count}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-2 flex-nowrap justify-end">
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
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-700 text-white text-sm font-semibold hover:bg-blue-800 disabled:opacity-50"
            >
              <Upload className="w-4 h-4" aria-hidden />
              <span className="hidden sm:inline">{t("upload_button")}</span>
              <span className="sm:hidden">XML</span>
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirmOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-sm font-semibold hover:bg-gray-50 disabled:opacity-50"
            >
              <Radar className="w-4 h-4" aria-hidden />
              <span className="hidden sm:inline">{t("scan_button")}</span>
              <span className="sm:hidden">Scan</span>
            </button>

            <span className="w-px h-6 bg-gray-300 mx-1 hidden sm:block" aria-hidden />

            <button
              type="button"
              onClick={onToggleExpert}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 text-sm"
              aria-pressed={expert}
              aria-label={t("mode_toggle_aria")}
            >
              {expert ? (
                <EyeOff className="w-4 h-4" aria-hidden />
              ) : (
                <Eye className="w-4 h-4" aria-hidden />
              )}
              <span className="hidden md:inline">
                {expert ? t("mode_expert") : t("mode_simple")}
              </span>
            </button>
            <button
              type="button"
              onClick={toggle}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 text-sm"
              aria-label={t("lang_toggle_aria")}
            >
              <Languages className="w-4 h-4" aria-hidden />
              {t("lang_toggle")}
            </button>
          </div>
        </div>
      </header>

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
    </>
  );
}
