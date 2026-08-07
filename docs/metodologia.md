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
**lch_100_119 ↔ xig_20_39**; 16 tienen fuentes según lch y están en ambos
archivos (en 13 de esas 16, xig también marcó fuentes).
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

### Reglas de reporte (aprendidas a fuerza de errores)

- **Calidad ≠ cobertura.** Las métricas se calculan **solo sobre las notas con
  predicción**; la cobertura (N/16) se reporta aparte. Publicar un recall
  calculado contra el gold completo cuando solo 3/16 notas tienen predicción
  produce números que se leen como calidad pero miden cobertura (nos pasó: un
  span-F1 de 0.14 que parecía "el LLM es 3× peor que las reglas" y solo decía
  "faltan 13 notas"). Solo corridas 16/16 son comparables entre sí.
- **Cache por (modelo, variante, nota).** Cada celda de una tabla comparativa
  tiene que ser 100% de un modelo. Antes el cache no distinguía modelo: completar
  una variante parcial con otro proveedor habría mezclado dos modelos en la misma
  fila sin dejar rastro. Los tres experimentos usan namespace de modelo y migran
  el formato viejo (que era 100% Gemini) automáticamente.
- **Modelos explícitos en experimentos.** Los scripts fijan el modelo por celda
  (`client_for_model`), ignorando `LLM_PROVIDER`: la misma corrida no puede
  cambiar de modelo según el entorno. (`LLM_PROVIDER` sigue valiendo para la CLI
  y el benchmark v0.)
- **Throttle solo donde hace falta:** 5 s entre llamadas de Gemini (free tier,
  ~20 req/min) y sin pausa para Anthropic (de pago). Circuit breaker tras N
  fallos seguidos para no quemar cuota contra un tier caído.
- **El set de selección no da el número final.** Los prompts se eligieron
  mirando las 16 notas doble-anotadas → medir ahí sobreestima (nos pasó: 0.86
  que en notas nunca vistas es 0.67; Exp 5). El número que se reporta como
  resultado sale del **held-out** (`load_heldout()`: las ~75 notas anotadas que
  no participaron de ninguna decisión, dedup por link, índice sintético
  `anotador_batch_n` porque el `index` crudo colisiona entre archivos).

### Hacia v1 (evaluación más estricta)
- Medir a **nivel de span** (posición exacta), no solo la lista de nombres.
- Evaluar los tres componentes (afirmacion/conector/referenciado) y la relación.
- ~~Usar **más lotes** (de los 106)~~ → hecho en el Exp 5 (held-out de 75 notas).
  Queda: **doble anotación o adjudicación** de una muestra del held-out, para
  separar error del modelo vs criterio del anotador (jcc marca 2,5 fuentes/nota
  donde lch marca 4,4).
- **Análisis de errores**: catalogar dónde falla (fuentes anónimas, entidades
  mencionadas pero no citadas, citas implícitas) para guiar mejoras.

## Notas honestas de entorno
- **El detector clásico** de Trust usa stanza/spaCy; en este entorno los modelos
  no se pudieron descargar (error SSL contra GitHub), así que se reimplementó su
  lógica con reglas (`detectors/classic.py`). Hace lo mismo para el benchmark; en
  el repo definitivo conviene usar el `SourceMatcher` real.
- **El LLM** se corre con dos proveedores: **Google Gemini** (free tier,
  `gemini-2.5-flash-lite`; cuota limitada, 429/503 si se usa mucho) y
  **Anthropic** (`claude-sonnet-5`, de pago). Hay cache en disco por modelo para
  reproducibilidad sin key.
- **TLS en Windows:** el SDK de Anthropic (httpx) moría con
  `CERTIFICATE_VERIFY_FAILED` porque un middlebox local intercepta TLS y su raíz
  está en el almacén de Windows pero no en `certifi`. Se resolvió con
  `truststore` (validar contra el almacén del sistema) — **no** con
  `verify=False`, que expondría la API key.
- **Razonamiento del modelo apagado** en el cliente Anthropic
  (`thinking: disabled`): los modelos nuevos razonan por defecto y esos tokens
  salen del mismo `max_tokens` que la respuesta (truncarían el JSON); además
  deja la comparación con Gemini pareja — una pasada, sin razonamiento, en ambos.
