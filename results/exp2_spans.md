# Exp 2 — salida v1: evaluación a nivel de span

- Notas: **16** · solapamiento mínimo (IoU) para acierto: 0.5
- Métricas calculadas **solo sobre las notas con predicción** (la cobertura se reporta aparte). Corridas parciales: no comparables.
- Baseline clásico (sin LLM): global F1 **0.39** — ver [exp2_spans_clasico.md](exp2_spans_clasico.md).

## `gemini-2.5-flash-lite` — cobertura 16/16

| Componente | P | R | F1 |
|---|---|---|---|
| Referenciado | 0.16 | 0.23 | **0.19** |
| Conector | 0.62 | 0.68 | **0.65** |
| Afirmacion | 0.71 | 0.77 | **0.74** |
| global | 0.49 | 0.59 | **0.54** |

## `claude-sonnet-5` — cobertura 16/16

| Componente | P | R | F1 |
|---|---|---|---|
| Referenciado | 0.22 | 0.33 | **0.27** |
| Conector | 0.58 | 0.62 | **0.60** |
| Afirmacion | 0.69 | 0.75 | **0.72** |
| global | 0.49 | 0.59 | **0.54** |

## Resumen (corridas completas vs baseline clásico)

| Detector | Referenciado F1 | Conector F1 | Afirmacion F1 | global F1 |
|---|---|---|---|---|
| clásico (reglas) | 0.09 | 0.46 | 0.56 | **0.39** |
| v1 `gemini-2.5-flash-lite` | 0.19 | 0.65 | 0.74 | **0.54** |
| v1 `claude-sonnet-5` | 0.27 | 0.60 | 0.72 | **0.54** |