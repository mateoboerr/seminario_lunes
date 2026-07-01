"""
Carga de las anotaciones humanas de Trust (exports de Label Studio).

Archivos: trust-monitor/label_studio/data/outputs/
          data_noticias_lavoz_<batch>_sources_<anotador>.json

GOTCHA: el campo `index` es un contador POR ARCHIVO, no una clave global. Para
cruzar dos anotadores hay que alinear por `link`. El par doble-anotado real es
lch_100_119 <-> xig_20_39 (nombre de archivo engañoso).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Ruta al repo de datos (clonado aparte). Configurable por si cambia.
REPO = Path(__file__).resolve().parents[1] / "trust-monitor"
OUTPUTS = REPO / "label_studio" / "data" / "outputs"


@dataclass
class Articulo:
    index: str
    link: str
    titulo: str
    cuerpo: str
    referenciados: list[str] = field(default_factory=list)   # textos gold (fuentes)
    spans: list[tuple] = field(default_factory=list)          # (start, end, label, text)


def load_batch(anotador: str, batch: str) -> list[Articulo]:
    """Carga un archivo de anotación como lista de Articulo."""
    path = OUTPUTS / f"data_noticias_lavoz_{batch}_sources_{anotador}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    arts: list[Articulo] = []
    for it in data:
        d = it["data"]
        spans, referenciados = [], []
        for ann in it["annotations"]:
            for r in ann["result"]:
                if r.get("type") != "labels":
                    continue
                v = r["value"]
                lab = (v.get("labels") or [""])[0]
                spans.append((v["start"], v["end"], lab, v["text"]))
                if lab == "Referenciado":
                    referenciados.append(v["text"])
        arts.append(Articulo(index=str(d.get("index")), link=d.get("link", ""),
                             titulo=d.get("titulo", ""), cuerpo=d.get("cuerpo", ""),
                             referenciados=referenciados, spans=spans))
    return arts


def load_double_annotated() -> tuple[list[Articulo], dict[str, Articulo]]:
    """Devuelve (articulos_lch, xig_por_link) del lote realmente doble-anotado
    (lch_100_119 <-> xig_20_39), solo los que tienen fuentes en el anotador
    principal y están en ambos. Alineados por link."""
    lch = [a for a in load_batch("lch", "100_119") if a.referenciados]
    xig = {a.link: a for a in load_batch("xig", "20_39")}
    lch = [a for a in lch if a.link in xig]
    return lch, xig
