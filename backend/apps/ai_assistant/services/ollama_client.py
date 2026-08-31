"""
Alice LLM client — local-first with WCHQ fallback.

Three tiers:
    1. Local Ollama (free, private, no network)
    2. WCHQ shared LLM (subscription, Athena-authenticated)
    3. Algorithms only (no LLM — Tier 1 services still work)

Usage:
    from apps.ai_assistant.services.ollama_client import OllamaClient

    client = OllamaClient()
    response = client.generate("Explain Django middleware")
    # Falls back to WCHQ automatically if Ollama is unavailable.
    # Returns algorithm-only message if both are unavailable.
"""
import json
import logging
from typing import Generator

import httpx
from django.conf import settings

from .prompt_templates import get_system_prompt, wrap_query

logger = logging.getLogger(__name__)

# Defaults — override in settings.py
OLLAMA_BASE_URL = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = getattr(settings, "OLLAMA_MODEL", "deepseek-r1:8b")
OLLAMA_TIMEOUT = getattr(settings, "OLLAMA_TIMEOUT", 120)

# WCHQ fallback — used when Ollama is unavailable
WCHQ_LLM_URL = "https://webclerk.com/wcapi/alice/llm/"

# Pricing: per person per month. Alice counts is_staff.
# Community (free) = run your own Ollama.
# Standard ($4/person/mo) = WCHQ Alice escalation.
# Professional ($9/person/mo) = WCHQ Alice + Claude escalation.
PRICE_PER_PERSON_STANDARD = 400   # cents
PRICE_PER_PERSON_PROFESSIONAL = 900  # cents


def _get_athena_token() -> str:
    """Get the Athena token for WCHQ authentication."""
    try:
        from apps.core.models import Setting
        conn = Setting.objects.filter(
            purpose='wchq_connection', is_active=True
        ).first()
        if conn and isinstance(conn.config, dict):
            return conn.config.get('athena_token', '')
    except Exception:
        pass
    return ''


def _is_subscribed() -> bool:
    """Check if this installation has an active WCHQ subscription."""
    try:
        from apps.core.models import Setting
        sub = Setting.objects.filter(
            purpose='wc:subscription', is_active=True
        ).first()
        if sub and isinstance(sub.config, dict):
            return bool(sub.config.get('subscribed', False))
    except Exception:
        pass
    return False


