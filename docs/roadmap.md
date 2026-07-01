# Roadmap y next steps

## Qué se pidió (acuerdos con el profe)

- **Entregable:** un **repositorio de GitHub** con una **GitHub Page** asociada
  donde se **documentan los experimentos, aciertos y fallas**. El valor no es solo
  "que funcione", sino **haber investigado bien**: probar distintos prompts,
  comparar enfoques, mostrar **visualizaciones**.
- **Implementación pulida:** funciones claras, principios **SOLID pero SIN
  overengineering**. (Ya reflejado en la arquitectura: interfaz `SourceDetector`
  + implementaciones intercambiables; módulos con una sola responsabilidad;
  cliente LLM inyectado.)
- **Énfasis en el OUTPUT:** ver [esquema_salida.md](esquema_salida.md).
  - **v0:** salida = lista de **referenciados** (quién es la fuente).
  - **v1:** salida = **lista de estructuras tipo diccionario** (como Trust
    `get_explicit_sources`): afirmacion + conector + referenciado + relación, cada
    uno **con dónde arranca y dónde termina** (spans). Para el LLM, los spans se
    calculan **con código** ubicando el texto en la nota.
- **Citas implícitas:** tenerlas en cuenta (afirmaciones sin verbo de habla / sin
  atribución explícita). El clásico casi no las ve; el LLM es el candidato.
- **Ordenar el repo** con estructura profesional (hecho: paquete `trust_sources`
  + `experiments/` + `docs/` + `results/`). Se descartaron los prototipos 2 y 3.

## Estado actual (v0 — ✅ hecho)

- Paquete `trust_sources` con dos detectores (`ClassicSourceDetector`,
  `LLMSourceDetector`) que comparten interfaz.
- Benchmark reproducible: Clásico **F1 0.26** · LLM Gemini **0.56** · techo humano
  **0.71** (16 notas doble-anotadas).
- Salida ya soporta la forma v1 (`Source.to_dict()`), aunque hoy solo se completa
  el `referenciado` en el LLM.

## Next steps (en orden)

### Etapa 0 — subir el repo
1. Crear repo en GitHub (`trust-sources`), pushear este contenido.
2. Activar **GitHub Pages** apuntando a `docs/` (o rama `gh-pages`).
3. Primer post en la Page: el benchmark v0 y esta metodología.

### Etapa 1 — mejorar el detector LLM (v0 sólido)
Esto es lo que "tiene valor": **probar y documentar experimentos**.
1. **Prompts:** probar variantes (más/menos estricto, con ejemplos few-shot,
   pidiendo que justifique) y medir P/R/F1 de cada uno → tabla comparativa en la
   Page. Objetivo: **subir la precisión** (hoy 0.44) sin perder recall.
2. **Salida estructurada:** pedir JSON validado (esquema), para robustez.
3. **Modelos:** comparar `gemini-2.5-flash-lite` vs otros (calidad/costo/latencia).
4. **Visualizaciones:** barras P/R/F1 por prompt/modelo; matriz de aciertos/fallas.

### Etapa 2 — salida rica (v1)
1. Que el LLM devuelva, por cada fuente, **afirmacion + conector + referenciado**
   (no solo el nombre), y calcular los **spans con código**.
2. Modelar la **relación** (qué afirmación respalda qué fuente).
3. **Clasificar tipo de fuente:** persona / institución / documento / anónima.
4. Cubrir **citas implícitas**.
5. Evaluar a **nivel de span** contra la anotación humana (no solo la lista).

### Etapa 3 — enfoque multi-LLM (experimento propuesto por el profe)
Probar un **pipeline de dos LLMs**:
- **LLM 1:** detecta **todas las afirmaciones** de la nota (o las **agrupa por
  persona/entidad**).
- **LLM 2:** toma esa salida y hace el siguiente paso (p. ej. asigna la fuente a
  cada afirmación, arma la estructura v1, o resume por fuente).
Comparar este pipeline contra el detector de una sola pasada. Documentar cuál
funciona mejor y por qué.

### Etapa 4 — integración a Trust
Exponer `LLMSourceDetector` con la **misma interfaz** que el `SourceMatcher`
clásico (entra noticia → sale lista de fuentes/atribuciones en la forma de
`get_explicit_sources`), para enchufarlo al pipeline de trust-monitor y poder
prender/apagar o comparar contra el clásico dentro del mismo repo.

## Principio guía
Cada experimento (prompt, modelo, pipeline) se **mide** contra la anotación humana
y se **documenta** en la Page con su número y su conclusión (qué anduvo, qué no).
Eso es el corazón del entregable.
