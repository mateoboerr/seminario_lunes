"""
CLI de demo: corre un detector sobre un texto y muestra la salida (forma Trust).

Ejemplos:
  python -m trust_sources "El ministro aseguró: “bajó”."          # clásico (sin API)
  python -m trust_sources --file nota.txt --detector v1           # LLM v1 (necesita key)
  echo "..." | python -m trust_sources --detector clasico

Detectores: clasico (default, sin API) | v0 | v1 | multi  (los LLM usan la key del
.env y LLM_PROVIDER; ver README).
"""
from __future__ import annotations

import argparse
import json
import sys

from . import (ClassicSourceDetector, LLMSourceDetector, LLMSourceDetectorV1,
               MultiLLMSourceDetector)
from .llm_client import load_dotenv, make_client


def _build_detector(nombre: str):
    if nombre == "clasico":
        return ClassicSourceDetector()
    client = make_client()
    if client is None:
        sys.exit("Este detector necesita una API key (poné GEMINI_API_KEY o "
                 "ANTHROPIC_API_KEY en .env). El detector 'clasico' funciona sin key.")
    return {"v0": LLMSourceDetector, "v1": LLMSourceDetectorV1,
            "multi": MultiLLMSourceDetector}[nombre](client)


def main(argv: list[str] | None = None) -> None:
    load_dotenv(".env")
    ap = argparse.ArgumentParser(prog="trust_sources",
                                 description="Detecta fuentes de una noticia.")
    ap.add_argument("texto", nargs="?", help="texto de la nota (o usar --file/stdin)")
    ap.add_argument("--file", help="archivo con el texto de la nota")
    ap.add_argument("--detector", default="clasico",
                    choices=["clasico", "v0", "v1", "multi"])
    args = ap.parse_args(argv)

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            texto = f.read()
    elif args.texto:
        texto = args.texto
    else:
        texto = sys.stdin.read()
    if not texto.strip():
        ap.error("no hay texto (pasá un argumento, --file o por stdin)")

    detector = _build_detector(args.detector)
    sources = detector.detect(texto)
    print(json.dumps([s.to_dict() for s in sources], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
