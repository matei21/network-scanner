import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { askAssistant } from "../lib/api";
import { X, Send, Loader2, GitBranch, Activity, BookOpen, Search, Library, Wrench, ShieldCheck, ChevronDown, ChevronUp } from "lucide-react";

const AGENT_STYLE = {
  orchestrator: { Icon: GitBranch, color: "text-gray-600", ring: "border-gray-200 bg-gray-50" },
  analyzer: { Icon: Activity, color: "text-indigo-700", ring: "border-indigo-200 bg-indigo-50" },
  explainer: { Icon: BookOpen, color: "text-emerald-700", ring: "border-emerald-200 bg-emerald-50" },
  searcher: { Icon: Search, color: "text-sky-700", ring: "border-sky-200 bg-sky-50" },
  search_integrator: { Icon: Library, color: "text-amber-700", ring: "border-amber-200 bg-amber-50" },
  advisor: { Icon: Wrench, color: "text-blue-700", ring: "border-blue-200 bg-blue-50" },
  technical: { Icon: ShieldCheck, color: "text-purple-700", ring: "border-purple-200 bg-purple-50" },
};

const SOURCE_LABEL = {
  groq: "Groq",
  local: "Qwen local",
  template: { ro: "sablon", en: "template" },
  rules: { ro: "reguli", en: "rules" },
  web: "web",
  unavailable: { ro: "indisponibil", en: "unavailable" },
};

