# RAG — 3 execuções das oito perguntas (RF19 e RF23)

top-k: 15. Cada linha mostra em quantas das 3 execuções a pergunta foi aprovada.
O modelo responde de forma diferente a cada chamada, então uma execução isolada engana.

| Pergunta | Tipo | Esperado | Aprovada em | Status correto em | Status obtidos | Falhas mais comuns |
|---|---|---|---:|---:|---|---|
| P01 | respondivel | fundamentada | 0/3 | 3/3 | fundamentada, fundamentada, fundamentada | elementos_na_resposta (3x) |
| P02 | respondivel | fundamentada | 0/3 | 3/3 | fundamentada, fundamentada, fundamentada | elementos_na_resposta (3x) |
| P03 | respondivel | fundamentada | 3/3 | 3/3 | fundamentada, fundamentada, fundamentada | - |
| P04 | respondivel | fundamentada | 3/3 | 3/3 | fundamentada, fundamentada, fundamentada | - |
| P05 | respondivel | fundamentada | 2/3 | 2/3 | fundamentada, fundamentada, conflito | status_correto (1x), decisao_correta (1x), elementos_na_resposta (1x) |
| P06 | sem_resposta | sem_evidencia | 3/3 | 3/3 | sem_evidencia, sem_evidencia, sem_evidencia | - |
| P07 | sem_resposta | sem_evidencia | 3/3 | 3/3 | sem_evidencia, sem_evidencia, sem_evidencia | - |
| P08 | contraditoria | conflito | 1/3 | 3/3 | conflito, conflito, conflito | divergencia_apresentada (2x), cita_os_dois_documentos (2x) |

Aprovadas por rodada (de 8): [6, 5, 4]  
Status correto por rodada (de 8): [8, 8, 7]
