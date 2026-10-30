# RAG — oito perguntas de avaliação (RF19 e RF23)

Execução: 2026-10-30T11:42:10-04:00  
top-k: 15  
Configuração de geração: principal

A conferência é automática. Confirme manualmente se cada afirmação decorre dos trechos citados.

## Métricas

| Métrica | Resultado |
|---|---:|
| Status igual ao esperado | 8/8 |
| Respondíveis aprovadas (status, elementos, citações verificadas) | 3/5 |
| Abstenção correta nas perguntas sem resposta | 2/2 |
| Caso contraditório tratado (registrado à parte) | 1/1 |
| Tokens | 76495 |
| Custo estimado (US$) | 0.012661 |

## Por pergunta

| Pergunta | Tipo | Esperado | Obtido | Aprovada | Alertas | Verificações que falharam |
|---|---|---|---|---|---:|---|
| P01 | respondivel | fundamentada | fundamentada | nao | 1 | elementos_na_resposta |
| P02 | respondivel | fundamentada | fundamentada | nao | 1 | elementos_na_resposta |
| P03 | respondivel | fundamentada | fundamentada | sim | 1 | - |
| P04 | respondivel | fundamentada | fundamentada | sim | 0 | - |
| P05 | respondivel | fundamentada | fundamentada | sim | 0 | - |
| P06 | sem_resposta | sem_evidencia | sem_evidencia | sim | 0 | - |
| P07 | sem_resposta | sem_evidencia | sem_evidencia | sim | 0 | - |
| P08 | contraditoria | conflito | conflito | sim | 1 | - |

## Respostas e fontes

### P01 — Quais documentos preciso apresentar para efetivar a matrícula?

Status: **fundamentada** · decisão: **responder**

Resposta: Para efetivar a matrícula, o candidato deve apresentar os seguintes documentos: 1) Comprovante de Escolaridade (Certificado de conclusão e Histórico Escolar do Ensino Médio ou declaração de matrícula); 2) Documento Oficial de Identificação; 3) CPF; 4) Certidão de Nascimento ou Certidão de Casamento; 5) 01 foto 3x4 atual; 6) Comprovante de Residência atual (últimos 3 meses).

Justificativa: As informações sobre os documentos necessários para a matrícula estão claramente especificadas no edital vigente, conforme os trechos citados.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.5. Para a efetivação da MATRÍCULA, serão necessárias a entrega de 01 cópia simples + a apresentação do documento original conforme relação a seguir: a) Comprovante de Escolaridade - Certificado de »
- `ACV-01-p11-s1-c3` — ACV-01 (Edital original), página 11: «10.5.2.1. NÃO serão aceitos como Documentos Oficiais de Identificação: Certidões de Nascimento, CPF, Títulos Eleitorais, Carteiras Nacional de Habilitação (modelo antigo sem foto), Carteiras de Estuda»

### P02 — Posso efetivar a matrícula a distância ou preciso ir pessoalmente?

Status: **fundamentada** · decisão: **responder**

Resposta: A matrícula deve ser efetivada presencialmente.

Justificativa: De acordo com o edital, a efetivação da matrícula requer a apresentação presencial de toda a documentação no local onde o candidato se inscreveu.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda a documentação listada no item »

### P03 — O que acontece se eu não fizer a matrícula no prazo?

Status: **fundamentada** · decisão: **responder**

Resposta: Se a matrícula não for realizada no prazo, o candidato será considerado desistente e perderá o direito à vaga.

Justificativa: O edital estabelece que os candidatos convocados para matrícula que não apresentarem a documentação exigida ou não comparecerem no período determinado serão considerados desistentes.

- `ACV-01-p12-s1-c3` — ACV-01 (Edital original), página 12: «os candidatos convocados para matrícula que não apresentarem toda a documentação exigida no período estabelecido pela Escola, ou que não comparecerem para efetivação da matrícula no período pré-determ»
- `ACV-01-p11-s1-c5` — ACV-01 (Edital original), página 11: «O candidato que não realizar sua matrícula nos prazos determinados, perderá o direito à vaga.»

### P04 — Quando começam as aulas de Agropecuária em Mimoso?

Status: **fundamentada** · decisão: **responder**

Resposta: As aulas de Agropecuária em Mimoso começam no dia 05 de outubro de 2026.

Justificativa: A informação sobre a data de início das aulas foi confirmada na retificação do edital, que especifica a alteração para o curso de Agropecuária em Mimoso.

- `ACV-07-p1-s1-c2` — ACV-07 (Retificação nº 06), página 1: «Fica alterada para o dia 05 de outubro de 2026 a data de início das aulas dos seguintes cursos: ... Agropecuária ... Mimoso»

### P05 — Qual é o período de efetivação das matrículas da 4ª chamada?

Status: **fundamentada** · decisão: **responder**

Resposta: O período de efetivação das matrículas da 4ª chamada é de 03/07/2026 a 08/07/2026.

Justificativa: A informação sobre o período de efetivação das matrículas da 4ª chamada está claramente especificada no documento ACV-06, que é a versão mais recente e vigente.

- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «20 Efetivação das matrículas da 4ª chamada das vagas remanescentes 03/07/2026 a 08/07/2026»

### P06 — A ETEC oferece auxílio transporte ou bolsa para os alunos?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Nenhum dos documentos analisados menciona a existência de auxílio transporte ou bolsa para os alunos da ETEC.


### P07 — Qual é o horário de atendimento da secretaria da ETEC?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Nenhum dos documentos disponíveis contém informações sobre o horário de atendimento da secretaria da ETEC.


### P08 — Quando é divulgada a lista das matrículas efetivadas na 4ª chamada?

Status: **conflito** · decisão: **revisar**

Resposta: Há informações documentais divergentes. É necessária revisão humana.

Justificativa: Os documentos ACV-01 e ACV-06 trazem valores diferentes para o mesmo fato e nenhuma retificação resolve a divergência. Os documentos ACV-01 e ACV-06 divergem quanto à data de divulgação da lista das matrículas efetivadas na 4ª chamada, sendo 11/06/2026 e 09/07/2026, respectivamente.

- `ACV-01-p13-s1-c1` — ACV-01 (Edital original), página 13: «a lista das matrículas efetivadas na 4ª chamada de vagas remanescentes serão divulgadas no mural das Escolas Técnicas no dia 11/06/2026.»
- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «Nº Descrição/Ação Período/Data 19 Convocação antecipada dos classificados para vagas remanescentes – 4ª chamada conforme item 11.3.1 03/07/2026 20 Efetivação das matrículas da 4ª chamada das vagas rem»
