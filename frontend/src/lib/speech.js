// Text-to-speech and speech-to-text with the browser's Web Speech API (no extra dependency).
// TTS works offline with the voices installed in the OS; STT in Chrome/Edge uses the browser vendor's
// online service. Only one text is read at a time; components follow it through the "tts-change" event.

const LANG_TAG = { ro: "ro-RO", en: "en-US" };
const MAX_CHUNK = 180; // Chrome stops long utterances after ~15 s, so long texts are read in short pieces

let currentId = null;
let voices = [];

export function canSpeak() {
  return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

export function canListen() {
  return typeof window !== "undefined" && !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

function loadVoices() {
  if (canSpeak()) voices = window.speechSynthesis.getVoices();
}
if (canSpeak()) {
  loadVoices();
  window.speechSynthesis.addEventListener?.("voiceschanged", loadVoices);
}

function pickVoice(lang) {
  const prefix = (LANG_TAG[lang] || lang).slice(0, 2).toLowerCase();
  const matching = voices.filter((v) => v.lang?.toLowerCase().startsWith(prefix));
  // Edge's "Natural"/"Online" voices sound far better than the old desktop ones.
  return matching.find((v) => /natural|online/i.test(v.name)) || matching.find((v) => v.localService) || matching[0] || null;
}

export function hasVoiceFor(lang) {
  loadVoices();
  return voices.length === 0 || !!pickVoice(lang); // voices not loaded yet: don't warn
}

export function cleanForSpeech(text) {
  return String(text || "")
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/\b[A-Z]{2,}(?:_[A-Z]+)+\b/g, (code) => code.replace(/_/g, " ").toLowerCase()) // CAMERA_STREAM_EXPOSED
    .replace(/→/g, ", ")
    .replace(/[⚠✓✗•«»*#`|[\]]/g, " ")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{2,}/g, "\n")
    .trim();
}

function splitChunks(text) {
  const pieces = text.split(/(?<=[.!?;:])\s+|\n+/).map((s) => s.trim()).filter(Boolean);
  const chunks = [];
  for (const piece of pieces) {
    if (piece.length <= MAX_CHUNK) {
      chunks.push(piece);
      continue;
    }
    let rest = piece;
    while (rest.length > MAX_CHUNK) {
      const cut = rest.lastIndexOf(" ", MAX_CHUNK);
      chunks.push(rest.slice(0, cut > 40 ? cut : MAX_CHUNK));
      rest = rest.slice(cut > 40 ? cut + 1 : MAX_CHUNK);
    }
    if (rest) chunks.push(rest);
  }
  return chunks;
}

function notify() {
  window.dispatchEvent(new CustomEvent("tts-change", { detail: currentId }));
}

export function isSpeaking(id) {
  return currentId !== null && currentId === id;
}

export function stopSpeaking() {
  if (!canSpeak()) return;
  window.speechSynthesis.cancel();
  currentId = null;
  notify();
}

export function speak(text, lang, id) {
  if (!canSpeak()) return false;
  const chunks = splitChunks(cleanForSpeech(text));
  window.speechSynthesis.cancel();
  if (!chunks.length) return false;
  currentId = id;
  notify();
  const voice = pickVoice(lang);
  chunks.forEach((chunk, i) => {
    const u = new SpeechSynthesisUtterance(chunk);
    u.lang = LANG_TAG[lang] || lang;
    if (voice) u.voice = voice;
    u.rate = 0.95;
    const finish = () => {
      if (currentId === id) {
        currentId = null;
        notify();
      }
    };
    if (i === chunks.length - 1) u.onend = finish;
    u.onerror = (e) => {
      if (e.error !== "interrupted" && e.error !== "canceled") finish();
    };
    window.speechSynthesis.speak(u);
  });
  return true;
}

// One-shot recognizer: onText(text, isFinal) while the person speaks, onEnd when it stops.
export function createRecognizer(lang, { onText, onEnd, onError }) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) return null;
  const rec = new Recognition();
  rec.lang = LANG_TAG[lang] || lang;
  rec.interimResults = true;
  rec.continuous = false;
  rec.maxAlternatives = 1;
  rec.onresult = (e) => {
    let text = "";
    let final = false;
    for (let i = 0; i < e.results.length; i++) {
      text += e.results[i][0].transcript;
      if (e.results[i].isFinal) final = true;
    }
    onText?.(text.trim(), final);
  };
  rec.onerror = (e) => onError?.(e.error);
  rec.onend = () => onEnd?.();
  return rec;
}
