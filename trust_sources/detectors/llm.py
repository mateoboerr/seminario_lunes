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
from ..schema import Source, source_from_components, source_from_referenciado
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


def items_sueltos(raw: str, clave: str) -> list:
    """Rescata los items COMPLETOS del array `clave` de un JSON TRUNCADO.

    Cuando el modelo excede su presupuesto de tokens, el JSON llega cortado a
    mitad y `json.loads` falla por completo: se pierde la nota entera. Acá
    escaneamos el array item por item con `raw_decode` y devolvemos los que
    cerraron bien, descartando el último a medias.

    Sirve para cualquier forma de item (strings, dicts, anidados) porque
    `raw_decode` parsea el siguiente valor JSON sea cual sea. Nota: escanear
    balanceando llaves a mano (como hacía la primera versión) se descuadra si
    hay una `}` DENTRO de un string; `raw_decode` no tiene ese problema.
    """
    m = raw.find(f'"{clave}"')
    lb = raw.find("[", m) if m >= 0 else raw.find("[")
    if lb < 0:
        return []
    dec = json.JSONDecoder()
    out, i = [], lb + 1
    while i < len(raw):
        while i < len(raw) and raw[i] in " \t\r\n,":
            i += 1
        if i >= len(raw) or raw[i] == "]":
            break  # fin del array
        try:
            val, i = dec.raw_decode(raw, i)
        except json.JSONDecodeError:
            break  # item cortado a mitad: descartamos y cortamos
        out.append(val)
    return out


def _parse_fuentes(raw: str) -> list[str]:
    """Extrae los nombres de fuente del JSON del modelo.

    Acepta dos formas de cada item: un string (`"INDEC"`) o un dict con el nombre
    bajo `nombre`/`fuente`/`name` (p. ej. cuando el prompt pide también evidencia:
    `{"nombre": "INDEC", "evidencia": "según el INDEC"}`).

    Tolera respuestas truncadas: si el JSON global no parsea, rescata los items
    completos en vez de perder la nota entera (le pasó a `v3_justifica`, cuyo
    JSON con evidencia excede presupuestos chicos).
    """
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start:end + 1]) if start >= 0 else {}
        items = data.get("fuentes", [])
    except json.JSONDecodeError:
        items = items_sueltos(raw, "fuentes")
    nombres = []
    for x in items:
        if isinstance(x, dict):
            x = x.get("nombre") or x.get("fuente") or x.get("name") or ""
        if str(x).strip():
            nombres.append(str(x).strip())
    return nombres


class LLMSourceDetector(SourceDetector):
    name = "llm"

    def __init__(self, client: LLMClient, prompt: str = PROMPT_V0,
                 max_chars: int = 6000, max_tokens: int = 400):
        self.client = client
        self.prompt = prompt
        self.max_chars = max_chars
        # Presupuesto de salida: los prompts que piden campos extra (p. ej.
        # evidencia) necesitan más: con 400 el JSON se TRUNCA y no parsea.
        self.max_tokens = max_tokens

    def detect(self, text: str) -> list[Source]:
        raw = self.client.generate(self.prompt, text[:self.max_chars],
                                   max_tokens=self.max_tokens)
        nombres = _parse_fuentes(raw)
        return [source_from_referenciado(text, n) for n in nombres]


# --- v1: salida rica (afirmacion + conector + referenciado + tipo, con spans) ---

PROMPT_V1 = (
    "Sos un extractor de FUENTES periodísticas. Para cada fuente a la que la nota le "
    "atribuye una afirmación, devolvé sus tres partes y su tipo.\n"
    "Definiciones:\n"
    "- referenciado: la fuente (persona, institución, documento u organismo).\n"
    "- conector: el verbo/expresión de atribución (dijo, afirmó, según, sostuvo...).\n"
    "- afirmacion: lo que se afirma o la cita textual atribuida a esa fuente.\n"
    "- tipo: uno de persona | institucion | documento | anonima.\n"
    "- explicita: true si hay verbo de habla o comillas; false si la atribución es "
    "implícita (dato presentado como de esa fuente sin verbo de habla directo).\n"
    "REGLA CLAVE: copiá el TEXTO EXACTO de la nota en referenciado/conector/afirmacion "
    "(mismos caracteres), porque las posiciones se calculan buscando ese texto. Si una "
    "parte no existe, dejala como cadena vacía.\n"
    "Unificá menciones de la misma fuente. Si no hay fuentes atribuidas, lista vacía.\n"
    'Devolvé SOLO JSON: {"fuentes": [{"referenciado": "...", "conector": "...", '
    '"afirmacion": "...", "tipo": "...", "explicita": true}]}. Sin texto adicional.'
)

_TIPOS = {"persona", "institucion", "documento", "anonima"}


def _objetos_sueltos(raw: str) -> list[dict]:
    """Objetos completos del array `fuentes` de una salida TRUNCADA (v1)."""
    return [x for x in items_sueltos(raw, "fuentes") if isinstance(x, dict)]


def _parse_fuentes_v1(raw: str) -> list[dict]:
    """Parsea la salida v1: lista de dicts con las partes de cada fuente.

    Tolera respuestas truncadas (por max_tokens): si el JSON global no parsea,
    rescata los objetos de fuente completos que haya."""
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start:end + 1]) if start >= 0 else {}
        items = data.get("fuentes", [])
    except json.JSONDecodeError:
        items = _objetos_sueltos(raw)  # salvamos lo que se pueda
    fuentes = []
    for x in items:
        if not isinstance(x, dict):
            x = {"referenciado": str(x)}
        ref = str(x.get("referenciado") or x.get("nombre") or "").strip()
        if not ref:
            continue
        tipo = str(x.get("tipo") or "").strip().lower() or None
        fuentes.append({
            "referenciado": ref,
            "conector": str(x.get("conector") or "").strip(),
            "afirmacion": str(x.get("afirmacion") or "").strip(),
            "tipo": tipo if tipo in _TIPOS else None,
            "explicita": bool(x.get("explicita", True)),
        })
    return fuentes


class LLMSourceDetectorV1(LLMSourceDetector):
    """Detector LLM con salida rica (v1): además del referenciado, extrae conector
    y afirmacion y clasifica el tipo. Los spans se calculan con código (find_span),
    igual que en el clásico. Misma interfaz `SourceDetector` (intercambiable)."""
    name = "llm_v1"

    def __init__(self, client: LLMClient, prompt: str = PROMPT_V1,
                 max_chars: int = 6000):
        super().__init__(client, prompt=prompt, max_chars=max_chars)

    def detect(self, text: str) -> list[Source]:
        raw = self.client.generate(self.prompt, text[:self.max_chars], max_tokens=1200)
        fuentes = _parse_fuentes_v1(raw)
        return [source_from_components(
                    text,
                    {"referenciado": f["referenciado"], "conector": f["conector"],
                     "afirmacion": f["afirmacion"]},
                    tipo=f["tipo"], explicit=f["explicita"])
                for f in fuentes]
