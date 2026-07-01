# Metodología: datos y evaluación

## Los datos (anotaciones de Trust)

Fuente: repo trust-monitor, carpeta
`trust-monitor/label_studio/data/outputs/data_noticias_lavoz_<batch>_sources_<anotador>.json`.
Son exports de **Label Studio**: una lista de "tareas" (cada tarea = una noticia
de La Voz), con `data` (link, titulo, cuerpo, index…) y `annotations[0].result`
(los spans marcados + relaciones).

**Esquema de etiquetas (4)** y conteos verificados:
| Etiqueta | Qué marca | Total |
|---|---|---|
| Referenciado | la fuente (quién/qué se cita) | 396 |
| Conector | verbo de atribución ("dijo", "según") | 512 |
| Afirmacion | lo que se afirma / la cita | 469 |
| Afirmacion Debil | afirmación más floja | 59 |

Total: **1.436 spans** + **1.261 relaciones**, sobre **106 noticias** con ≥1 fuente.

**Batches y anotadores:** `lch` (principal): 20_39, 40_59, 100_119, 120_139;
`xig`: 20_39 (ver gotcha); `jcc`: 80_99.

### GOTCHA de alineación (importante)
El campo `index` es un **contador por archivo**, no una clave global. El archivo
`xig_20_39` en realidad anota los **mismos artículos que `lch_100_119`** (19/20
links compartidos). Para cruzar anotadores hay que alinear por **`link`**, no por
`index`. El par realmente doble-anotado (para el techo humano) es
**lch_100_119 ↔ xig_20_39**; 16 tienen fuentes en ambos.
(Ver `trust_sources/io_anotaciones.load_double_annotated`.)

## Cómo se evalúa (v0)

Unidad: **conjunto de fuentes (referenciados) por noticia**. Como la misma fuente
se menciona de varias formas ("Llaryora" / "el gobernador Martín Llaryora"), se
**normaliza** (minúsculas, sin acentos, sin artículos) y se **agrupa** (clustering
por matching difuso: substring o Jaccard≥0.5). Luego se empareja predicción vs
humano y se calcula:
- **Precisión**: de lo que marcó, qué % era correcto.
- **Recall**: de las fuentes reales, qué % encontró.
- **F1**: combina ambas.
- **Techo humano**: mismas métricas entre los dos anotadores (lch vs xig).

(Ver `trust_sources/matching.py` y `evaluation.py`.)

### Hacia v1 (evaluación más estricta)
- Medir a **nivel de span** (posición exacta), no solo la lista de nombres.
- Evaluar los tres componentes (afirmacion/conector/referenciado) y la relación.
- Usar **más lotes** (de los 106) y **los dos anotadores**.
- **Análisis de errores**: catalogar dónde falla (fuentes anónimas, entidades
  mencionadas pero no citadas, citas implícitas) para guiar mejoras.

## Notas honestas de entorno
- **El detector clásico** de Trust usa stanza/spaCy; en este entorno los modelos
  no se pudieron descargar (error SSL contra GitHub), así que se reimplementó su
  lógica con reglas (`detectors/classic.py`). Hace lo mismo para el benchmark; en
  el repo definitivo conviene usar el `SourceMatcher` real.
- **El LLM** se corre con **Google Gemini** (free tier, `gemini-2.5-flash-lite`).
  La cuota gratis es limitada (429 si se usa mucho). Hay cache en disco para
  reproducibilidad sin key.
