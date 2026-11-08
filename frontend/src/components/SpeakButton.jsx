import { useEffect, useRef, useState } from "react";
import { Volume2, Square } from "lucide-react";
import { canSpeak, hasVoiceFor, isSpeaking, speak, stopSpeaking } from "../lib/speech";

const TEXT = {
  ro: { read: "Citeste cu voce tare", stop: "Opreste citirea", noVoice: "Nu exista o voce romaneasca instalata. In Windows: Setari > Ora si limba > Vorbire > Adauga voci (Romana)." },
  en: { read: "Read aloud", stop: "Stop reading", noVoice: "No English voice is installed in your system." },
};

let counter = 0;

// "Read aloud" toggle for any text. Only one text is read at a time across the whole page.
export default function SpeakButton({ text, lang, label = true, className = "" }) {
  const idRef = useRef(`tts-${++counter}`);
  const [active, setActive] = useState(false);
  const l = TEXT[lang] || TEXT.ro;

  useEffect(() => {
    const id = idRef.current;
    const onChange = (e) => setActive(e.detail === id);
    window.addEventListener("tts-change", onChange);
    return () => {
      window.removeEventListener("tts-change", onChange);
      if (isSpeaking(id)) stopSpeaking();
    };
  }, []);

  if (!canSpeak() || !text) return null;

  const voiceOk = hasVoiceFor(lang);
  const title = active ? l.stop : voiceOk ? l.read : `${l.read}. ${l.noVoice}`;

  return (
    <button
      type="button"
      onClick={() => (active ? stopSpeaking() : speak(text, lang, idRef.current))}
      aria-pressed={active}
      aria-label={active ? l.stop : l.read}
      title={title}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-base font-medium shrink-0 ${
        active ? "border-red-300 bg-red-50 text-red-800" : "border-gray-300 bg-white text-gray-800 hover:bg-gray-50"
      } ${className}`}
    >
      {active ? <Square className="w-4 h-4" aria-hidden /> : <Volume2 className="w-4 h-4" aria-hidden />}
      {label && <span>{active ? l.stop : l.read}</span>}
    </button>
  );
}
