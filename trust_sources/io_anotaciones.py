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


# Todos los archivos de anotación disponibles, en orden de PREFERENCIA de
# anotador (lch primero: es el gold de las 16 de selección, así el gold del
# held-out queda lo más homogéneo posible). Los nombres de batch son engañosos
# (el gotcha del `index` por archivo), así que la dedup es SIEMPRE por link.
_BATCHES = [("lch", "100_119"), ("lch", "120_139"), ("lch", "20_39"),
            ("lch", "40_59"), ("xig", "20_39"), ("jcc", "80_99")]


def load_heldout() -> list[Articulo]:
    """Notas anotadas NO usadas para elegir prompts: el conjunto held-out.

    Junta todos los archivos de anotación, se queda con las notas con fuentes,
    excluye por link las 16 doble-anotadas (con ellas se seleccionaron los
    prompts → medir ahí sobreestima) y dedup por link prefiriendo lch. Como el
    `index` original es contador POR ARCHIVO (colisiona entre archivos), acá el
    index pasa a ser sintético y único: "<anotador>_<batch>_<index>".
    Gold de UN solo anotador por nota (más ruidoso que el lote doble-anotado:
    acá no hay techo humano).
    """
    seleccion = {a.link for a in load_double_annotated()[0]}
    vistos: set[str] = set()
    out: list[Articulo] = []
    for anotador, batch in _BATCHES:
        for a in load_batch(anotador, batch):
            if not a.referenciados or a.link in seleccion or a.link in vistos:
                continue
            vistos.add(a.link)
            a.index = f"{anotador}_{batch}_{a.index}"
            out.append(a)
    return out
