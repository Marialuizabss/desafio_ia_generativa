# RAG — oito perguntas de avaliação (RF19 e RF23)

Execução: 2026-10-30T00:44:11-04:00  
top-k: 15  
Configuração de geração: principal

A conferência é automática. Confirme manualmente se cada afirmação decorre dos trechos citados.

## Métricas

| Métrica | Resultado |
|---|---:|
| Status igual ao esperado | 6/8 |
| Respondíveis aprovadas (status, elementos, citações verificadas) | 1/5 |
| Abstenção correta nas perguntas sem resposta | 2/2 |
| Caso contraditório tratado (registrado à parte) | 1/1 |
| Tokens | 36473 |
| Custo estimado (US$) | 0.006141 |

## Por pergunta

| Pergunta | Tipo | Esperado | Obtido | Aprovada | Verificações que falharam |
|---|---|---|---|---|---|
| P01 | respondivel | fundamentada | sem_evidencia | nao | status_correto, decisao_correta, elementos_na_resposta, citacoes_rastreaveis, cita_pagina_de_referencia |
| P02 | respondivel | fundamentada | fundamentada | nao | elementos_na_resposta |
| P03 | respondivel | fundamentada | fundamentada | sim | - |
| P04 | respondivel | fundamentada | fundamentada | nao | citacoes_rastreaveis |
| P05 | respondivel | fundamentada | conflito | nao | status_correto, decisao_correta, elementos_na_resposta, cita_pagina_de_referencia |
| P06 | sem_resposta | sem_evidencia | sem_evidencia | sim | - |
| P07 | sem_resposta | sem_evidencia | sem_evidencia | sim | - |
| P08 | contraditoria | conflito | conflito | sim | - |

## Respostas e fontes

### P01 — Quais documentos preciso apresentar para efetivar a matrícula?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Falha na validação: O trecho citado não foi comprovado na fonte.


### P02 — Posso efetivar a matrícula a distância ou preciso ir pessoalmente?

Status: **fundamentada** · decisão: **responder**

Resposta: É necessário comparecer pessoalmente para efetivar a matrícula.

Justificativa: O edital especifica que a efetivação da matrícula requer a apresentação presencial de toda a documentação listada.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «Para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda a documentação listada no item »

### P03 — O que acontece se eu não fizer a matrícula no prazo?

Status: **fundamentada** · decisão: **responder**

Resposta: Se você não fizer a matrícula no prazo, perderá o direito à vaga.

Justificativa: O edital estabelece que o candidato que não realizar sua matrícula nos prazos determinados perderá o direito à vaga.

- `ACV-01-p11-s1-c5` — ACV-01 (Edital original), página 11: «O candidato que não realizar sua matrícula nos prazos determinados, perderá o direito à vaga.»

### P04 — Quando começam as aulas de Agropecuária em Mimoso?

Status: **fundamentada** · decisão: **responder**

Resposta: As aulas de Agropecuária em Mimoso começam no dia 05 de outubro de 2026.

Justificativa: A data de início das aulas foi alterada conforme a retificação do edital.

- `ACV-07-p1-s1-c2` — ACV-07 (Retificação nº 06), página 1: «Fica alterada para o dia 05 de outubro de 2026 a data de início das aulas dos seguintes cursos: ... Agropecuária ... Mimoso»

### P05 — Qual é o período de efetivação das matrículas da 4ª chamada?

Status: **conflito** · decisão: **revisar**

Resposta: Há informações documentais divergentes. É necessária revisão humana.

Justificativa: Período da 4ª chamada não comprovado na ACV-06.

- `ACV-04-p2-s1-c1` — ACV-04 (Retificação nº 03), página 2: «19. Efetivação das matrículas da 4º chamada das vagas remanescentes 23 e 24/07/2026»

### P06 — A ETEC oferece auxílio transporte ou bolsa para os alunos?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Nenhum dos documentos analisados menciona explicitamente a existência de auxílio transporte ou bolsa para os alunos.


### P07 — Qual é o horário de atendimento da secretaria da ETEC?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: As fontes disponíveis não contêm informações específicas sobre o horário de atendimento da secretaria da ETEC.


### P08 — Quando é divulgada a lista das matrículas efetivadas na 4ª chamada?

Status: **conflito** · decisão: **revisar**

Resposta: Há informações documentais divergentes. É necessária revisão humana.

Justificativa: ACV-01 (item 11.3.1) informa 11/06/2026; ACV-06 (item 5) informa 09/07/2026. Os escopos catalogados não resolvem a divergência.

- `ACV-01-p13-s1-c1` — ACV-01 (Edital original), página 13: «13 
b) A entrega dos documentos não garante a matrícula do candidato, que será efetivada 
em obediência a ordem classificatória do resultado final do Processo Seletivo divulgado 
no dia 11/06/2026. 
c»
- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «Nº 
Descrição/Ação 
Período/Data 
19 Convocação antecipada dos classificados para vagas 
remanescentes – 4ª chamada conforme item 11.3.1 
03/07/2026 
20 Efetivação das matrículas da 4ª chamada das vag»
