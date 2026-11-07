/**
 * Voice module: TTS (citeste raspunsuri) + STT (pune intrebari cu vocea).
 * Zero dependinte -- foloseste Web Speech API din browser.
 *
 * Folosire:
 *   import { speak, stopSpeaking, listen, getVoices, isSupported } from './voice.js';
 *
 *   // Citeste un text in romana
 *   speak("Camera ta poate fi vazuta de oricine.", "ro-RO");
 *
 *   // Asculta o intrebare de la utilizator
 *   const text = await listen("ro-RO");
 */

// ── TTS (Text-to-Speech) ──────────────────────────────────────────

const synth = window.speechSynthesis;

/**
 * Returneaza vocile disponibile pentru o limba.
 * Apeleaza dupa ce vocile s-au incarcat (vezi onVoicesReady).
 */
export function getVoices(langPrefix = "ro") {
    return synth.getVoices().filter(v => v.lang.startsWith(langPrefix));
}

/**
 * Callback cand vocile sunt gata (pe unele browsere se incarca async).
 */
export function onVoicesReady(callback) {
    if (synth.getVoices().length > 0) {
        callback();
    }
    synth.onvoiceschanged = callback;
}

/**
 * Citeste un text cu voce.
 * @param {string} text - Textul de citit
 * @param {string} lang - Limba (ex: "ro-RO", "en-US")
 * @param {object} opts - Optiuni: rate (0.5-2), pitch (0-2), volume (0-1)
 * @returns {Promise<void>} - Se rezolva cand termina de vorbit
 */
export function speak(text, lang = "ro-RO", opts = {}) {
    return new Promise((resolve, reject) => {
        if (!synth) {
            reject(new Error("TTS not supported"));
            return;
        }

        synth.cancel();

        // Spargem textul in bucati de max 200 caractere (limita pe unele browsere)
        const chunks = splitText(text, 200);
        let index = 0;

        function speakNext() {
            if (index >= chunks.length) {
                resolve();
                return;
            }

            const utterance = new SpeechSynthesisUtterance(chunks[index]);
            utterance.lang = lang;
            utterance.rate = opts.rate || 0.9;
            utterance.pitch = opts.pitch || 1.0;
            utterance.volume = opts.volume || 1.0;

            // Alege cea mai buna voce pentru limba
            const voices = getVoices(lang.split("-")[0]);
            if (voices.length > 0) {
                utterance.voice = voices[0];
            }

            utterance.onend = () => {
                index++;
                speakNext();
            };
            utterance.onerror = (e) => {
                if (e.error === "canceled") {
                    resolve();
                } else {
                    reject(e);
                }
            };

            synth.speak(utterance);
        }

        speakNext();
    });
}

/**
 * Opreste vorbirea.
 */
export function stopSpeaking() {
    if (synth) synth.cancel();
}

/**
 * Verifica daca vorbeste acum.
 */
export function isSpeaking() {
    return synth ? synth.speaking : false;
}

function splitText(text, maxLen) {
    const chunks = [];
    const sentences = text.split(/(?<=[.!?])\s+/);
    let current = "";

    for (const sentence of sentences) {
        if (current.length + sentence.length > maxLen && current.length > 0) {
            chunks.push(current.trim());
            current = "";
        }
        current += sentence + " ";
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
}


// ── STT (Speech-to-Text) ──────────────────────────────────────────

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

/**
 * Asculta vocea utilizatorului si returneaza textul.
 * @param {string} lang - Limba de recunoastere ("ro-RO", "en-US")
 * @param {object} opts - Optiuni: timeout (ms, default 10000), onInterim (callback)
 * @returns {Promise<string>} - Textul recunoscut
 */
export function listen(lang = "ro-RO", opts = {}) {
    return new Promise((resolve, reject) => {
        if (!SpeechRecognition) {
            reject(new Error("Speech recognition not supported. Use Chrome or Edge."));
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = lang;
        recognition.continuous = false;
        recognition.interimResults = !!opts.onInterim;
        recognition.maxAlternatives = 1;

        const timeout = opts.timeout || 10000;
        const timer = setTimeout(() => {
            recognition.stop();
        }, timeout);

        recognition.onresult = (event) => {
            clearTimeout(timer);
            const last = event.results[event.results.length - 1];

            if (opts.onInterim && !last.isFinal) {
                opts.onInterim(last[0].transcript);
                return;
            }

            if (last.isFinal) {
                resolve(last[0].transcript);
            }
        };

        recognition.onerror = (event) => {
            clearTimeout(timer);
            if (event.error === "no-speech") {
                resolve("");
            } else {
                reject(new Error(`Speech recognition error: ${event.error}`));
            }
        };

        recognition.onend = () => {
            clearTimeout(timer);
        };

        recognition.start();
    });
}


// ── Helpers ────────────────────────────────────────────────────────

/**
 * Verifica suportul browser-ului.
 */
export function isSupported() {
    return {
        tts: !!window.speechSynthesis,
        stt: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
    };
}

/**
 * Detecteaza limba textului (simplu, bazat pe diacritice).
 */
export function detectLang(text) {
    const roChars = /[ăâîșțĂÂÎȘȚ]/;
    return roChars.test(text) ? "ro-RO" : "en-US";
}
