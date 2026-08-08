"""
Detector multi-LLM (Etapa 3): pipeline de DOS pasadas, según la propuesta de la cátedra.

  - LLM 1 (extractor): lee la nota y lista TODAS las afirmaciones (declaraciones o
    datos presentados como dichos/hechos).
  - LLM 2 (asignador): recibe la nota + esas afirmaciones y, para cada una, resuelve
    la fuente → devuelve la estructura v1 (referenciado + conector + afirmacion +
    tipo), con los spans calculados por código.

La idea a comparar contra el detector de una sola pasada (`LLMSourceDetectorV1`): al
separar "encontrar afirmaciones" de "asignar la fuente", ¿mejora la precisión/recall?

Diseño: dos clientes inyectables (por defecto el mismo). Misma interfaz
`SourceDetector`, así que se evalúa con las mismas métricas (referenciados y spans).
Son 2 llamadas por nota (no una por afirmación) para no disparar la cuota.
"""
from __future__ import annotations

import json

from ..llm_client import LLMClient
from ..schema import Source, source_from_components
from .base import SourceDetector
from .llm import _parse_fuentes_v1, items_sueltos

PROMPT_AFIRMACIONES = (
    "Sos un extractor de AFIRMACIONES de una noticia. Una afirmación es una "
    "declaración, dato o valoración que la nota presenta como DICHA por alguien o "
    "como un hecho atribuible a una fuente.\n"
    "Listá todas las afirmaciones, COPIANDO EL TEXTO EXACTO de la nota (una porción "
    "que la identifique; puede ser la cita o la oración).\n"
    'Devolvé SOLO JSON: {"afirmaciones": ["...", "..."]}. Sin texto adicional.'
)

PROMPT_ASIGNAR = (
    "Recibís una noticia y una lista de AFIRMACIONES ya detectadas. Para cada "
    "afirmación, identificá su FUENTE: quién la dice o de quién es el dato.\n"
    "Para cada una devolvé referenciado (la fuente), conector (verbo de atribución, "
    "si hay), afirmacion (copiá el texto de la afirmación tal como vino), tipo "
    "(persona|institucion|documento|anonima) y explicita (true si hay verbo de habla "
    "o comillas; false si es implícita).\n"
    "COPIÁ EL TEXTO EXACTO de la nota en referenciado/conector/afirmacion (las "
    "posiciones se calculan buscándolo). Si una afirmación no tiene fuente atribuible, "
    "omitila.\n"
    'Devolvé SOLO JSON: {"fuentes": [{"referenciado": "...", "conector": "...", '
    '"afirmacion": "...", "tipo": "...", "explicita": true}]}. Sin texto adicional.'
)


def _strings_sueltos(raw: str) -> list[str]:
    """Afirmaciones completas de un JSON truncado. Sin esto, una respuesta
    cortada devolvía [] EN SILENCIO y el pipeline reportaba "0 fuentes" sin
    ningún error visible (ver bitácora, Exp 3)."""
    return [x for x in items_sueltos(raw, "afirmaciones") if isinstance(x, str)]


def _parse_afirmaciones(raw: str) -> list[str]:
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start:end + 1]) if start >= 0 else {}
        items = data.get("afirmaciones", [])
    except json.JSONDecodeError:
        items = _strings_sueltos(raw)  # salida truncada: salvamos lo que se pueda
    return [str(x).strip() for x in items if str(x).strip()]


class MultiLLMSourceDetector(SourceDetector):
    """Pipeline de dos LLMs: extraer afirmaciones → asignar fuente (salida v1)."""
    name = "multi_llm"

    def __init__(self, client: LLMClient, client2: LLMClient | None = None,
                 prompt1: str = PROMPT_AFIRMACIONES, prompt2: str = PROMPT_ASIGNAR,
                 max_chars: int = 6000):
        self.c1 = client
        self.c2 = client2 or client          # por defecto, el mismo modelo en ambas
        self.prompt1 = prompt1
        self.prompt2 = prompt2
        self.max_chars = max_chars

    def detect(self, text: str) -> list[Source]:
        recorte = text[:self.max_chars]
        # 1200 y no 800: listar TODAS las afirmaciones copiando texto exacto es
        # largo; con 800 el JSON se truncaba en 10/16 notas (y sin parser
        # tolerante eso se veía como "0 fuentes", no como error).
        raw1 = self.c1.generate(self.prompt1, recorte, max_tokens=1200)
        afirmaciones = _parse_afirmaciones(raw1)
        if not afirmaciones:
            return []
        user2 = recorte + "\n\nAFIRMACIONES:\n" + json.dumps(
            afirmaciones, ensure_ascii=False)
        raw2 = self.c2.generate(self.prompt2, user2, max_tokens=1400)
        fuentes = _parse_fuentes_v1(raw2)  # misma forma v1 → reutilizamos parser
        return [source_from_components(
                    text,
                    {"referenciado": f["referenciado"], "conector": f["conector"],
                     "afirmacion": f["afirmacion"]},
                    tipo=f["tipo"], explicit=f["explicita"])
                for f in fuentes]
