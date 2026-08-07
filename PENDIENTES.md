# Pendientes

Checklist vivo de lo que falta. Estado general y detalle en
[docs/roadmap.md](docs/roadmap.md) y la [bitácora](docs/experimentos.md).

## 🟠 Espera cuota de Gemini (el free tier diario se agotó el 2026-08-07)

Las corridas con `claude-sonnet-5` están completas; faltan las celdas de Gemini.
Re-correr en una ventana de cuota fresca — cada script retoma desde su cache y
solo llama lo que falta:

- [ ] **`v3_justifica` de Gemini (8/16).** `python -m experiments.exp1_prompts`
- [ ] **v1 a nivel de span con Gemini (3/16).** `python -m experiments.exp2_salida_v1`
- [ ] **Multi-LLM cross-model (0/16)** — `gemini` extrae afirmaciones + `sonnet`
      asigna fuentes (la lectura literal de la propuesta del profe).
      `python -m experiments.exp3_multi_llm`
- [ ] Tras completar: re-correr `python -m experiments.viz_matriz` (suma columnas
      nuevas) y volcar los números a la bitácora.

## 🟡 Mejoras de modelado (código + medición)

- [ ] **Relación afirmación↔fuente explícita:** hoy va implícita dentro de cada
      `Source`; modelarla/evaluarla aparte si aporta.
- [ ] **Flag `explicita` poco confiable** (Exp 4: marcó 1/94 como implícita):
      probar un prompt que defina "implícita" con ejemplos, y medir contra más
      anotación.
- [ ] **Bajar el ruido del gold:** con 16 notas, F1 > 0.85 ya no se distingue del
      desacuerdo entre anotadores. Anotar más notas (hay 106 con fuentes) es la
      única forma de seguir midiendo mejoras.

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
documentado) · Exp 4 citas implícitas (exploratorio) · matriz de aciertos/fallas ·
cache por (modelo, variante, nota) con migración · métricas de calidad separadas
de cobertura · 30 tests + CLI (sin API) · GitHub Page en vivo.
