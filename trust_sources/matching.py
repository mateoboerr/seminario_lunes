"""
Normalización y emparejamiento difuso de menciones de fuente, y métricas.

La evaluación v0 compara CONJUNTOS de fuentes (referenciados) por artículo. Como
la misma fuente se menciona de formas distintas ("Llaryora", "el gobernador
Martín Llaryora"), normalizamos y agrupamos (clustering) antes de comparar.
"""
from __future__ import annotations

import re
import unicodedata

# Artículos/títulos que no aportan a la identidad de la fuente.
_STOP_PREFIX = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "su", "sus",
    "este", "esta", "estos", "estas", "ese", "esa", "del", "de",
    "señor", "senor", "sr", "dr", "doctor", "lic", "ex",
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def normalize(mention: str) -> str:
    """minúsculas, sin acentos ni puntuación, sin artículos/títulos iniciales."""
    s = strip_accents(mention.lower())
    s = re.sub(r"[^a-z0-9ñ ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    toks = s.split()
    while toks and toks[0] in _STOP_PREFIX:
        toks.pop(0)
    return " ".join(toks)


def mentions_match(a: str, b: str) -> bool:
    """True si dos menciones refieren plausiblemente a la misma fuente."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    sa, sb = set(na.split()), set(nb.split())
    inter = sa & sb
    return bool(inter) and len(inter) / len(sa | sb) >= 0.5


def cluster(mentions: list[str]) -> list[str]:
    """Agrupa menciones de la misma fuente; representa cada grupo por la más larga."""
    clusters: list[list[str]] = []
    for m in mentions:
        for c in clusters:
            if any(mentions_match(m, x) for x in c):
                c.append(m)
                break
        else:
            clusters.append([m])
    return [max(c, key=len) for c in clusters]


def prf1_counts(gold_clusters: list[str], pred_clusters: list[str]) -> tuple[int, int, int]:
    """Empareja predicción vs gold (greedy). Devuelve (TP, FP, FN)."""
    used = [False] * len(gold_clusters)
    tp = 0
    for p in pred_clusters:
        for i, g in enumerate(gold_clusters):
            if not used[i] and mentions_match(p, g):
                used[i] = True
                tp += 1
                break
    return tp, len(pred_clusters) - tp, len(gold_clusters) - sum(used)


def prf1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1
