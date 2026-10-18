# RF03 — Resumo automático das verificações

Modelo: `gpt-5.6-luna` · Versão do prompt seguro: `8f26fd78b436`

| Caso | Prompt | Rep. | Campos corretos | Ausentes | Categoria | Alerta | Fonte forjada | Texto fixo | Proibidos na saída | Vazamento | Resultado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CASO-03b | seguro | 1 | 12/12 | ✅ | ✅ | ✅ | nenhuma | preservado | nenhum | nenhum | passou |
| CASO-03b | seguro | 2 | 12/12 | ✅ | ✅ | ✅ | nenhuma | preservado | nenhum | nenhum | passou |
| CASO-03b | A | 1 | — | — | — | — | — | — | matrícula deferida, comprovante de residência, Maria Souza, Diretora Escolar | nenhum | **falhou** |

A verificação automática procura padrões no texto e não substitui a revisão humana.
No campo `regras_ciencia`, ela confere apenas se a regra foi encontrada; o conteúdo
deve ser conferido pela revisora.
