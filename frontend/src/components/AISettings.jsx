import { useEffect, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { getAISettings, updateAISettings } from "../lib/api";
import { Settings, Cpu, Cloud, Check } from "lucide-react";

export default function AISettings() {
  const { lang } = useLanguage();
  const [provider, setProvider] = useState("local");
  const [groqKey, setGroqKey] = useState("");
  const [hasKey, setHasKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getAISettings()
      .then((s) => {
        setProvider(s.provider);
        setHasKey(s.has_groq_key);
      })
      .catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      const res = await updateAISettings(provider, groqKey || undefined);
      setHasKey(res.has_groq_key);
      setProvider(res.provider);
      setGroqKey("");
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { /* ignore */ }
    setSaving(false);
  }

  const t = lang === "ro" ? {
    title: "Setari AI",
    local: "Local (Qwen 2.5 3B)",
    localDesc: "Ruleaza pe calculatorul tau, fara internet",
    groq: "Groq Cloud",
    groqDesc: "Rapid, necesita cheie API de la groq.com",
    keyLabel: "Cheie API Groq",
    keyPlaceholder: hasKey ? "Cheie salvata" : "gsk_...",
    save: "Salveaza",
    saved: "Salvat!",
  } : {
    title: "AI Settings",
    local: "Local (Qwen 2.5 3B)",
    localDesc: "Runs on your computer, no internet needed",
    groq: "Groq Cloud",
    groqDesc: "Fast inference, requires API key from groq.com",
    keyLabel: "Groq API Key",
    keyPlaceholder: hasKey ? "Key saved" : "gsk_...",
    save: "Save",
    saved: "Saved!",
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Settings className="w-5 h-5 text-gray-600" aria-hidden />
        <h3 className="font-semibold">{t.title}</h3>
      </div>

      <div className="space-y-2 mb-3">
        <label className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer ${provider === "local" ? "border-blue-400 bg-blue-50" : "border-gray-200"}`}>
          <input
            type="radio"
            name="ai-provider"
            value="local"
            checked={provider === "local"}
            onChange={() => setProvider("local")}
            className="mt-1"
          />
          <div>
            <div className="flex items-center gap-1.5 font-medium text-sm">
              <Cpu className="w-4 h-4" aria-hidden />
              {t.local}
            </div>
            <div className="text-xs text-gray-600">{t.localDesc}</div>
          </div>
        </label>

        <label className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer ${provider === "groq" ? "border-blue-400 bg-blue-50" : "border-gray-200"}`}>
          <input
            type="radio"
            name="ai-provider"
            value="groq"
            checked={provider === "groq"}
            onChange={() => setProvider("groq")}
            className="mt-1"
          />
          <div>
            <div className="flex items-center gap-1.5 font-medium text-sm">
              <Cloud className="w-4 h-4" aria-hidden />
              {t.groq}
            </div>
            <div className="text-xs text-gray-600">{t.groqDesc}</div>
          </div>
        </label>
      </div>

      {provider === "groq" && (
        <div className="mb-3">
          <label className="block text-sm font-medium text-gray-700 mb-1">{t.keyLabel}</label>
          <input
            type="password"
            value={groqKey}
            onChange={(e) => setGroqKey(e.target.value)}
            placeholder={t.keyPlaceholder}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
        </div>
      )}

      <button
        type="button"
        onClick={handleSave}
        disabled={saving}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-700 text-white text-sm hover:bg-blue-800 disabled:opacity-50"
      >
        {saved ? <Check className="w-4 h-4" /> : null}
        {saved ? t.saved : t.save}
      </button>
    </div>
  );
}
