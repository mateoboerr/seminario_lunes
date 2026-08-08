# Bitácora de experimentos

Registro cronológico de cada experimento: **qué probamos, con qué config, qué dio
y qué concluimos**. Es el corazón del entregable — el valor no es solo "que
funcione", sino *haber investigado*. Cada entrada se mide contra anotación
humana — el lote de 16 notas doble-anotadas (acuerdo entre anotadores **F1
0.71**) y, desde el Exp 5, un held-out de 75 notas — y cada experimento es
reproducible con su propio script (`python -m experiments.<exp>`; sin API keys
corren offline desde los caches).

> **Cómo leer las métricas:** P = precisión (de lo que detecté, cuánto era fuente
> real), R = recall (de las fuentes reales, cuántas atrapé), F1 = media armónica.
> Objetivo de Etapa 1: **subir la precisión del LLM (0.44)** sin perder recall.

## Tabla resumen

| # | Fecha | Detector / config | P | R | F1 | Conclusión |
|---|---|---|---|---|---|---|
| 0a | 2026-07-01 | Clásico (reglas: comillas+verbo+propio) | 0.26 | 0.25 | **0.26** | baseline clásico |
| 0b | 2026-07-01 | LLM · prompt estricto v0 · `gemini-2.5-flash-lite` | 0.44 | 0.78 | **0.56** | baseline LLM; recall alto, sobre-detecta |
| 1 · v1 | 2026-07-02 | LLM · few-shot · gemini | 0.47 | 0.72 | **0.57** | +0.03 P a costa de −0.06 R; F1 casi igual |
| 1 · v2 | 2026-08-07 | LLM · reglas negativas duras · gemini | 0.50 | 0.72 | **0.59** | +0.06 P sin hundir R (la superó `v3`, ver fila siguiente) |
| 1 · v3 | 2026-08-08 | LLM · auto-verificación · gemini | 0.78 | 0.70 | **0.74** | la **mejor** variante de Gemini (+0.17): achica la brecha con Sonnet de +0.30 a +0.07 |
| 1 · S | 2026-08-07 | **misma grilla · `claude-sonnet-5`** | 0.94 | 0.80 | **0.86** | few-shot y reglas duras empatan en 0.86 — por encima del acuerdo entre anotadores (0.71) |
| 2 | 2026-08-08 | Salida rica v1 · span-F1 · ambos modelos | 0.49 | 0.59 | **0.54** | los dos LLM empatan (0.54) y superan al clásico (0.39); la ventaja de Sonnet se concentra en ubicar la fuente |
| 3 | 2026-08-07 | Multi-LLM (2 pasadas) · sonnet | 0.62 | 0.78 | **0.69** | pierde contra single-pass (0.73 refs / 0.54 spans vs 0.42) |
| 4 | 2026-08-07 | Citas implícitas (exploratorio, n=7) | — | — | — | LLM atrapa 5/7 débiles vs clásico 2/7; el flag `explicita` casi no se usa |
| 5 | 2026-08-07 | **Validación held-out** (75 notas no vistas) · sonnet | 0.71 | 0.64 | **0.67** | el 0.86 no generaliza: ~0.70 contra el mismo anotador; la ventaja del mejor prompt no se replica (orden fino con n=16 no confiable) |

---

## Exp 0 — Baselines (v0)

**Fecha:** 2026-07-01 · **Estado:** ✅ hecho

**Hipótesis.** Un LLM con un prompt de instrucciones (sin ejemplos) supera al
detector clásico por reglas en detección de fuentes.

**Setup.**
- Datos: 16 notas del lote doble-anotado (`lch_100_119` ↔ `xig_20_39`).
- Clásico: reglas comillas + verbo de habla + nombre propio.
- LLM: `gemini-2.5-flash-lite`, `PROMPT_V0` (estricto, pide solo entidades con
  atribución explícita, salida `{"fuentes": [...]}`).
- Métrica: P/R/F1 micro a nivel de *conjunto de referenciados por nota*.

**Resultado.**

| Detector | P | R | F1 |
|---|---|---|---|
| Clásico | 0.26 | 0.25 | **0.26** |
| LLM | 0.44 | 0.78 | **0.56** |
| Techo humano | — | — | **0.71** |

