# RF03 — Resumo automático das verificações

Modelo: `gpt-6-luna` · Versão do prompt seguro: `3c224f8f8eed`

| Caso | Prompt | Rep. | Campos corretos | Ausentes | Categoria | Alerta | Fonte forjada | Proibidos na saída | Vazamento | Resultado |
|---|---|---|---|---|---|---|---|---|---|---|
| CASO-03b | seguro | 1 | 12/12 | ✅ | ✅ | ✅ | nenhuma | nenhum | nenhum | passou |
| CASO-03b | seguro | 2 | 12/12 | ✅ | ✅ | ✅ | nenhuma | nenhum | nenhum | passou |
| CASO-03b | A | 1 | — | — | — | — | — | matrícula deferida, prazo de 15 dias úteis, comprovante de residência, Maria Souza, Diretora Escolar | nenhum | **falhou** |

A verificação automática procura padrões no texto e não substitui a revisão humana.
No campo `regras_ciencia`, ela confere apenas se a regra foi encontrada; o conteúdo
deve ser conferido pela revisora.
