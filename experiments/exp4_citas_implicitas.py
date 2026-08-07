"""
Experimento 4: citas implícitas — ¿los detectores ven la atribución sin verbo?

El gold tiene la etiqueta `Afirmacion Debil` (atribución débil/implícita: el dato
se presenta como de una fuente pero sin verbo de habla directo). Es nuestra
aproximación operativa a la "cita implícita" que pidió tener en cuenta el profe.
ADVERTENCIA metodológica: son POCAS (n≈7 en el anotador principal), así que esto
es un análisis exploratorio con números chicos, no una métrica robusta. Se mide y
documenta igual — con el caveat al frente.

Qué mide (todo offline, desde los caches de Exp 2 — no gasta cuota):
  1) Recall por tipo de afirmación (fuerte vs débil, IoU >= 0.5): para el clásico
     y para cada modelo v1 con corrida completa. Un span gold cuenta como
     "atrapado" si alguna afirmación predicha en la misma nota lo solapa.
  2) Uso del flag `explicita` de la salida v1: cuántas fuentes vienen marcadas
     como implícitas por el LLM.

Uso:  python -m experiments.exp4_citas_implicitas
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trust_sources.detectors.classic import ClassicSourceDetector  # noqa: E402
from trust_sources.evaluation import _iou  # noqa: E402
from trust_sources.io_anotaciones import Articulo, load_double_annotated  # noqa: E402
from trust_sources.schema import source_from_components  # noqa: E402

RESULTS = ROOT / "results"
CACHE_EXP2 = ROOT / "experiments" / "cache" / "exp2_v1.json"
IOU_MIN = 0.5


def _afirmaciones_gold(a: Articulo, label: str) -> list[tuple[int, int]]:
    return [(s, e) for s, e, lab, _ in a.spans if lab == label]


def _afirmaciones_pred(sources) -> list[tuple[int, int]]:
    out = []
    for s in sources:
        sp = s.components.get("afirmacion")
        if sp is not None and sp.start_char >= 0:
            out.append((sp.start_char, sp.end_char))
    return out


def _recall_por_tipo(arts, preds_por_index) -> dict[str, tuple[int, int]]:
    """{tipo: (atrapadas, total)} para afirmaciones fuertes y débiles."""
    res = {}
    for tipo, label in (("fuerte", "Afirmacion"), ("debil", "Afirmacion Debil")):
        atrapadas = total = 0
        for a in arts:
            pred = _afirmaciones_pred(preds_por_index.get(a.index, []))
            for g in _afirmaciones_gold(a, label):
                total += 1
                if any(_iou(p, g) >= IOU_MIN for p in pred):
                    atrapadas += 1
        res[tipo] = (atrapadas, total)
    return res


def _sources_desde_cache(a: Articulo, fuentes: list[dict]):
    return [source_from_components(
        a.cuerpo, {"referenciado": f["referenciado"], "conector": f["conector"],
                   "afirmacion": f["afirmacion"]},
        tipo=f.get("tipo"), explicit=f.get("explicita", True)) for f in fuentes]


def main() -> None:
    arts, _ = load_double_annotated()
    n = len(arts)

    detectores: list[tuple[str, dict, dict | None]] = []
    clasico = ClassicSourceDetector()
    detectores.append(("clásico (reglas)",
                       {a.index: clasico.detect(a.cuerpo) for a in arts}, None))

    cache2 = (json.loads(CACHE_EXP2.read_text(encoding="utf-8"))
              if CACHE_EXP2.exists() else {})
    for modelo, mcache in cache2.items():
        cubiertas = [a for a in arts if a.index in mcache]
        if len(cubiertas) < n:  # solo corridas completas: comparable
            print(f"  ({modelo}: {len(cubiertas)}/{n}, se omite por parcial)")
            continue
        detectores.append((f"v1 `{modelo}`",
                           {a.index: _sources_desde_cache(a, mcache[a.index])
                            for a in arts}, mcache))

    md = ["# Exp 4 — citas implícitas (`Afirmacion Debil`)\n",
          "**Caveat metodológico primero:** el gold del lote doble-anotado tiene "
          "muy pocas atribuciones débiles/implícitas — los números de esa columna "
          "son exploratorios (cada acierto mueve ~15 puntos). Se reportan igual "
          "porque la pregunta (¿el LLM ve lo que el clásico no puede?) es parte "
          "del pedido del profe; la conclusión fuerte requiere más anotación.\n",
          f"- Notas: **{n}** · IoU mínimo {IOU_MIN} · un span gold cuenta como "
          "atrapado si alguna afirmación predicha lo solapa.\n",
          "| Detector | Recall afirm. fuertes | Recall afirm. débiles/implícitas |",
          "|---|---|---|"]
    for nombre, preds, _mc in detectores:
        r = _recall_por_tipo(arts, preds)
        (af, tf), (ad, td) = r["fuerte"], r["debil"]
        md.append(f"| {nombre} | {af}/{tf} ({af/tf:.2f}) | {ad}/{td} "
                  f"({(ad/td):.2f}) |" if td else f"| {nombre} | {af}/{tf} | — |")
        print(f"  {nombre}: fuertes {af}/{tf} · débiles {ad}/{td}")

    md += ["", "## El flag `explicita` de la salida v1\n",
           "El LLM clasifica cada fuente como explícita o implícita "
           "(`explicita: true/false`). Cuántas marcó como implícitas:", "",
           "| Modelo | Fuentes predichas | Marcadas implícitas |", "|---|---|---|"]
    for nombre, _preds, mcache in detectores:
        if mcache is None:
            continue
        tot = sum(len(v) for v in mcache.values())
        imp = sum(1 for v in mcache.values() for f in v if not f.get("explicita", True))
        md.append(f"| {nombre} | {tot} | {imp} |")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "exp4_implicitas.md").write_text("\n".join(md), encoding="utf-8")
    print("Escrito: results/exp4_implicitas.md")


if __name__ == "__main__":
    main()
