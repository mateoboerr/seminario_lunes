"""
Cliente LLM multi-proveedor con una interfaz mínima: `generate(system, user)`.

Elige proveedor por variable de entorno (Gemini gratis primero, luego Anthropic).
Reintenta 429/503 (cuota/sobrecarga transitoria). Sin dependencias pesadas: usa
la REST API de Gemini con urllib (probado en este entorno).
"""
from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Interfaz mínima de un cliente LLM."""
    name: str = "abstract"

    @abstractmethod
    def generate(self, system: str, user: str, max_tokens: int = 500) -> str:
        ...


class GeminiClient(LLMClient):
    name = "gemini"

    def __init__(self, model: str | None = None, temperature: float = 0.0):
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.temperature = temperature
        self.key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def generate(self, system: str, user: str, max_tokens: int = 500) -> str:
        import urllib.error
        import urllib.request
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={self.key}")
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": max_tokens,
                                 "temperature": self.temperature},
        }
        data = json.dumps(body).encode("utf-8")
        last: Exception | None = None
        for intento in range(5):
            try:
                req = urllib.request.Request(
                    url, data=data, headers={"Content-Type": "application/json"})
                r = urllib.request.urlopen(req, timeout=60)
                d = json.load(r)
                return d["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 503) and intento < 4:
                    time.sleep(2 * (intento + 1))
                    continue
                raise
        raise last  # type: ignore[misc]


class AnthropicClient(LLMClient):
    name = "anthropic"

    def __init__(self, model: str = "claude-haiku-4-5", temperature: float = 0.0):
        self.model = model
        self.temperature = temperature

    def generate(self, system: str, user: str, max_tokens: int = 500) -> str:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=self.model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
        )
        return next((b.text for b in resp.content if b.type == "text"), "")


def load_dotenv(path: str | os.PathLike = ".env") -> None:
    """Carga variables `CLAVE=valor` de un archivo .env al entorno (sin dependencias).

    No pisa variables ya seteadas. Pensado para que la API key viva en un `.env`
    gitignoreado y NUNCA se hardcodee ni se pase por línea de comandos. Es un
    no-op si el archivo no existe.
    """
    import pathlib
    p = pathlib.Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        clave, valor = line.split("=", 1)
        clave, valor = clave.strip(), valor.strip().strip('"').strip("'")
        os.environ.setdefault(clave, valor)


def default_client() -> LLMClient | None:
    """Devuelve el cliente según qué API key esté seteada. None si no hay ninguna."""
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return GeminiClient()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    return None
