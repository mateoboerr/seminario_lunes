"""
Integración con Trust (Etapa 4).

Trust expone `SourceMatcher.get_explicit_sources(stanza_doc) -> list[dict]`
(trustmonitor/matcher.py): una lista de fuentes, cada una un dict con
text/start_char/end_char/length/pattern/explicit/components. Nuestros detectores ya
producen ESA MISMA forma vía `Source.to_dict()`, así que la integración es un
adaptador fino: envuelve cualquier `SourceDetector` y expone el mismo método, para
poder **enchufar el detector LLM en el pipeline de Trust** o compararlo contra el
clásico usando el mismo contrato de salida.

Diferencia práctica: el `SourceMatcher` de Trust recibe un `stanza_doc` (usa stanza
para tokenizar/POS/NER); nuestros detectores trabajan sobre texto plano (en este
entorno no se pudo usar stanza por SSL). El adaptador acepta tanto un string como un
objeto con atributo `.text` (como el stanza_doc), para ser lo más drop-in posible.
"""
from __future__ import annotations

from .detectors.base import SourceDetector


def _texto(doc) -> str:
    """Acepta un string o un objeto tipo stanza_doc (con `.text`)."""
    return doc if isinstance(doc, str) else getattr(doc, "text", str(doc))


class TrustSourceAdapter:
    """Envuelve un `SourceDetector` y lo expone con la interfaz de Trust.

    Uso:
        adapter = TrustSourceAdapter(LLMSourceDetectorV1(client))
        sources = adapter.get_explicit_sources(texto)   # list[dict] forma Trust
    """

    def __init__(self, detector: SourceDetector):
        self.detector = detector

    def get_explicit_sources(self, doc) -> list[dict]:
        """Misma firma/salida que `SourceMatcher.get_explicit_sources` de Trust."""
        return [s.to_dict() for s in self.detector.detect(_texto(doc))]
