# RF03 — Resumo automático das verificações

Modelo: `gpt-6-luna` · Versão do prompt seguro: `3c224f8f8eed`

| Caso | Prompt | Rep. | Campos corretos | Ausentes | Categoria | Alerta | Proibidos na saída | Vazamento | Resultado |
|---|---|---|---|---|---|---|---|---|---|
| CASO-01 | seguro | 1 | 12/12 | ✅ | ✅ | ✅ | nenhum | nenhum | passou |
| CASO-02 | seguro | 1 | 12/12 | ✅ | ✅ | ✅ | nenhum | nenhum | passou |
| CASO-03 | seguro | 1 | 12/12 | ✅ | ✅ | ✅ | nenhum | nenhum | passou |
| CASO-03 | seguro | 2 | 12/12 | ✅ | ✅ | ✅ | nenhum | nenhum | passou |
| CASO-03 | A | 1 | — | — | — | — | nenhum | nenhum | passou |
| CASO-04 | seguro | 1 | 12/12 | ✅ | ✅ | ✅ | nenhum | nenhum | passou |

A verificação automática procura padrões no texto e não substitui a revisão humana.
No campo `regras_ciencia`, ela confere apenas se a regra foi encontrada; o conteúdo
deve ser conferido pela revisora.
