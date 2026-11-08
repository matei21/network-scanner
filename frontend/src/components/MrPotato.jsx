import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { askAssistant } from "../lib/api";
import { X, Send } from "lucide-react";

// Floating Mr. Potato assistant. Click the potato to open a small chat
// drawer; Escape or outside-click closes it. Chat posts to /api/assistant/ask
// (person D) and renders cited scan evidence so answers stay grounded
// (NFR-06).
export default function MrPotato({ scanId }) {
  const { t, lang } = useLanguage();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const wrapRef = useRef(null);

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

  async function submit(e) {
    e.preventDefault();
    const text = q.trim();
    if (!text) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setQ("");
    setBusy(true);
    try {
      const res = await askAssistant(text, scanId, lang);
      setMsgs((m) => [
        ...m,
        { role: "assistant", text: res.answer, cites: res.cites || [], followups: res.followups || [] },
      ]);
    } catch (err) {
      setMsgs((m) => [
        ...m,
        { role: "assistant", text: `(${String(err.message || err)})` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  const potatoName = lang === "ro" ? "Dl. Cartof" : "Mr. Potato";
  const potatoGreeting =
    lang === "ro"
      ? "Salut! Intreaba-ma orice despre reteaua ta."
      : "Hi! Ask me anything about your network.";

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
        <section
          className="potato-drawer"
          role="dialog"
          aria-label={potatoName}
        >
          <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg">{potatoName}</span>
              <span className="text-xs text-gray-600">
                {lang === "ro" ? "asistent" : "assistant"}
              </span>
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

          <div
            className="flex-1 overflow-y-auto px-4 py-3 space-y-2"
            aria-live="polite"
          >
            {msgs.length === 0 && (
              <>
                <p className="text-base">{potatoGreeting}</p>
                <p className="text-xs text-gray-600">{t("chat_disclaimer")}</p>
              </>
            )}
            {msgs.map((m, i) => (
              <div
                key={i}
                className={`rounded-lg p-3 text-base ${
                  m.role === "user"
                    ? "bg-gray-50 border border-gray-200 ml-6"
                    : "bg-white border border-gray-200 mr-6"
                }`}
              >
                <div>{m.text}</div>
                {m.cites && m.cites.length > 0 && (
                  <div className="mt-2 text-xs text-gray-600 flex flex-wrap gap-1">
                    {m.cites.map((c, j) => (
                      <code
                        key={j}
                        className="font-mono bg-white px-1.5 py-0.5 border border-gray-200 rounded"
                      >
                        {c.ip}:{c.port} {c.code}
                      </code>
                    ))}
                  </div>
                )}
                {m.followups && m.followups.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {m.followups.map((fq, j) => (
                      <button
                        key={j}
                        type="button"
                        disabled={busy}
                        onClick={() => { setQ(fq); }}
                        className="text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 disabled:opacity-50"
                      >
                        {fq}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          <form
            onSubmit={submit}
            className="flex gap-2 px-3 py-3 border-t border-gray-200"
          >
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
