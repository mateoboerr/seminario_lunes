"""
Experimento 3 (Etapa 3): pipeline MULTI-LLM (dos pasadas) vs una sola pasada.

Propuesta de la cátedra: un LLM detecta/lista las afirmaciones y OTRO LLM les asigna la
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
from trust_sources.llm_client import LLMClient, client_for_model, load_dotenv  # noqa: E402

RESULTS = ROOT / "results"
CACHE = ROOT / "experiments" / "cache" / "exp3_multi.json"
CACHE_EXP2 = ROOT / "experiments" / "cache" / "exp2_v1.json"

MODELO_GEMINI = "gemini-2.5-flash-lite"
MODELO_HAIKU = "claude-haiku-4-5"
MODELO_SONNET = "claude-sonnet-5"

# Configuraciones del pipeline (cache separado por config):
#  - multi_sonnet: dos pasadas del MISMO modelo (¿separar la tarea ayuda per se?)
#  - multi_gemini_sonnet: DOS MODELOS: la lectura literal de la propuesta de la
#    cátedra ("un LLM detecta afirmaciones, otro les asigna la fuente"): el
#    barato/gratis extrae, el fuerte asigna.
#  - multi_haiku_sonnet: la MISMA idea con otro modelo barato. Existe porque la
#    config con Gemini depende del free tier (~23 llamadas/día) y quedó parcial;
#    Haiku cumple el mismo rol conceptual, corre sin esperar cuota y además
#    aísla la variable: acá las dos etapas son del mismo proveedor y familia, así
#    que lo que se mide es "barato vs caro", no "Google vs Anthropic".
CONFIGS = [
    {"id": "multi_sonnet", "extractor": MODELO_SONNET, "asignador": MODELO_SONNET,
     "desc": f"dos pasadas, mismo modelo (`{MODELO_SONNET}`)"},
    {"id": "multi_gemini_sonnet", "extractor": MODELO_GEMINI, "asignador": MODELO_SONNET,
     "desc": f"dos modelos: `{MODELO_GEMINI}` extrae, `{MODELO_SONNET}` asigna"},
    {"id": "multi_haiku_sonnet", "extractor": MODELO_HAIKU, "asignador": MODELO_SONNET,
     "desc": f"dos modelos: `{MODELO_HAIKU}` extrae, `{MODELO_SONNET}` asigna"},
]


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


def _evaluar_fuentes(arts_cov, crudas: dict[str, list]) -> tuple[dict, dict]:
    """(métricas referenciados, métricas spans) sobre las notas cubiertas."""
    from trust_sources.schema import source_from_components
    preds = {a.index: [source_from_components(
        a.cuerpo, {"referenciado": f["referenciado"], "conector": f["conector"],
                   "afirmacion": f["afirmacion"]},
        tipo=f.get("tipo"), explicit=f.get("explicita", True))
        for f in crudas[a.index]] for a in arts_cov}
    pred_refs = {a.index: [f["referenciado"] for f in crudas[a.index]
                           if f["referenciado"]] for a in arts_cov}
    return evaluate_referenciados(arts_cov, pred_refs), evaluate_spans(arts_cov, preds)


def _run_config(cfg: dict, arts, cache: dict) -> dict | None:
    """Corre una config del pipeline (cache o vivo). Métricas solo sobre las
    notas cubiertas; cobertura aparte."""
    ccache = cache.setdefault(cfg["id"], {})
    c1 = client_for_model(cfg["extractor"])
    c2 = client_for_model(cfg["asignador"])
    detector = MultiLLMSourceDetector(c1, c2) if (c1 and c2) else None
    usa_gemini = any(m.startswith("gemini") for m in (cfg["extractor"], cfg["asignador"]))
    throttle = float(os.environ.get("EXP_THROTTLE_S", "5")) if (detector and usa_gemini) else 0.0
    max_fallos = int(os.environ.get("EXP_MAX_FALLOS", "4"))
    fallos = 0
    corto = False
    for a in arts:
        if a.index in ccache or detector is None or corto:
            continue
        if throttle:
            time.sleep(throttle)  # pace: una de las etapas usa el free tier de Gemini
        try:
            srcs = detector.detect(a.cuerpo)
            ccache[a.index] = [
                {"referenciado": s.referenciado_text or "",
                 "conector": (s.components.get("conector").text
                              if s.components.get("conector") else ""),
                 "afirmacion": (s.components.get("afirmacion").text
                                if s.components.get("afirmacion") else ""),
                 "tipo": s.tipo, "explicita": s.explicit} for s in srcs]
            fallos = 0
        except Exception as e:  # noqa: BLE001
            print(f"  [{cfg['id']}] {a.index}: {e}"); fallos += 1
            if fallos >= max_fallos:
                corto = True; print(f"  [{cfg['id']}] {max_fallos} fallos: corto.")
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    arts_cov = [a for a in arts if a.index in ccache]
    if not arts_cov:
        print(f"  [{cfg['id']}] sin datos (faltan keys o cuota); se omite.")
        return None
    crudas = {a.index: ccache[a.index] for a in arts_cov}
    m_ref, ev = _evaluar_fuentes(arts_cov, crudas)
    print(f"  [{cfg['id']}] {len(arts_cov)}/{len(arts)} · referenciados F1 "
          f"{m_ref['F1']:.2f} · span-F1 global {ev['global']['F1']:.2f}")
    return {"id": cfg["id"], "desc": cfg["desc"], "cobertura": f"{len(arts_cov)}/{len(arts)}",
            "completo": len(arts_cov) == len(arts), "ref": m_ref, "spans": ev}


def _single_pass_sonnet(arts) -> dict | None:
    """Fila de referencia: single-pass v1 con Sonnet, desde el cache de Exp 2
    (mismas notas, mismas métricas: comparación directa sin re-llamar)."""
    if not CACHE_EXP2.exists():
        return None
    cache2 = json.loads(CACHE_EXP2.read_text(encoding="utf-8"))
    crudas = cache2.get(MODELO_SONNET) or {}
    arts_cov = [a for a in arts if a.index in crudas]
    if not arts_cov:
        return None
    m_ref, ev = _evaluar_fuentes(arts_cov, {a.index: crudas[a.index] for a in arts_cov})
    return {"id": "single_pass_sonnet", "desc": f"una pasada (`{MODELO_SONNET}`, Exp 2)",
            "cobertura": f"{len(arts_cov)}/{len(arts)}",
            "completo": len(arts_cov) == len(arts), "ref": m_ref, "spans": ev}


def corrida_real() -> None:
    """Corre las configs multi-LLM sobre las 16 notas y las compara contra el
    single-pass de Exp 2 (si hay key/cache)."""
    arts, _ = load_double_annotated()
    cache = _load_cache()
    filas = [f for f in (_run_config(cfg, arts, cache) for cfg in CONFIGS) if f]
    if not filas:
        print("  corrida real: sin datos (falta key/cuota); el pipeline quedó listo "
              "para comparar contra single-pass al conectar Anthropic.")
        return
    sp = _single_pass_sonnet(arts)
    comparables = ([sp] if sp else []) + filas

    md = ["# Exp 3: multi-LLM (dos pasadas) vs single-pass\n",
          f"- Notas: **{len(arts)}** · métricas **solo sobre notas con "
          "predicción** (cobertura aparte); corridas parciales no comparables.",
          "- Configs: " + " · ".join(f"`{c['id']}` ({c['desc']})" for c in CONFIGS) + "\n",
          "## Comparación (referenciados y span global)\n",
          "| Pipeline | Cobertura | Referenciados F1 | span-F1 global |",
          "|---|---|---|---|"]
    for f in comparables:
        flag = "" if f["completo"] else " ⚠ parcial"
        md.append(f"| {f['desc']} | {f['cobertura']}{flag} | "
                  f"**{f['ref']['F1']:.2f}** (P {f['ref']['P']:.2f} / R {f['ref']['R']:.2f}) | "
                  f"**{f['spans']['global']['F1']:.2f}** |")
    for f in filas:
        md += ["", f"## `{f['id']}`: spans por componente (cobertura {f['cobertura']})\n",
               "| Componente | P | R | F1 |", "|---|---|---|---|"]
        for lab in ["Referenciado", "Conector", "Afirmacion", "global"]:
            m = f["spans"][lab]
            md.append(f"| {lab} | {m['P']:.2f} | {m['R']:.2f} | **{m['F1']:.2f}** |")
    (RESULTS / "exp3_multi.md").write_text("\n".join(md), encoding="utf-8")
    print("  escrito: results/exp3_multi.md")


def main() -> None:
    load_dotenv(ROOT / ".env")
    print("Exp 3: pipeline multi-LLM")
    demo_stub()
    corrida_real()


if __name__ == "__main__":
    main()
