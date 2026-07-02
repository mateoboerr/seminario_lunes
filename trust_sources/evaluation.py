"""
Evaluación de detectores contra la anotación humana.

v0: compara el conjunto de fuentes (referenciados) por artículo. Devuelve
precisión / recall / F1 micro. También calcula el "techo humano" (acuerdo entre
los dos anotadores).

v1 (nivel de span): compara los spans predichos (afirmacion / conector /
referenciado, con posición) contra los spans humanos, emparejando por etiqueta y
solapamiento de caracteres (IoU). Da P/R/F1 por etiqueta.
"""
from __future__ import annotations

from .io_anotaciones import Articulo
from .matching import cluster, prf1, prf1_counts
from .schema import Source


def _metrics(tp: int, fp: int, fn: int) -> dict:
    p, r, f1 = prf1(tp, fp, fn)
    return {"TP": tp, "FP": fp, "FN": fn,
            "P": round(p, 3), "R": round(r, 3), "F1": round(f1, 3)}


def evaluate_referenciados(arts: list[Articulo],
                           pred_por_index: dict[str, list[str]]) -> dict:
    """Métricas micro de un detector (predicción = lista de fuentes por index)."""
    TP = FP = FN = 0
    for a in arts:
        g = cluster(a.referenciados)
        p = cluster(pred_por_index.get(a.index, []))
        tp, fp, fn = prf1_counts(g, p)
        TP += tp; FP += fp; FN += fn
    return _metrics(TP, FP, FN)


# --- Evaluación a nivel de span (v1) -------------------------------------

# Etiquetas del esquema humano que evaluamos; "Afirmacion Debil" cuenta como afirmación.
_GOLD_LABELS = {"Referenciado", "Conector", "Afirmacion", "Afirmacion Debil"}
_NORM_LABEL = {"Afirmacion Debil": "Afirmacion"}


def _iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Solapamiento (intersección sobre unión) de dos rangos de caracteres."""
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0


def _pred_spans(sources: list[Source]) -> list[tuple[int, int, str]]:
    """(start, end, label) de cada componente ubicado (start>=0) de las Sources."""
    out = []
    for s in sources:
        for sp in s.components.values():
            if sp.start_char >= 0:
                out.append((sp.start_char, sp.end_char, sp.label))
    return out


def _gold_spans(art: Articulo) -> list[tuple[int, int, str]]:
    out = []
    for start, end, lab, _txt in art.spans:
        if lab in _GOLD_LABELS:
            out.append((start, end, _NORM_LABEL.get(lab, lab)))
    return out


def evaluate_spans(arts: list[Articulo],
                   pred_por_index: dict[str, list[Source]],
                   iou_min: float = 0.5) -> dict:
    """P/R/F1 a nivel de span, por etiqueta y global (micro).

    Un span predicho acierta si hay un span humano de la MISMA etiqueta con IoU
    >= `iou_min` (emparejamiento greedy 1-a-1). Devuelve un dict por etiqueta con
    TP/FP/FN/P/R/F1 y una entrada 'global'.
    """
    labels = ["Referenciado", "Conector", "Afirmacion"]
    acc = {lab: [0, 0, 0] for lab in labels}  # [TP, FP, FN]
    for a in arts:
        gold = _gold_spans(a)
        pred = _pred_spans(pred_por_index.get(a.index, []))
        for lab in labels:
            g = [(s, e) for s, e, L in gold if L == lab]
            p = [(s, e) for s, e, L in pred if L == lab]
            used = [False] * len(g)
            tp = 0
            for pr in p:
                best_i, best_iou = -1, iou_min
                for i, gr in enumerate(g):
                    if used[i]:
                        continue
                    v = _iou(pr, gr)
                    if v >= best_iou:
                        best_i, best_iou = i, v
                if best_i >= 0:
                    used[best_i] = True
                    tp += 1
            acc[lab][0] += tp
            acc[lab][1] += len(p) - tp
            acc[lab][2] += len(g) - sum(used)

    out = {}
    TP = FP = FN = 0
    for lab in labels:
        tp, fp, fn = acc[lab]
        TP += tp; FP += fp; FN += fn
        out[lab] = _metrics(tp, fp, fn)
    out["global"] = _metrics(TP, FP, FN)
    return out


def human_ceiling(arts: list[Articulo], xig_por_link: dict[str, Articulo]) -> dict:
    """Acuerdo lch vs xig sobre los mismos artículos (vara superior)."""
    TP = FP = FN = 0
    for a in arts:
        if a.link not in xig_por_link:
            continue
        g = cluster(a.referenciados)
        p = cluster(xig_por_link[a.link].referenciados)
        tp, fp, fn = prf1_counts(g, p)
        TP += tp; FP += fp; FN += fn
    return _metrics(TP, FP, FN)
