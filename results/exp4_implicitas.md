# Exp 4 — citas implícitas (`Afirmacion Debil`)

**Caveat metodológico primero:** el gold del lote doble-anotado tiene muy pocas atribuciones débiles/implícitas — los números de esa columna son exploratorios (cada acierto mueve ~15 puntos). Se reportan igual porque la pregunta (¿el LLM ve lo que el clásico no puede?) es parte del pedido del profe; la conclusión fuerte requiere más anotación.

- Notas: **16** · IoU mínimo 0.5 · un span gold cuenta como atrapado si alguna afirmación predicha lo solapa.

| Detector | Recall afirm. fuertes | Recall afirm. débiles/implícitas |
|---|---|---|
| clásico (reglas) | 35/76 (0.46) | 2/7 (0.29) |
| v1 `claude-sonnet-5` | 57/76 (0.75) | 5/7 (0.71) |

## El flag `explicita` de la salida v1

El LLM clasifica cada fuente como explícita o implícita (`explicita: true/false`). Cuántas marcó como implícitas:

| Modelo | Fuentes predichas | Marcadas implícitas |
|---|---|---|
| v1 `claude-sonnet-5` | 94 | 1 |