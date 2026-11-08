import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { askAssistant } from "../lib/api";
import { canListen, createRecognizer, speak, stopSpeaking } from "../lib/speech";
import SpeakButton from "./SpeakButton";
import { X, Send, Loader2, GitBranch, Activity, BookOpen, Search, Library, Wrench, ShieldCheck, ChevronDown, ChevronUp, Globe, AlertTriangle, Route, Mic, MicOff } from "lucide-react";

const WEB_TEXT = {
  ro: {
    offer: "Cauta pe internet",
    offerHint: "Raspunsul va veni de pe internet, nu din scanul tau.",
    banner: "Raspuns de pe internet, NU din scanul tau. Verifica sursele inainte sa schimbi ceva.",
    asked: "Cautare pe internet",
  },
  en: {
    offer: "Search online",
    offerHint: "The answer will come from the internet, not from your scan.",
    banner: "Answer from the internet, NOT from your scan. Check the sources before changing anything.",
    asked: "Internet search",
  },
};

const MIC_TEXT = {
  ro: {
    start: "Vorbeste (microfon)",
    stop: "Opreste microfonul",
    listening: "Te ascult... vorbeste acum.",
    denied: "Permite accesul la microfon din browser (iconita de langa adresa).",
    noSpeech: "Nu am auzit nimic. Apasa din nou pe microfon si vorbeste.",
    network: "Recunoasterea vocii are nevoie de internet.",
    other: "Microfonul nu a functionat. Poti scrie intrebarea.",
  },
  en: {
    start: "Speak (microphone)",
    stop: "Stop the microphone",
    listening: "Listening... speak now.",
    denied: "Allow microphone access in the browser (icon next to the address bar).",
    noSpeech: "I didn't hear anything. Press the microphone again and speak.",
    network: "Speech recognition needs an internet connection.",
    other: "The microphone didn't work. You can type the question.",
  },
};

function spokenAnswer(res) {
  const final = (res.agents || []).filter((a) => a.agent === res.agent).pop();
  return (final?.text || res.answer || "").replace(/^⚠[^\n]*\n+/, "");
}

const AGENT_STYLE = {
  orchestrator: { Icon: GitBranch, color: "text-gray-600", ring: "border-gray-200 bg-gray-50" },
  query_planner: { Icon: Route, color: "text-orange-700", ring: "border-orange-200 bg-orange-50" },
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

function AssistantMessage({ m, lang, busy, onFollowup, onSearchWeb }) {
  const [showTrace, setShowTrace] = useState(true);
  const W = WEB_TEXT[lang] || WEB_TEXT.ro;
  const agents = m.agents || [];
  const finalIdx = agents.map((a) => a.agent).lastIndexOf(m.finalAgent);
  const trace = agents.filter((_, i) => i !== finalIdx);
  // The backend prefixes web answers with a notice line; the banner below shows it instead.
  const finalStep = agents[finalIdx] && m.fromWeb
    ? { ...agents[finalIdx], text: agents[finalIdx].text.replace(/^⚠[^\n]*\n+/, "") }
    : agents[finalIdx];

  return (
    <div className="mr-2 space-y-2">
      {m.fromWeb && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-2.5 text-amber-900 text-base" role="note">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" aria-hidden />
          <span>{W.banner}</span>
        </div>
      )}
      {finalStep ? (
        <AgentBlock step={finalStep} lang={lang} highlight />
      ) : (
        <div className="rounded-lg p-3 text-base bg-white border border-gray-200 whitespace-pre-line">{m.text}</div>
      )}
      <div className="flex justify-end">
        <SpeakButton text={finalStep?.text || m.text} lang={lang} />
      </div>

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

      {m.offerWeb && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-2.5">
          <button
            type="button"
            disabled={busy}
            onClick={() => onSearchWeb(m.question)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-700 text-white text-base font-semibold hover:bg-sky-800 disabled:opacity-50"
          >
            <Globe className="w-4 h-4" aria-hidden />
            {W.offer}
          </button>
          <p className="mt-1 text-base text-sky-900">{W.offerHint}</p>
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
  const [listening, setListening] = useState(false);
  const [micError, setMicError] = useState("");
  const wrapRef = useRef(null);
  const endRef = useRef(null);
  const recRef = useRef(null);
  const askedByVoice = useRef(false);
  const M = MIC_TEXT[lang] || MIC_TEXT.ro;

  useEffect(() => () => recRef.current?.abort(), []);
  useEffect(() => {
    if (!open) recRef.current?.abort();
  }, [open]);

  function toggleMic() {
    if (listening) {
      recRef.current?.stop();
      return;
    }
    stopSpeaking();
    setMicError("");
    let heard = "";
    const rec = createRecognizer(lang, {
      onText: (text, isFinal) => {
        setQ(text);
        if (isFinal) heard = text;
      },
      onError: (err) => {
        const key = err === "not-allowed" || err === "service-not-allowed" ? "denied"
          : err === "no-speech" ? "noSpeech" : err === "network" ? "network" : err === "aborted" ? null : "other";
        if (key) setMicError(M[key]);
      },
      onEnd: () => {
        setListening(false);
        recRef.current = null;
        if (heard) {
          askedByVoice.current = true; // the answer to a spoken question is read back
          send(heard);
        }
      },
    });
    if (!rec) return;
    recRef.current = rec;
    try {
      rec.start();
      setListening(true);
    } catch {
      setMicError(M.other);
    }
  }

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

  async function send(text, { allowWeb = false } = {}) {
    text = text.trim();
    if (!text || busy) return;
    const W = WEB_TEXT[lang] || WEB_TEXT.ro;
    setMsgs((m) => [...m, { role: "user", text: allowWeb ? `${W.asked}: ${text}` : text }]);
    setQ("");
    setBusy(true);
    try {
      const res = await askAssistant(text, scanId, lang, expert, allowWeb);
      setMsgs((m) => [
        ...m,
        {
          role: "assistant",
          question: text,
          text: res.answer,
          finalAgent: res.agent,
          agents: res.agents || [],
          cites: res.cites || [],
          followups: res.followups || [],
          offerWeb: !!res.offer_web,
          fromWeb: !!res.from_web,
        },
      ]);
      if (askedByVoice.current) speak(spokenAnswer(res), lang, "potato-voice-answer");
    } catch (err) {
      setMsgs((m) => [...m, { role: "assistant", text: `(${String(err.message || err)})` }]);
    } finally {
      askedByVoice.current = false;
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
                <AssistantMessage
                  key={i}
                  m={m}
                  lang={lang}
                  busy={busy}
                  onFollowup={send}
                  onSearchWeb={(question) => send(question, { allowWeb: true })}
                />
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

          {(listening || micError) && (
            <p className={`px-3 pt-2 text-base ${micError ? "text-red-700" : "text-gray-700"}`} role="status">
              {micError || M.listening}
            </p>
          )}
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
            {canListen() && (
              <button
                type="button"
                onClick={toggleMic}
                disabled={busy}
                aria-pressed={listening}
                aria-label={listening ? M.stop : M.start}
                title={listening ? M.stop : M.start}
                className={`inline-flex items-center px-3 py-2 rounded-lg border disabled:opacity-50 ${
                  listening ? "border-red-400 bg-red-600 text-white animate-pulse" : "border-gray-300 bg-white hover:bg-gray-50"
                }`}
              >
                {listening ? <MicOff className="w-4 h-4" aria-hidden /> : <Mic className="w-4 h-4" aria-hidden />}
              </button>
            )}
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