function sourceLabel(src, lang) {
  const l = SOURCE_LABEL[src];
  if (!l) return src;
  return typeof l === "string" ? l : l[lang] || l.en;
}

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function AgentBlock({ step, lang, highlight }) {
  const style = AGENT_STYLE[step.agent] || AGENT_STYLE.orchestrator;
  const { Icon } = style;
  return (
    <div className={`rounded-lg border p-2.5 ${style.ring} ${highlight ? "ring-2 ring-blue-400" : ""}`}>
      <div className="flex items-center gap-1.5 text-xs">
        <Icon className={`w-3.5 h-3.5 ${style.color}`} aria-hidden />
        <span className={`font-semibold ${style.color}`}>{step.name}</span>
        <span className="text-gray-500 truncate">· {step.role}</span>
        <span className="ml-auto shrink-0 px-1.5 py-0.5 rounded bg-white border border-gray-200 text-[10px] text-gray-600">
          {sourceLabel(step.source, lang)}
        </span>
      </div>
      <div className={`mt-1.5 whitespace-pre-line ${highlight ? "text-base text-gray-900" : "text-sm text-gray-800"}`}>
        {step.text}
      </div>
      {step.sources?.length > 0 && step.agent === "searcher" && (
        <ul className="mt-1.5 space-y-0.5">
          {step.sources.map((s, i) => (
            <li key={i} className="text-xs truncate">
              <span className="text-gray-500">[{i + 1}]</span>{" "}
              <a href={s.href} target="_blank" rel="noopener noreferrer" className="text-blue-700 hover:underline" title={s.title}>
                {s.title || hostOf(s.href)}
              </a>{" "}
              <span className="text-gray-400">{hostOf(s.href)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AssistantMessage({ m, lang, busy, onFollowup }) {
  const [showTrace, setShowTrace] = useState(true);
  const agents = m.agents || [];
  const finalIdx = agents.map((a) => a.agent).lastIndexOf(m.finalAgent);
  const trace = agents.filter((_, i) => i !== finalIdx);
  const finalStep = agents[finalIdx];

  return (
    <div className="mr-2 space-y-2">
      {finalStep ? (
        <AgentBlock step={finalStep} lang={lang} highlight />
      ) : (
        <div className="rounded-lg p-3 text-base bg-white border border-gray-200 whitespace-pre-line">{m.text}</div>
      )}

      {trace.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowTrace((v) => !v)}
            className="inline-flex items-center gap-1 text-xs text-gray-600 hover:text-gray-900"
            aria-expanded={showTrace}
          >
            {showTrace ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {lang === "ro" ? `Ce a facut fiecare agent (${trace.length})` : `What each agent did (${trace.length})`}
          </button>
          {showTrace && (
            <div className="mt-1.5 space-y-1.5 border-l-2 border-gray-200 pl-2">
              {trace.map((s, i) => (
                <AgentBlock key={i} step={s} lang={lang} />
              ))}
            </div>
          )}
        </div>
      )}

      {m.cites?.length > 0 && (
        <div className="text-xs text-gray-600 flex flex-wrap gap-1">
          {m.cites.map((c, j) => (
            <code key={j} className="font-mono bg-white px-1.5 py-0.5 border border-gray-200 rounded">
              {c.ip}:{c.port} {c.code}
            </code>
          ))}
        </div>
      )}

      {m.followups?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {m.followups.map((fq, j) => (
            <button
              key={j}
              type="button"
              disabled={busy}
              onClick={() => onFollowup(fq)}
              className="text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 disabled:opacity-50"
            >
              {fq}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Floating Mr. Potato assistant. Each answer shows which agent produced which part,
// plus cited scan evidence so answers stay grounded (NFR-06).
export default function MrPotato({ scanId, expert = false }) {
  const { t, lang } = useLanguage();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const wrapRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onDoc(e) {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    }
    function onKey(e) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [msgs, busy]);

  async function send(text) {
    text = text.trim();
    if (!text || busy) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setQ("");
    setBusy(true);
    try {
      const res = await askAssistant(text, scanId, lang, expert);
      setMsgs((m) => [
        ...m,
        {
          role: "assistant",
          text: res.answer,
          finalAgent: res.agent,
          agents: res.agents || [],
          cites: res.cites || [],
          followups: res.followups || [],
        },
      ]);
    } catch (err) {
      setMsgs((m) => [...m, { role: "assistant", text: `(${String(err.message || err)})` }]);
    } finally {
      setBusy(false);
    }
  }

  function submit(e) {
    e.preventDefault();
    send(q);
  }

  const potatoName = lang === "ro" ? "Dl. Cartof" : "Mr. Potato";
  const potatoGreeting =
    lang === "ro" ? "Salut! Intreaba-ma orice despre reteaua ta." : "Hi! Ask me anything about your network.";
  const modeLabel = expert ? (lang === "ro" ? "mod avansat" : "expert mode") : (lang === "ro" ? "mod simplu" : "simple mode");

  return (
    <div ref={wrapRef}>
      <button
        type="button"
        className="potato-launcher"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? `Close ${potatoName}` : `Open ${potatoName}`}
        aria-expanded={open}
      >
        <img src="/mr-potato.png" alt="" aria-hidden />
        {!open && <span className="potato-bubble">{potatoName}</span>}
      </button>

      {open && (
        <section className="potato-drawer" role="dialog" aria-label={potatoName}>
          <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg">{potatoName}</span>
              <span className="text-xs text-gray-600">{modeLabel}</span>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label={lang === "ro" ? "Inchide" : "Close"}
              className="p-1 rounded-lg hover:bg-gray-50"
            >
              <X className="w-5 h-5" />
            </button>
          </header>

          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3" aria-live="polite">
            {msgs.length === 0 && (
              <>
                <p className="text-base">{potatoGreeting}</p>
                <p className="text-xs text-gray-600">{t("chat_disclaimer")}</p>
              </>
            )}
            {msgs.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="rounded-lg p-3 text-base bg-gray-50 border border-gray-200 ml-6">
                  {m.text}
                </div>
              ) : (
                <AssistantMessage key={i} m={m} lang={lang} busy={busy} onFollowup={send} />
              )
            )}
            {busy && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
                {lang === "ro" ? "Agentii lucreaza la raspuns..." : "The agents are working on it..."}
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={submit} className="flex gap-2 px-3 py-3 border-t border-gray-200">
            <label htmlFor="potato-q" className="sr-only">
              {t("chat_placeholder")}
            </label>
            <input
              id="potato-q"
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("chat_placeholder")}
              disabled={busy}
              className="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-lg text-base"
            />
            <button
              type="submit"
              disabled={busy || !q.trim()}
              className="inline-flex items-center gap-1 px-3 py-2 rounded-lg bg-blue-700 text-white hover:bg-blue-800 disabled:opacity-50"
              aria-label={t("chat_send")}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </section>
      )}
    </div>
  );
}
