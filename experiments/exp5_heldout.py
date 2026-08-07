"""
Experimento 5: ¿el F1 de la selección GENERALIZA? Validación held-out.

Motivación (hallazgo del Exp 1/4): Sonnet llegó a F1 0.86 sobre las 16 notas
doble-anotadas — por encima del acuerdo entre anotadores (0.71). Pero esas 16
notas se usaron para ELEGIR el prompt ganador, así que medir ahí sobreestima
(sobreajuste de selección). Este experimento mide los mismos prompts sobre las
~75 notas anotadas que el modelo nunca vio (`load_heldout`).

Diseño: dos variantes a propósito —
  - `v0_estricto`: el baseline, que NO fue elegido mirando las 16 → su caída
    esperada es solo ruido de gold.
  - `v1_fewshot`: el GANADOR elegido contra las 16 → si cae más que v0, esa
    diferencia es sobreajuste de selección; si ambos aguantan, generaliza.
Más el detector clásico como referencia (offline, sin API).

Advertencia metodológica (va también en el reporte): el gold del held-out es de
UN solo anotador por nota (56 lch, 16 jcc, 3 xig) — más ruidoso que el lote
doble-anotado, y acá no hay techo humano. Los números de selección y held-out se
comparan entre sí como Δ, no contra el 0.71.

Cache por (modelo, variante, index-sintético) en `cache/exp5_heldout.json`.
Metodología de reporte: métricas SOLO sobre notas con predicción; cobertura
aparte; corridas parciales no comparables.

Uso:  python -m experiments.exp5_heldout
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.exp1_prompts import (MAX_FALLOS_SEGUIDOS,  # noqa: E402
                                      MODELO_SONNET, THROTTLE_GEMINI_S,
                                      VARIANTES, _estilo, _load_cache)
from trust_sources import ClassicSourceDetector, LLMSourceDetector  # noqa: E402
from trust_sources.evaluation import evaluate_referenciados  # noqa: E402
from trust_sources.io_anotaciones import (load_double_annotated,  # noqa: E402
                                          load_heldout)
from trust_sources.llm_client import client_for_model, load_dotenv  # noqa: E402

CACHE = Path(__file__).resolve().parent / "cache" / "exp5_heldout.json"
RESULTS = ROOT / "results"
ASSETS = ROOT / "docs" / "assets"

MODELO = MODELO_SONNET
# Solo el baseline y el ganador: el contraste entre sus caídas es la medición.
IDS = ["v0_estricto", "v1_fewshot"]
VARS = [v for v in VARIANTES if v["id"] in IDS]

# Paleta del repo (validada): los dos primeros hues del orden categórico fijo.
C_SEL, C_HELD, C_CLASICO = "#2a78d6", "#eb6834", "#898781"
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"


def _cache_io(path: Path, data: dict | None = None) -> dict:
    if data is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _run_variante(variante: dict, arts, cache: dict) -> dict:
    """Corre una variante sobre el held-out (cache o vivo) y evalúa calidad
    sobre lo cubierto (cobertura aparte, como en exp1)."""
    vcache = cache.setdefault(MODELO, {}).setdefault(variante["id"], {})
    client = client_for_model(MODELO)
    detector = (LLMSourceDetector(client, prompt=variante["prompt"],
                                  max_tokens=variante.get("max_tokens", 400))
                if client else None)
    throttle = THROTTLE_GEMINI_S if (client and client.name == "gemini") else 0.0
    fallos_seguidos, corto = 0, False
    for a in arts:
        if a.index in vcache or detector is None or corto:
            continue
        if throttle:
            time.sleep(throttle)
        try:
            vcache[a.index] = detector.referenciados(a.cuerpo)
            fallos_seguidos = 0
        except Exception as e:  # noqa: BLE001
            print(f"  [{variante['id']}] {a.index}: {e}")
            fallos_seguidos += 1
            if fallos_seguidos >= MAX_FALLOS_SEGUIDOS:
                corto = True
                print(f"  [{variante['id']}] {MAX_FALLOS_SEGUIDOS} fallos seguidos: "
                      "corto (el cache retoma después).")
        _cache_io(CACHE, cache)  # persistimos por nota: un corte no pierde nada

    arts_cov = [a for a in arts if a.index in vcache]
    m = evaluate_referenciados(arts_cov, {a.index: vcache[a.index] for a in arts_cov})
    return {"id": variante["id"], "desc": variante["desc"],
            "P": m["P"], "R": m["R"], "F1": m["F1"],
            "cobertura": f"{len(arts_cov)}/{len(arts)}",
            "completo": len(arts_cov) == len(arts)}


def _f1_seleccion(variante_id: str, arts_sel) -> float | None:
    """F1 de la variante sobre las 16 de selección, recalculado del cache de
    exp1 (mismo modelo). Offline: no llama a ninguna API."""
    vcache = _load_cache().get(MODELO, {}).get(variante_id, {})
    cov = [a for a in arts_sel if a.index in vcache]
    if len(cov) != len(arts_sel):
        return None  # celda incompleta en exp1: no comparable
    return evaluate_referenciados(cov, {a.index: vcache[a.index] for a in cov})["F1"]


def _clasico(arts) -> dict:
    det = ClassicSourceDetector()
    preds = {a.index: det.referenciados(a.cuerpo) for a in arts}
    return evaluate_referenciados(arts, preds)


def _chart(rows: list[dict], clasico_sel: float, clasico_held: float) -> None:
    """Barras agrupadas: F1 selección vs held-out por variante (+ clásico).
    Paleta/estilo del repo (validados); dos series → azul/naranja del orden fijo."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # noqa: BLE001
        print(f"  (sin gráfico: {e})")
        return
    ASSETS.mkdir(parents=True, exist_ok=True)
    ids = [r["id"] for r in rows] + ["clásico (reglas)"]
    sel = [r["F1_sel"] for r in rows] + [clasico_sel]
    held = [r["F1"] for r in rows] + [clasico_held]
    x, w = range(len(ids)), 0.36
    fig, ax = plt.subplots(figsize=(1.9 * len(ids) + 2.4, 4.2))
    fig.patch.set_facecolor("white")
    ax.bar([i - w / 2 for i in x], sel, w, label="selección (16 notas)", color=C_SEL)
    ax.bar([i + w / 2 for i in x], held, w, label="held-out (75 notas)", color=C_HELD)
    for i, (s, h) in enumerate(zip(sel, held)):
        ax.text(i - w / 2, s + 0.02, f"{s:.2f}", ha="center", fontsize=8, color=INK)
        ax.text(i + w / 2, h + 0.02, f"{h:.2f}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(list(x)); ax.set_xticklabels(ids, rotation=10, ha="right")
    ax.set_ylim(0, 1.12); ax.set_ylabel("F1 (referenciados)")
    _estilo(ax)
    ax.legend(fontsize=8, frameon=False, ncol=2, loc="upper center")
    ax.set_title(f"Exp 5 — ¿generaliza? selección vs held-out · {MODELO}", color=INK)
    fig.tight_layout()
    fig.savefig(ASSETS / "exp5_heldout.png", dpi=130); plt.close(fig)


def main() -> None:
    load_dotenv(ROOT / ".env")
    RESULTS.mkdir(exist_ok=True)
    arts_sel, _ = load_double_annotated()
    arts_held = load_heldout()
    anotadores: dict[str, int] = {}
    for a in arts_held:
        anot = a.index.split("_")[0]
        anotadores[anot] = anotadores.get(anot, 0) + 1
    comp = " · ".join(f"{k} {v}" for k, v in sorted(anotadores.items(),
                                                    key=lambda kv: -kv[1]))
    print(f"Held-out: {len(arts_held)} notas ({comp}) · modelo: {MODELO}")
    if client_for_model(MODELO) is None:
        print("  (sin ANTHROPIC_API_KEY: solo se evalúa lo cacheado)")

    cache = _cache_io(CACHE)
    rows = []
    for v in VARS:
        r = _run_variante(v, arts_held, cache)
        r["F1_sel"] = _f1_seleccion(v["id"], arts_sel)
        rows.append(r)
        flag = "" if r["completo"] else f"  [PARCIAL {r['cobertura']}]"
        print(f"  {r['id']:16s} held-out F1={r['F1']:.2f} (P={r['P']:.2f} "
              f"R={r['R']:.2f}) · selección F1={r['F1_sel']}{flag}")

    cl_sel = _clasico(arts_sel)["F1"]
    cl_held = _clasico(arts_held)["F1"]
    print(f"  {'clasico':16s} held-out F1={cl_held:.2f} · selección F1={cl_sel:.2f}")

    md = ["# Exp 5 — validación held-out: ¿el F1 de la selección generaliza?\n",
          f"- Held-out: **{len(arts_held)} notas** anotadas nunca vistas "
          f"(gold de UN anotador por nota: {comp}); las 16 de selección se "
          "excluyen por link.",
          "- Las 16 de selección se usaron para ELEGIR prompts → medir solo ahí "
          "sobreestima. Acá los mismos prompts corren sobre notas no vistas.",
          "- Gold held-out más ruidoso (sin doble anotación, sin techo humano): "
          "comparar los Δ entre columnas, no contra el 0.71.",
          "- Métricas **solo sobre notas con predicción**; cobertura aparte; "
          "parciales no comparables.\n",
          f"| Detector | F1 selección (16) | F1 held-out ({len(arts_held)}) | Δ | Cobertura |",
          "|---|---|---|---|---|"]
    for r in rows:
        f1s = f"{r['F1_sel']:.2f}" if r["F1_sel"] is not None else "—"
        d = (f"{r['F1'] - r['F1_sel']:+.2f}" if r["F1_sel"] is not None
             and r["completo"] else "—")
        f1h = f"**{r['F1']:.2f}**" if r["completo"] else f"{r['F1']:.2f} (parcial)"
        md.append(f"| `{r['id']}` ({MODELO}) | {f1s} | {f1h} | {d} | {r['cobertura']} |")
    md.append(f"| clásico (reglas) | {cl_sel:.2f} | **{cl_held:.2f}** | "
              f"{cl_held - cl_sel:+.2f} | {len(arts_held)}/{len(arts_held)} |")
    # --- Descomposición por anotador: ¿cuánto es modelo y cuánto es gold? ---
    # lch es el mismo anotador que el gold de selección → su subgrupo es la
    # comparación más limpia (misma vara, notas nuevas). jcc/xig marcan MENOS
    # fuentes por nota que lch: contra ese gold, parte de la caída es criterio.
    md += ["", "## Descomposición por anotador del gold\n",
           "El subgrupo **lch** usa la misma vara que la selección (mismo "
           "anotador): su F1 es la brecha de generalización limpia. jcc y xig "
           "marcan menos fuentes por nota que lch — contra su gold, parte de la "
           "caída es diferencia de criterio, no del modelo.\n"]
    for r in rows:
        if not r["completo"]:
            continue
        vc = cache[MODELO][r["id"]]
        md += [f"### `{r['id']}`\n",
               "| Gold | n | P | R | F1 | fuentes gold/nota | pred/nota |",
               "|---|---|---|---|---|---|---|"]
        for origen in sorted(anotadores, key=lambda k: -anotadores[k]):
            grupo = [a for a in arts_held if a.index.startswith(origen)]
            m = evaluate_referenciados(grupo, {a.index: vc[a.index] for a in grupo})
            gold_x_nota = sum(len(a.referenciados) for a in grupo) / len(grupo)
            pred_x_nota = sum(len(vc[a.index]) for a in grupo) / len(grupo)
            md.append(f"| {origen} | {len(grupo)} | {m['P']:.2f} | {m['R']:.2f} | "
                      f"**{m['F1']:.2f}** | {gold_x_nota:.1f} | {pred_x_nota:.1f} |")
        md.append("")

    md += ["![F1 selección vs held-out](../docs/assets/exp5_heldout.png)"]
    (RESULTS / "exp5_heldout.md").write_text("\n".join(md), encoding="utf-8")

    if all(r["completo"] and r["F1_sel"] is not None for r in rows):
        _chart(rows, cl_sel, cl_held)
    print("Escrito: results/exp5_heldout.md y docs/assets/exp5_heldout.png")


if __name__ == "__main__":
    main()
