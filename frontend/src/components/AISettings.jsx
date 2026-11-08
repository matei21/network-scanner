import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { getAISettings, updateAISettings } from "../lib/api";
import { Settings, Cpu, Cloud, Check, ChevronDown, AlertTriangle } from "lucide-react";

const TEXT = {
  ro: {
    button: "AI",
    title: "Setari AI",
    intro: "Alege ce model scrie explicatiile si raspunde in chat. Scorul si problemele gasite nu depind de AI.",
    local: "Local (Qwen 2.5 3B)",
    localDesc: "Ruleaza pe calculatorul tau, fara internet. Mai lent.",
    groq: "Groq Cloud",
    groqDesc: "Rapid. Trimite intrebarea si datele scanului catre Groq, deci are nevoie de internet si de o cheie API.",
    keyLabel: "Cheie API Groq",
    keySaved: "Cheie salvata (scrie una noua ca sa o inlocuiesti)",
    noKey: "Fara cheie, se foloseste modelul local.",
    save: "Salveaza",
    saved: "Salvat",
    error: "Nu am putut salva setarile.",
  },
  en: {
    button: "AI",
    title: "AI settings",
    intro: "Choose which model writes explanations and answers in the chat. The score and findings never depend on AI.",
    local: "Local (Qwen 2.5 3B)",
    localDesc: "Runs on your computer, no internet. Slower.",
    groq: "Groq Cloud",
    groqDesc: "Fast. Sends the question and scan data to Groq, so it needs internet and an API key.",
    keyLabel: "Groq API key",
    keySaved: "Key saved (type a new one to replace it)",
    noKey: "Without a key, the local model is used.",
    save: "Save",
    saved: "Saved",
    error: "Could not save the settings.",
  },
};

// AI provider picker shown as a dropdown in the top menu bar.
export default function AISettings() {
  const { lang } = useLanguage();
  const l = TEXT[lang] || TEXT.ro;
  const [open, setOpen] = useState(false);
  const [provider, setProvider] = useState("local");
  const [active, setActive] = useState("local");
  const [groqKey, setGroqKey] = useState("");
  const [hasKey, setHasKey] = useState(false);
  const [state, setState] = useState("idle");
  const wrapRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    getAISettings()
      .then((s) => {
        setProvider(s.provider);
        setActive(s.provider);
        setHasKey(s.has_groq_key);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) return;
    function onDoc(e) {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    }
    function onKey(e) {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function handleSave(e) {
    e.preventDefault();
    setState("saving");
    try {
      const res = await updateAISettings(provider, groqKey || undefined);
      setHasKey(res.has_groq_key);
      setProvider(res.provider);
      setActive(res.provider);
      setGroqKey("");
      setState("saved");
      setTimeout(() => setState("idle"), 1500);
    } catch {
      setState("error");
    }
  }

  const usingGroq = active === "groq" && hasKey;
  const ActiveIcon = usingGroq ? Cloud : Cpu;

  return (
    <div ref={wrapRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1 px-2.5 py-1.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 text-sm"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`${l.title}: ${usingGroq ? l.groq : l.local}`}
      >
        <Settings className="w-4 h-4" aria-hidden />
        <ActiveIcon className="w-4 h-4" aria-hidden />
        <span className="hidden lg:inline">{l.button}: {usingGroq ? "Groq" : "Local"}</span>
        <ChevronDown className="w-3.5 h-3.5" aria-hidden />
      </button>

      {open && (
        <form
          role="dialog"
          aria-label={l.title}
          onSubmit={handleSave}
          className="ai-menu absolute right-0 top-full mt-2 z-50 w-[min(22rem,calc(100vw-2rem))] rounded-xl p-4 shadow-xl"
        >
          <div className="flex items-center gap-2 mb-1">
            <Settings className="w-5 h-5" aria-hidden />
            <h2 className="font-semibold text-lg">{l.title}</h2>
          </div>
          <p className="ai-menu-muted text-base mb-3">{l.intro}</p>

          <fieldset className="space-y-2 mb-3">
            <legend className="sr-only">{l.title}</legend>
            {[
              { id: "local", Icon: Cpu, name: l.local, desc: l.localDesc },
              { id: "groq", Icon: Cloud, name: l.groq, desc: l.groqDesc },
            ].map(({ id, Icon, name, desc }) => (
              <label key={id} className={`ai-menu-option flex items-start gap-3 p-3 rounded-lg cursor-pointer ${provider === id ? "is-selected" : ""}`}>
                <input
                  type="radio"
                  name="ai-provider"
                  value={id}
                  checked={provider === id}
                  onChange={() => setProvider(id)}
                  className="mt-1.5"
                />
                <span className="min-w-0">
                  <span className="flex items-center gap-1.5 font-semibold text-base">
                    <Icon className="w-4 h-4" aria-hidden />
                    {name}
                  </span>
                  <span className="ai-menu-muted block text-base">{desc}</span>
                </span>
              </label>
            ))}
          </fieldset>

          {provider === "groq" && (
            <div className="mb-3">
              <label htmlFor="groq-key" className="block text-base font-medium mb-1">{l.keyLabel}</label>
              <input
                id="groq-key"
                type="password"
                autoComplete="off"
                value={groqKey}
                onChange={(e) => setGroqKey(e.target.value)}
                placeholder={hasKey ? l.keySaved : "gsk_..."}
                className="ai-menu-input w-full px-3 py-2 rounded-lg text-base"
              />
              {!hasKey && !groqKey && (
                <p className="ai-menu-warn mt-1.5 flex items-center gap-1.5 text-base">
                  <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden />
                  {l.noKey}
                </p>
              )}
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={state === "saving"}
              className="ai-menu-save inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-base font-semibold disabled:opacity-60"
            >
              {state === "saved" && <Check className="w-4 h-4" aria-hidden />}
              {state === "saved" ? l.saved : l.save}
            </button>
            {state === "error" && <span className="ai-menu-warn text-base">{l.error}</span>}
          </div>
        </form>
      )}
    </div>
  );
}