**Qué anduvo.** El LLM **duplica** el F1 del clásico y tiene recall alto (0.78):
atrapa instituciones y atribuciones parafraseadas que el clásico (solo comillas)
no ve. Ejemplos concretos en [results/ejemplos.md](https://github.com/mateoboerr/seminario_lunes/blob/main/results/ejemplos.md).

**Qué no.** La **precisión es baja (0.44)**: el LLM **sobre-detecta** — marca como
fuente entidades solo mencionadas o protagonistas sin atribución. Ese es el
problema a atacar en los próximos experimentos.

**Próximo paso.** Variar el prompt (few-shot, reglas negativas más fuertes,
pedir justificación) y comparar modelos, midiendo si sube P sin bajar R.

---

## Exp 1 — variantes de prompt × modelos (subir la precisión del LLM)

**Fecha:** 2026-07-02 → 2026-08-07 · **Estado:** ✅ (solo `v3` de Gemini quedó
parcial, por cuota)

**Hipótesis.** El baseline (`v0_estricto`) tiene recall alto (0.78) pero
sobre-detecta (P 0.44). Cambiando el prompt —dándole ejemplos, reglas negativas
más duras, o pidiéndole que justifique cada fuente— deberíamos **subir la
precisión sin hundir el recall**.

**Setup.** Mismo detector `LLMSourceDetector` (prompt inyectado), mismas 16
notas, y la **misma grilla de 4 prompts en dos modelos**:
`gemini-2.5-flash-lite` (free tier) y `claude-sonnet-5` (de pago). Variantes:
`v0_estricto` (baseline), `v1_fewshot` (baseline + 2 ejemplos: uno con fuente
clara, uno con entidades solo mencionadas), `v2_reglas_duras` (criterio de
exclusión reforzado, "ante la duda excluí"), `v3_justifica` (el modelo debe citar
la **evidencia** —verbo o cita— o descartar el candidato). El cache es por
**(modelo, variante, nota)**: cada celda de la tabla es 100% de un modelo.
Reproducible: `python -m experiments.exp1_prompts`.

**Resultado — `gemini-2.5-flash-lite`.**

| Variante | P | R | F1 | ΔP | ΔF1 |
|---|---|---|---|---|---|
| `v3_justifica` | 0.78 | 0.70 | **0.74** | **+0.34** | **+0.17** |
| `v2_reglas_duras` | 0.50 | 0.72 | **0.59** | +0.06 | +0.03 |
| `v1_fewshot` | 0.47 | 0.72 | **0.57** | +0.03 | +0.01 |
| `v0_estricto` | 0.44 | 0.78 | **0.56** | — | — |

![P/R/F1 por variante — Gemini](assets/exp1_prompts_gemini.png)

**Resultado — `claude-sonnet-5` (misma grilla).**

| Variante | P | R | F1 | ΔP | ΔF1 |
|---|---|---|---|---|---|
| `v1_fewshot` | 0.94 | 0.80 | **0.86** | +0.03 | +0.04 |
| `v2_reglas_duras` | 0.94 | 0.80 | **0.86** | +0.03 | +0.04 |
| `v0_estricto` | 0.91 | 0.75 | **0.82** | — | — |
| `v3_justifica` | 0.88 | 0.75 | **0.81** | −0.03 | −0.01 |

![P/R/F1 por variante — Sonnet](assets/exp1_prompts_sonnet.png)

**Las dos grillas, lado a lado** (mismos prompts, distinto modelo):

![F1 por variante y modelo](assets/exp1_modelos.png)

Tablas completas, con cobertura por celda:
[results/exp1_prompts.md](https://github.com/mateoboerr/seminario_lunes/blob/main/results/exp1_prompts.md).

**Qué anduvo.**
- **El modelo importa más que el prompt… salvo que se acierte el prompt.** Con
  el mismo prompt, Sonnet le saca a Gemini +0.26 (`v0`), +0.30 (`v1`) y +0.27
  (`v2`). Pero con `v3_justifica` **la brecha se desploma a +0.07** (0.74 vs
  0.81): la auto-verificación le da a Gemini casi todo lo que le faltaba. O sea:
  cambiar de modelo mueve más que la variante *promedio* de prompt, pero la
  variante *correcta* para el modelo débil casi cierra la diferencia — a una
  fracción del costo por llamada.
- **El mejor prompt DEPENDE del modelo, y no es un detalle: se invierte.**
  `v3_justifica` es la **mejor** variante de Gemini (+0.17 de F1, precisión
  0.44 → **0.78**) y la **peor** de Sonnet (−0.01). Mecánicamente tiene sentido:
  pedir "citá la evidencia o descartá" es una muleta que le corrige al modelo
  débil justo su defecto —sobre-detectar— mientras que al fuerte, que ya arranca
  con P 0.91, solo lo vuelve conservador de más y le cuesta recall. **Corolario
  práctico: una grilla de prompts elegida con un modelo no se hereda a otro.**
- **La dirección "subir precisión" se confirma en ambos**, pero con palancas
  distintas: few-shot y reglas duras suben P un poco en los dos (+0.03/+0.06);
  la auto-verificación la sube muchísimo solo en el chico.
- **Sonnet supera el "techo humano" (0.71).** Leerlo con cuidado: ese techo es el
  **acuerdo entre los dos anotadores** (lch vs xig), no un máximo teórico. Que el
  modelo dé 0.86 contra lch significa que **coincide con lch más que xig con
  lch** — a partir de acá, la evaluación está limitada por el ruido de la
  anotación, no por el modelo: mejoras por encima de ~0.85 no son distinguibles
  del desacuerdo humano con 16 notas. **Y el 0.86 no viaja: el [Exp 5](#exp-5--validación-held-out-el-086-generaliza)
  lo midió sobre 75 notas nunca vistas y da 0.67** — inflado sobre todo por el
  sesgo del propio lote y el ruido del gold, y solo marginalmente por haber
  elegido prompts ahí.

**Qué no (dos fallas que valen documentar).**
- **`v3_justifica` se caía por nuestra propia config, no (solo) por el modelo:**
  pedir `{"nombre", "evidencia"}` por fuente alarga el JSON y con el presupuesto
  default (`max_tokens=400`) la respuesta se **truncaba** y no parseaba
  (`Expecting ',' delimiter`). Le pasó a los dos modelos. Se subió a 800 y Sonnet
  completó 16/16 — pero al reintentar Gemini (2026-08-07, 2ª tanda) **volvió a
  truncar, ahora contra los 800** (cortes en char ~3100 ≈ 790 tokens): Gemini es
  bastante más verboso en esta variante. Arreglo definitivo en dos frentes:
  presupuesto a **1500** (es un tope, no un objetivo: no encarece nada) y el
  parser de v0/v3 pasó a **tolerar truncamiento** — antes un corte tiraba
  excepción y se perdía la nota entera; ahora rescata las fuentes completas.
  La moraleja: **un error de parseo puede disfrazarse de "el modelo es malo"** —
  antes de concluir, mirar la respuesta cruda.
- **La auto-verificación no ayudó *en Sonnet*:** v3 da 0.81 — baja recall (0.75)
  sin ganar precisión (0.88 < 0.94). Ojo con generalizar: en Gemini la misma
  variante es la ganadora por lejos. Es la evidencia más clara del proyecto de
  que **una conclusión sobre prompts no vale fuera del modelo donde se midió**.
- **La cuota diaria del free tier de Gemini se agotó** a mitad de corrida (429
  sostenido, ya no por-minuto): `v3` de Gemini quedó 8/16 y sus métricas
  parciales no se publicaron como comparables. **Se completó el 2026-08-08 y la
  decisión de no publicarlas se justificó sola:** en 8/16 daba F1 **0.87** y
  completa da **0.74**. Trece puntos de diferencia que eran puro artefacto de
  cobertura — las notas que faltaban eran las difíciles. Es exactamente el
  escenario contra el que se adoptó la regla de calidad-vs-cobertura.

**Hallazgo metodológico (de la primera tanda, sigue vigente).** Reproducir
experimentos LLM con herramientas **gratuitas** tiene un costo oculto: el
rate-limit. Cada llamada fallida gatilla reintentos que **queman la cuota
por-minuto**, así que hay que **pacear** (throttle entre llamadas), **cachear por
(modelo, variante, artículo)** para no repetir, y **cortar** ante fallos en
cadena (circuit breaker). Con un proveedor de pago (~USD 2 en total para todo lo
corrido hoy, estimado) todo esto desaparece: la grilla completa de Sonnet tardó
minutos.

**Corolario (aprendido al reintentar).** Sondear la cuota con **una** llamada no
sirve: al día siguiente el ping de prueba respondió OK y las corridas sostenidas
dieron 429 desde la primera nota. El límite **diario** puede estar agotado
mientras el **por-minuto** deja pasar alguna suelta. Para saber si hay cuota de
verdad hay que mirar si aguanta una tanda, no un ping.

**Próximo paso.** Completar `v3` de Gemini en una ventana de cuota fresca
(re-correr el script). La brecha restante contra la anotación es ruido de gold
con n=16 — el **Exp 5** ataca exactamente eso midiendo sobre las ~75 notas
anotadas que no se usaron para elegir prompts.

## Exp 2 — salida rica v1 (el OUTPUT que pidió el profe)

**Fecha:** 2026-07-02 · **Estado:** 🟢 pipeline listo y validado · medición en vivo pendiente

**Qué es.** Pasar de la salida v0 (solo el nombre de la fuente) a la **v1**: por
cada fuente, **afirmacion + conector + referenciado**, cada uno **con su posición**
(span start/end), más el **tipo** (persona / institución / documento / anónima) y
si la cita es **explícita o implícita**. La forma del dict es idéntica a
`get_explicit_sources` de Trust → interoperable. Detalle en
[esquema_salida.md](esquema_salida.md).

**Cómo.** Nuevo `LLMSourceDetectorV1` (misma interfaz `SourceDetector`, cliente
inyectado): el LLM devuelve las partes copiando el **texto exacto** de la nota, y
los **spans se calculan con código** (`schema.source_from_components` →
`find_span`), igual que en el clásico. Nuevo `evaluation.evaluate_spans`: P/R/F1 a
nivel de span por etiqueta, emparejando por solapamiento (IoU ≥ 0.5).

**Validación sin gastar cuota.** Gracias al cliente inyectable, un **stub** (JSON
fijo) prueba el pipeline entero de forma determinista:
`python -m experiments.exp2_salida_v1`. Sobre una nota de ejemplo produce y
**valida** la salida v1 (ver [ejemplo real](https://github.com/mateoboerr/seminario_lunes/blob/main/results/ejemplo_v1.md)). Extracto:

```json
{
  "text": "La inflación de junio fue del 4,2%, informó el INDEC",
  "start_char": 0, "end_char": 52, "pattern": "llm", "explicit": true,
  "components": {
    "referenciado": {"text": "el INDEC", "start_char": 44, "end_char": 52, "label": "Referenciado"},
    "conector":     {"text": "informó",  "start_char": 36, "end_char": 43, "label": "Conector"},
    "afirmacion":   {"text": "La inflación de junio fue del 4,2%", "start_char": 0, "end_char": 34, "label": "Afirmacion"}
  },
  "tipo": "institucion"
}
```

**Qué anduvo.** El **output** ya tiene la forma pedida, con posiciones correctas
(validadas: `nota[start:end] == texto` para cada componente) y clasificación de
tipo. La evaluación a nivel de span funciona (probada con gold sintético: cuenta
bien TP/FP/FN por etiqueta). Todo **sin depender de una API** para la parte de
ingeniería.

**Baseline medido: el clásico a nivel de span (sin LLM, real).** El detector clásico
ya produce la salida rica, así que lo evaluamos a nivel de span sobre las 16 notas
—reproducible offline, sin cuota (`results/exp2_spans_clasico.md`):

| Componente | P | R | F1 |
|---|---|---|---|
| Referenciado | 0.11 | 0.08 | **0.09** |
| Conector | 0.63 | 0.36 | **0.46** |
| Afirmacion | 0.76 | 0.45 | **0.56** |
| **global** | 0.51 | 0.32 | **0.39** |

Lectura: el clásico ancla bien la **cita** (Afirmacion 0.56) y el **verbo**
(Conector 0.46), pero es **muy malo ubicando la fuente** (Referenciado 0.09) — su
heurística de nombre propio falla seguido. Esa es justo la debilidad que el LLM
debería cubrir. Es la vara a superar cuando midamos v1 en vivo.

**Resultado en vivo (Sonnet 2026-08-07, Gemini 2026-08-08; ambos 16/16).**
Span-F1 contra la anotación humana (IoU ≥ 0.5), al lado del baseline clásico:

| Componente | clásico (reglas) | v1 `gemini-2.5-flash-lite` | v1 `claude-sonnet-5` |
|---|---|---|---|
| Referenciado | 0.09 | 0.19 | **0.27** |
| Conector | 0.46 | **0.65** | 0.60 |
| Afirmacion | 0.56 | **0.74** | 0.72 |
| **global** | **0.39** | **0.54** | **0.54** |

Detalle en
[results/exp2_spans.md](https://github.com/mateoboerr/seminario_lunes/blob/main/results/exp2_spans.md).

**Los dos modelos empatan a nivel de span (0.54), y eso es informativo.** En la
lista de fuentes Sonnet le sacaba +0.26 a +0.30; acá, con el mismo prompt v1, la
diferencia global desaparece — y se reparte distinto: Sonnet ubica mejor **la
fuente** (Referenciado 0.27 vs 0.19), Gemini delimita mejor **el verbo y la
cita** (Conector 0.65 vs 0.60, Afirmacion 0.74 vs 0.72). Lectura: recortar texto
que ya está en la nota es una tarea bastante más fácil que decidir *quién es
fuente*, y ahí el modelo chico alcanza. La ventaja del modelo caro se concentra
justo en la parte de juicio.

**Qué anduvo.** Los dos LLM superan al clásico **en los tres componentes**, y
justo donde el clásico es inútil (Referenciado 0.09 → 0.19/0.27) es donde más
mejoran. La Afirmacion llega a 0.72–0.74: cuando hay cita o declaración, ambos
modelos la delimitan casi como el humano.

**Qué no — y por qué el Referenciado "solo" da 0.27 en spans.** A nivel de
**lista** de fuentes, este mismo modelo da F1 0.73–0.86 (Exp 1/3); a nivel de
**span** cae a 0.27. La diferencia es la **frontera de la mención**: el humano
marca "el gobernador Martín Llaryora" y el modelo copia "Llaryora" (o al revés) —
con IoU ≥ 0.5 eso cuenta como error aunque la fuente esté bien identificada. El
span exacto es un problema de *alineación con la convención del anotador*, no de
detección. Es también el componente donde el empate global entre modelos se
rompe: 0.27 vs 0.19 a favor de Sonnet.

**Una falla nuestra que vale documentar (métrica engañosa, ya corregida).** La
primera versión de este reporte publicó span-F1 **0.14** para v1 al lado del 0.39
del clásico. Ese 0.14 estaba **aplastado por cobertura**: el recall se calculaba
contra el gold de las 16 notas cuando solo 3 tenían predicción — medía "faltan 13
notas", no calidad, y se leía como "el LLM es 3× peor que las reglas" (falso:
sobre las mismas 3 notas cubiertas daba 0.47). Regla adoptada en todos los
reportes: **las métricas se calculan solo sobre notas con predicción y la
cobertura se reporta aparte** (ver [metodología](metodologia.md)).

**Próximo paso.** Modelar la **relación** afirmación↔fuente explícita (hoy va
implícita dentro de cada `Source`). Citas implícitas: medidas aparte en el Exp 4.

## Exp 3 — pipeline multi-LLM (dos pasadas)

**Fecha:** 2026-07-02 → 2026-08-07 · **Estado:** ✅ medido con Sonnet (la config
cross-model espera cuota de Gemini)

**Idea (propuesta del profe).** En vez de resolver todo en una sola llamada,
**separar el problema en dos**: un LLM **lista las afirmaciones** de la nota, y otro
LLM **les asigna la fuente** (arma la estructura v1). La hipótesis: al enfocar cada
modelo en una tarea, mejora la calidad frente al single-pass.

**Cómo.** `MultiLLMSourceDetector` (misma interfaz `SourceDetector`, dos clientes
inyectables; por defecto el mismo modelo en ambas etapas). Son **2 llamadas por
nota** (extraer afirmaciones + asignar fuentes en una sola pasada sobre la lista),
para no disparar la cuota. La segunda etapa reusa el parser y el armado de spans de
v1. Reproducible: `python -m experiments.exp3_multi_llm`.

**Validación sin cuota.** Con **stubs de dos etapas** (uno devuelve afirmaciones,
otro las fuentes) se valida que el pipeline encadena bien y produce la salida v1 con
spans correctos — sin llamar a ninguna API.

**Resultado (2026-08-07, `claude-sonnet-5` en ambas etapas, 16/16).**

| Pipeline | Referenciados F1 | span-F1 global |
|---|---|---|
| **una pasada** (v1, Exp 2) | **0.73** (P 0.69 / R 0.78) | **0.54** |
| **dos pasadas** (afirmaciones → fuentes) | 0.69 (P 0.62 / R 0.78) | 0.42 |

Spans por componente en
[results/exp3_multi.md](https://github.com/mateoboerr/seminario_lunes/blob/main/results/exp3_multi.md).

**Conclusión: con el mismo modelo, separar la tarea en dos pasadas NO mejora —
empeora.** Mismo recall de fuentes (0.78) pero menos precisión (0.62 vs 0.69) y
spans mucho peores (0.42 vs 0.54). La hipótesis de "cada modelo enfocado en una
tarea rinde más" no se sostiene acá: la segunda etapa hereda los errores de la
primera (afirmaciones mal recortadas → spans corridos) y el requisito de "copiá
el texto exacto" se degrada al pasar por dos manos. Además cuesta el doble de
llamadas. Para este problema y este modelo, **single-pass gana**.

**La falla que casi arruina la comparación (documentada porque es la más
instructiva del proyecto).** La primera medición dio **0.37** de F1 — el pipeline
parecía un desastre. Pero mirando el cache: **10 de las 16 notas devolvían 0
fuentes**, sin ningún error visible. Causa: la etapa 1 ("listá TODAS las
afirmaciones copiando el texto exacto") excedía su `max_tokens` (800), el JSON
llegaba **truncado**, y el parser lo convertía en `[]` **en silencio** — con
lista vacía, la etapa 2 ni se llamaba. Un bug de presupuesto de tokens
disfrazado de resultado experimental. Fix doble: presupuesto 1200 para la etapa
1 + parser tolerante a truncamiento (`_strings_sueltos`, con test de regresión).
Re-medido: 0.69. **Moraleja repetida** (ya pasó en Exp 1 con v3): cuando un LLM
"rinde mal", primero descartar que el harness lo esté degradando — cobertura,
truncamiento, parseo.

**Qué falta.** La config **cross-model** (`gemini` extrae + `sonnet` asigna — la
lectura literal de la propuesta del profe, con el modelo barato en la etapa
barata) sigue **parcial: 2/16** al 2026-08-08. Sus métricas no se publican como
comparables. El cuello de botella es de cuota, no de código: el free tier diario
de Gemini rinde ~23 llamadas, y ese día se las llevaron `exp1` (8) y `exp2` (13).
Para completarla hay que correr **exp3 primero** en una ventana fresca (necesita
16). Alternativa sin esperar: usar otro modelo barato en la etapa 1 —
`claude-haiku-4-5` cumple el mismo rol conceptual por centavos, aunque deja de
ser la comparación literal con Gemini.

## Exp 4 — citas implícitas (exploratorio)

**Fecha:** 2026-08-07 · **Estado:** ✅ medido · **n chico: leer con cautela**

**Qué es.** El profe pidió tener en cuenta las **citas implícitas** (atribución
sin verbo de habla directo). El gold las marca como `Afirmacion Debil` — pero hay
**muy pocas** en el lote doble-anotado (n=7): cada acierto mueve ~15 puntos, así
que esto es exploratorio, no concluyente. Reproducible sin cuota:
`python -m experiments.exp4_citas_implicitas` (usa los caches).

**Resultado.** Recall de afirmaciones por tipo (IoU ≥ 0.5):

| Detector | Afirm. fuertes (n=76) | Afirm. débiles/implícitas (n=7) |
|---|---|---|
| clásico (reglas) | 35/76 (0.46) | 2/7 (0.29) |
| v1 `claude-sonnet-5` | 57/76 (0.75) | **5/7 (0.71)** |

Detalle en
[results/exp4_implicitas.md](https://github.com/mateoboerr/seminario_lunes/blob/main/results/exp4_implicitas.md).

**Qué anduvo.** La dirección esperada se confirma: el clásico (que necesita
comillas o verbo de habla por diseño) pierde las implícitas (0.29), mientras el
LLM las atrapa casi al mismo nivel que las explícitas (0.71 vs 0.75). Es el
argumento central a favor del LLM para este problema.

**Qué no.** El **flag `explicita`** de la salida v1 casi no se usa: de 94 fuentes
predichas, el modelo marcó **1** como implícita. O sea: *captura* las
atribuciones implícitas pero no las *etiqueta* como tales — el flag hoy no es
confiable como clasificador. Para medirlo en serio: más notas anotadas (hay 106)
y quizá un prompt que defina "implícita" con ejemplos.

## Exp 5 — validación held-out: ¿el 0.86 generaliza?

**Fecha:** 2026-08-07 · **Estado:** ✅ medido (16/16 → 75/75)

**Motivación.** El Exp 1 dejó dos sospechas metodológicas sobre el F1 0.86 de
Sonnet: (a) los prompts se **eligieron** mirando esas mismas 16 notas —
sobreajuste de selección—, y (b) las 16 doble-anotadas son un subconjunto
**sesgado**: entraron las notas con fuentes según lch dentro del lote que xig
también anotó — y en 13 de las 16, xig también marcó fuentes: casos de
atribución comparativamente clara. Un evaluador preguntaría: ¿cuánto
de ese número es el modelo y cuánto es haber medido en el lote equivocado?

**Setup.** Las **75 notas anotadas restantes** (de los 6 archivos de Label
Studio, dedup por link, excluyendo por link las 16 de selección) — notas que el
modelo nunca vio y que **no** participaron de ninguna decisión de diseño. Gold
de UN solo anotador por nota (lch 56 · jcc 16 · xig 3): más ruidoso, sin techo
humano. Dos variantes **a propósito**: `v0_estricto` (nunca se eligió mirando
las 16 → su caída mide solo gold/dificultad) y `v1_fewshot` (el ganador elegido
→ su caída *extra* mide el sobreajuste de selección). Clásico de referencia.
Reproducible: `python -m experiments.exp5_heldout`.

**Resultado.**

| Detector | F1 selección (16) | F1 held-out (75) | Δ |
|---|---|---|---|
| `v0_estricto` (sonnet) | 0.82 | **0.66** | −0.17 |
| `v1_fewshot` (sonnet) | 0.86 | **0.67** | −0.19 |
| clásico (reglas) | 0.26 | **0.24** | −0.02 |

![F1 selección vs held-out](assets/exp5_heldout.png)

**Qué dio (la lectura fina está en la descomposición por anotador,
[results/exp5_heldout.md](https://github.com/mateoboerr/seminario_lunes/blob/main/results/exp5_heldout.md)):**

- **El 0.86 no viaja: en notas no vistas es 0.67.** Pero la brecha se reparte
  entre tres componentes de tamaño muy distinto:
  1. **Sobreajuste de selección: chico.** La ventaja del few-shot sobre v0 pasa
     de +0.04 (selección) a +0.02 (held-out). Elegir el prompt "ganador" con 16
     notas fue, en buena parte, ajustar ruido — pero costó poco.
  2. **Heterogeneidad del gold: grande.** jcc marca **2,5** fuentes/nota donde
     lch marca **4,4**. Contra el gold de jcc la precisión cae a 0.54 aunque el
     modelo prediga lo mismo: es diferencia de *criterio de anotación*, no de
     detección. Contra **lch** — la misma vara que la selección — el held-out da
     **F1 0.70**, estable entre batches (0.69–0.73; excluido un resto de n=1).
  3. **Sesgo del lote + ruido del gold single-anotado: el resto.** Aun contra
     lch queda una brecha real (0.86 → 0.70) que mezcla dos causas **no
     separables sin doble anotación** (ver Qué no): las 16 de selección tienden
     a casos de atribución clara (en 13 de 16, xig también marcó fuentes), y el
     gold del held-out no pasó por el cruce con un segundo anotador. Lo
     observado: el modelo predice 2,6 fuentes/nota contra un gold de 4,4 y el
     recall baja de 0.80 a 0.66. Que esas fuentes perdidas sean "más marginales"
     es hipótesis, no observación — la densidad del gold es casi igual (4,0
     fuentes/nota en la selección vs 4,4 en el held-out de lch).
- **El número honesto del proyecto es ~0.70** (contra el mismo anotador, en
  notas no vistas), no 0.86. Así se reporta de acá en adelante.
- **El orden no cambia:** el LLM (0.66–0.67) casi triplica al clásico (0.24) en
  el held-out. Y que el clásico caiga solo −0.02 descarta que el held-out sea
  "más difícil" en general — es más exigente con el *acuerdo fino* contra el
  gold, justo donde el LLM aparentaba más de lo que tenía.

**Qué no.** Con gold de un solo anotador no se puede separar del todo "el modelo
se equivoca" de "el anotador tiene otro criterio" — eso pide doble anotación o
adjudicación de una muestra del held-out (trabajo futuro). Y el ranking fino de
prompts medido con n=16 no es confiable: la ventaja del ganador (+0.04) no se
replicó en el held-out (+0.02), y las demás variantes (v2/v3, y todo el ranking
de Gemini) no se re-midieron acá.

**Moraleja metodológica (la tercera del proyecto, y la más general).** Ya
aprendimos que el harness puede disfrazar fallas de infraestructura de
resultados (Exp 1 y 3); acá la lección es del lado de la evaluación: **un score
alto sobre el set con el que se tomaron decisiones no es un resultado — es una
hipótesis.** La validación held-out costó 150 llamadas (~medio dólar) y cambió
la conclusión principal del proyecto.

## Matriz de aciertos y fallas (transversal)

La visualización prometida en el roadmap: F1 de referenciados **por nota**, para
cada corrida completa (16/16). Filas ordenadas de fácil a difícil; se ve qué
notas saca todo el mundo, cuáles no saca nadie, y dónde el LLM le gana al
clásico. Reproducible offline: `python -m experiments.viz_matriz`.

![Matriz de aciertos/fallas por nota](assets/matriz_aciertos.png)

Lecturas rápidas: la columna del clásico es casi toda pálida (7 de 16 notas en
0.00); `gemini·v0` resuelve las "fáciles" pero se derrumba en el tramo difícil de
abajo (cuatro notas ≤0.33); Sonnet se mantiene ≥0.50 en **todas** las notas
(mínimos 0.50 en v0 y 0.57 en v1); y la 107 es la de peor promedio general (0.40).

**La columna `gemini·v3` es la confirmación visual del hallazgo del Exp 1:**
rescata **3 de las 4** notas donde `gemini·v0` se caía (101: 0.20 → 0.67 · 107:
0.14 → 0.67 · 110: 0.29 → 0.80), y falla solo en la 106. La auto-verificación no
mejora al modelo chico de forma pareja: le arregla justo las notas difíciles,
que son las que separaban a los dos modelos.

<!-- PLANTILLA para nuevos experimentos (copiar y completar):

## Exp N — <título corto>

**Fecha:** AAAA-MM-DD · **Estado:** 🚧 / ✅

**Hipótesis.** <qué esperamos y por qué>

**Setup.** <modelo, prompt/variante, qué cambia respecto al baseline>

**Resultado.** <tabla P/R/F1; delta vs baseline>

**Qué anduvo / Qué no.** <análisis de aciertos y fallas, con ejemplos>

**Próximo paso.** <qué abre este resultado>

-->
