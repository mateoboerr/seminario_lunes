"""Tests de evaluación: referenciados (v0) y a nivel de span (v1)."""
from trust_sources.evaluation import (_iou, evaluate_referenciados,
                                      evaluate_spans)
from trust_sources.io_anotaciones import Articulo
from trust_sources.schema import source_from_components

TEXTO = "La inflación fue del 4,2%, informó el INDEC. El ministro aseguró que sí."


def _art_con_spans():
    ref = TEXTO.find("el INDEC")
    con = TEXTO.find("informó")
    return Articulo(index="1", link="", titulo="", cuerpo=TEXTO,
                    referenciados=["el INDEC"],
                    spans=[(0, len("La inflación fue del 4,2%"), "Afirmacion", "..."),
                           (con, con + len("informó"), "Conector", "informó"),
                           (ref, ref + len("el INDEC"), "Referenciado", "el INDEC")])


def test_iou():
    assert _iou((0, 10), (0, 10)) == 1.0
    assert _iou((0, 10), (10, 20)) == 0.0
    assert abs(_iou((0, 10), (5, 15)) - (5 / 15)) < 1e-9


def test_evaluate_referenciados_perfecto():
    art = _art_con_spans()
    m = evaluate_referenciados([art], {"1": ["el INDEC"]})
    assert m["TP"] == 1 and m["FP"] == 0 and m["FN"] == 0
    assert m["F1"] == 1.0


def test_evaluate_spans_perfecto():
    art = _art_con_spans()
    pred = [source_from_components(TEXTO, {
        "referenciado": "el INDEC", "conector": "informó",
        "afirmacion": "La inflación fue del 4,2%"})]
    ev = evaluate_spans([art], {"1": pred})
    assert ev["global"]["F1"] == 1.0
    assert ev["Referenciado"]["TP"] == 1


def test_evaluate_spans_penaliza_faltante():
    art = _art_con_spans()
    # predigo solo el referenciado -> conector y afirmacion quedan como FN
    pred = [source_from_components(TEXTO, {"referenciado": "el INDEC"})]
    ev = evaluate_spans([art], {"1": pred})
    assert ev["Referenciado"]["F1"] == 1.0
    assert ev["Conector"]["FN"] == 1
    assert ev["global"]["TP"] == 1 and ev["global"]["FN"] == 2
