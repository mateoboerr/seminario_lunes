# Esquema de salida de los detectores (v0 → v1)

El profe puso especial énfasis en el **output** de la función. La meta es que se
parezca lo más posible a la estructura de **`get_explicit_sources`** de Trust
([trustmonitor/matcher.py](https://github.com/timmd-9216/trust/blob/main/trustmonitor/matcher.py)):
una **lista de fuentes**, cada una con posiciones de carácter y `components`.

## v0 — lo mínimo que ya funciona
Cada detector expone dos vistas (ver `trust_sources/detectors/base.py`):
- `detector.referenciados(texto)` → **lista de nombres de fuente** (referenciados).
  Es lo más simple; es lo que se evalúa hoy (F1 0.56 el LLM).
- `detector.detect(texto)` → **lista de `Source`** (ya con la forma rica, abajo).

## v1 — el objetivo (estructura tipo Trust) — ✅ implementado
Implementado en `LLMSourceDetectorV1` (misma interfaz que el clásico) + evaluación
a nivel de span (`evaluation.evaluate_spans`). Ejemplo generado y validado:
[results/ejemplo_v1.md](https://github.com/mateoboerr/seminario_lunes/blob/main/results/ejemplo_v1.md) (ver **Exp 2** en la
[bitácora](experimentos.md#exp-2)).

`detect(texto)` devuelve una lista de `Source`. Cada `Source.to_dict()` produce
**exactamente** la forma de Trust:

```python
{
  "text": "aseguró que “no fueron 30 mil”. ... Schiaretti marcó...",
  "start_char": 937,
  "end_char": 1035,
  "length": 98,
  "pattern": "cita_comillas",     # nombre del patrón (clásico) o "llm"
  "explicit": True,
  "components": {
     "afirmacion":   {"text": "“no fueron 30 mil”", "start_char": 949, "end_char": 967, "label": "Afirmacion"},
     "conector":     {"text": "aseguró",            "start_char": 937, "end_char": 944, "label": "Conector"},
     "referenciado": {"text": "Villarruel",         "start_char": ...,  "end_char": ...,  "label": "Referenciado"}
  }
}
```

Las 4 piezas del esquema humano de Trust:
| Componente | Qué es | Ejemplo |
|---|---|---|
| **afirmacion** | lo que se afirma / la cita | *"no fueron 30 mil"* |
| **conector** | el verbo de atribución | *aseguró* |
| **referenciado** | la fuente | *Victoria Villarruel* |
| (relación) | qué afirmación ↔ qué fuente | implícita entre los anteriores |

## "Dónde arranca y dónde termina" — con código
Cada componente lleva `start_char` / `end_char` (span). Para el **detector clásico**
salen de las reglas. Para el **LLM**, el modelo devuelve el *texto* de la fuente y
nosotros calculamos el span **con código** ubicando ese texto en la nota
(`schema.find_span`). Así incluso la salida del LLM queda posicionada, como pidió
el profe ("fijarse igual con el LLM").

## Tipos (código)
En `trust_sources/schema.py`:
- `Span(text, start_char, end_char, label)`
- `Source(text, start_char, end_char, pattern, explicit, components: dict[str, Span])`
  con `.length`, `.referenciado_text` y `.to_dict()` (forma Trust).

## Citas implícitas (a tener en cuenta)
Hoy detectamos sobre todo **citas explícitas** (con verbo/comillas). Una línea de
trabajo es cubrir **citas implícitas**: afirmaciones cuya fuente no está marcada
con un verbo de habla directo (p. ej. *"La medida, criticada por la oposición,
…"*, o datos presentados como hechos sin atribución). El LLM es el candidato
natural para esto; el clásico por reglas casi no las ve. Es parte de la evaluación
de v1.
