"""Configuración de pytest: asegura que `trust_sources` sea importable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
