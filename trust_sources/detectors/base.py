"""Interfaz común de un detector de fuentes (patrón Strategy).

Cualquier detector (clásico, LLM, futuro híbrido) implementa `detect(text)` y
devuelve una lista de `Source`. Así se pueden intercambiar y comparar sin tocar
el resto del código (Open/Closed + Dependency Inversion).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..schema import Source


class SourceDetector(ABC):
    name: str = "abstract"

    @abstractmethod
    def detect(self, text: str) -> list[Source]:
        """Devuelve las fuentes detectadas en `text` (estructura tipo Trust)."""
        ...

    def referenciados(self, text: str) -> list[str]:
        """Vista v0: solo los nombres de las fuentes (referenciados)."""
        return [s.referenciado_text for s in self.detect(text)
                if s.referenciado_text]
