import { AlertOctagon } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";

// The parser's technical detail is shown only in Expert mode; Simple mode keeps the plain explanation.
export default function ErrorBanner({ scan, expert = false }) {
  const { t } = useLanguage();
  if (!scan || scan.status !== "error") return null;
  return (
    <div
      role="alert"
      className="rounded-xl border border-red-300 bg-red-50 p-4 flex items-start gap-3"
    >
      <AlertOctagon className="w-6 h-6 text-risk-high shrink-0" aria-hidden />
      <div>
        <div className="font-semibold text-risk-high">{t("error_title")}</div>
        {scan.error_code === "unreadable" ? (
          <>
            {/* The explanation in the UI language; the parser's exact message stays as a technical detail. */}
            {/* Fixed dark red: the box stays light pink in dark mode, where text-gray-* turns white. */}
            <p className="text-red-900 mt-1">{t("error_broken")}</p>
            {expert && scan.error && (
              <p className="text-sm text-red-800 mt-1 break-words">
                {t("error_technical")}: {scan.error}
              </p>
            )}
          </>
        ) : (
          <p className="text-red-900 mt-1">{scan.error || t("error_broken")}</p>
        )}
      </div>
    </div>
  );
}
