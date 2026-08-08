"""
Experimento 2 (Etapa 2): salida RICA v1: afirmacion + conector + referenciado
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
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trust_sources.detectors.classic import ClassicSourceDetector  # noqa: E402
from trust_sources.detectors.llm import (LLMSourceDetectorV1,  # noqa: E402
                                         _parse_fuentes_v1)
from trust_sources.evaluation import evaluate_spans  # noqa: E402
from trust_sources.io_anotaciones import load_double_annotated  # noqa: E402
from trust_sources.llm_client import LLMClient, client_for_model, load_dotenv  # noqa: E402
from trust_sources.schema import source_from_components  # noqa: E402

RESULTS = ROOT / "results"
CACHE = ROOT / "experiments" / "cache" / "exp2_v1.json"

# Modelos sobre los que se mide la salida v1 (cache separado por modelo).
MODELO_GEMINI = "gemini-2.5-flash-lite"
MODELO_SONNET = "claude-sonnet-5"
MODELOS = [MODELO_GEMINI, MODELO_SONNET]


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


def baseline_clasico_spans() -> dict:
    """Evalúa el detector CLÁSICO a nivel de span (real, sin LLM ni cuota). Es el
    baseline medible de la salida rica: el clásico ya produce Sources con spans."""
    arts, _ = load_double_annotated()
    clasico = ClassicSourceDetector()
    preds = {a.index: clasico.detect(a.cuerpo) for a in arts}
    ev = evaluate_spans(arts, preds)
    md = ["# Exp 2 (baseline): clásico a nivel de span\n",
          f"- Artículos: **{len(arts)}** · IoU mínimo 0.5 · sin LLM (reproducible offline)\n",
          "| Componente | P | R | F1 |", "|---|---|---|---|"]
    for lab in ["Referenciado", "Conector", "Afirmacion", "global"]:
        m = ev[lab]
        md.append(f"| {lab} | {m['P']:.2f} | {m['R']:.2f} | **{m['F1']:.2f}** |")
    (RESULTS / "exp2_spans_clasico.md").write_text("\n".join(md), encoding="utf-8")
    g = ev["global"]
    print(f"  baseline clásico (spans): global P={g['P']:.2f} R={g['R']:.2f} "
          f"F1={g['F1']:.2f} · escrito results/exp2_spans_clasico.md")
    return ev


def _load_cache() -> dict:
    """Cache {modelo: {index: [fuentes]}}. Migra el formato viejo (plano, por
    index), que era 100% Gemini: mezclar modelos bajo la misma clave haría
    imposible saber qué respondió cada uno."""
    if not CACHE.exists():
        return {}
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    if cache and not any(k.startswith(("gemini", "claude")) for k in cache):
        cache = {MODELO_GEMINI: cache}
    return cache


def _predecir_modelo(modelo: str, arts, cache: dict) -> dict[str, list]:
    """Completa el cache del modelo (vivo si hay key) y devuelve las fuentes
    crudas por index: SOLO de las notas cubiertas."""
    mcache = cache.setdefault(modelo, {})
    client = client_for_model(modelo)
    detector = LLMSourceDetectorV1(client) if client else None
    throttle = (float(os.environ.get("EXP_THROTTLE_S", "5"))
                if (client and client.name == "gemini") else 0.0)
    max_fallos = int(os.environ.get("EXP_MAX_FALLOS", "4"))
    fallos_seguidos = 0
    corto = False
    for a in arts:
        if a.index in mcache or detector is None or corto:
            continue
        if throttle:
            time.sleep(throttle)  # pace bajo el rate-limit del free tier
        try:
            raw = client.generate(detector.prompt, a.cuerpo[:detector.max_chars],
                                  max_tokens=1200)
            mcache[a.index] = _parse_fuentes_v1(raw)
            fallos_seguidos = 0
        except Exception as e:  # noqa: BLE001
            print(f"  [v1/{modelo}] {a.index}: {e}")
            fallos_seguidos += 1
            if fallos_seguidos >= max_fallos:
                corto = True
                print(f"  [v1/{modelo}] {max_fallos} fallos seguidos: corto (se "
                      "retoma en otra ventana; el cache guarda lo hecho).")
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    return {a.index: mcache[a.index] for a in arts if a.index in mcache}


def corrida_real(ev_clasico: dict | None = None) -> None:
    """Corre v1 sobre las 16 notas POR MODELO y evalúa a nivel de span.

    Regla de reporte: las métricas se calculan SOLO sobre las notas con
    predicción (calidad); la cobertura va aparte. Una corrida parcial se marca
    como no comparable: nunca se publica recall aplastado por cobertura."""
    arts, _ = load_double_annotated()
    cache = _load_cache()
    n = len(arts)

    md = ["# Exp 2: salida v1: evaluación a nivel de span\n",
          f"- Notas: **{n}** · solapamiento mínimo (IoU) para acierto: 0.5",
          "- Métricas calculadas **solo sobre las notas con predicción** (la "
          "cobertura se reporta aparte). Corridas parciales: no comparables.",
          "- Baseline clásico (sin LLM): global F1 **{:.2f}**: ver "
          "[exp2_spans_clasico.md](exp2_spans_clasico.md).\n".format(
              ev_clasico["global"]["F1"] if ev_clasico else 0.39)]
    resumen = []
    for modelo in MODELOS:
        crudas = _predecir_modelo(modelo, arts, cache)
        if not crudas:
            print(f"  [v1/{modelo}] sin datos (falta key o cuota); se omite.")
            continue
        arts_cov = [a for a in arts if a.index in crudas]
        preds = {a.index: [source_from_components(
            a.cuerpo, {"referenciado": f["referenciado"], "conector": f["conector"],
                       "afirmacion": f["afirmacion"]},
            tipo=f.get("tipo"), explicit=f.get("explicita", True))
            for f in crudas[a.index]] for a in arts_cov}
        ev = evaluate_spans(arts_cov, preds)
        completo = len(arts_cov) == n
        estado = "" if completo else " · **PARCIAL, no comparable**"
        md += [f"## `{modelo}`: cobertura {len(arts_cov)}/{n}{estado}\n",
               "| Componente | P | R | F1 |", "|---|---|---|---|"]
        for lab in ["Referenciado", "Conector", "Afirmacion", "global"]:
            m = ev[lab]
            md.append(f"| {lab} | {m['P']:.2f} | {m['R']:.2f} | **{m['F1']:.2f}** |")
        md.append("")
        resumen.append({"modelo": modelo, "cobertura": f"{len(arts_cov)}/{n}",
                        "completo": completo, "ev": ev})
        print(f"  [v1/{modelo}] {len(arts_cov)}/{n} notas · span-F1 global "
              f"{ev['global']['F1']:.2f}{' (parcial)' if not completo else ''}")

    if not resumen:
        print("  corrida real: sin datos (faltan keys o cuota); el pipeline v1 "
              "quedó listo, se completa al conectar un proveedor.")
        return

    completos = [r for r in resumen if r["completo"]]
    if completos and ev_clasico:
        md += ["## Resumen (corridas completas vs baseline clásico)\n",
               "| Detector | Referenciado F1 | Conector F1 | Afirmacion F1 | global F1 |",
               "|---|---|---|---|---|",
               "| clásico (reglas) | {:.2f} | {:.2f} | {:.2f} | **{:.2f}** |".format(
                   *(ev_clasico[k]["F1"] for k in
                     ("Referenciado", "Conector", "Afirmacion", "global")))]
        for r in completos:
            md.append("| v1 `{}` | {:.2f} | {:.2f} | {:.2f} | **{:.2f}** |".format(
                r["modelo"], *(r["ev"][k]["F1"] for k in
                               ("Referenciado", "Conector", "Afirmacion", "global"))))
    (RESULTS / "exp2_spans.md").write_text("\n".join(md), encoding="utf-8")
    print("  escrito: results/exp2_spans.md")


def main() -> None:
    load_dotenv(ROOT / ".env")
    print("Exp 2: salida rica v1")
    dicts = demo_stub()
    _write_ejemplo(dicts)
    ev_clasico = baseline_clasico_spans()
    corrida_real(ev_clasico)


if __name__ == "__main__":
    main()
