# RAG — oito perguntas de avaliação (RF19 e RF23)

Execução: 2026-10-30T11:04:14-04:00  
top-k: 15  
Configuração de geração: principal

A conferência é automática. Confirme manualmente se cada afirmação decorre dos trechos citados.

## Métricas

| Métrica | Resultado |
|---|---:|
| Status igual ao esperado | 7/8 |
| Respondíveis aprovadas (status, elementos, citações verificadas) | 2/5 |
| Abstenção correta nas perguntas sem resposta | 2/2 |
| Caso contraditório tratado (registrado à parte) | 0/1 |
| Tokens | 44770 |
| Custo estimado (US$) | 0.007455 |

## Por pergunta

| Pergunta | Tipo | Esperado | Obtido | Aprovada | Verificações que falharam |
|---|---|---|---|---|---|
| P01 | respondivel | fundamentada | fundamentada | sim | - |
| P02 | respondivel | fundamentada | fundamentada | nao | elementos_na_resposta |
| P03 | respondivel | fundamentada | fundamentada | nao | citacoes_rastreaveis |
| P04 | respondivel | fundamentada | fundamentada | nao | citacoes_rastreaveis |
| P05 | respondivel | fundamentada | fundamentada | sim | - |
| P06 | sem_resposta | sem_evidencia | sem_evidencia | sim | - |
| P07 | sem_resposta | sem_evidencia | sem_evidencia | sim | - |
| P08 | contraditoria | conflito | fundamentada | nao | status_correto, decisao_correta, divergencia_apresentada, cita_os_dois_documentos |

## Respostas e fontes

### P01 — Quais documentos preciso apresentar para efetivar a matrícula?

Status: **fundamentada** · decisão: **responder**

Resposta: Para efetivar a matrícula, o candidato deve apresentar os seguintes documentos: 01 cópia simples + o original de: Comprovante de Escolaridade, Documento Oficial de Identificação, CPF, Certidão de Nascimento ou Casamento, 01 foto 3x4 atual e Comprovante de Residência atual.

Justificativa: As informações sobre os documentos necessários para a matrícula estão claramente especificadas no edital original, conforme o item 10.5.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.5. Para a efetivação da MATRÍCULA, serão necessárias a entrega de 01 cópia simples + a apresentação do documento original conforme relação a seguir: a) Comprovante de Escolaridade - Certificado de »

### P02 — Posso efetivar a matrícula a distância ou preciso ir pessoalmente?

Status: **fundamentada** · decisão: **responder**

Resposta: É necessário comparecer pessoalmente para efetivar a matrícula.

Justificativa: O edital especifica que a efetivação da matrícula requer a apresentação presencial de toda a documentação listada.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.4. Para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda a documentação listada no»

### P03 — O que acontece se eu não fizer a matrícula no prazo?

Status: **fundamentada** · decisão: **responder**

Resposta: Se você não fizer a matrícula no prazo, perderá o direito à vaga.

Justificativa: O edital estabelece que os candidatos convocados para matrícula que não comparecerem no período determinado serão considerados desistentes e perderão o direito à matrícula.

- `ACV-01-p12-s1-c3` — ACV-01 (Edital original), página 12: «os candidatos convocados para matrícula que não apresentarem toda a documentação exigida no período estabelecido pela Escola, ou que não comparecerem para efetivação da matrícula no período pré-determ»
- `ACV-01-p11-s1-c5` — ACV-01 (Edital original), página 11: «O candidato que não realizar sua matrícula nos prazos determinados, perderá o direito à vaga.»

### P04 — Quando começam as aulas de Agropecuária em Mimoso?

Status: **fundamentada** · decisão: **responder**

Resposta: As aulas de Agropecuária em Mimoso começam no dia 05 de outubro de 2026.

Justificativa: A informação é suportada pela retificação do Edital nº 006/2026/SECITECI-MT, que estabelece a nova data de início das aulas.

- `ACV-07-p1-s1-c2` — ACV-07 (Retificação nº 06), página 1: «Fica alterada para o dia 05 de outubro de 2026 a data de início das aulas dos seguintes cursos: ... Agropecuária ... Mimoso ...»

### P05 — Qual é o período de efetivação das matrículas da 4ª chamada?

Status: **fundamentada** · decisão: **responder**

Resposta: O período de efetivação das matrículas da 4ª chamada é de 03/07/2026 a 08/07/2026.

Justificativa: A informação sobre o período de efetivação das matrículas da 4ª chamada está claramente especificada no documento ACV-06, que é a versão mais recente e vigente.

- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «20 Efetivação das matrículas da 4ª chamada das vagas remanescentes 03/07/2026 a 08/07/2026»

### P06 — A ETEC oferece auxílio transporte ou bolsa para os alunos?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Nenhum dos documentos analisados menciona auxílio transporte ou bolsa para os alunos.


### P07 — Qual é o horário de atendimento da secretaria da ETEC?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Nenhum dos documentos disponíveis contém informações sobre o horário de atendimento da secretaria da ETEC.


### P08 — Quando é divulgada a lista das matrículas efetivadas na 4ª chamada?

Status: **fundamentada** · decisão: **responder**

Resposta: A lista das matrículas efetivadas na 4ª chamada será divulgada no dia 09/07/2026.

Justificativa: O documento ACV-06, que é a retificação mais recente, estabelece que a divulgação/organização das matrículas efetivadas da 4ª chamada ocorrerá em 09/07/2026.

- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «21 Divulgação/organização das matrículas efetivadas da 4ª chamada pelas Escolas Técnicas Estaduais 09/07/2026»
