# Exp 1 — variantes de prompt (LLM)

- Artículos: **16** (lote doble-anotado) · techo humano **F1 0.71**
- Objetivo: subir la **precisión** (baseline 0.44) sin perder recall.

| Variante | Descripción | P | R | F1 | ΔP | ΔF1 |
|---|---|---|---|---|---|---|
| `v1_fewshot` | baseline + 2 ejemplos (few-shot) | 0.47 | 0.72 | **0.57** | +0.03 | +0.01 |
| `v0_estricto` | baseline v0 (prompt estricto) | 0.44 | 0.78 | **0.56** | +0.00 | +0.00 |

**Variantes incompletas** (free tier rate-limited; se completan en otra ventana de cuota re-corriendo el script — el cache retoma donde quedó). Sus métricas NO son comparables todavía:

| Variante | Descripción | Cobertura |
|---|---|---|
| `v2_reglas_duras` | reglas negativas duras (ante la duda, excluir) | 8/16 |
| `v3_justifica` | auto-verificación: citar evidencia o descartar | 2/16 |

![P/R/F1 por variante](../docs/assets/exp1_prompts.png)