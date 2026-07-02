"""
Experimento 1 (Etapa 1): comparar variantes de PROMPT del detector LLM.

Objetivo: **subir la precisión** del LLM (baseline 0.44) sin perder recall,
probando prompts distintos y midiendo P/R/F1 de cada uno contra la anotación
humana (16 notas doble-anotadas). Es el "corazón del entregable": investigar y
documentar qué prompt funciona mejor y por qué.

Diseño (respeta la arquitectura): el prompt se INYECTA en `LLMSourceDetector`, así
que cada variante es el mismo detector con otro texto de sistema. Cache por
(variante, artículo) en `cache/exp1_prompts.json` para no re-llamar ni gastar
cuota. Sin key funciona offline con lo cacheado; con `GEMINI_API_KEY` corre en vivo
lo que falte.

Uso:  python -m experiments.exp1_prompts
      (poné tu key en un archivo .env:  GEMINI_API_KEY=...)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trust_sources import LLMSourceDetector  # noqa: E402
from trust_sources.detectors.llm import PROMPT_V0  # noqa: E402
from trust_sources.evaluation import evaluate_referenciados  # noqa: E402
from trust_sources.io_anotaciones import load_double_annotated  # noqa: E402
from trust_sources.llm_client import GeminiClient, default_client, load_dotenv  # noqa: E402

CACHE = Path(__file__).resolve().parent / "cache" / "exp1_prompts.json"
RESULTS = ROOT / "results"
ASSETS = ROOT / "docs" / "assets"  # los PNG van a docs/ para verse en la Page

# El free tier de Gemini limita requests/minuto: pausamos entre llamadas EN VIVO
# para no gatillar 429 (los reintentos con backoff del cliente queman RPM rápido).
# Configurable con EXP_THROTTLE_S; 0 desactiva. Las lecturas de cache no pausan.
THROTTLE_S = float(os.environ.get("EXP_THROTTLE_S", "5"))
# Circuit breaker: tras N fallos seguidos, dejamos de llamar en esa variante para
# no quemar cuota contra un free tier caído (los faltantes se retoman después).
MAX_FALLOS_SEGUIDOS = int(os.environ.get("EXP_MAX_FALLOS", "3"))

# --- Variantes de prompt a comparar ---------------------------------------
# Cada una apunta a subir la PRECISIÓN de una forma distinta. El baseline v0 es
# estricto pero sobre-detecta; probamos few-shot, reglas negativas duras, y
# auto-verificación (que el modelo cite la evidencia y descarte si no la hay).

_FEWSHOT = PROMPT_V0 + (
    "\n\nEJEMPLOS:\n"
    "Texto: «El ministro Caputo aseguró que la inflación bajará. Milei viajó a EEUU. "
    "En el acto estuvo la vicepresidenta Villarruel.»\n"
    'Correcto: {"fuentes": ["el ministro Caputo"]}  '
    "(Milei y Villarruel se mencionan pero NO se les atribuye ninguna afirmación).\n"
    "Texto: «Según el INDEC, la pobreza subió al 40%. Vecinos protestaron.»\n"
    'Correcto: {"fuentes": ["el INDEC"]}  '
    '("Vecinos" no es una fuente atribuida concreta).'
)

_REGLAS_DURAS = (
    "Sos un detector de FUENTES periodísticas. Una fuente es SOLO una entidad "
    "(persona, institución, documento) a la que la nota le atribuye EXPLÍCITAMENTE "
    "una afirmación mediante (a) un verbo de habla (dijo, afirmó, aseguró, informó, "
    "sostuvo, según, explicó, denunció, advirtió...) o (b) una cita textual entre "
    "comillas.\n"
    "CRITERIO DE EXCLUSIÓN (aplicalo con dureza, ante la duda EXCLUÍ):\n"
    "- NO es fuente quien solo aparece como protagonista de la acción, es nombrado "
    "al pasar, o es objeto de la noticia sin declarar nada.\n"
    "- NO incluyas colectivos vagos ('vecinos', 'la gente', 'analistas') salvo que "
    "haya una atribución concreta.\n"
    "- Ante la duda entre incluir o no, NO incluyas.\n"
    "Unificá menciones de la misma fuente en una (la más completa).\n"
    'Devolvé SOLO JSON: {"fuentes": ["...", "..."]}. Sin texto adicional.'
)

_JUSTIFICA = (
    "Sos un detector de FUENTES periodísticas. Una fuente es una entidad a la que "
    "la nota le atribuye EXPLÍCITAMENTE una afirmación (verbo de habla o cita "
    "textual). Para cada candidato, identificá la EVIDENCIA (el verbo o la cita que "
    "se la atribuye). Si no podés señalar una evidencia clara, DESCARTALO.\n"
    "Unificá menciones de la misma fuente en una (la más completa).\n"
    'Devolvé SOLO JSON con la evidencia: '
    '{"fuentes": [{"nombre": "...", "evidencia": "..."}]}. Sin texto adicional.'
)

VARIANTES = [
    {"id": "v0_estricto", "model": "gemini-2.5-flash-lite", "prompt": PROMPT_V0,
     "desc": "baseline v0 (prompt estricto)"},
    {"id": "v1_fewshot", "model": "gemini-2.5-flash-lite", "prompt": _FEWSHOT,
     "desc": "baseline + 2 ejemplos (few-shot)"},
    {"id": "v2_reglas_duras", "model": "gemini-2.5-flash-lite", "prompt": _REGLAS_DURAS,
     "desc": "reglas negativas duras (ante la duda, excluir)"},
    {"id": "v3_justifica", "model": "gemini-2.5-flash-lite", "prompt": _JUSTIFICA,
     "desc": "auto-verificación: citar evidencia o descartar"},
]


def _load_cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def _save_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_variant(variante: dict, arts, cache: dict) -> tuple[dict, str]:
    """Corre una variante sobre todos los artículos (cache o vivo). Devuelve
    (pred_por_index, origen)."""
    vid = variante["id"]
    vcache = cache.setdefault(vid, {})
    client = GeminiClient(model=variante["model"]) if default_client() else None
    detector = LLMSourceDetector(client, prompt=variante["prompt"]) if client else None
    pred, origenes = {}, set()
    fallos_seguidos = 0
    corto = False  # circuit breaker: si el free tier no responde, dejamos de martillar
    for a in arts:
        if a.index in vcache:
            pred[a.index] = vcache[a.index]; origenes.add("cache")
        elif detector is not None and not corto:
            # Pausa ANTES de cada llamada en vivo (paceamos éxitos Y fallas) para
            # no saturar la ventana de 20 req/min del free tier.
            if THROTTLE_S:
                time.sleep(THROTTLE_S)
            try:
                names = detector.referenciados(a.cuerpo)
                pred[a.index] = names; vcache[a.index] = names
                origenes.add(f"gemini:{variante['model']}")
                fallos_seguidos = 0
            except Exception as e:  # noqa: BLE001
                print(f"  [{vid}] {a.index}: {e}")
                pred[a.index] = []; origenes.add("error")
                fallos_seguidos += 1
                if fallos_seguidos >= MAX_FALLOS_SEGUIDOS:
                    corto = True
                    print(f"  [{vid}] {MAX_FALLOS_SEGUIDOS} fallos seguidos: corto "
                          "las llamadas en vivo (se completan en otra ventana).")
        else:
            # sin key, o circuit breaker abierto: no cacheamos (reintentable luego)
            pred[a.index] = []
            origenes.add("cortado" if corto else "sin-key")
    n_ok = sum(1 for a in arts if a.index in vcache)  # cobertura real (predicciones)
    return pred, " + ".join(sorted(origenes)), n_ok


def _chart(rows: list[dict]) -> Path | None:
    """Barras agrupadas P/R/F1 por variante → docs/assets/exp1_prompts.png."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # noqa: BLE001
        print(f"  (sin gráfico: {e})")
        return None
    ASSETS.mkdir(parents=True, exist_ok=True)
    ids = [r["id"] for r in rows]
    x = range(len(ids))
    w = 0.26
    fig, ax = plt.subplots(figsize=(1.8 * len(ids) + 2, 4.2))
    ax.bar([i - w for i in x], [r["P"] for r in rows], w, label="Precisión", color="#d1495b")
    ax.bar(list(x), [r["R"] for r in rows], w, label="Recall", color="#00798c")
    ax.bar([i + w for i in x], [r["F1"] for r in rows], w, label="F1", color="#edae49")
    ax.axhline(0.71, ls="--", color="gray", lw=1, label="techo humano (0.71)")
    ax.set_xticks(list(x)); ax.set_xticklabels(ids, rotation=15, ha="right")
    ax.set_ylim(0, 1); ax.set_ylabel("score"); ax.legend(fontsize=8)
    ax.set_title("Exp 1 — variantes de prompt (LLM) vs anotación humana")
    for i, r in zip(x, rows):
        ax.text(i + w, r["F1"] + 0.02, f"{r['F1']:.2f}", ha="center", fontsize=8)
    fig.tight_layout()
    out = ASSETS / "exp1_prompts.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    return out


