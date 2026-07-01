"""Genera experiments/demo.ipynb (demo del paquete trust_sources)."""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell as md, new_code_cell as code
from pathlib import Path

HERE = Path(__file__).resolve().parent
nb = new_notebook()
nb.cells = [
    md("# Demo — detección de fuentes (paquete `trust_sources`)\n\n"
       "Muestra los dos detectores, la salida estructurada (formato tipo Trust) "
       "y el benchmark v0."),
    code("import sys; sys.path.insert(0, '..')\n"
         "from trust_sources import ClassicSourceDetector, LLMSourceDetector\n"
         "from trust_sources.io_anotaciones import load_double_annotated\n"
         "arts, xig = load_double_annotated()\n"
         "print(len(arts), 'artículos doble-anotados')"),
    md("## Una nota: fuentes según el humano"),
    code("a = next(x for x in arts if x.index == '105')\n"
         "print(a.titulo)\n"
         "print('FUENTES (humano):', a.referenciados)"),
    md("## Detector clásico — salida estructurada (formato tipo Trust `get_explicit_sources`)"),
    code("import json\n"
         "srcs = ClassicSourceDetector().detect(a.cuerpo)\n"
         "print(json.dumps([s.to_dict() for s in srcs[:1]], ensure_ascii=False, indent=1))"),
    md("## Vista v0 (solo referenciados) de cada detector"),
    code("print('CLASICO:', ClassicSourceDetector().referenciados(a.cuerpo))\n"
         "import json\n"
         "cache = json.load(open('cache/llm_sources.json', encoding='utf-8'))\n"
         "print('LLM (cache):', cache.get(a.index))"),
    md("## Benchmark v0\n\n"
       "Correr desde la raíz: `python -m experiments.run_benchmark`.\n\n"
       "| Detector | F1 |\n|---|---|\n| Clásico | 0.26 |\n"
       "| LLM (Gemini) | 0.56 |\n| Techo humano | 0.71 |"),
]
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python",
                             "name": "python3"}
nbf.write(nb, str(HERE / "demo.ipynb"))
print("escrito experiments/demo.ipynb")
