# ESTADO DEL PROYECTO — handoff completo

> Documento maestro para retomar el trabajo desde cero. Reúne TODO lo hecho, lo
> acordado con el profe y los next steps. (Docs específicas en `docs/`.)

## 0) Qué es

Proyecto del seminario: **detección de fuentes periodísticas con LLMs**, sobre el
proyecto **trust-monitor** (versión del profe:
https://github.com/timmd-9216/trust). Se eligió esta línea (era el "Proyecto 1"
entre 3 alternativas exploradas; las otras dos —agente corrector y precios SEPA—
se **descartaron y borraron**).

## 1) Acuerdos con el profe (todo lo que se habló)

- **Entregable:** repo de GitHub + **GitHub Page** documentando **experimentos,
  aciertos y fallas**. No alcanza con "que funcione": hay que **investigar bien**,
  probar prompts, comparar, mostrar **visualizaciones**.
- **Código pulido:** funciones claras, **SOLID sin overengineering**.
- **Énfasis en el OUTPUT** (ver `docs/esquema_salida.md`):
  - v0: salida = lista de **referenciados** (quién es la fuente).
  - v1: salida = **lista de dicts tipo Trust `get_explicit_sources`**: afirmacion +
    conector + referenciado + relación, cada uno con **dónde arranca y termina**
    (spans). Para el LLM los spans se calculan **con código**.
- **Citas implícitas:** tenerlas en cuenta.
- **Experimento multi-LLM:** un LLM detecta/agrupa afirmaciones (o por persona),
  otro LLM procesa esa salida.
- **Ordenar el repo:** estructura profesional (hecho).

## 2) Arquitectura (nueva, profesional)

```
trust_sources/            # PAQUETE (código reusable)
  schema.py               # Source / Span — estructura de salida (estilo Trust)
  io_anotaciones.py       # carga de anotaciones humanas (Label Studio); Articulo
  matching.py             # normalize / mentions_match / cluster / prf1
  evaluation.py           # evaluate_referenciados / human_ceiling
  llm_client.py           # LLMClient (ABC) + GeminiClient + AnthropicClient + default_client()
  detectors/
    base.py               # SourceDetector (ABC): detect()->list[Source]; referenciados()
    classic.py            # ClassicSourceDetector (reglas: comillas+verbo+propio)
    llm.py                # LLMSourceDetector (cliente inyectado, prompt, v0)
experiments/
  run_benchmark.py        # experimento v0 (python -m experiments.run_benchmark)
  cache/llm_sources.json  # cache de detecciones LLM (Gemini) por índice de artículo
results/                  # benchmark_v0.md/json, ejemplos.md (generados)
docs/                     # GitHub Page: index, metodologia, esquema_salida, roadmap
README.md, requirements.txt, ESTADO_PROYECTO.md, .gitignore
trust-monitor/            # datos (GITIGNOREADO; se clona)
```

**SOLID aplicado (sin exagerar):** `SourceDetector` es la interfaz (Strategy) →
clásico y LLM son intercambiables (Open/Closed, Liskov). El cliente LLM se inyecta
en el detector (Dependency Inversion). Cada módulo tiene una responsabilidad (SRP):
carga, matching, evaluación, cliente, esquema. Sin capas ni abstracciones de más.

## 3) Resultado v0 (reproducible)

| Detector | Precisión | Recall | F1 |
|---|---|---|---|
| Clásico (reglas) | 0.26 | 0.25 | **0.26** |
| LLM (Gemini gratis, `gemini-2.5-flash-lite`) | 0.44 | 0.78 | **0.56** |
| Techo humano (lch vs xig) | — | — | **0.71** |

Comando: `python -m experiments.run_benchmark` (offline usa cache; con
`GEMINI_API_KEY` corre en vivo). El LLM duplica al clásico pero sobre-detecta.

## 4) Los datos (resumen; detalle en docs/metodologia.md)

- Anotaciones Label Studio en `trust-monitor/label_studio/data/outputs/
  data_noticias_lavoz_<batch>_sources_<anotador>.json`.
- Esquema: **Referenciado (396), Conector (512), Afirmacion (469), Afirmacion
  Debil (59)** = 1.436 spans + 1.261 relaciones, en **106 noticias**.
- **GOTCHA:** `index` es contador por archivo; cruzar anotadores por **`link`**.
  Par doble-anotado real = **lch_100_119 ↔ xig_20_39** (16 con fuentes en ambos).

## 5) Gotchas de entorno

- **SSL roto para GitHub:** spaCy/stanza NO bajan modelos → el clásico se
  reimplementó con reglas. `pip` y `urllib` a sitios .gob SÍ funcionan.
- **Gemini gratis:** modelo que anda = `gemini-2.5-flash-lite` (2.0-flash da 429,
  2.5-flash 503, 1.5-flash 404). Cuota limitada → 429 si se abusa. La key la tiene
  el usuario (NO se guarda en archivos). Cliente multi-proveedor: `GEMINI_API_KEY`
  → Gemini; si no `ANTHROPIC_API_KEY`; si no cache.
- **Windows console:** correr con `PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8`.
- **No committear:** `trust-monitor/`, `__pycache__`, `.ipynb_checkpoints`.

## 6) Next steps (detalle y estado en docs/roadmap.md + docs/experimentos.md)

Avance al **2026-07-02** (Etapas 0-3 arrancadas; ver bitácora):
0. **Subir a GitHub + Pages** — prep local ✅ (`_config.yml`, bitácora); subida
   **diferida** por decisión del usuario (será público).
1. **Mejorar el LLM (prompts)** 🟡 — `v1_fewshot` 0.57 vs baseline 0.56 medido y
   documentado; `v2`/`v3` parciales (free tier agotado).
2. **Salida rica v1** 🟢 — `LLMSourceDetectorV1` + `evaluate_spans` hechos y
   validados con stub; **medición en vivo pendiente**.
3. **Multi-LLM** 🟢 — `MultiLLMSourceDetector` (2 pasadas) hecho y validado con
   stub; **comparación en vivo pendiente**.
4. **Integrar a Trust** — pendiente.

**Cuota:** el free tier de Gemini no alcanza para las corridas grandes (~20 req/min
+ 503). Todo quedó **listo para Anthropic**: `LLM_PROVIDER=anthropic` +
`ANTHROPIC_API_KEY` en `.env` (gitignoreado). Con eso se completan v2/v3, el span-F1
de v1 y la comparación multi-LLM vs single-pass. Ver README.

## 7) Pendiente menor
- Renombrar la carpeta raíz `prototipos/` a `trust-sources` al crear el repo.
