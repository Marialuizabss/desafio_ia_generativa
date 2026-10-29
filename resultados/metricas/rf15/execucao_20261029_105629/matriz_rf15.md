# RF15 — Matriz do T03 (resumo, categoria e entidades)

- Modo: **Real** — chamada ao modelo
- Executado em: 2026-10-29T10:57:15-04:00
- Prompt: `prompts/desafio2/extracao_v2.1.md` (versão `c72216a916fc`) · versão do esquema: `2.0`
- Custo estimado: US$ 0.006799

| Caso | Tipo | Categoria (esperada → obtida) | Entidades: acertos · omissões · extras do texto · incorretas | Fatos no resumo (automático) · a conferir | Sem suporte no resumo | RF14 | Tempo (s) |
|---|---|---|---|---|---|---|---|
| CASO-01 | completa | matricula → matricula ✅ | 4/4 · 0 · 0 · 0 | 4/6 · 2 | — | aceita | 8.04 |
| CASO-04 | completa | matricula → matricula ✅ | 4/4 · 0 · 1 · 0 | 4/6 · 2 | — | aceita | 6.49 |
| CASO-05 | completa | matricula → matricula ✅ | 3/3 · 0 · 0 · 0 | 3/5 · 2 | — | revisar | 6.52 |
| CASO-06 | completa | matricula → matricula ✅ | 7/7 · 0 · 0 · 0 | 6/7 · 1 | — | revisar | 8.16 |
| CASO-02 | incompleta | matricula → matricula ✅ | 2/2 · 0 · 0 · 0 | 4/6 · 2 | — | revisar | 4.17 |
| CASO-07 | ambigua | frequencia_cancelamento → frequencia_cancelamento ✅ | 4/4 · 0 · 0 · 0 | 3/6 · 3 | — | revisar | 6.63 |
| CASO-08 | completa | matricula → matricula ✅ | 5/5 · 0 · 0 · 0 | 6/8 · 2 | — | aceita | 5.57 |

## Métricas preliminares (antes da conferência humana)

- Acurácia da categoria: 7/7 (100.0%); só os seis casos do enunciado: 6/6 (100.0%)
- Entidades esperadas encontradas: 29/29 (100.0%); omissões: 0; parecidas a conferir: 0; extras do texto (aceitas): 1; incorretas: 0; inferidas a conferir: 0
- Fatos essenciais encontrados no resumo automaticamente: 30/44 (68.2%); a conferir: 14
- Dados do resumo sem suporte no texto: 0
- Saídas rejeitadas pelo RF14: 0/7 (0.0%)

Os itens "a conferir" estão em `conferencia_rf15.json`; depois de preenchidos, `--consolidar` gera `metricas_rf15.md`.
