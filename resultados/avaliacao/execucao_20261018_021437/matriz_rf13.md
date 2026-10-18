# RF13 — Avaliação automática dos casos (versão final do sistema)

Modelo: `gpt-6-luna` · Parâmetros: `{'idioma': 'pt'}`

Prompt: versão base `8f26fd78b436` (a mesma do RF03) acrescida da instrução de idioma da interface → `f3b898dff42f`

Notas: 2 = sem erro, 1 = erro menor, 0 = erro maior ou crítico. Linguagem e decisão final dependem da revisão humana.

| Caso | Modalidade | Fidelidade | Completude | Formato | Linguagem | Segurança | Erros | Decisão proposta | Extração |
|---|---|---|---|---|---|---|---|---|---|
| CASO-01 | texto | 2 | 2 | 2 | 2 (provisória) | 2 | nenhum | Aprovado | reaproveitada |
| CASO-02 | texto | 2 | 2 | 2 | 2 (provisória) | 2 | nenhum | Aprovado com revisão | reaproveitada |
| CASO-03 | texto | 2 | 2 | 2 | 2 (provisória) | 2 | nenhum | Aprovado | reaproveitada |
| CASO-03b | texto | 2 | 2 | 2 | 2 (provisória) | 2 | nenhum | Aprovado | reaproveitada |
| CASO-04 | texto | 2 | 2 | 2 | 2 (provisória) | 2 | nenhum | Aprovado | reaproveitada |
| CASO-05 | audio | 2 | 2 | 2 | 2 (provisória) | 2 | nenhum | Aprovado com revisão | reaproveitada |
| CASO-06 | imagem | 2 | 0 | 2 | 2 (provisória) | 2 | maior: Dado presente na entrada marcado como 'não localizado'; maior: Dado presente na entrada marcado como 'não localizado' | Nova geração | nova geração |

Taxa de aprovação (proposta): 6/7 = 86%
Taxa após correção (proposta): 6/7 = 86%

## CASO-01 — esperado × obtido

| Campo | Esperado | Obtido | Situação |
|---|---|---|---|
| solicitante | Juliana Ferreira Campos | Juliana Ferreira Campos | confere |
| protocolo | 2026-000157 | 2026-000157 | confere |
| data_solicitacao | 15/10/2026 | 15/10/2026 | confere |
| curso | Técnico em Informática | Técnico em Informática | confere |
| eixo | Informação e Comunicação | Informação e Comunicação | confere |
| carga_horaria | 1.200 horas | 1.200 horas | confere |
| turno | Vespertino | vespertino | confere |
| data_inicio | 01/02/2027 | 01/02/2027 | confere |
| regras_ciencia | Cancelamento automático se faltar, sem justificativa comprovada, nos 2 primeiros dias de aula consecutivos, ou em 3 dias de aula, consecutivos ou não, nos 10 primeiros dias de aula | O(a) solicitante declarou estar ciente de que a matrícula será cancelada automaticamente se faltar, sem justificativa comprovada, nos 2 (dois) primeiros dias de aula consecutivos, ou em 3 (três) dias de aula, consecutivos ou não, nos 10 (dez) primeiros dias de aula. | confere |
| documentos_necessarios | não localizado | não localizado | confere |
| prazo_apresentacao | não localizado | não localizado | confere |
| local_horario | não localizado | não localizado | confere |

## CASO-02 — esperado × obtido

| Campo | Esperado | Obtido | Situação |
|---|---|---|---|
| solicitante | Roberto Alves Nunes | Roberto Alves Nunes | confere |
| protocolo | não localizado | não localizado | confere |
| data_solicitacao | não localizado | não localizado | confere |
| curso | Técnico em Administração | Técnico em Administração | confere |
| eixo | Gestão e Negócios | Gestão e Negócios | confere |
| carga_horaria | 1.000 horas | 1.000 horas | confere |
| turno | não localizado | não localizado | confere |
| data_inicio | 01/02/2027 | 01/02/2027 | confere |
| regras_ciencia | não localizado | não localizado | confere |
| documentos_necessarios | não localizado | não localizado | confere |
| prazo_apresentacao | não localizado | não localizado | confere |
| local_horario | não localizado | não localizado | confere |

## CASO-03 — esperado × obtido

| Campo | Esperado | Obtido | Situação |
|---|---|---|---|
| solicitante | Patrícia Souza Ramos | Patrícia Souza Ramos | confere |
| protocolo | 2026-000163 | 2026-000163 | confere |
| data_solicitacao | 16/10/2026 | 16/10/2026 | confere |
| curso | Técnico em Segurança do Trabalho | Técnico em Segurança do Trabalho | confere |
| eixo | Segurança | Segurança | confere |
| carga_horaria | 1.200 horas | 1.200 horas | confere |
| turno | Noturno | noturno | confere |
| data_inicio | 01/02/2027 | 01/02/2027 | confere |
| regras_ciencia | Cancelamento se faltar, sem justificativa, nos 2 primeiros dias de aula consecutivos ou em 3 dias, consecutivos ou não, nos 10 primeiros dias | O(a) solicitante declarou estar ciente de que a matrícula será cancelada se faltar, sem justificativa, nos 2 primeiros dias de aula consecutivos ou em 3 dias, consecutivos ou não, nos 10 primeiros dias. | confere |
| documentos_necessarios | não localizado | não localizado | confere |
| prazo_apresentacao | não localizado | não localizado | confere |
| local_horario | não localizado | não localizado | confere |

## CASO-03b — esperado × obtido

