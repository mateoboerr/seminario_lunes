"""
Experimento base (v0): benchmark Clásico vs LLM vs humano en detección de fuentes.

Corre los dos detectores sobre el lote doble-anotado, compara contra el humano
(lch) y contra el segundo anotador (techo humano), y escribe resultados en
`results/`. La columna LLM usa un cache en disco (para no gastar cuota ni requerir
API key); con `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` seteada, corre en vivo.

Uso:  python -m experiments.run_benchmark   (desde la raíz del repo)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trust_sources import ClassicSourceDetector, LLMSourceDetector  # noqa: E402
from trust_sources.evaluation import evaluate_referenciados, human_ceiling  # noqa: E402
from trust_sources.io_anotaciones import load_double_annotated  # noqa: E402
from trust_sources.llm_client import default_client  # noqa: E402
from trust_sources import matching  # noqa: E402

CACHE = Path(__file__).resolve().parent / "cache" / "llm_sources.json"
RESULTS = ROOT / "results"


def _load_cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    arts, xig = load_double_annotated()
    print(f"Artículos doble-anotados: {len(arts)}")

    clasico = ClassicSourceDetector()
    client = default_client()
    llm = LLMSourceDetector(client) if client else None
    cache = _load_cache()
    origenes: set[str] = set()

    pred_clasico, pred_llm = {}, {}
    for a in arts:
        pred_clasico[a.index] = clasico.referenciados(a.cuerpo)
        if a.index in cache and llm is None:
            pred_llm[a.index] = cache[a.index]; origenes.add("cache")
        elif llm is not None:
            try:
                names = llm.referenciados(a.cuerpo)
                pred_llm[a.index] = names
                cache[a.index] = names; origenes.add(client.name)
            except Exception as e:  # noqa: BLE001
                print(f"  [llm] {a.index}: {e}; uso cache")
                pred_llm[a.index] = cache.get(a.index, []); origenes.add("cache")
        else:
            pred_llm[a.index] = cache.get(a.index, []); origenes.add("cache")
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    m_clasico = evaluate_referenciados(arts, pred_clasico)
    m_llm = evaluate_referenciados(arts, pred_llm)
    techo = human_ceiling(arts, xig)
    origen = " + ".join(sorted(origenes))

    # --- Tabla markdown ---
    tabla = [
        "| Detector | Precisión | Recall | F1 |",
        "|---|---|---|---|",
        f"| Clásico (reglas) vs humano | {m_clasico['P']:.2f} | {m_clasico['R']:.2f} | **{m_clasico['F1']:.2f}** |",
        f"| LLM vs humano | {m_llm['P']:.2f} | {m_llm['R']:.2f} | **{m_llm['F1']:.2f}** |",
        f"| Techo humano (lch vs xig) | — | — | **{techo['F1']:.2f}** |",
    ]
    md = [
        "# Benchmark v0 — detección de fuentes (referenciados)\n",
        f"- Artículos: **{len(arts)}** (lote doble-anotado lch_100_119 ↔ xig_20_39)",
        f"- Origen columna LLM: **{origen}**\n",
        "\n".join(tabla), "",
        "> v0 compara el conjunto de fuentes (referenciados) por nota. El clásico "
        "solo ve citas entre comillas; el LLM toma también instituciones y "
        "atribuciones parafraseadas, pero sobre-detecta (precisión más baja).",
    ]
    (RESULTS / "benchmark_v0.md").write_text("\n".join(md), encoding="utf-8")
    (RESULTS / "benchmark_v0.json").write_text(json.dumps(
        {"n": len(arts), "clasico": m_clasico, "llm": m_llm, "techo": techo,
         "origen_llm": origen}, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Ejemplos: LLM gana al clásico ---
    ej = ["# Ejemplos — LLM vs Clásico\n"]
    n = 0
    for a in arts:
        cl = matching.cluster(pred_clasico[a.index])
        ll = matching.cluster(pred_llm[a.index])
        ganadas = [s for s in matching.cluster(a.referenciados)
                   if any(matching.mentions_match(s, x) for x in ll)
                   and not any(matching.mentions_match(s, x) for x in cl)]
        if ganadas and n < 3:
            n += 1
            ej += [f"## {a.titulo[:70]}",
                   f"- LLM atrapó y el clásico no: {ganadas}",
                   f"- Clásico: {cl or '(nada)'}", ""]
    (RESULTS / "ejemplos.md").write_text("\n".join(ej), encoding="utf-8")

    print(f"Clásico  F1={m_clasico['F1']:.2f}  (P={m_clasico['P']:.2f} R={m_clasico['R']:.2f})")
    print(f"LLM      F1={m_llm['F1']:.2f}  (P={m_llm['P']:.2f} R={m_llm['R']:.2f})  origen={origen}")
    print(f"Techo humano F1={techo['F1']:.2f}")
    print("Escrito en results/: benchmark_v0.md, benchmark_v0.json, ejemplos.md")


if __name__ == "__main__":
    main()
