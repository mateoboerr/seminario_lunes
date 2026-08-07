"""
Matriz de aciertos/fallas por nota — la visualización prometida en el roadmap.

Heatmap: filas = las 16 notas doble-anotadas, columnas = detectores (clásico,
LLM por modelo/variante, pipelines multi-LLM), celda = F1 de referenciados EN ESA
NOTA. Muestra DÓNDE falla cada sistema: qué notas son fáciles para todos, cuáles
no las saca nadie, y en cuáles el LLM le gana al clásico.

Todo offline, desde los caches (no gasta cuota). Solo entran corridas completas
(16/16): una columna parcial no sería comparable fila a fila.

Uso:  python -m experiments.viz_matriz
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trust_sources.detectors.classic import ClassicSourceDetector  # noqa: E402
from trust_sources.evaluation import evaluate_referenciados  # noqa: E402
from trust_sources.io_anotaciones import load_double_annotated  # noqa: E402

ASSETS = ROOT / "docs" / "assets"
CACHE_EXP1 = ROOT / "experiments" / "cache" / "exp1_prompts.json"
CACHE_EXP3 = ROOT / "experiments" / "cache" / "exp3_multi.json"

# Tinta y rampa secuencial (azul 100→700 de la paleta validada): una celda clara
# = falla, oscura = acierto. Un solo tono — la magnitud la lleva la luminosidad.
RAMPA = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"

ETIQUETA_MODELO = {"gemini-2.5-flash-lite": "gemini", "claude-sonnet-5": "sonnet"}
ETIQUETA_CONFIG = {"multi_sonnet": "multi s+s", "multi_gemini_sonnet": "multi g→s"}


def _columnas(arts) -> list[tuple[str, dict[str, list[str]]]]:
    """[(etiqueta, {index: [referenciados]})] — solo corridas completas."""
    n = len(arts)
    cols: list[tuple[str, dict[str, list[str]]]] = []
    clasico = ClassicSourceDetector()
    cols.append(("clásico", {a.index: clasico.referenciados(a.cuerpo) for a in arts}))

    if CACHE_EXP1.exists():
        cache1 = json.loads(CACHE_EXP1.read_text(encoding="utf-8"))
        for modelo, variantes in cache1.items():
            met = ETIQUETA_MODELO.get(modelo, modelo)
            completas = {vid: vc for vid, vc in variantes.items()
                         if all(a.index in vc for a in arts)}
            # v0 (baseline) + la mejor otra variante del modelo (por F1 global)
            elegidas = {"v0_estricto"} if "v0_estricto" in completas else set()
            otras = [v for v in completas if v not in elegidas]
            if otras:
                mejor = max(otras, key=lambda v: evaluate_referenciados(
                    arts, completas[v])["F1"])
                elegidas.add(mejor)
            for vid in sorted(elegidas):
                cols.append((f"{met}·{vid.split('_')[0]}", completas[vid]))

    if CACHE_EXP3.exists():
        cache3 = json.loads(CACHE_EXP3.read_text(encoding="utf-8"))
        for cfg, ccache in cache3.items():
            if all(a.index in ccache for a in arts):
                refs = {i: [f["referenciado"] for f in v if f.get("referenciado")]
                        for i, v in ccache.items()}
                cols.append((ETIQUETA_CONFIG.get(cfg, cfg), refs))
    return cols


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    arts, _ = load_double_annotated()
    cols = _columnas(arts)
    if len(cols) < 2:
        print("Faltan corridas completas en cache; nada para graficar.")
        return

    # F1 por (nota, detector); filas ordenadas de fácil a difícil (promedio)
    f1 = {a.index: [evaluate_referenciados([a], {a.index: preds.get(a.index, [])})["F1"]
                    for _, preds in cols] for a in arts}
    orden = sorted(arts, key=lambda a: -sum(f1[a.index]) / len(cols))
    matriz = [f1[a.index] for a in orden]
    filas = [f"{a.index} · {a.titulo[:34]}…" if len(a.titulo) > 34
             else f"{a.index} · {a.titulo}" for a in orden]

    cmap = LinearSegmentedColormap.from_list("azul", RAMPA)
    fig, ax = plt.subplots(figsize=(1.35 * len(cols) + 4.4, 0.42 * len(orden) + 1.8))
    fig.patch.set_facecolor("white")
    im = ax.imshow(matriz, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(cols)), [c[0] for c in cols], fontsize=9, color=INK)
    ax.set_yticks(range(len(orden)), filas, fontsize=8, color=INK)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    # separadores hairline entre celdas (spacer del método de dataviz)
    for i in range(len(orden) + 1):
        ax.axhline(i - 0.5, color="white", lw=2)
    for j in range(len(cols) + 1):
        ax.axvline(j - 0.5, color="white", lw=2)
    for i, fila in enumerate(matriz):
        for j, v in enumerate(fila):
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if v > 0.55 else INK)
    ax.set_title("Aciertos y fallas por nota — F1 de referenciados "
                 "(fila = nota, ordenadas de fácil a difícil)", color=INK, fontsize=11)
    cb = fig.colorbar(im, ax=ax, shrink=0.7)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, color=MUTED, labelcolor=INK)
    fig.tight_layout()
    ASSETS.mkdir(parents=True, exist_ok=True)
    out = ASSETS / "matriz_aciertos.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"Escrito: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