class OllamaClient:
    """Alice LLM client — local Ollama with WCHQ fallback.

    Tries local Ollama first. If unavailable and the installation has
    a WCHQ subscription with LLM access, falls back to WCHQ.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._wchq_available = None  # cached per instance

    def _build_messages(
        self,
        prompt: str,
        context: str = "",
        history: list[dict] | None = None,
        mode: str = "general",
    ) -> list[dict]:
        """Build the message list for the chat API, using mode-specific system prompt."""
        system_prompt = get_system_prompt(mode)
        messages = [{"role": "system", "content": system_prompt}]

        if context:
            messages.append({
                "role": "system",
                "content": f"Relevant documentation and code context:\n\n{context}",
            })

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": prompt})
        return messages

    def generate(
        self,
        prompt: str,
        context: str = "",
        history: list[dict] | None = None,
        mode: str = "general",
    ) -> str:
        """Non-streaming generation — returns the full response.

        Tries local Ollama first. Falls back to WCHQ if:
        - Ollama is not running
        - Installation has a subscription tier with LLM access
        - WCHQ is reachable and Athena token is valid
        """
        messages = self._build_messages(prompt, context, history, mode=mode)

        # Try local Ollama first
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                return resp.json()["message"]["content"]
        except httpx.ConnectError:
            logger.info("Ollama unavailable at %s — trying WCHQ fallback", self.base_url)
        except Exception as e:
            logger.warning("Ollama generation failed: %s — trying WCHQ fallback", e)

        # Fallback to WCHQ
        return self._wchq_generate(messages, mode)

    def _wchq_generate(self, messages: list[dict], mode: str = "general") -> str:
        """Call WCHQ's shared Alice LLM endpoint.

        Sends the prompt (not raw data) to WCHQ. WCHQ never sees
        the installation's commerce data — only the formulated question.
        """
        if not _is_subscribed():
            logger.info("No WCHQ subscription — returning algorithm-only response")
            raise ConnectionError(
                "Alice LLM unavailable. Install Ollama for local AI, "
                "or subscribe at webclerk.com for cloud AI access."
            )

        athena_token = _get_athena_token()
        if not athena_token:
            raise ConnectionError(
                "WCHQ LLM fallback requires an Athena token. "
                "Register this installation at webclerk.com."
            )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    WCHQ_LLM_URL,
                    headers={
                        'Authorization': f'Athena {athena_token}',
                        'X-Alice-Mode': mode,
                    },
                    json={
                        "messages": messages,
                        "mode": mode,
                    },
                )

                if resp.status_code == 402:
                    raise ConnectionError(
                        "WCHQ LLM daily limit reached. "
                        "Upgrade your subscription or install Ollama locally."
                    )
                if resp.status_code == 401:
                    raise ConnectionError(
                        "Athena token rejected by WCHQ. "
                        "Re-register this installation at webclerk.com."
                    )

                resp.raise_for_status()
                data = resp.json()
                logger.info("WCHQ LLM fallback succeeded (tokens=%s)",
                           data.get('usage', {}).get('total_tokens', '?'))
                return data.get('response', data.get('message', {}).get('content', ''))

        except httpx.ConnectError:
            raise ConnectionError(
                "Cannot reach webclerk.com — Alice LLM unavailable. "
                "Install Ollama for offline AI."
            )
        except ConnectionError:
            raise
        except Exception as e:
            logger.exception("WCHQ LLM fallback failed")
            raise ConnectionError(f"WCHQ LLM error: {e}")

    def stream(
        self,
        prompt: str,
        context: str = "",
        history: list[dict] | None = None,
        mode: str = "general",
    ) -> Generator[str, None, None]:
        """Streaming generation — yields content chunks.

        Falls back to non-streaming WCHQ if Ollama unavailable.
        """
        messages = self._build_messages(prompt, context, history, mode=mode)

        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                    },
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                    return  # success — don't fall through
        except httpx.ConnectError:
            logger.info("Ollama unavailable for streaming — falling back to WCHQ")
        except Exception as e:
            logger.warning("Ollama streaming failed: %s — falling back to WCHQ", e)

        # Fallback: WCHQ non-streaming, yield as single chunk
        response = self._wchq_generate(messages, mode)
        yield response

    def is_available(self) -> bool:
        """Check if any LLM is available — local Ollama or WCHQ."""
        return self._ollama_available() or self._wchq_available_check()

    def _ollama_available(self) -> bool:
        """Check if local Ollama is running with the configured model."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                return any(
                    m == self.model or m.startswith(f"{self.model}:")
                    for m in models
                )
        except Exception:
            return False

    def _wchq_available_check(self) -> bool:
        """Check if WCHQ LLM fallback is configured and accessible."""
        return _is_subscribed() and bool(_get_athena_token())

    def get_llm_status(self) -> dict:
        """Return status of all LLM sources — for diagnostics."""
        ollama = self._ollama_available()
        subscribed = _is_subscribed()
        has_token = bool(_get_athena_token())

        return {
            'ollama': {
                'available': ollama,
                'url': self.base_url,
                'model': self.model,
            },
            'wchq': {
                'available': subscribed and has_token,
                'subscribed': subscribed,
                'has_athena_token': has_token,
                'pricing': '$14 per 5 staff users/mo',
            },
            'active_source': 'ollama' if ollama else ('wchq' if subscribed and has_token else 'none'),
        }

    def list_models(self) -> list[str]:
        """Return list of available local model names."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []
