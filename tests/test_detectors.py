"""Tests de los detectores (con cliente stub) y de los parsers."""
import json

from trust_sources.detectors.classic import ClassicSourceDetector
from trust_sources.detectors.llm import (LLMSourceDetector, LLMSourceDetectorV1,
                                         _parse_fuentes, _parse_fuentes_v1)
from trust_sources.detectors.multi_llm import (MultiLLMSourceDetector,
                                              _parse_afirmaciones)
from trust_sources.llm_client import LLMClient

TEXTO = ("La inflación fue del 4,2%, informó el INDEC. "
         "El ministro aseguró que “baja”.")


class Stub(LLMClient):
    """Cliente falso: devuelve una respuesta fija (o por turno)."""
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.i = 0

    def generate(self, system, user, max_tokens=500):
        r = self.respuestas[min(self.i, len(self.respuestas) - 1)]
        self.i += 1
        return r


# --- parsers ---

def test_parse_fuentes_v0_strings_y_dicts():
    assert _parse_fuentes('{"fuentes": ["INDEC", "Llaryora"]}') == ["INDEC", "Llaryora"]
    # acepta dicts con nombre bajo distintas claves
    assert _parse_fuentes('{"fuentes": [{"nombre": "INDEC"}]}') == ["INDEC"]


def test_parse_fuentes_v0_rescata_truncado():
    # Regresión (3ª aparición de la familia): con `v3_justifica` (nombre +
    # evidencia por fuente) Gemini excedía max_tokens y el JSON llegaba cortado;
    # el parser estricto tiraba JSONDecodeError y se perdía la nota ENTERA.
    truncado = ('{"fuentes": [{"nombre": "el INDEC", "evidencia": "informó"}, '
                '{"nombre": "Llaryora", "evide')
    assert _parse_fuentes(truncado) == ["el INDEC"]  # descarta el objeto a medias
    # también con items string sueltos
    assert _parse_fuentes('{"fuentes": ["INDEC", "Llaryo') == ["INDEC"]


def test_items_sueltos_no_se_descuadra_con_llaves_en_strings():
    # El escaneo por balanceo de llaves (versión vieja) contaba la "}" DENTRO
    # del string y cerraba el objeto antes de tiempo; raw_decode no.
    raw = '{"fuentes": [{"nombre": "A}B", "evidencia": "dijo {x}"}, {"nombre": "C'
    assert _parse_fuentes(raw) == ["A}B"]


def test_parse_fuentes_v1_bien_formado():
    raw = json.dumps({"fuentes": [{"referenciado": "el INDEC", "conector": "informó",
                                   "afirmacion": "x", "tipo": "institucion"}]})
    fs = _parse_fuentes_v1(raw)
    assert fs[0]["referenciado"] == "el INDEC" and fs[0]["tipo"] == "institucion"


def test_parse_fuentes_v1_rescata_truncado():
    truncado = ('{"fuentes": [{"referenciado": "A", "conector": "dijo", '
                '"afirmacion": "x", "tipo": "persona"}, {"referenciado": "B", "con')
    fs = _parse_fuentes_v1(truncado)
    assert [f["referenciado"] for f in fs] == ["A"]  # descarta el objeto a medias


def test_parse_fuentes_v1_tipo_invalido_queda_none():
    raw = '{"fuentes": [{"referenciado": "A", "tipo": "cualquiera"}]}'
    assert _parse_fuentes_v1(raw)[0]["tipo"] is None


def test_parse_afirmaciones():
    assert _parse_afirmaciones('{"afirmaciones": ["a", "b", ""]}') == ["a", "b"]


def test_parse_afirmaciones_rescata_truncado():
    # Regresión: una respuesta truncada por max_tokens devolvía [] EN SILENCIO
    # y el pipeline multi-LLM reportaba "0 fuentes" sin error visible.
    truncado = '{"afirmaciones": ["completa una", "completa \\"dos\\"", "cortada a mit'
    assert _parse_afirmaciones(truncado) == ["completa una", 'completa "dos"']


# --- detectores ---

def test_llm_v0_devuelve_referenciados_con_span():
    det = LLMSourceDetector(Stub('{"fuentes": ["el INDEC"]}'))
    sources = det.detect(TEXTO)
    assert [s.referenciado_text for s in sources] == ["el INDEC"]
    assert sources[0].start_char >= 0


def test_llm_v1_salida_rica_con_spans():
    raw = json.dumps({"fuentes": [{"referenciado": "el INDEC", "conector": "informó",
                                   "afirmacion": "La inflación fue del 4,2%",
                                   "tipo": "institucion", "explicita": True}]})
    det = LLMSourceDetectorV1(Stub(raw))
    s = det.detect(TEXTO)[0]
    assert s.tipo == "institucion"
    for sp in s.components.values():
        assert TEXTO[sp.start_char:sp.end_char] == sp.text


def test_multi_llm_encadena_dos_etapas():
    r1 = json.dumps({"afirmaciones": ["La inflación fue del 4,2%"]})
    r2 = json.dumps({"fuentes": [{"referenciado": "el INDEC", "conector": "informó",
                                  "afirmacion": "La inflación fue del 4,2%",
                                  "tipo": "institucion", "explicita": True}]})
    det = MultiLLMSourceDetector(Stub(r1, r2))
    sources = det.detect(TEXTO)
    assert [s.referenciado_text for s in sources] == ["el INDEC"]


def test_multi_llm_sin_afirmaciones_devuelve_vacio():
    det = MultiLLMSourceDetector(Stub('{"afirmaciones": []}'))
    assert det.detect(TEXTO) == []


def test_clasico_detecta_cita_con_conector():
    texto = 'El ministro Martín aseguró: “la economía mejora” en su discurso.'
    sources = ClassicSourceDetector().detect(texto)
    assert len(sources) >= 1
    assert "afirmacion" in sources[0].components


def test_trust_adapter_devuelve_forma_trust():
    from trust_sources.integration import TrustSourceAdapter
    adapter = TrustSourceAdapter(LLMSourceDetector(Stub('{"fuentes": ["el INDEC"]}')))
    out = adapter.get_explicit_sources(TEXTO)      # acepta string
    assert isinstance(out, list) and out
    assert set(out[0]) >= {"text", "start_char", "end_char", "components"}

    class Doc:  # objeto tipo stanza_doc (con .text)
        text = TEXTO
    out2 = adapter.get_explicit_sources(Doc())
    assert out2 == out
