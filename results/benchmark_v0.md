# Benchmark v0 — detección de fuentes (referenciados)

- Artículos: **16** (lote doble-anotado lch_100_119 ↔ xig_20_39)
- Origen columna LLM: **cache**

| Detector | Precisión | Recall | F1 |
|---|---|---|---|
| Clásico (reglas) vs humano | 0.26 | 0.25 | **0.26** |
| LLM vs humano | 0.44 | 0.78 | **0.56** |
| Techo humano (lch vs xig) | — | — | **0.71** |

> v0 compara el conjunto de fuentes (referenciados) por nota. El clásico solo ve citas entre comillas; el LLM toma también instituciones y atribuciones parafraseadas, pero sobre-detecta (precisión más baja).