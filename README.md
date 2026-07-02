# trust-sources — detección de fuentes periodísticas con LLMs

Proyecto del seminario, sobre **[trust-monitor](https://github.com/timmd-9216/trust)**.
Objetivo: **detectar las fuentes de una noticia** (a quién se le atribuye cada
información) y superar al detector clásico basado en reglas, usando modelos de
lenguaje (LLMs). Es una investigación: comparamos enfoques, probamos prompts,
medimos contra anotaciones humanas y **documentamos aciertos y fallas** en la
[GitHub Page](docs/).

> **Repositorio INDEPENDIENTE** (no es un fork de `trust` ni se pushea ahí). Este
> directorio es la raíz de un repo nuevo y propio (renombrar a `trust-sources` al
> crearlo). El repo original se usa **solo como fuente de datos**: se clona aparte
> en `trust-monitor/` (gitignoreado), no se toca ni se sube.

## Resultado actual (v0)

| Detector | Precisión | Recall | F1 |
|---|---|---|---|
| Clásico (reglas) | 0.26 | 0.25 | **0.26** |
| LLM (Gemini gratis, en vivo) | 0.44 | 0.78 | **0.56** |
| Techo humano (2 anotadores) | — | — | **0.71** |

El LLM **duplica** al clásico; tiene recall alto pero sobre-detecta (precisión más
baja). Detalle en [results/benchmark_v0.md](results/benchmark_v0.md).

## Estructura

```
trust_sources/            # paquete (código reusable)
  schema.py               # Source / Span — estructura de salida (estilo Trust)
  io_anotaciones.py       # carga de anotaciones humanas (Label Studio)
  matching.py             # normalización + emparejamiento difuso + métricas
  evaluation.py           # P/R/F1 + techo humano
  llm_client.py           # cliente multi-proveedor (Gemini/Anthropic)
  detectors/
    base.py               # interfaz SourceDetector (Strategy)
    classic.py            # detector clásico por reglas
    llm.py                # detector LLM (v0)
experiments/
  run_benchmark.py        # experimento base (v0)
  cache/llm_sources.json  # cache de detecciones LLM
results/                  # métricas y gráficos generados
docs/                     # contenido de la GitHub Page (experimentos, metodología)
trust-monitor/            # repo de datos (gitignoreado; se clona)
```

## Instalación y uso

```bash
# 1. Datos
git clone https://github.com/timmd-9216/trust.git trust-monitor
# 2. Dependencias
pip install -r requirements.txt
# 3. Correr el benchmark (usa cache; sin API key funciona igual)
python -m experiments.run_benchmark
```

Para correr el LLM **en vivo** (gratis con Google Gemini):
```bash
export GEMINI_API_KEY="<key de https://aistudio.google.com/apikey>"
python -m experiments.run_benchmark
```
El cliente elige proveedor solo: Gemini si hay `GEMINI_API_KEY`, si no Anthropic
(`ANTHROPIC_API_KEY`), si no usa el cache.

**Elegir proveedor explícitamente.** Con ambas keys, `LLM_PROVIDER` fuerza cuál usar
(el free tier de Gemini no alcanza para todas las corridas; Anthropic las completa):
```bash
export ANTHROPIC_API_KEY="..."
export LLM_PROVIDER=anthropic      # gemini | anthropic
python -m experiments.exp1_prompts    # variantes de prompt
python -m experiments.exp2_salida_v1  # salida rica v1 + eval de spans
```

**La API key va en `.env`** (gitignoreado, NUNCA se committea); el paquete lo carga
con `llm_client.load_dotenv()`. Ejemplo de `.env`:
```
GEMINI_API_KEY=...
# o
ANTHROPIC_API_KEY=...
LLM_PROVIDER=anthropic
```

## Documentación

- [docs/esquema_salida.md](docs/esquema_salida.md) — el formato de salida (v0 → v1, compatible con Trust)
- [docs/metodologia.md](docs/metodologia.md) — datasets y cómo se evalúa
- [docs/roadmap.md](docs/roadmap.md) — plan, experimentos y **next steps**
- [ESTADO_PROYECTO.md](ESTADO_PROYECTO.md) — handoff completo (todo lo que se hizo y se sabe)
