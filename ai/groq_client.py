"""Groq cloud LLM client.

Uses Llama 3.3 70B by default: it writes far better Romanian than the 8B model and is still fast on Groq.
Falls back to the 8B model (higher rate limits) if the large one is slow, rate-limited or unavailable.

Built for a live demo: short timeouts and no silent SDK retries (the SDK default is 60 s x 3 attempts),
and when Groq fails it is skipped for a minute so the local model answers instead of every agent call
waiting for another timeout.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"
_TIMEOUTS = {DEFAULT_MODEL: 12.0, FALLBACK_MODEL: 8.0}
_COOLDOWN_SECONDS = 60

# Shared by every GroqLLM instance (one exists per scan's assistant).
_state_lock = threading.Lock()
_down_until = 0.0


def _mark_down(reason: str) -> None:
    global _down_until
    with _state_lock:
        _down_until = time.time() + _COOLDOWN_SECONDS
    logger.warning("Groq unavailable (%s); using the local model for %d s", reason, _COOLDOWN_SECONDS)


def groq_cooling_down() -> bool:
    with _state_lock:
        return time.time() < _down_until


class GroqLLM:
    """Groq cloud LLM via the groq SDK."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._available = False
        try:
            from groq import Groq
            self._client = Groq(api_key=api_key, max_retries=0, timeout=_TIMEOUTS.get(model, 12.0))
            self._available = True
            logger.info("GroqLLM initialized (model=%s)", model)
        except ImportError:
            logger.warning("groq package not installed. Run: pip install groq")
        except Exception as e:
            logger.warning("GroqLLM init failed: %s", e)

    @property
    def available(self):
        return self._available and not groq_cooling_down()

    def chat(self, system_prompt: str, user_message: str, max_tokens: int = 512):
        return self.chat_ex(system_prompt, user_message, max_tokens)[0]

    def chat_ex(self, system_prompt: str, user_message: str, max_tokens: int = 512):
        """(text, finish_reason); finish_reason 'length' means the answer was cut by max_tokens."""
        if not self._client or groq_cooling_down():
            return None, None
        last_error = ""
        for model in dict.fromkeys([self.model, FALLBACK_MODEL]):
            try:
                response = self._client.with_options(timeout=_TIMEOUTS.get(model, 10.0)).chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=max_tokens,
                    temperature=0.2,
                )
                choice = response.choices[0]
                return choice.message.content, choice.finish_reason
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)[:120]}"
                logger.warning("Groq API error (%s): %s", model, last_error)
                if "auth" in last_error.lower() or "401" in last_error:
                    break  # a wrong key won't work on the other model either
        _mark_down(last_error)
        return None, None
