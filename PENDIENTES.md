# Pendientes

Checklist vivo de lo que falta. Estado general y detalle en
[docs/roadmap.md](docs/roadmap.md) y la [bitácora](docs/experimentos.md).

## 🟢 Todas las preguntas del proyecto tienen respuesta

El 2026-08-08 se cerraron las tres pendientes:

- [x] **`v3_justifica` de Gemini** → 16/16, **F1 0.74**: resultó la *mejor*
      variante de Gemini y achicó la brecha con Sonnet de +0.30 a +0.07.
- [x] **v1 a nivel de span con Gemini** → 16/16, **span-F1 0.54**: empata con
      Sonnet.
- [x] **Multi-LLM cross-model** → se midió con `claude-haiku-4-5` extrayendo y
      Sonnet asignando (16/16): span-F1 **0.36**, la peor de las tres configs.
      Responde la propuesta de la cátedra y además aísla la variable (mismo
      proveedor en las dos etapas: mide "barato vs caro", no "Google vs
      Anthropic").

**Opcional, no bloquea nada:** la misma config con **Gemini** en la etapa 1 (la
lectura literal) quedó **2/16** por cuota. Agregaría un segundo punto de datos,
no una conclusión nueva. Para completarla: correr `python -m
experiments.exp3_multi_llm` **primero** en una ventana de cuota fresca (necesita
16 llamadas; el free tier rinde ~23/día y el 2026-08-08 se las llevaron exp1 y
exp2), y después `python -m experiments.viz_matriz`.

**Nota de método:** un ping suelto no dice nada sobre la cuota, el 2026-08-07
respondió OK y la tanda igual murió en 429 a la primera llamada. Hay que mirar
si aguanta una tanda.

## 🟡 Mejoras de modelado (código + medición)

- [ ] **Relación afirmación↔fuente explícita:** hoy va implícita dentro de cada
      `Source`; modelarla/evaluarla aparte si aporta.
- [ ] **Flag `explicita` poco confiable** (Exp 4: marcó 1/94 como implícita):
      probar un prompt que defina "implícita" con ejemplos, y medir contra más
      anotación.
- [ ] **Bajar el ruido del gold:** el Exp 5 ya explotó las ~75 notas
      single-anotadas como held-out (resultado: el 0.86 no generaliza, ~0.70
      real). Lo que queda es **doble anotación o adjudicación** de una muestra
      del held-out, para separar "el modelo se equivoca" de "el anotador tiene
      otro criterio" (jcc marca 2,5 fuentes/nota donde lch marca 4,4).

## 🟢 Opcionales / cosméticos

- [ ] **Landing curado en la Page:** cambiar en GitHub *Settings → Pages → Source*
      a la carpeta `/docs` para que la home sea `docs/index.md` (tema Cayman +
      tablas al frente) en vez del README. El `docs/_config.yml` ya está listo.
- [ ] **Integración end-to-end a Trust:** `TrustSourceAdapter` ya expone
      `get_explicit_sources`; enchufarlo al pipeline real de Trust requiere su
      entorno (usa stanza, que acá no baja por SSL).

## ✅ Hecho (para referencia)

v0 (benchmark) · Exp 1 completo con **dos modelos** (grilla de 4 prompts ×
Gemini/Sonnet; Sonnet 0.86) · Exp 2 span-F1 en vivo (Sonnet 0.54 vs clásico
0.39) · Exp 3 multi-LLM vs single-pass (gana single-pass; bug de truncamiento
documentado) · Exp 4 citas implícitas (exploratorio) · **Exp 5 validación
held-out (75 notas no vistas: 0.67; el 0.86 no generaliza)** · matriz de
aciertos/fallas · cache por (modelo, variante, nota) con migración · métricas de
calidad separadas de cobertura · **auditoría externa aplicada** (premisa 13/16,
claims calibrados) · Page servida desde `/docs` con anclajes verificados en vivo ·
parsers de JSON truncado unificados en `items_sueltos` · 34 tests + CLI (sin API) ·
GitHub Page en vivo.
