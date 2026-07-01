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
- [Metodología](metodologia.md) — datasets y cómo evaluamos.
- [Esquema de salida](esquema_salida.md) — el formato v0 → v1 (compatible con Trust).
- [Roadmap y next steps](roadmap.md) — plan, experimentos y multi-LLM.

## Experimentos
_(Se irán agregando acá: cada prompt/modelo probado, su número y su conclusión.)_

| Fecha | Experimento | F1 | Nota |
|---|---|---|---|
| — | v0 · prompt estricto · gemini-2.5-flash-lite | 0.56 | baseline LLM |
| — | v0 · clásico (reglas) | 0.26 | baseline clásico |
