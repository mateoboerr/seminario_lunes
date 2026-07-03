# Pendientes

Checklist vivo de lo que falta. Estado general y detalle en
[docs/roadmap.md](docs/roadmap.md) y la [bitácora](docs/experimentos.md).

## 🔴 Requiere Anthropic (el free tier de Gemini no alcanza)

Poné la key en `.env` y elegí proveedor (ver [README](README.md#instalación-y-uso)):
```
ANTHROPIC_API_KEY=...
LLM_PROVIDER=anthropic
```
Cada script retoma desde su cache (solo llama lo que falta):

- [ ] **Etapa 1 — completar variantes de prompt.** `python -m experiments.exp1_prompts`
      → llena `v2_reglas_duras` (8/16) y `v3_justifica` (2/16) y actualiza la tabla
      comparativa + el gráfico.
- [ ] **Etapa 2 — span-F1 de v1 en vivo.** `python -m experiments.exp2_salida_v1`
      → mide `LLMSourceDetectorV1` a nivel de span y lo compara contra el **baseline
      clásico (global F1 0.39; Referenciado 0.09)**.
- [ ] **Etapa 3 — multi-LLM vs single-pass.** `python -m experiments.exp3_multi_llm`
      → corre el pipeline de 2 pasadas y lo compara contra v1. Decidir cuál conviene.
- [ ] **Volcar los números nuevos a la bitácora** (`docs/experimentos.md`) y a las
      tablas de `docs/index.md`.

## 🟡 Mejoras de modelado (código + medición)

- [ ] **Citas implícitas:** evaluar aparte las fuentes con `explicit=false` (hoy se
      capturan pero no se miden por separado).
- [ ] **Relación afirmación↔fuente:** hoy está implícita dentro de cada `Source`;
      modelarla/evaluarla de forma explícita si aporta.
- [ ] **Comparar modelos** (Etapa 1, punto 3): correr las variantes con distintos
      modelos (el harness ya lo soporta vía `make_client(model=...)`).

## 🟢 Opcionales / cosméticos

- [ ] **Landing curado en la Page:** cambiar en GitHub *Settings → Pages → Source* a
      la carpeta `/docs` para que la home sea `docs/index.md` (tema Cayman + tabla de
      experimentos al frente) en vez del README. Es un clic; el `docs/_config.yml` ya
      está listo para eso.
- [ ] **Integración end-to-end a Trust:** el `TrustSourceAdapter` ya expone la
      interfaz `get_explicit_sources`; enchufarlo en el pipeline real de Trust
      requiere su entorno (usa stanza, que acá no baja por SSL).

## ✅ Hecho (para referencia)

v0 (benchmark) · Etapa 1 v0-vs-v1 medido · Etapa 2 salida rica v1 (código + eval de
spans + baseline clásico) · Etapa 3 pipeline multi-LLM · Etapa 4 adaptador a Trust ·
29 tests + CLI (sin API) · GitHub Page en vivo.
