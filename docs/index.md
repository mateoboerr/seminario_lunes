# Detección de fuentes periodísticas con LLMs

Bitácora de investigación del proyecto (seminario), sobre
**[trust-monitor](https://github.com/timmd-9216/trust)**.

**Problema:** detectar las *fuentes* de una noticia — a quién se le atribuye cada
información ("según el Banco Central…", "dijo el ministro…"). Queremos superar al
detector clásico basado en reglas usando modelos de lenguaje (LLMs), y documentar
el camino: experimentos, aciertos y fallas.

## Resultado actual (v0)

| Detector | Precisión | Recall | F1 |
|---|---|---|---|
| Clásico (reglas) | 0.26 | 0.25 | **0.26** |
| LLM (Gemini gratis) | 0.44 | 0.78 | **0.56** |
| Techo humano (2 anotadores) | — | — | **0.71** |

El LLM **duplica** al clásico. Tiene recall alto pero sobre-detecta (precisión más
baja) → la línea de trabajo es subir la precisión probando prompts y modelos.

## Secciones
- [Bitácora de experimentos](experimentos.md) — **cada prompt/modelo probado, su número y su conclusión** (el corazón del proyecto).
- [Metodología](metodologia.md) — datasets y cómo evaluamos.
- [Esquema de salida](esquema_salida.md) — el formato v0 → v1 (compatible con Trust).
- [Roadmap y next steps](roadmap.md) — plan, experimentos y multi-LLM.

## Experimentos (resumen)
Detalle completo en la [bitácora](experimentos.md).

| # | Fecha | Experimento | F1 | Nota |
|---|---|---|---|---|
| 2 | 2026-07-02 | Salida rica v1 (spans + tipo) | — | pipeline listo y validado (stub); ver [ejemplo](../results/ejemplo_v1.md) |
| 1 · v1 | 2026-07-02 | LLM · few-shot (2 ejemplos) | 0.57 | +0.03 P, pero F1 casi igual |
| 0b | 2026-07-01 | v0 · prompt estricto · gemini-2.5-flash-lite | 0.56 | baseline LLM |
| 0a | 2026-07-01 | v0 · clásico (reglas) | 0.26 | baseline clásico |

_Exp 1 · v2 (reglas duras) y v3 (auto-verificación) quedaron parciales por el
rate-limit del free tier; se completan re-corriendo el script. Ver [bitácora](experimentos.md#exp-1)._
