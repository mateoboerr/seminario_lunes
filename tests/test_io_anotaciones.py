"""Tests de la carga de anotaciones. Necesitan el clon de trust-monitor
(gitignoreado), así que se saltan si no está, el resto de la suite es offline."""
import pytest

from trust_sources.io_anotaciones import OUTPUTS, load_double_annotated, load_heldout

pytestmark = pytest.mark.skipif(
    not OUTPUTS.exists(), reason="requiere el clon de trust-monitor (datos)")


def test_heldout_disjunto_de_la_seleccion():
    """El held-out no comparte ninguna nota (link) con las 16 de selección."""
    seleccion = {a.link for a in load_double_annotated()[0]}
    heldout = load_heldout()
    assert seleccion.isdisjoint({a.link for a in heldout})


def test_heldout_sin_duplicados_y_con_fuentes():
    """Links únicos, índices sintéticos únicos (el `index` crudo colisiona entre
    archivos) y todas las notas con al menos una fuente gold."""
    heldout = load_heldout()
    assert len(heldout) == 75  # con los 6 archivos de anotación actuales
    links = [a.link for a in heldout]
    assert len(links) == len(set(links))
    indexes = [a.index for a in heldout]
    assert len(indexes) == len(set(indexes))
    assert all(a.referenciados for a in heldout)
    # el índice sintético declara su origen: "<anotador>_<batch>_<n>"
    assert all(a.index.split("_")[0] in {"lch", "xig", "jcc"} for a in heldout)
