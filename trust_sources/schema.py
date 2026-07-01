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
    En v0 solo se completa 'referenciado'.
    """
    text: str
    start_char: int
    end_char: int
    pattern: str = "llm"          # nombre del patrón (clásico) o "llm"
    explicit: bool = True
    components: dict[str, Span] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return self.end_char - self.start_char

    @property
    def referenciado_text(self) -> Optional[str]:
        ref = self.components.get("referenciado")
        return ref.text if ref else None

    def to_dict(self) -> dict:
        """Forma de dict idéntica a la de Trust `get_explicit_sources`."""
        return {
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "length": self.length,
            "pattern": self.pattern,
            "explicit": self.explicit,
            "components": {k: v.to_dict() for k, v in self.components.items()},
        }


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
