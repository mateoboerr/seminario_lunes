# Exp 5: validación held-out: ¿el F1 de la selección generaliza?

- Held-out: **75 notas** anotadas nunca vistas (gold de UN anotador por nota: lch 56 · jcc 16 · xig 3); las 16 de selección se excluyen por link.
- Las 16 de selección se usaron para ELEGIR prompts → medir solo ahí sobreestima. Acá los mismos prompts corren sobre notas no vistas.
- Gold held-out más ruidoso (sin doble anotación, sin techo humano): comparar los Δ entre columnas, no contra el 0.71.
- Métricas **solo sobre notas con predicción**; cobertura aparte; parciales no comparables.

| Detector | F1 selección (16) | F1 held-out (75) | Δ | Cobertura |
|---|---|---|---|---|
| `v0_estricto` (claude-sonnet-5) | 0.82 | **0.66** | -0.17 | 75/75 |
| `v1_fewshot` (claude-sonnet-5) | 0.86 | **0.67** | -0.19 | 75/75 |
| clásico (reglas) | 0.26 | **0.24** | -0.02 | 75/75 |

## Descomposición por anotador del gold

El subgrupo **lch** usa la misma vara que la selección (mismo anotador): su F1 es la brecha de generalización limpia. jcc y xig marcan menos fuentes por nota que lch: contra su gold, parte de la caída es diferencia de criterio, no del modelo.

### `v0_estricto`

| Gold | n | P | R | F1 | fuentes gold/nota | pred/nota |
|---|---|---|---|---|---|---|
| lch | 56 | 0.73 | 0.65 | **0.69** | 4.4 | 2.6 |
| jcc | 16 | 0.51 | 0.61 | **0.56** | 2.5 | 2.4 |
| xig | 3 | 0.33 | 0.33 | **0.33** | 2.0 | 2.0 |

### `v1_fewshot`

| Gold | n | P | R | F1 | fuentes gold/nota | pred/nota |
|---|---|---|---|---|---|---|
| lch | 56 | 0.76 | 0.66 | **0.70** | 4.4 | 2.6 |
| jcc | 16 | 0.54 | 0.61 | **0.57** | 2.5 | 2.3 |
| xig | 3 | 0.50 | 0.33 | **0.40** | 2.0 | 1.3 |

![F1 selección vs held-out](../docs/assets/exp5_heldout.png)