"""
Experimento 1 (Etapa 1): comparar variantes de PROMPT del detector LLM — y, de
paso, comparar MODELOS con la misma grilla de prompts.

Objetivo: **subir la precisión** del LLM (baseline Gemini 0.44) sin perder
recall, probando prompts distintos y midiendo P/R/F1 de cada uno contra la
anotación humana (16 notas doble-anotadas).

Diseño (respeta la arquitectura): el prompt se INYECTA en `LLMSourceDetector`,
así que cada celda de la grilla es el mismo detector con otro texto de sistema y
otro cliente. El cache es por **(modelo, variante, artículo)** en
`cache/exp1_prompts.json`: mezclar respuestas de dos modelos bajo la misma clave
invalidaría la comparación de prompts (cada variante debe ser 100% de un modelo).
Sin keys funciona offline con lo cacheado; con keys corre en vivo lo que falte.

Metodología de reporte: las métricas se calculan SOLO sobre las notas con
predicción (calidad), y la cobertura se reporta aparte — nunca se publica una
métrica aplastada por cobertura parcial como si fuera calidad. Solo variantes
16/16 son comparables entre sí.

Uso:  python -m experiments.exp1_prompts
      (keys en .env: GEMINI_API_KEY y/o ANTHROPIC_API_KEY)
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
from trust_sources.llm_client import client_for_model, load_dotenv  # noqa: E402

CACHE = Path(__file__).resolve().parent / "cache" / "exp1_prompts.json"
RESULTS = ROOT / "results"
ASSETS = ROOT / "docs" / "assets"  # los PNG van a docs/ para verse en la Page

# El free tier de Gemini limita requests/minuto: pausamos entre llamadas EN VIVO
# para no gatillar 429. Solo aplica a Gemini (Anthropic es de pago, sin throttle).
THROTTLE_GEMINI_S = float(os.environ.get("EXP_THROTTLE_S", "5"))
# Circuit breaker: tras N fallos seguidos, dejamos de llamar en esa celda para no
# quemar cuota contra un free tier caído (los faltantes se retoman después).
MAX_FALLOS_SEGUIDOS = int(os.environ.get("EXP_MAX_FALLOS", "3"))

# --- Modelos a comparar (misma grilla de prompts en cada uno) ----------------
MODELO_GEMINI = "gemini-2.5-flash-lite"
MODELO_SONNET = "claude-sonnet-5"
MODELOS = [MODELO_GEMINI, MODELO_SONNET]
SLUG = {MODELO_GEMINI: "gemini", MODELO_SONNET: "sonnet"}

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
    {"id": "v0_estricto", "prompt": PROMPT_V0,
     "desc": "baseline v0 (prompt estricto)"},
    {"id": "v1_fewshot", "prompt": _FEWSHOT,
     "desc": "baseline + 2 ejemplos (few-shot)"},
    {"id": "v2_reglas_duras", "prompt": _REGLAS_DURAS,
     "desc": "reglas negativas duras (ante la duda, excluir)"},
    # v3 devuelve un objeto por fuente (nombre + evidencia): con el default
    # (400) el JSON se truncaba y no parseaba. 800 alcanzó para Sonnet pero NO
    # para Gemini, que es más verboso acá (cortes en ~790 tokens). 1500 le da
    # aire a ambos; es un tope, no un objetivo, así que no encarece nada.
    {"id": "v3_justifica", "prompt": _JUSTIFICA, "max_tokens": 1500,
     "desc": "auto-verificación: citar evidencia o descartar"},
]

# Paleta y tinta (validadas con el método de dataviz; orden fijo de series)
C_P, C_R, C_F1 = "#2a78d6", "#eb6834", "#1baf7a"   # azul, naranja, aqua
COLOR_MODELO = {MODELO_GEMINI: "#2a78d6", MODELO_SONNET: "#eb6834"}
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"


def _load_cache() -> dict:
    """Cache {modelo: {variante: {index: [fuentes]}}}. Migra el formato viejo
    (pre-comparación de modelos: {variante: {index: ...}}), que era 100% Gemini."""
    if not CACHE.exists():
        return {}
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    if cache and not any(k.startswith(("gemini", "claude")) for k in cache):
        cache = {MODELO_GEMINI: cache}
    return cache


def _save_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_cell(modelo: str, variante: dict, arts, cache: dict) -> dict:
    """Corre una celda (modelo, variante) sobre los artículos (cache o vivo).
    Las métricas se calculan SOLO sobre las notas con predicción."""
    vcache = cache.setdefault(modelo, {}).setdefault(variante["id"], {})
    client = client_for_model(modelo)
    detector = (LLMSourceDetector(client, prompt=variante["prompt"],
                                  max_tokens=variante.get("max_tokens", 400))
                if client else None)
    throttle = THROTTLE_GEMINI_S if (client and client.name == "gemini") else 0.0
    origenes = set()
    fallos_seguidos = 0
    corto = False  # circuit breaker: si el free tier no responde, dejamos de martillar
    for a in arts:
        if a.index in vcache:
            origenes.add("cache")
        elif detector is not None and not corto:
            if throttle:
                time.sleep(throttle)  # pace bajo la ventana de 20 req/min del free tier
            try:
                names = detector.referenciados(a.cuerpo)
                vcache[a.index] = names
                origenes.add(f"{client.name}:{modelo}")
                fallos_seguidos = 0
            except Exception as e:  # noqa: BLE001
                print(f"  [{modelo}/{variante['id']}] {a.index}: {e}")
                origenes.add("error")
                fallos_seguidos += 1
                if fallos_seguidos >= MAX_FALLOS_SEGUIDOS:
                    corto = True
                    print(f"  [{modelo}/{variante['id']}] {MAX_FALLOS_SEGUIDOS} fallos "
                          "seguidos: corto las llamadas en vivo (se retoma después).")
        else:
            origenes.add("cortado" if corto else "sin-key")

    # Calidad sobre lo cubierto; la cobertura va aparte (nunca mezcladas).
    arts_cov = [a for a in arts if a.index in vcache]
    m = evaluate_referenciados(arts_cov, {a.index: vcache[a.index] for a in arts_cov})
    return {"modelo": modelo, "id": variante["id"], "desc": variante["desc"],
            "P": m["P"], "R": m["R"], "F1": m["F1"],
            "cobertura": f"{len(arts_cov)}/{len(arts)}",
            "completo": len(arts_cov) == len(arts),
            "origen": " + ".join(sorted(origenes))}


def _estilo(ax) -> None:
    """Chrome recesivo: sin bordes arriba/derecha, grilla hairline, tinta suave."""
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRID)
    ax.tick_params(colors=MUTED, labelcolor=INK)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, lw=0.7)


def _chart_variantes(rows: list[dict], modelo: str) -> Path | None:
    """Barras agrupadas P/R/F1 por variante (un modelo) → exp1_prompts_<slug>.png."""
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
    fig.patch.set_facecolor("white")
    ax.bar([i - w for i in x], [r["P"] for r in rows], w, label="Precisión", color=C_P)
    ax.bar(list(x), [r["R"] for r in rows], w, label="Recall", color=C_R)
    ax.bar([i + w for i in x], [r["F1"] for r in rows], w, label="F1", color=C_F1)
    ax.axhline(0.71, ls="--", color=MUTED, lw=1, label="techo humano (0.71)")
    ax.set_xticks(list(x)); ax.set_xticklabels(ids, rotation=15, ha="right")
    # techo alto + leyenda horizontal arriba: que no pise ninguna barra/etiqueta
    ax.set_ylim(0, 1.18); ax.set_ylabel("score")
    _estilo(ax)
    ax.legend(fontsize=8, frameon=False, ncol=4, loc="upper center")
    ax.set_title(f"Exp 1 — variantes de prompt · {modelo}", color=INK)
    for i, r in zip(x, rows):
        ax.text(i + w, r["F1"] + 0.02, f"{r['F1']:.2f}", ha="center", fontsize=8, color=INK)
    fig.tight_layout()
    out = ASSETS / f"exp1_prompts_{SLUG.get(modelo, modelo)}.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    return out


def _chart_modelos(rows: list[dict]) -> Path | None:
    """F1 por variante, una serie por modelo (solo celdas completas) →
    exp1_modelos.png. Es la comparación de modelos con prompts idénticos."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # noqa: BLE001
        print(f"  (sin gráfico: {e})")
        return None
    ids = [v["id"] for v in VARIANTES]
    por_modelo = {m: {r["id"]: r for r in rows if r["modelo"] == m and r["completo"]}
                  for m in MODELOS}
    modelos_ok = [m for m in MODELOS if por_modelo[m]]
    if len(modelos_ok) < 2:
        return None
    ASSETS.mkdir(parents=True, exist_ok=True)
    x = range(len(ids))
    w = 0.8 / len(modelos_ok)
    fig, ax = plt.subplots(figsize=(1.8 * len(ids) + 2, 4.2))
    fig.patch.set_facecolor("white")
    for j, m in enumerate(modelos_ok):
        offs = (j - (len(modelos_ok) - 1) / 2) * w
        vals = [por_modelo[m].get(v, {}).get("F1") for v in ids]
        xs = [i + offs for i, v in zip(x, vals) if v is not None]
        ys = [v for v in vals if v is not None]
        ax.bar(xs, ys, w * 0.92, label=m, color=COLOR_MODELO.get(m, MUTED))
        for xi, yi in zip(xs, ys):
            ax.text(xi, yi + 0.02, f"{yi:.2f}", ha="center", fontsize=8, color=INK)
    ax.axhline(0.71, ls="--", color=MUTED, lw=1, label="techo humano (0.71)")
    ax.set_xticks(list(x)); ax.set_xticklabels(ids, rotation=15, ha="right")
    ax.set_ylim(0, 1.18); ax.set_ylabel("F1")
    _estilo(ax)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper center")
    ax.set_title("Exp 1/4 — mismos prompts, dos modelos (F1 sobre 16 notas)", color=INK)
    fig.tight_layout()
    out = ASSETS / "exp1_modelos.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    return out


