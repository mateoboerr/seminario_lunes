"""
Detector de fuentes con LLM (v0).

Recibe una noticia, le pide al modelo la lista de fuentes citadas y devuelve
`Source`s. En v0 solo completa el `referenciado`; el span (start/end) se calcula
CON CÓDIGO ubicando el nombre en el texto (ver schema.find_span).

El cliente LLM se inyecta (Dependency Inversion): se puede usar Gemini, Anthropic
o un stub en tests sin tocar esta clase.
"""
from __future__ import annotations

import json

from ..llm_client import LLMClient
from ..schema import Source, source_from_referenciado
from .base import SourceDetector

PROMPT_V0 = (
    "Sos un detector de FUENTES periodísticas. Una 'fuente' es la persona, "
    "institución, documento u organismo a quien la nota le ATRIBUYE "
    "EXPLÍCITAMENTE una declaración, información o dato, normalmente con un verbo "
    "de habla (dijo, afirmó, aseguró, informó, según, sostuvo, explicó, etc.) o "
    "una cita textual entre comillas.\n"
    "Reglas estrictas:\n"
    "- Incluí SOLO entidades a las que se les atribuye algo.\n"
    "- NO incluyas personas/lugares/organismos solo MENCIONADOS, nombrados al "
    "pasar, protagonistas que no aportan información, ni listas de nombres sin "
    "atribución.\n"
    "- Unificá las menciones de una misma fuente en UNA (nombre más completo). "
    "Si no hay ninguna fuente atribuida, devolvé lista vacía.\n"
    'Devolvé SOLO un JSON: {"fuentes": ["...", "..."]}. Sin texto adicional.'
)


def _parse_fuentes(raw: str) -> list[str]:
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start:end + 1]) if start >= 0 else {}
    return [str(x) for x in data.get("fuentes", [])]


class LLMSourceDetector(SourceDetector):
    name = "llm"

    def __init__(self, client: LLMClient, prompt: str = PROMPT_V0,
                 max_chars: int = 6000):
        self.client = client
        self.prompt = prompt
        self.max_chars = max_chars

    def detect(self, text: str) -> list[Source]:
        raw = self.client.generate(self.prompt, text[:self.max_chars], max_tokens=400)
        nombres = _parse_fuentes(raw)
        return [source_from_referenciado(text, n) for n in nombres]
