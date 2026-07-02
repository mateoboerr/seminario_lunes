"""
Experimento 2 (Etapa 2): salida RICA v1 — afirmacion + conector + referenciado
(con spans) + tipo de fuente, y evaluación a nivel de span.

Dos partes:
  1) DEMO DETERMINISTA con un cliente STUB (no usa API, no gasta cuota): sobre una
     nota de ejemplo muestra el dict de salida v1 (forma Trust `get_explicit_sources`)
     con las posiciones calculadas por código, y valida que los spans son correctos.
     Escribe `results/ejemplo_v1.md` para la Page.
  2) CORRIDA REAL (si hay GEMINI_API_KEY): corre `LLMSourceDetectorV1` sobre las 16
     notas doble-anotadas y evalúa a nivel de span (evaluate_spans) contra el humano.
     Cache por índice para reproducibilidad; sin key, solo usa lo cacheado.

Uso:  python -m experiments.exp2_salida_v1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trust_sources.detectors.llm import (LLMSourceDetectorV1,  # noqa: E402
                                         _parse_fuentes_v1)
from trust_sources.evaluation import evaluate_spans  # noqa: E402
from trust_sources.io_anotaciones import load_double_annotated  # noqa: E402
from trust_sources.llm_client import LLMClient, GeminiClient, default_client, load_dotenv  # noqa: E402
from trust_sources.schema import source_from_components  # noqa: E402

RESULTS = ROOT / "results"
CACHE = ROOT / "experiments" / "cache" / "exp2_v1.json"


class StubClient(LLMClient):
    """Cliente falso: devuelve un JSON fijo. Sirve para probar el pipeline v1 sin
    llamar a ninguna API (el diseño con cliente inyectado lo hace trivial)."""
    name = "stub"

    def __init__(self, respuesta: str):
        self.respuesta = respuesta

    def generate(self, system: str, user: str, max_tokens: int = 500) -> str:
        return self.respuesta


# --- Nota de ejemplo (sintética, con una fuente clara) ---
NOTA_DEMO = (
    "La inflación de junio fue del 4,2%, informó el INDEC este martes. "
    "El ministro de Economía aseguró que “la tendencia es a la baja” y pidió calma. "
    "Vecinos de Córdoba se manifestaron frente a la sede."
)
# Lo que "devolvería" el LLM (textos copiados EXACTOS de la nota):
STUB_JSON = json.dumps({"fuentes": [
    {"referenciado": "el INDEC", "conector": "informó",
     "afirmacion": "La inflación de junio fue del 4,2%",
     "tipo": "institucion", "explicita": True},
    {"referenciado": "El ministro de Economía", "conector": "aseguró",
     "afirmacion": "“la tendencia es a la baja”",
     "tipo": "persona", "explicita": True},
]}, ensure_ascii=False)


def demo_stub() -> list[dict]:
    """Corre el detector v1 con el stub sobre la nota demo y valida los spans."""
    detector = LLMSourceDetectorV1(StubClient(STUB_JSON))
    sources = detector.detect(NOTA_DEMO)
    dicts = [s.to_dict() for s in sources]

    # Validación: cada componente ubicado debe apuntar al texto correcto en la nota.
    for s in sources:
        for sp in s.components.values():
            if sp.start_char >= 0:
                assert NOTA_DEMO[sp.start_char:sp.end_char] == sp.text, \
                    f"span mal calculado: {sp}"
    assert sources[0].referenciado_text == "el INDEC"
    assert sources[0].tipo == "institucion"
    assert sources[1].components["afirmacion"].label == "Afirmacion"
    print("  demo stub: OK (2 fuentes, spans validados)")
    return dicts


def _write_ejemplo(dicts: list[dict]) -> None:
    RESULTS.mkdir(exist_ok=True)
    md = ["# Ejemplo de salida v1 (forma tipo Trust `get_explicit_sources`)\n",
          "Generado de forma determinista con un cliente **stub** (sin API) sobre una "
          "nota de ejemplo, para mostrar el **output**: cada fuente trae afirmacion + "
          "conector + referenciado **con sus posiciones** (calculadas por código) y su "
          "**tipo**.\n",
          "**Nota de entrada:**\n", f"> {NOTA_DEMO}\n", "**Salida (`detect()` → dicts):**\n",
          "```json", json.dumps(dicts, ensure_ascii=False, indent=2), "```"]
    (RESULTS / "ejemplo_v1.md").write_text("\n".join(md), encoding="utf-8")
    print("  escrito: results/ejemplo_v1.md")


def _load_cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def corrida_real() -> None:
    """Si hay key/cache, corre v1 sobre las 16 notas y evalúa a nivel de span."""
    arts, _ = load_double_annotated()
    cache = _load_cache()
    client = GeminiClient() if default_client() else None
    detector = LLMSourceDetectorV1(client) if client else None

    preds: dict[str, list] = {}
    n_ok = 0
    for a in arts:
        if a.index in cache:
            fuentes = cache[a.index]; n_ok += 1
        elif detector is not None:
            try:
                raw = client.generate(detector.prompt, a.cuerpo[:detector.max_chars],
                                      max_tokens=800)
                fuentes = _parse_fuentes_v1(raw); cache[a.index] = fuentes; n_ok += 1
            except Exception as e:  # noqa: BLE001
                print(f"  [v1] {a.index}: {e}"); fuentes = []
        else:
            fuentes = []
        preds[a.index] = [source_from_components(
            a.cuerpo, {"referenciado": f["referenciado"], "conector": f["conector"],
                       "afirmacion": f["afirmacion"]},
            tipo=f.get("tipo"), explicit=f.get("explicita", True)) for f in fuentes]

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    if n_ok == 0:
        print("  corrida real: sin datos (falta GEMINI_API_KEY o cuota); "
              "el pipeline v1 quedó listo, se completa al conectar un proveedor.")
        return

    ev = evaluate_spans(arts, preds)
    md = ["# Exp 2 — salida v1: evaluación a nivel de span\n",
          f"- Notas con predicción v1: **{n_ok}/{len(arts)}**",
          f"- Solapamiento mínimo (IoU) para acierto: 0.5\n",
          "| Componente | P | R | F1 |", "|---|---|---|---|"]
    for lab in ["Referenciado", "Conector", "Afirmacion", "global"]:
        m = ev[lab]
        md.append(f"| {lab} | {m['P']:.2f} | {m['R']:.2f} | **{m['F1']:.2f}** |")
    (RESULTS / "exp2_spans.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  corrida real: {n_ok}/{len(arts)} notas · span-F1 global "
          f"{ev['global']['F1']:.2f} · escrito results/exp2_spans.md")


def main() -> None:
    load_dotenv(ROOT / ".env")
    print("Exp 2 — salida rica v1")
    dicts = demo_stub()
    _write_ejemplo(dicts)
    corrida_real()


if __name__ == "__main__":
    main()
