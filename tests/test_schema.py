"""Tests del esquema de salida: spans, construcción de Source, forma de dict."""
from trust_sources.schema import (find_span, source_from_components,
                                  source_from_referenciado)

TEXTO = "La inflación fue del 4,2%, informó el INDEC. El ministro aseguró que sí."


def test_find_span_exacto():
    sp = find_span(TEXTO, "el INDEC", "Referenciado")
    assert sp is not None
    assert TEXTO[sp.start_char:sp.end_char] == "el INDEC"
    assert sp.label == "Referenciado"


def test_find_span_case_insensitive():
    sp = find_span(TEXTO, "EL INDEC", "Referenciado")
    assert sp is not None and sp.text == "el INDEC"  # devuelve el texto real de la nota


def test_find_span_no_encontrado():
    assert find_span(TEXTO, "no está esto", "Referenciado") is None
    assert find_span(TEXTO, "", "Referenciado") is None


def test_source_from_referenciado_ubica_span():
    s = source_from_referenciado(TEXTO, "el INDEC")
    assert s.referenciado_text == "el INDEC"
    assert s.start_char >= 0 and s.length == len("el INDEC")


def test_source_from_referenciado_no_ubicado_queda_en_menos_uno():
    s = source_from_referenciado(TEXTO, "Fuente Inexistente")
    assert s.components["referenciado"].start_char == -1


def test_source_from_components_calcula_spans_y_span_global():
    s = source_from_components(TEXTO, {
        "referenciado": "el INDEC", "conector": "informó",
        "afirmacion": "La inflación fue del 4,2%"}, tipo="institucion")
    for sp in s.components.values():
        assert TEXTO[sp.start_char:sp.end_char] == sp.text
    # el span global abarca de la primera a la última posición
    assert s.start_char == 0
    assert s.end_char == TEXTO.find("el INDEC") + len("el INDEC")
    assert s.tipo == "institucion"


def test_source_from_components_omite_vacios():
    s = source_from_components(TEXTO, {"referenciado": "el INDEC", "conector": "",
                                       "afirmacion": ""})
    assert set(s.components) == {"referenciado"}


def test_to_dict_forma_trust_y_tipo_condicional():
    s = source_from_components(TEXTO, {"referenciado": "el INDEC"}, tipo="institucion")
    d = s.to_dict()
    assert set(d) >= {"text", "start_char", "end_char", "length", "pattern",
                      "explicit", "components"}
    assert d["components"]["referenciado"]["label"] == "Referenciado"
    assert d["tipo"] == "institucion"
    # sin tipo, la clave no aparece (compat v0/Trust)
    s2 = source_from_referenciado(TEXTO, "el INDEC")
    assert "tipo" not in s2.to_dict()
