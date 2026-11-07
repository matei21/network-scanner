import { AlertOctagon } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";

export default function ErrorBanner({ scan }) {
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
        <p className="text-sm text-gray-800 mt-1">
          {scan.error || t("error_broken")}
        </p>
      </div>
    </div>
  );
}
