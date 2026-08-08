# Exp 3: multi-LLM (dos pasadas) vs single-pass

- Notas: **16** · métricas **solo sobre notas con predicción** (cobertura aparte); corridas parciales no comparables.
- Configs: `multi_sonnet` (dos pasadas, mismo modelo (`claude-sonnet-5`)) · `multi_gemini_sonnet` (dos modelos: `gemini-2.5-flash-lite` extrae, `claude-sonnet-5` asigna) · `multi_haiku_sonnet` (dos modelos: `claude-haiku-4-5` extrae, `claude-sonnet-5` asigna)

## Comparación (referenciados y span global)

| Pipeline | Cobertura | Referenciados F1 | span-F1 global |
|---|---|---|---|
| una pasada (`claude-sonnet-5`, Exp 2) | 16/16 | **0.73** (P 0.69 / R 0.78) | **0.54** |
| dos pasadas, mismo modelo (`claude-sonnet-5`) | 16/16 | **0.69** (P 0.62 / R 0.78) | **0.42** |
| dos modelos: `gemini-2.5-flash-lite` extrae, `claude-sonnet-5` asigna | 5/16 ⚠ parcial | **0.64** (P 0.58 / R 0.70) | **0.43** |
| dos modelos: `claude-haiku-4-5` extrae, `claude-sonnet-5` asigna | 16/16 | **0.69** (P 0.60 / R 0.80) | **0.36** |

## `multi_sonnet`: spans por componente (cobertura 16/16)

| Componente | P | R | F1 |
|---|---|---|---|
| Referenciado | 0.15 | 0.28 | **0.19** |
| Conector | 0.46 | 0.60 | **0.52** |
| Afirmacion | 0.45 | 0.66 | **0.53** |
| global | 0.35 | 0.53 | **0.42** |

## `multi_gemini_sonnet`: spans por componente (cobertura 5/16)

| Componente | P | R | F1 |
|---|---|---|---|
| Referenciado | 0.06 | 0.10 | **0.08** |
| Conector | 0.48 | 0.52 | **0.50** |
| Afirmacion | 0.62 | 0.71 | **0.67** |
| global | 0.39 | 0.49 | **0.43** |

## `multi_haiku_sonnet`: spans por componente (cobertura 16/16)

| Componente | P | R | F1 |
|---|---|---|---|
| Referenciado | 0.16 | 0.28 | **0.21** |
| Conector | 0.52 | 0.55 | **0.54** |
| Afirmacion | 0.32 | 0.34 | **0.33** |
| global | 0.32 | 0.40 | **0.36** |