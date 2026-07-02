# Ejemplo de salida v1 (forma tipo Trust `get_explicit_sources`)

Generado de forma determinista con un cliente **stub** (sin API) sobre una nota de ejemplo, para mostrar el **output**: cada fuente trae afirmacion + conector + referenciado **con sus posiciones** (calculadas por código) y su **tipo**.

**Nota de entrada:**

> La inflación de junio fue del 4,2%, informó el INDEC este martes. El ministro de Economía aseguró que “la tendencia es a la baja” y pidió calma. Vecinos de Córdoba se manifestaron frente a la sede.

**Salida (`detect()` → dicts):**

```json
[
  {
    "text": "La inflación de junio fue del 4,2%, informó el INDEC",
    "start_char": 0,
    "end_char": 52,
    "length": 52,
    "pattern": "llm",
    "explicit": true,
    "components": {
      "referenciado": {
        "text": "el INDEC",
        "start_char": 44,
        "end_char": 52,
        "label": "Referenciado"
      },
      "conector": {
        "text": "informó",
        "start_char": 36,
        "end_char": 43,
        "label": "Conector"
      },
      "afirmacion": {
        "text": "La inflación de junio fue del 4,2%",
        "start_char": 0,
        "end_char": 34,
        "label": "Afirmacion"
      }
    },
    "tipo": "institucion"
  },
  {
    "text": "El ministro de Economía aseguró que “la tendencia es a la baja”",
    "start_char": 66,
    "end_char": 129,
    "length": 63,
    "pattern": "llm",
    "explicit": true,
    "components": {
      "referenciado": {
        "text": "El ministro de Economía",
        "start_char": 66,
        "end_char": 89,
        "label": "Referenciado"
      },
      "conector": {
        "text": "aseguró",
        "start_char": 90,
        "end_char": 97,
        "label": "Conector"
      },
      "afirmacion": {
        "text": "“la tendencia es a la baja”",
        "start_char": 102,
        "end_char": 129,
        "label": "Afirmacion"
      }
    },
    "tipo": "persona"
  }
]
```