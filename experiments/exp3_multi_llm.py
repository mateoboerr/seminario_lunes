"""
Experimento 3 (Etapa 3): pipeline MULTI-LLM (dos pasadas) vs una sola pasada.

Propuesta del profe: un LLM detecta/lista las afirmaciones y OTRO LLM les asigna la
fuente. Este script:
  1) DEMO DETERMINISTA con stubs de dos etapas (sin API): valida que el pipeline
     encadena bien (afirmaciones → fuentes) y produce la salida v1 con spans.
  2) CORRIDA REAL (si hay key / LLM_PROVIDER): corre `MultiLLMSourceDetector` sobre
     las 16 notas, evalúa referenciados (comparable con Exp 0/1) y spans (Exp 2), y
     lo compara contra el single-pass `LLMSourceDetectorV1`. Cache por índice.

Uso:  python -m experiments.exp3_multi_llm
      (para Anthropic: LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY, ver README)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trust_sources.detectors.multi_llm import MultiLLMSourceDetector  # noqa: E402
from trust_sources.evaluation import evaluate_referenciados, evaluate_spans  # noqa: E402
from trust_sources.io_anotaciones import load_double_annotated  # noqa: E402
from trust_sources.llm_client import LLMClient, load_dotenv, make_client  # noqa: E402

RESULTS = ROOT / "results"
CACHE = ROOT / "experiments" / "cache" / "exp3_multi.json"


class StubClient(LLMClient):
    """Cliente falso con respuesta fija (para probar el pipeline sin API)."""
    name = "stub"

    def __init__(self, respuesta: str):
        self.respuesta = respuesta

    def generate(self, system: str, user: str, max_tokens: int = 500) -> str:
        return self.respuesta


NOTA_DEMO = (
    "La inflación de junio fue del 4,2%, informó el INDEC este martes. "
    "El ministro de Economía aseguró que “la tendencia es a la baja” y pidió calma."
)
STUB_AFIRMACIONES = json.dumps({"afirmaciones": [
    "La inflación de junio fue del 4,2%", "“la tendencia es a la baja”"]},
    ensure_ascii=False)
STUB_FUENTES = json.dumps({"fuentes": [
    {"referenciado": "el INDEC", "conector": "informó",
     "afirmacion": "La inflación de junio fue del 4,2%",
     "tipo": "institucion", "explicita": True},
    {"referenciado": "El ministro de Economía", "conector": "aseguró",
     "afirmacion": "“la tendencia es a la baja”", "tipo": "persona",
     "explicita": True}]}, ensure_ascii=False)


def demo_stub() -> None:
    det = MultiLLMSourceDetector(StubClient(STUB_AFIRMACIONES), StubClient(STUB_FUENTES))
    sources = det.detect(NOTA_DEMO)
    for s in sources:
        for sp in s.components.values():
            if sp.start_char >= 0:
                assert NOTA_DEMO[sp.start_char:sp.end_char] == sp.text, f"span mal: {sp}"
    assert [s.referenciado_text for s in sources] == ["el INDEC", "El ministro de Economía"]
    print(f"  demo stub: OK (pipeline 2 etapas → {len(sources)} fuentes, spans validados)")


def _load_cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def corrida_real() -> None:
    """Corre multi-LLM sobre las 16 notas y evalúa (si hay key/cache)."""
    from trust_sources.schema import source_from_components
    arts, _ = load_double_annotated()
    cache = _load_cache()
    client = make_client()
    detector = MultiLLMSourceDetector(client) if client else None
    throttle = float(os.environ.get("EXP_THROTTLE_S", "5"))
    max_fallos = int(os.environ.get("EXP_MAX_FALLOS", "4"))

    preds: dict[str, list] = {}
    pred_refs: dict[str, list] = {}
    n_ok = fallos = 0
    corto = False
    for a in arts:
        if a.index in cache:
            fuentes = cache[a.index]; n_ok += 1
        elif detector is not None and not corto:
            if throttle:
                time.sleep(throttle)
            try:
                srcs = detector.detect(a.cuerpo)
                fuentes = [{"referenciado": s.referenciado_text or "",
                            "conector": (s.components.get("conector").text
                                         if s.components.get("conector") else ""),
                            "afirmacion": (s.components.get("afirmacion").text
                                           if s.components.get("afirmacion") else ""),
                            "tipo": s.tipo, "explicita": s.explicit} for s in srcs]
                cache[a.index] = fuentes; n_ok += 1; fallos = 0
            except Exception as e:  # noqa: BLE001
                print(f"  [multi] {a.index}: {e}"); fuentes = []; fallos += 1
                if fallos >= max_fallos:
                    corto = True; print(f"  [multi] {max_fallos} fallos: corto.")
        else:
            fuentes = []
        preds[a.index] = [source_from_components(
            a.cuerpo, {"referenciado": f["referenciado"], "conector": f["conector"],
                       "afirmacion": f["afirmacion"]},
            tipo=f.get("tipo"), explicit=f.get("explicita", True)) for f in fuentes]
        pred_refs[a.index] = [f["referenciado"] for f in fuentes if f["referenciado"]]

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    if n_ok == 0:
        print("  corrida real: sin datos (falta key/cuota); el pipeline quedó listo "
              "para comparar contra single-pass al conectar Anthropic.")
        return

    m_ref = evaluate_referenciados(arts, pred_refs)
    ev = evaluate_spans(arts, preds)
    md = ["# Exp 3 — multi-LLM (dos pasadas)\n",
          f"- Notas con predicción multi-LLM: **{n_ok}/{len(arts)}**\n",
          "Referenciados (comparable con Exp 0/1):", "",
          f"- P {m_ref['P']:.2f} · R {m_ref['R']:.2f} · **F1 {m_ref['F1']:.2f}**\n",
          "Spans por componente:", "", "| Componente | P | R | F1 |", "|---|---|---|---|"]
    for lab in ["Referenciado", "Conector", "Afirmacion", "global"]:
        m = ev[lab]
        md.append(f"| {lab} | {m['P']:.2f} | {m['R']:.2f} | **{m['F1']:.2f}** |")
    (RESULTS / "exp3_multi.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  corrida real: {n_ok}/{len(arts)} · referenciados F1 {m_ref['F1']:.2f} · "
          f"span-F1 global {ev['global']['F1']:.2f} · escrito results/exp3_multi.md")


def main() -> None:
    load_dotenv(ROOT / ".env")
    print("Exp 3 — pipeline multi-LLM")
    demo_stub()
    corrida_real()


if __name__ == "__main__":
    main()
