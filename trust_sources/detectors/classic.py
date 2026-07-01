"""
Detector CLÁSICO de fuentes (reglas), estilo `SourceMatcher` de Trust.

Reproduce la lógica de trust-monitor: una fuente se detecta ante una CITA TEXTUAL
entre comillas tipográficas “ ” acompañada de un VERBO CONECTOR y, opcionalmente,
una entidad REFERENCIADA (nombre con mayúscula).

El `SourceMatcher` original usa stanza (tokens + POS + NER PER); acá se reimplementa
con reglas léxicas porque en este entorno no se pudieron descargar los modelos de
stanza/spaCy (error SSL). Conserva su comportamiento y su limitación: solo ve
fuentes ancladas a comillas con referente con mayúscula.

Salida: lista de `Source`. Cuando puede, completa afirmacion + conector +
referenciado (ya con forma v1); si no encuentra referente, la Source queda sin él.
"""
from __future__ import annotations

import re

from ..schema import Source, Span
from .base import SourceDetector

CONECTORES = {
    "dijo", "afirmo", "afirmó", "aseguro", "aseguró", "sostuvo", "señalo",
    "señaló", "senalo", "expreso", "expresó", "indico", "indicó", "manifesto",
    "manifestó", "declaro", "declaró", "agrego", "agregó", "explico", "explicó",
    "destaco", "destacó", "remarco", "remarcó", "subrayo", "subrayó",
    "considero", "consideró", "advirtio", "advirtió", "preciso", "precisó",
    "puntualizo", "puntualizó", "recordo", "recordó", "comento", "comentó",
    "anuncio", "anunció", "confirmo", "confirmó", "apunto", "apuntó",
    "enfatizo", "enfatizó", "detallo", "detalló", "aclaro", "aclaró",
    "sumo", "sumó", "concluyo", "concluyó", "respondio", "respondió",
    "agrega", "asegura", "afirma", "sostiene", "explica", "dice", "señala",
    "informo", "informó", "lanzo", "lanzó",
}
_CURLY = "[“”]"
_PROPER = re.compile(
    r"(?:[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ]+(?:\s+(?:de|del|la|los|las|y|el)\s+|\s+)){0,4}"
    r"[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ]+")
_START = {"El", "La", "Los", "Las", "En", "Por", "Con", "Al", "Su", "Este",
          "Esta", "Esto", "Asimismo", "Ademas", "Además", "Tambien", "También",
          "No", "Luego", "Antes", "Hasta", "Desde", "Para", "Segun", "Según",
          "Hoy", "Ayer", "Como", "Cuando", "Mientras", "Aunque"}


def _norm(tok: str) -> str:
    return tok.lower().strip(".,;:()¿?¡!“”\"'")


def _proper_span(full: str, region_start: int, region_end: int):
    """Último nombre propio dentro de full[region_start:region_end] (más cercano
    a la cita). Devuelve (texto, start, end) en coords absolutas, o None."""
    region = full[region_start:region_end]
    best = None
    for m in _PROPER.finditer(region):
        toks = m.group(0).split()
        while toks and toks[0] in _START:
            toks.pop(0)
        if not toks or len(" ".join(toks)) < 3:
            continue
        cand = " ".join(toks)
        off = region.find(cand, m.start())
        best = (cand, region_start + off, region_start + off + len(cand))
    return best


class ClassicSourceDetector(SourceDetector):
    name = "clasico"

    def detect(self, text: str) -> list[Source]:
        sources: list[Source] = []
        for m in re.finditer(_CURLY + r"(.+?)" + _CURLY, text, flags=re.DOTALL):
            ini, fin = m.start(), m.end()
            before_s = max(0, ini - 90)
            after_e = min(len(text), fin + 90)
            ventana = text[before_s:ini] + " " + text[fin:after_e]
            toks = [_norm(t) for t in re.split(r"\s+", ventana) if t]
            if not any(t in CONECTORES for t in toks):
                continue

            comps: dict[str, Span] = {
                "afirmacion": Span(text[ini:fin], ini, fin, "Afirmacion")}

            # Conector: primer verbo de habla en la ventana posterior/anterior.
            for region in ((fin, after_e), (before_s, ini)):
                reg = text[region[0]:region[1]]
                mv = next((w for w in re.finditer(r"\w+", reg)
                           if _norm(w.group(0)) in CONECTORES), None)
                if mv:
                    cs = region[0] + mv.start()
                    comps["conector"] = Span(text[cs:cs + len(mv.group(0))], cs,
                                             cs + len(mv.group(0)), "Conector")
                    break

            # Referenciado: nombre propio más cercano (después, si no antes).
            ref = _proper_span(text, fin, after_e) or _proper_span(text, before_s, ini)
            if ref:
                comps["referenciado"] = Span(ref[0], ref[1], ref[2], "Referenciado")

            starts = [s.start_char for s in comps.values()]
            ends = [s.end_char for s in comps.values()]
            sources.append(Source(text=text[min(starts):max(ends)],
                                  start_char=min(starts), end_char=max(ends),
                                  pattern="cita_comillas", components=comps))
        return sources
