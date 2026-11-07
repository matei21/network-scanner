import { useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { askAssistant } from "../lib/api";
import { Sparkles, Send } from "lucide-react";

// Thin wrapper that will call person D's /api/assistant/ask endpoint.
// Renders the answer text + cited evidence (ip:port:code) so a juror can
// verify the AI isn't inventing findings (NFR-06: grounded).
export default function AssistantPanel({ scanId }) {
  const { lang, t } = useLanguage();
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState([]);

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
        { role: "assistant", text: res.answer, cites: res.cites || [] },
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

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Sparkles className="w-5 h-5 text-blue-700" aria-hidden />
        <h3 className="font-semibold">Asistent</h3>
      </div>

      <div className="space-y-2 max-h-72 overflow-y-auto" aria-live="polite">
        {msgs.length === 0 && (
          <p className="text-sm text-gray-600">{t("chat_disclaimer")}</p>
        )}
        {msgs.map((m, i) => (
          <div
            key={i}
            className={`rounded-lg p-3 text-base ${
              m.role === "user"
                ? "bg-blue-50 border border-blue-200"
                : "bg-gray-50 border border-gray-200"
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
          </div>
        ))}
      </div>

      <form onSubmit={submit} className="flex gap-2">
        <label htmlFor="assistant-q" className="sr-only">
          {t("chat_placeholder")}
        </label>
        <input
          id="assistant-q"
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
        >
          <Send className="w-4 h-4" aria-hidden />
          {t("chat_send")}
        </button>
      </form>
    </div>
  );
}
