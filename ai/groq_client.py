"""Groq cloud LLM client.

Uses the Groq SDK to call fast cloud models (Llama 3.1 8B by default).
Activated when the user provides an API key via frontend settings.
"""

import logging

logger = logging.getLogger(__name__)


class GroqLLM:
    """Groq cloud LLM via the groq SDK."""

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._available = False
        try:
            from groq import Groq
            self._client = Groq(api_key=api_key)
            self._available = True
            logger.info("GroqLLM initialized (model=%s)", model)
        except ImportError:
            logger.warning("groq package not installed. Run: pip install groq")
        except Exception as e:
            logger.warning("GroqLLM init failed: %s", e)

    @property
    def available(self):
        return self._available

    def chat(self, system_prompt: str, user_message: str, max_tokens: int = 512):
        if not self._client:
            return None
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning("Groq API error: %s", e)
            return None
