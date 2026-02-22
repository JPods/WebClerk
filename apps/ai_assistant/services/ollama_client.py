"""
Ollama client — communicates with the local Ollama API for LLM inference.

Usage:
    from apps.ai_assistant.services.ollama_client import OllamaClient

    client = OllamaClient()
    response = client.generate("Explain Django middleware")
    # or stream:
    for chunk in client.stream("Explain Django middleware"):
        print(chunk, end="")
    # with modes:
    response = client.generate("What's wrong?", mode="debugger", context=traceback)
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


class OllamaClient:
    """Thin wrapper around Ollama's REST API."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

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
        """Non-streaming generation — returns the full response."""
        messages = self._build_messages(prompt, context, history, mode=mode)

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
            logger.error("Cannot connect to Ollama at %s — is it running?", self.base_url)
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Start it with: ollama serve"
            )
        except Exception as e:
            logger.exception("Ollama generation failed")
            raise

    def stream(
        self,
        prompt: str,
        context: str = "",
        history: list[dict] | None = None,
        mode: str = "general",
    ) -> Generator[str, None, None]:
        """Streaming generation — yields content chunks."""
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
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Start it with: ollama serve"
            )

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is loaded."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                # Match model name with or without version tag
                return any(
                    m == self.model or m.startswith(f"{self.model}:")
                    for m in models
                )
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Return list of available model names."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []
