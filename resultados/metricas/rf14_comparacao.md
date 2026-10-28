# RF14 — JSON sintático × esquema × regras de negócio (T01)

- Executado em: 2026-10-28T19:40:55-04:00
- Caso base: CASO-08 (`dados/originais/caso8_solicitacao_coerente_acervo.txt`), extração correta montada a partir do gabarito
- Data mínima da solicitação (abertura do processo, lida do acervo): 2026-03-31
- Chamou a API: não — as saídas do modelo são simuladas para isolar cada tipo de erro

De 8 versões, `json.loads` aceitou **7**, o esquema aceitou **3** e as regras de negócio aceitaram **1**: JSON válido não garante esquema válido, e esquema válido não garante dado correto.

| Versão | Defeito | `json.loads` | Esquema | Regras | Erros classificados | Tentativas | Decisão | Minuta |
|---|---|---|---|---|---|---|---|---|
| valida | nenhum | sim | sim | sim | — | 1 | aceita | liberada |
| chave_extra | chave "prioridade" fora do contrato | sim | **não** | — | `chave_extra:prioridade` | 2 | rejeitada | bloqueada |
| tipo_incorreto | requer_revisao como texto ("não") | sim | **não** | — | `tipo_incorreto:requer_revisao` | 2 | rejeitada | bloqueada |
| campo_obrigatorio_ausente | sem a chave "categoria" | sim | **não** | — | `campo_obrigatorio_ausente:categoria` | 2 | rejeitada | bloqueada |
| valor_fora_do_dominio | categoria "transferencia", fora das seis | sim | **não** | — | `valor_fora_do_dominio:categoria` | 2 | rejeitada | bloqueada |
| json_invalido | resposta cortada no meio | **não** | **não** | — | `json_invalido` | 2 | rejeitada | bloqueada |
| data_impossivel | data_solicitacao 31/02/2026 | sim | sim | **não** | `data_impossivel:data_solicitacao` | 1 | revisar | bloqueada |
| dado_nao_presente_no_original | protocolo 2026-000999, que não está no texto | sim | sim | **não** | `dado_nao_presente_no_original:protocolo` | 1 | revisar | bloqueada |

Erro de sintaxe ou de esquema gera uma nova tentativa (2 no total); como a saída simulada repete o erro,
a versão é rejeitada. Regra de negócio violada não gera nova tentativa: o caso vai para revisão.
Nos dois casos a minuta fica bloqueada.