def main() -> None:
    load_dotenv(ROOT / ".env")
    RESULTS.mkdir(exist_ok=True)
    arts, _ = load_double_annotated()
    print(f"Artículos: {len(arts)} · variantes: {len(VARIANTES)}")
    if default_client() is None:
        print("  (sin GEMINI_API_KEY: solo se evalúa lo que ya esté en cache)")

    cache = _load_cache()

    # Enfriamiento: si hay key y quedan artículos sin cachear, esperamos a que la
    # ventana de rate-limit se drene antes de empezar a llamar (evita 429 en cadena).
    cooldown = float(os.environ.get("EXP_COOLDOWN_S", "0"))
    if cooldown and default_client() is not None:
        faltan = sum(1 for v in VARIANTES for a in arts
                     if a.index not in cache.get(v["id"], {}))
        if faltan:
            print(f"  Enfriando {cooldown:.0f}s antes de {faltan} llamadas en vivo...")
            time.sleep(cooldown)

    n = len(arts)
    rows = []
    for v in VARIANTES:
        pred, origen, n_ok = _run_variant(v, arts, cache)
        m = evaluate_referenciados(arts, pred)
        completo = n_ok == n
        rows.append({"id": v["id"], "desc": v["desc"], "model": v["model"],
                     "P": m["P"], "R": m["R"], "F1": m["F1"], "origen": origen,
                     "cobertura": f"{n_ok}/{n}", "completo": completo})
        flag = "" if completo else f"  [PARCIAL {n_ok}/{n} — no comparable]"
        print(f"  {v['id']:16s} P={m['P']:.2f} R={m['R']:.2f} F1={m['F1']:.2f}  ({origen}){flag}")
    _save_cache(cache)

    base = next((r for r in rows if r["id"] == "v0_estricto" and r["completo"]), None)
    base_f1 = base["F1"] if base else 0.0
    base_p = base["P"] if base else 0.0
    completos = [r for r in rows if r["completo"]]
    parciales = [r for r in rows if not r["completo"]]

    # --- Tabla markdown (solo variantes COMPLETAS son comparables) ---
    md = ["# Exp 1 — variantes de prompt (LLM)\n",
          f"- Artículos: **{n}** (lote doble-anotado) · techo humano **F1 0.71**",
          "- Objetivo: subir la **precisión** (baseline 0.44) sin perder recall.\n",
          "| Variante | Descripción | P | R | F1 | ΔP | ΔF1 |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted(completos, key=lambda r: -r["F1"]):
        md.append(f"| `{r['id']}` | {r['desc']} | {r['P']:.2f} | {r['R']:.2f} | "
                  f"**{r['F1']:.2f}** | {r['P']-base_p:+.2f} | {r['F1']-base_f1:+.2f} |")
    if parciales:
        md += ["", "**Variantes incompletas** (free tier rate-limited; se completan "
               "en otra ventana de cuota re-corriendo el script — el cache retoma "
               "donde quedó). Sus métricas NO son comparables todavía:", "",
               "| Variante | Descripción | Cobertura |", "|---|---|---|"]
        md += [f"| `{r['id']}` | {r['desc']} | {r['cobertura']} |" for r in parciales]
    md += ["", "![P/R/F1 por variante](../docs/assets/exp1_prompts.png)"]
    (RESULTS / "exp1_prompts.md").write_text("\n".join(md), encoding="utf-8")
    (RESULTS / "exp1_prompts.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    _chart(completos)  # el gráfico solo muestra variantes comparables
    print("Escrito: results/exp1_prompts.md, .json y docs/assets/exp1_prompts.png")


if __name__ == "__main__":
    main()
