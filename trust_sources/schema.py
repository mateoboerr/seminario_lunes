"""
Esquema de salida de los detectores de fuentes.

Objetivo de diseño: que la salida se parezca lo más posible a la estructura de
`get_explicit_sources` del proyecto Trust (trustmonitor/matcher.py), que devuelve
una **lista de fuentes**, cada una un dict con posiciones de carácter y
`components` (afirmacion / conector / referenciado).

Dos niveles de detalle:
  - **v0**: cada `Source` trae solo el `referenciado` (quién es la fuente).
  - **v1**: cada `Source` trae `afirmacion` + `conector` + `referenciado` (+ la
    relación implícita entre ellos), cada uno con su span (start/end).

Usamos dataclasses (claridad + tipado) con `.to_dict()` que produce exactamente
la forma de dict de Trust, para que sea interoperable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Span:
    """Un fragmento de texto con su posición exacta y su etiqueta."""
    text: str
    start_char: int
    end_char: int
    label: str  # "Afirmacion" | "Conector" | "Referenciado" | "Afirmacion Debil"

    def to_dict(self) -> dict:
        return {"text": self.text, "start_char": self.start_char,
                "end_char": self.end_char, "label": self.label}


@dataclass
class Source:
    """Una atribución detectada (una fuente y lo que se le atribuye).

    `components` mapea 'afirmacion' / 'conector' / 'referenciado' -> Span.
    En v0 solo se completa 'referenciado'; en v1, los tres.
    `tipo` (v1): persona / institucion / documento / anonima.
    """
    text: str
    start_char: int
    end_char: int
    pattern: str = "llm"          # nombre del patrón (clásico) o "llm"
    explicit: bool = True
    components: dict[str, Span] = field(default_factory=dict)
    tipo: Optional[str] = None    # v1: tipo de fuente

    @property
    def length(self) -> int:
        return self.end_char - self.start_char

    @property
    def referenciado_text(self) -> Optional[str]:
        ref = self.components.get("referenciado")
        return ref.text if ref else None

    def to_dict(self) -> dict:
        """Forma de dict idéntica a la de Trust `get_explicit_sources`.

        `tipo` se agrega solo cuando está presente (v1), para no romper la
        compatibilidad con la salida v0/Trust cuando no se usa.
        """
        d = {
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "length": self.length,
            "pattern": self.pattern,
            "explicit": self.explicit,
            "components": {k: v.to_dict() for k, v in self.components.items()},
        }
        if self.tipo is not None:
            d["tipo"] = self.tipo
        return d


def find_span(full_text: str, substring: str, label: str) -> Optional[Span]:
    """Ubica `substring` dentro de `full_text` y devuelve su Span (start/end).

    Esto es lo que permite darle POSICIÓN a la salida de un LLM: el modelo devuelve
    el texto de la fuente y acá calculamos, con código, dónde arranca y termina.
    Intenta match exacto y, si falla, sin distinguir mayúsculas.
    """
    if not substring:
        return None
    i = full_text.find(substring)
    if i < 0:
        i = full_text.lower().find(substring.lower())
    if i < 0:
        return None
    return Span(text=full_text[i:i + len(substring)], start_char=i,
                end_char=i + len(substring), label=label)


def source_from_referenciado(full_text: str, nombre: str,
                             pattern: str = "llm") -> Source:
    """Construye una `Source` v0 a partir del nombre de la fuente (referenciado),
    calculando su span en el texto. Si no se encuentra, el span queda en (-1,-1)."""
    span = find_span(full_text, nombre, "Referenciado")
    if span is None:
        span = Span(text=nombre, start_char=-1, end_char=-1, label="Referenciado")
    return Source(text=span.text, start_char=span.start_char,
                  end_char=span.end_char, pattern=pattern,
                  components={"referenciado": span})


# Mapa de clave de componente -> etiqueta del esquema humano de Trust.
_LABELS = {"afirmacion": "Afirmacion", "conector": "Conector",
           "referenciado": "Referenciado"}


def source_from_components(full_text: str, comps: dict[str, str], *,
                           tipo: Optional[str] = None, explicit: bool = True,
                           pattern: str = "llm") -> Source:
    """Construye una `Source` v1 a partir de los textos de cada componente.

    `comps` mapea 'afirmacion'/'conector'/'referenciado' -> el substring que el LLM
    copió de la nota. Para cada uno calculamos su span CON CÓDIGO (find_span); así la
    salida del LLM queda posicionada como la del clásico. El span global de la Source
    abarca de la primera a la última posición encontrada.
    """
    spans: dict[str, Span] = {}
    for clave, sub in comps.items():
        if not sub:
            continue
        label = _LABELS.get(clave, clave.capitalize())
        sp = find_span(full_text, sub, label)
        if sp is None:  # el LLM parafraseó y no calza literal: guardamos sin posición
            sp = Span(text=sub, start_char=-1, end_char=-1, label=label)
        spans[clave] = sp

    ubicados = [s for s in spans.values() if s.start_char >= 0]
    if ubicados:
        start = min(s.start_char for s in ubicados)
        end = max(s.end_char for s in ubicados)
        texto = full_text[start:end]
    else:
        start = end = -1
        texto = comps.get("referenciado", "") or comps.get("afirmacion", "")
    return Source(text=texto, start_char=start, end_char=end, pattern=pattern,
                  explicit=explicit, components=spans, tipo=tipo)
