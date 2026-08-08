# Pendientes

Checklist vivo de lo que falta. Estado general y detalle en
[docs/roadmap.md](docs/roadmap.md) y la [bitácora](docs/experimentos.md).

## 🟠 Queda UNA celda, y espera cuota de Gemini

El 2026-08-08 la cuota volvió y se completaron dos de las tres pendientes:

- [x] **`v3_justifica` de Gemini** → 16/16, **F1 0.74**: resultó la *mejor*
      variante de Gemini y achicó la brecha con Sonnet de +0.30 a +0.07.
- [x] **v1 a nivel de span con Gemini** → 16/16, **span-F1 0.54**: empata con
      Sonnet.
- [ ] **Multi-LLM cross-model — parcial 2/16.** `gemini` extrae afirmaciones +
      `sonnet` asigna (la lectura literal de la propuesta del profe).
      `python -m experiments.exp3_multi_llm`

**Cómo completar la que falta.** El free tier diario de Gemini rinde ~23
llamadas; ese día se las llevaron exp1 (8) y exp2 (13) y exp3 entró solo 2 veces.
En la próxima ventana hay que **correr exp3 primero** (necesita 16). El cache
retoma solo; después re-correr `python -m experiments.viz_matriz`.

**Alternativa sin esperar:** poner `claude-haiku-4-5` como modelo de la etapa 1.
Cumple el mismo rol conceptual (barato en la etapa fácil, caro en la difícil) por
centavos y corre hoy, aunque deja de ser la comparación literal con Gemini.

**Nota de método para el próximo intento:** un ping suelto no dice nada sobre la
cuota — el 2026-08-07 respondió OK y la tanda igual murió en 429 a la primera
llamada. Hay que mirar si aguanta una tanda.

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
