"""
trust_sources — detección de fuentes periodísticas para trust-monitor.

Paquete del Proyecto 1. Expone:
  - schema: Source / Span (estructura de salida, estilo Trust get_explicit_sources)
  - detectors: ClassicSourceDetector, LLMSourceDetector (interfaz común SourceDetector)
  - io_anotaciones: carga de las anotaciones humanas
  - matching / evaluation: emparejamiento y métricas P/R/F1
  - llm_client: cliente multi-proveedor (Gemini/Anthropic)
"""
from .schema import Source, Span
from .detectors.base import SourceDetector
from .detectors.classic import ClassicSourceDetector
from .detectors.llm import LLMSourceDetector, LLMSourceDetectorV1

__all__ = ["Source", "Span", "SourceDetector", "ClassicSourceDetector",
           "LLMSourceDetector", "LLMSourceDetectorV1"]