def _tabla_md(rows: list[dict], base_id: str = "v0_estricto") -> list[str]:
    """Tabla P/R/F1 con deltas contra el v0 del MISMO modelo (solo completas)."""
    base = next((r for r in rows if r["id"] == base_id and r["completo"]), None)
    base_p = base["P"] if base else 0.0
    base_f1 = base["F1"] if base else 0.0
    md = ["| Variante | Descripción | P | R | F1 | ΔP | ΔF1 |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted([r for r in rows if r["completo"]], key=lambda r: -r["F1"]):
        md.append(f"| `{r['id']}` | {r['desc']} | {r['P']:.2f} | {r['R']:.2f} | "
                  f"**{r['F1']:.2f}** | {r['P']-base_p:+.2f} | {r['F1']-base_f1:+.2f} |")
    parciales = [r for r in rows if not r["completo"]]
    if parciales:
        md += ["", "Celdas incompletas (sus métricas son sobre las notas cubiertas y "
               "NO son comparables con las corridas 16/16):", "",
               "| Variante | Cobertura | P | R | F1 (parcial) |", "|---|---|---|---|---|"]
        md += [f"| `{r['id']}` | {r['cobertura']} | {r['P']:.2f} | {r['R']:.2f} | "
               f"{r['F1']:.2f} |" for r in parciales]
    return md


def main() -> None:
    load_dotenv(ROOT / ".env")
    RESULTS.mkdir(exist_ok=True)
    arts, _ = load_double_annotated()
    print(f"Artículos: {len(arts)} · modelos: {len(MODELOS)} · variantes: {len(VARIANTES)}")
    for m in MODELOS:
        if client_for_model(m) is None:
            print(f"  (sin key para {m}: solo se evalúa lo cacheado de ese modelo)")

    cache = _load_cache()
    rows = []
    for modelo in MODELOS:
        print(f"— {modelo}")
        for v in VARIANTES:
            r = _run_cell(modelo, v, arts, cache)
            _save_cache(cache)  # persistimos por celda: un corte no pierde lo hecho
            rows.append(r)
            flag = "" if r["completo"] else f"  [PARCIAL {r['cobertura']}]"
            print(f"  {r['id']:16s} P={r['P']:.2f} R={r['R']:.2f} F1={r['F1']:.2f}  "
                  f"({r['origen']}){flag}")

    # --- Reporte markdown -------------------------------------------------
    n = len(arts)
    md = ["# Exp 1 — variantes de prompt (LLM) × modelos\n",
          f"- Artículos: **{n}** (lote doble-anotado) · techo humano **F1 0.71**",
          "- Objetivo: subir la **precisión** sin perder recall; misma grilla de "
          "prompts en cada modelo (cache por modelo+variante — nunca mezclados).",
          "- Las métricas se calculan **solo sobre notas con predicción**; la "
          "cobertura se reporta aparte. Solo celdas 16/16 son comparables.\n"]
    for modelo in MODELOS:
        rows_m = [r for r in rows if r["modelo"] == modelo]
        if not any(r["completo"] or r["P"] or r["R"] for r in rows_m):
            continue
        md += [f"## `{modelo}`\n"]
        md += _tabla_md(rows_m)
        md += ["", f"![P/R/F1 por variante]"
                   f"(../docs/assets/exp1_prompts_{SLUG.get(modelo, modelo)}.png)", ""]

    completas_ambos = [v["id"] for v in VARIANTES
                       if all(any(r["modelo"] == m and r["id"] == v["id"] and r["completo"]
                                  for r in rows) for m in MODELOS)]
    if completas_ambos:
        md += ["## Comparación de modelos (prompts idénticos)\n",
               "| Variante | " + " | ".join(f"F1 `{m}`" for m in MODELOS) + " | ΔF1 |",
               "|---|" + "---|" * (len(MODELOS) + 1)]
        for vid in completas_ambos:
            f1s = [next(r["F1"] for r in rows if r["modelo"] == m and r["id"] == vid)
                   for m in MODELOS]
            md.append(f"| `{vid}` | " + " | ".join(f"{f:.2f}" for f in f1s) +
                      f" | {f1s[-1]-f1s[0]:+.2f} |")
        md += ["", "![F1 por variante y modelo](../docs/assets/exp1_modelos.png)"]

    (RESULTS / "exp1_prompts.md").write_text("\n".join(md), encoding="utf-8")
    (RESULTS / "exp1_prompts.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    for modelo in MODELOS:
        comp = [r for r in rows if r["modelo"] == modelo and r["completo"]]
        if comp:
            _chart_variantes(comp, modelo)
    _chart_modelos(rows)
    print("Escrito: results/exp1_prompts.md, .json y docs/assets/exp1_*.png")


if __name__ == "__main__":
    main()