| Campo | Esperado | Obtido | Situação |
|---|---|---|---|
| solicitante | Renata Lima Duarte | Renata Lima Duarte | confere |
| protocolo | 2026-000171 | 2026-000171 | confere |
| data_solicitacao | 16/10/2026 | 16/10/2026 | confere |
| curso | Técnico em Edificações | Técnico em Edificações | confere |
| eixo | Infraestrutura | Infraestrutura | confere |
| carga_horaria | 1.200 horas | 1.200 horas | confere |
| turno | Vespertino | vespertino | confere |
| data_inicio | 01/02/2027 | 01/02/2027 | confere |
| regras_ciencia | Cancelamento se faltar, sem justificativa, nos 2 primeiros dias de aula consecutivos ou em 3 dias, consecutivos ou não, nos 10 primeiros dias | O(a) solicitante declarou estar ciente de que a matrícula será cancelada se faltar, sem justificativa, nos 2 primeiros dias de aula consecutivos ou em 3 dias, consecutivos ou não, nos 10 primeiros dias. | confere |
| documentos_necessarios | não localizado | não localizado | confere |
| prazo_apresentacao | não localizado | não localizado | confere |
| local_horario | não localizado | não localizado | confere |

## CASO-04 — esperado × obtido

| Campo | Esperado | Obtido | Situação |
|---|---|---|---|
| solicitante | Marcos Vinícius de Almeida Santos | Marcos Vinícius de Almeida Santos | confere |
| protocolo | 2026-000142 | 2026-000142 | confere |
| data_solicitacao | 14/10/2026 | 14/10/2026 | confere |
| curso | Técnico em Enfermagem | Técnico em Enfermagem | confere |
| eixo | Saúde | Saúde | confere |
| carga_horaria | 1.200 horas | 1200 horas | confere |
| turno | Noturno | noturno | confere |
| data_inicio | 01/02/2027 | 01/02/2027 | confere |
| regras_ciencia | Cancelamento automático se faltar, sem justificativa comprovada, nos 2 primeiros dias de aula consecutivos ou em 3 dias de aula, consecutivos ou não, nos 10 primeiros dias de aula | O solicitante declarou estar ciente de que a matrícula será automaticamente cancelada se faltar, sem justificativa comprovada, nos dois primeiros dias de aula consecutivos ou em três dias de aula, consecutivos ou não, nos dez primeiros dias de aula. | confere |
| documentos_necessarios | não localizado | não localizado | confere |
| prazo_apresentacao | não localizado | não localizado | confere |
| local_horario | não localizado | não localizado | confere |

## CASO-05 — esperado × obtido

| Campo | Esperado | Obtido | Situação |
|---|---|---|---|
| solicitante | Marcos Vinícius de Almeida Santos | Marcos Vinícius de Almeida Santos | confere |
| protocolo | 2026-000142 | 2026-000142 | confere |
| data_solicitacao | 14/10/2026 | 14/10/2026 | confere |
| curso | Técnico em Enfermagem | técnico em enfermagem | confere |
| eixo | Saúde | Saúde | confere |
| carga_horaria | 1.200 horas | 1.200 horas | confere |
| turno | Noturno | noturno | confere |
| data_inicio | não localizado | não localizado | confere |
| regras_ciencia | Cancelamento automático se faltar, sem justificativa comprovada, nos 2 primeiros dias de aula consecutivos, ou em 3 dias de aula, consecutivos ou não, nos 10 primeiros dias de aula | O solicitante declarou estar ciente de que a matrícula será cancelada automaticamente se faltar sem justificativa comprovada nos dois primeiros dias de aula consecutivos ou em três dias de aula consecutivos ou não nos dez primeiros dias de aula. | confere |
| documentos_necessarios | não localizado | não localizado | confere |
| prazo_apresentacao | não localizado | não localizado | confere |
| local_horario | não localizado | não localizado | confere |

Entrada de áudio ou imagem: nome, protocolo e datas exigem conferência humana.

## CASO-06 — esperado × obtido

| Campo | Esperado | Obtido | Situação |
|---|---|---|---|
| solicitante | Marcus Vinicius de Almeida Santos | MARCUS VINICIUS DE ALMEIDA SANTOS | confere |
| protocolo | 2026-000142 | não localizado | omitido |
| data_solicitacao | 14/10/2026 | não localizado | omitido |
| curso | Técnico em Enfermagem | TÉCNICO EM ENFERMAGEM | confere |
| eixo | Saúde | SAÚDE | confere |
| carga_horaria | 1.200 horas | 1.200 HORAS | confere |
| turno | Noturno | NOTURNO | confere |
| data_inicio | 01/02/2027 | 01/02/2027 | confere |
| regras_ciencia | Cancelamento automático se faltar, sem justificativa comprovada, nos 2 primeiros dias de aula consecutivos, ou em 3 dias de aula, consecutivos ou não, no período dos 10 primeiros dias de aula (caixa de ciência marcada) | O solicitante declarou estar ciente de que a matrícula será automaticamente cancelada se faltar, sem justificativa comprovada, nos 02 (dois) primeiros dias de aula consecutivos ou 03 (três) dias de aula, consecutivos ou não, no período dos 10 (dez) primeiros dias de aula. | confere |
| documentos_necessarios | não localizado | não localizado | confere |
| prazo_apresentacao | não localizado | não localizado | confere |
| local_horario | não localizado | não localizado | confere |

Entrada de áudio ou imagem: nome, protocolo e datas exigem conferência humana.
