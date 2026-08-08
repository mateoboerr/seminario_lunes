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

## Estado actual (avance al 2026-08-07)

- **v0 ✅** Paquete `trust_sources` con detectores que comparten interfaz. Benchmark
  reproducible: Clásico **F1 0.26** · LLM Gemini **0.56** · acuerdo humano **0.71**.
- **Etapa 1 (prompts × modelos) ✅ completa** Grilla de 4 prompts × 2 modelos,
  16/16 en las 8 celdas. Gemini: mejor variante `v3_justifica` **0.74**. Sonnet:
  `v1_fewshot` / `v2_reglas_duras` **0.86**. Conclusión matizada: el modelo mueve
  más que el prompt *promedio* (+0.26–0.30), pero **el mejor prompt se invierte
  según el modelo** — `v3` es el mejor de Gemini y el peor de Sonnet, y con él la
  brecha cae a **+0.07**. [Bitácora Exp 1](experimentos.md#exp-1--variantes-de-prompt--modelos-subir-la-precisión-del-llm).
- **Etapa 2 (salida rica v1) ✅ completa** Los dos modelos 16/16: span-F1 global
  **0.54** ambos, vs clásico **0.39**. Empatan en total pero no en detalle —
  Sonnet ubica mejor la fuente (0.27 vs 0.19), Gemini delimita mejor verbo y cita.
  [Exp 2](experimentos.md#exp-2--salida-rica-v1-el-output-que-pidió-el-profe).
- **Etapa 3 (multi-LLM) ✅** Medido con Sonnet: dos pasadas **0.69** pierde contra
  single-pass **0.73** (spans 0.42 vs 0.54) — con el bug de truncamiento silencioso
  encontrado y documentado en el camino. **Cross-model medido 16/16** con
  `claude-haiku-4-5` extrayendo: span-F1 **0.36**, la peor de las tres — y el
  daño se concentra en `Afirmacion` (0.53→0.33), el componente que produce la
  etapa 1. La misma config con Gemini quedó 2/16 (cuota), pero ya no aporta
  conclusión nueva. [Exp 3](experimentos.md#exp-3--pipeline-multi-llm-dos-pasadas).
- **Citas implícitas (exploratorio) ✅** LLM atrapa 5/7 débiles vs clásico 2/7
  (n chico; el flag `explicita` del modelo casi no se usa). [Exp 4](experimentos.md#exp-4--citas-implícitas-exploratorio).
- **Validación held-out ✅** Los mismos prompts sobre **75 notas nunca vistas**:
  el 0.86 de la selección **no generaliza** (held-out 0.67; ~0.70 contra el
  mismo anotador). El número honesto del proyecto es ~0.70; el LLM igual casi
  triplica al clásico (0.24). [Exp 5](experimentos.md#exp-5--validación-held-out-el-086-generaliza).
- **Visualizaciones ✅** Barras P/R/F1 por variante y por modelo + **matriz de
  aciertos/fallas por nota** (la prometida acá abajo). `experiments/viz_matriz.py`.
- **Etapa 4 (integración a Trust) 🟢** `TrustSourceAdapter` expone cualquier detector
  con la interfaz `get_explicit_sources` de Trust (mismo contrato de salida).
- **Calidad:** suite de **tests** (`pytest tests/`, 34 casos) y **CLI** de demo
  (`python -m trust_sources`). El clásico y los tests corren **sin API**; los
  experimentos son reproducibles offline desde los caches (por modelo).
- **Pendiente:** nada que bloquee. Solo una variante opcional (cross-model con
  Gemini, 2/16 por cuota) cuya pregunta ya está contestada. Ver
  [PENDIENTES.md](https://github.com/mateoboerr/seminario_lunes/blob/main/PENDIENTES.md).

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
