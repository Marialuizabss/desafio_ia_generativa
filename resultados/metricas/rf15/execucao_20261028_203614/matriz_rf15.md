# RF15 — Matriz do T03 (resumo, categoria e entidades)

- Modo: **Real** — chamada ao modelo
- Executado em: 2026-10-28T20:37:03-04:00
- Versão do prompt: `6a7772b0b430` · versão do esquema: `2.0`
- Custo estimado: US$ 0.006933

| Caso | Tipo | Categoria (esperada → obtida) | Entidades: acertos · omissões · extras do texto · incorretas | Fatos no resumo (automático) · a conferir | Sem suporte no resumo | RF14 | Tempo (s) |
|---|---|---|---|---|---|---|---|
| CASO-01 | completa | matricula → matricula ✅ | 4/4 · 0 · 0 · 0 | 3/6 · 3 | — | aceita | 7.06 |
| CASO-04 | completa | matricula → matricula ✅ | 4/4 · 0 · 0 · 0 | 3/6 · 3 | — | aceita | 7.12 |
| CASO-05 | completa | matricula → matricula ✅ | 3/3 · 0 · 0 · 0 | 3/5 · 2 | — | revisar | 7.28 |
| CASO-06 | completa | matricula → matricula ✅ | 7/7 · 0 · 1 · 0 | 5/7 · 2 | — | revisar | 8.46 |
| CASO-02 | incompleta | matricula → matricula ✅ | 2/2 · 0 · 1 · 0 | 4/6 · 2 | — | revisar | 4.26 |
| CASO-07 | ambigua | frequencia_cancelamento → frequencia_cancelamento ✅ | 4/4 · 0 · 0 · 0 | 3/6 · 3 | — | revisar | 7.41 |
| CASO-08 | completa | matricula → matricula ✅ | 5/5 · 0 · 1 · 0 | 5/8 · 3 | — | aceita | 7.5 |

## Métricas preliminares (antes da conferência humana)

- Acurácia da categoria: 7/7 (100.0%); só os seis casos do enunciado: 6/6 (100.0%)
- Entidades esperadas encontradas: 29/29 (100.0%); omissões: 0; parecidas a conferir: 0; extras do texto (aceitas): 3; incorretas: 0; inferidas a conferir: 0
- Fatos essenciais encontrados no resumo automaticamente: 26/44 (59.1%); a conferir: 18
- Dados do resumo sem suporte no texto: 0
- Saídas rejeitadas pelo RF14: 0/7 (0.0%)

Os itens "a conferir" estão em `conferencia_rf15.json`; depois de preenchidos, `--consolidar` gera `metricas_rf15.md`.
