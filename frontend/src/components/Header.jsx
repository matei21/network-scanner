import { useLanguage } from "../i18n/LanguageContext";
import { ShieldCheck, Languages, Eye, EyeOff } from "lucide-react";

export default function Header({ expert, onToggleExpert }) {
  const { t, toggle } = useLanguage();
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3 flex-wrap">
        <ShieldCheck className="w-7 h-7 text-blue-700" aria-hidden />
        <div className="min-w-0">
          <h1 className="text-xl font-bold leading-tight">{t("app_title")}</h1>
          <p className="text-sm text-gray-600 leading-tight">
            {t("app_subtitle")}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={onToggleExpert}
            className="inline-flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 text-sm"
            aria-pressed={expert}
            aria-label={t("mode_toggle_aria")}
          >
            {expert ? (
              <EyeOff className="w-4 h-4" aria-hidden />
            ) : (
              <Eye className="w-4 h-4" aria-hidden />
            )}
            {expert ? t("mode_expert") : t("mode_simple")}
          </button>
          <button
            type="button"
            onClick={toggle}
            className="inline-flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 text-sm"
            aria-label={t("lang_toggle_aria")}
          >
            <Languages className="w-4 h-4" aria-hidden />
            {t("lang_toggle")}
          </button>
        </div>
      </div>
    </header>
  );
}
