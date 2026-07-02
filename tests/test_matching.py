"""Tests de normalización, emparejamiento difuso y métricas."""
from trust_sources.matching import (cluster, mentions_match, normalize, prf1,
                                    prf1_counts)


def test_normalize_saca_acentos_articulos_y_titulos():
    # saca acentos, minúsculas y artículos/títulos iniciales (los del set _STOP_PREFIX)
    assert normalize("el Martín Llaryora") == "martin llaryora"
    assert normalize("INDEC") == "indec"
    assert normalize("la Municipalidad") == "municipalidad"
    # "gobernador" NO está en la lista de stopwords, así que se conserva
    assert normalize("el Gobernador Llaryora") == "gobernador llaryora"


def test_mentions_match_por_inclusion():
    assert mentions_match("Llaryora", "el gobernador Martín Llaryora")
    assert mentions_match("Martín Llaryora", "Llaryora")


def test_mentions_match_distintas_no_matchean():
    assert not mentions_match("INDEC", "Ministerio de Economía")
    assert not mentions_match("", "algo")


def test_cluster_agrupa_y_toma_la_mas_larga():
    ms = ["Llaryora", "el gobernador Martín Llaryora", "INDEC"]
    cl = cluster(ms)
    assert "el gobernador Martín Llaryora" in cl
    assert "INDEC" in cl
    assert len(cl) == 2


def test_prf1_counts_greedy():
    tp, fp, fn = prf1_counts(["INDEC", "Llaryora"], ["INDEC", "Otro"])
    assert (tp, fp, fn) == (1, 1, 1)


def test_prf1_valores():
    p, r, f1 = prf1(1, 1, 1)
    assert p == 0.5 and r == 0.5 and abs(f1 - 0.5) < 1e-9
    assert prf1(0, 0, 0) == (0.0, 0.0, 0.0)
