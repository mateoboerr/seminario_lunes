# Bitácora de experimentos

Registro cronológico de cada experimento: **qué probamos, con qué config, qué dio
y qué concluimos**. Es el corazón del entregable — el valor no es solo "que
funcione", sino *haber investigado*. Cada entrada se mide contra la anotación
humana (16 notas doble-anotadas, techo humano **F1 0.71**) y se reproduce con
`python -m experiments.run_benchmark`.

> **Cómo leer las métricas:** P = precisión (de lo que detecté, cuánto era fuente
> real), R = recall (de las fuentes reales, cuántas atrapé), F1 = media armónica.
> Objetivo de Etapa 1: **subir la precisión del LLM (0.44)** sin perder recall.

## Tabla resumen

| # | Fecha | Detector / config | P | R | F1 | Conclusión |
|---|---|---|---|---|---|---|
| 0a | 2026-07-01 | Clásico (reglas: comillas+verbo+propio) | 0.26 | 0.25 | **0.26** | baseline clásico |
| 0b | 2026-07-01 | LLM · prompt estricto v0 · `gemini-2.5-flash-lite` | 0.44 | 0.78 | **0.56** | baseline LLM; recall alto, sobre-detecta |

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
no ve. Ejemplos concretos en [results/ejemplos.md](../results/ejemplos.md).

**Qué no.** La **precisión es baja (0.44)**: el LLM **sobre-detecta** — marca como
fuente entidades solo mencionadas o protagonistas sin atribución. Ese es el
problema a atacar en los próximos experimentos.

**Próximo paso.** Variar el prompt (few-shot, reglas negativas más fuertes,
pedir justificación) y comparar modelos, midiendo si sube P sin bajar R.

---

<!-- PLANTILLA para nuevos experimentos (copiar y completar):

## Exp N — <título corto>

**Fecha:** AAAA-MM-DD · **Estado:** 🚧 / ✅

**Hipótesis.** <qué esperamos y por qué>

**Setup.** <modelo, prompt/variante, qué cambia respecto al baseline>

**Resultado.** <tabla P/R/F1; delta vs baseline>

**Qué anduvo / Qué no.** <análisis de aciertos y fallas, con ejemplos>

**Próximo paso.** <qué abre este resultado>

-->
