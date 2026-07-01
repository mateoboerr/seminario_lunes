"""
Evaluación de detectores contra la anotación humana.

v0: compara el conjunto de fuentes (referenciados) por artículo. Devuelve
precisión / recall / F1 micro. También calcula el "techo humano" (acuerdo entre
los dos anotadores).
"""
from __future__ import annotations

from .io_anotaciones import Articulo
from .matching import cluster, prf1, prf1_counts


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
