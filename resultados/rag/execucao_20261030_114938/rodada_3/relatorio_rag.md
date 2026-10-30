# RAG — oito perguntas de avaliação (RF19 e RF23)

Execução: 2026-10-30T11:54:50-04:00  
top-k: 15  
Configuração de geração: forte

A conferência é automática. Confirme manualmente se cada afirmação decorre dos trechos citados.

## Métricas

| Métrica | Resultado |
|---|---:|
| Status igual ao esperado | 8/8 |
| Respondíveis aprovadas (status, elementos, citações verificadas) | 3/5 |
| Abstenção correta nas perguntas sem resposta | 2/2 |
| Caso contraditório tratado (registrado à parte) | 1/1 |
| Tokens | 80140 |
| Custo estimado (US$) | 0.022045 |

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

Resposta: Para efetivar a matrícula, o candidato deve comparecer presencialmente ao local onde se inscreveu, conforme os endereços do Anexo I, levando 1 cópia simples e o documento original de cada item exigido: a) certificado de conclusão e histórico escolar do Ensino Médio (1º ao 3º ano) ou declaração de matrícula no ensino médio; b) documento oficial de identificação; c) CPF; d) certidão de nascimento ou casamento; e) uma foto 3x4 atual; f) comprovante de residência dos últimos três meses; g) título de eleitor; h) comprovação de quitação com a Justiça Eleitoral para maiores de 18 anos; i) prova de quitação das obrigações militares para candidatos do sexo masculino maiores de 18 anos; e j) para quem se inscreveu na reserva de vagas para pessoas com deficiência, o documento original do laudo médico emitido nos últimos 12 meses contados da publicação do edital. O documento de identificação deve estar em perfeitas condições; não são aceitos imagem digital de cópia, protocolo de emissão ou documentos ilegíveis, não identificáveis ou danificados. Candidatos estrangeiros devem apresentar visto de permanência como estudante ou RNE de residência permanente, salvo beneficiários de acordos de cooperação internacional, com prazos de estada válidos.

Justificativa: O edital exige a entrega presencial de toda a documentação do item 10.5, no local da inscrição, com uma cópia simples e a apresentação dos originais. A relação documental e as condições específicas para pessoas com deficiência e estrangeiros estão expressamente previstas nos trechos citados.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.4. Para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda a documentação listada no»
- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «a) Comprovante de Escolaridade - Certificado de conclusão e Histórico Escolar do Ensino Médio (1º ao 3º ano), ou declaração de matrícula no ensino médio. b) Documento Oficial de Identificação; c) CPF;»
- `ACV-01-p10-s1-c4` — ACV-01 (Edital original), página 10: «Certidão de Casamento; e) 01 (uma) foto 3x4 atual; f) Comprovante de Residência atual (últimos 3 (três) meses); g) Título de Eleitor; h) Comprovação de quitação com a Justiça Eleitoral, para maiores d»
- `ACV-01-p3-s1-c2` — ACV-01 (Edital original), página 3: «3.9. O candidato aprovado para as vagas L4 (reservadas às Pessoas com Deficiência (PcD), ou seu procurador legalmente constituído) deverá entregar no ato de matrícula, além dos documentos citados no s»
- `ACV-01-p11-s1-c2` — ACV-01 (Edital original), página 11: «Não será efetivada a matrícula de estudante estrangeira/o sem o visto de permanência como estudante ou sem apresentar Registro Nacional de Estrangeiro (RNE) na condição de residência permanente, salvo»
- `ACV-01-p11-s1-c3` — ACV-01 (Edital original), página 11: «10.5.2.2. O Documento Oficial de Identificação deverá estar em perfeitas condições, de forma a permitir, com clareza, a identificação da/o candidata/o e sua assinatura. 10.5.2.3. Não será aceita image»
- `ACV-01-p11-s1-c4` — ACV-01 (Edital original), página 11: «10.5.2.3. Não será aceita imagem digital de cópia do Documento Oficial de Identificação, ainda que autenticada. Nem será aceito o protocolo de emissão do Documento Oficial de Identificação.»

### P02 — Posso efetivar a matrícula a distância ou preciso ir pessoalmente?

Status: **fundamentada** · decisão: **responder**

Resposta: Para a matrícula regular, é preciso comparecer pessoalmente ao local onde você se inscreveu e apresentar toda a documentação exigida. Para vagas remanescentes, é possível procurar a escola presencialmente ou pelos canais oficiais da unidade, entre 03/07/2026 e 18/08/2026, mas a matrícula depende de vaga, conferência dos documentos, atendimento aos requisitos e validação da escola.

Justificativa: O edital determina a apresentação presencial da documentação para a efetivação da matrícula regular. A retificação específica sobre vagas remanescentes permite o contato presencial ou por canais oficiais, sem garantir a matrícula automática.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.4. Para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda a documentação listada no»
- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.5. Para a efetivação da MATRÍCULA, serão necessárias a entrega de 01 cópia simples + a apresentação do documento original conforme relação a seguir:»
- `ACV-06-p2-s1-c3` — ACV-06 (Retificação nº 05), página 2: «Os interessados deverão procurar a Escola Técnica Estadual responsável pela turma, de forma presencial ou por meio dos canais oficiais da unidade, para verificar a existência de vaga, apresentar a doc»
- `ACV-06-p2-s1-c3` — ACV-06 (Retificação nº 05), página 2: «A matrícula somente será efetivada mediante existência de vaga, conferência da documentação, atendimento aos requisitos de acesso ao curso e validação pela Escola Técnica Estadual responsável.»

### P03 — O que acontece se eu não fizer a matrícula no prazo?

Status: **fundamentada** · decisão: **responder**

Resposta: Se você não fizer a matrícula no prazo determinado, perderá o direito à vaga. Além disso, quem não apresentar toda a documentação exigida ou não comparecer para efetivar a matrícula no período estabelecido será considerado desistente, e a vaga será considerada remanescente.

Justificativa: O edital estabelece expressamente a perda do direito à vaga pelo não cumprimento do prazo e prevê a geração de vagas remanescentes quando o candidato não apresentar a documentação exigida ou não comparecer para efetivar a matrícula.

- `ACV-01-p11-s1-c5` — ACV-01 (Edital original), página 11: «10.8. O candidato que não realizar sua matrícula nos prazos determinados, perderá o direito à vaga.»
- `ACV-01-p12-s1-c3` — ACV-01 (Edital original), página 12: «Os candidatos convocados para matrícula que não apresentarem toda a documentação exigida no período estabelecido pela Escola, ou que não comparecerem para efetivação da matrícula no período pré-determ»

### P04 — Quando começam as aulas de Agropecuária em Mimoso?

Status: **fundamentada** · decisão: **responder**

Resposta: As aulas de Agropecuária em Mimoso começam em 05 de outubro de 2026.

Justificativa: A Retificação nº 06 alterou a data de início das aulas para os cursos listados no item 1.1, entre os quais consta Agropecuária em Mimoso.

- `ACV-07-p1-s1-c2` — ACV-07 (Retificação nº 06), página 1: «Fica alterada para o dia 05 de outubro de 2026 a data de início das aulas dos seguintes cursos: ... Cuiabá 
Agropecuária 
Mimoso»

### P05 — Qual é o período de efetivação das matrículas da 4ª chamada?

Status: **fundamentada** · decisão: **responder**

Resposta: O período de efetivação das matrículas da 4ª chamada é de 03/07/2026 a 08/07/2026.

Justificativa: A Retificação nº 05 substituiu o cronograma anterior no item referente à efetivação das matrículas da 4ª chamada.

- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «20 Efetivação das matrículas da 4ª chamada das vagas remanescentes 
03/07/2026 a 
08/07/2026»

### P06 — A ETEC oferece auxílio transporte ou bolsa para os alunos?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Não foi localizado, nas fontes fornecidas, trecho vigente que estabeleça a oferta, os requisitos ou o procedimento para obtenção de auxílio-transporte ou bolsa estudantil.


### P07 — Qual é o horário de atendimento da secretaria da ETEC?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Os documentos mencionam a secretaria da ETEC em procedimentos específicos, mas não informam seu horário de atendimento.


### P08 — Quando é divulgada a lista das matrículas efetivadas na 4ª chamada?

Status: **conflito** · decisão: **revisar**

Resposta: Há informações documentais divergentes. É necessária revisão humana.

Justificativa: Os documentos ACV-01 e ACV-06 trazem valores diferentes para o mesmo fato e nenhuma retificação resolve a divergência. Os documentos ACV-06 e ACV-01 divergem sobre a data de divulgação da lista de matrículas efetivadas na 4ª chamada: 09/07/2026 e 11/06/2026, respectivamente.

- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «21 Divulgação/organização das matrículas efetivadas da 4ª chamada pelas Escolas Técnicas Estaduais 
09/07/2026»
- `ACV-01-p13-s1-c1` — ACV-01 (Edital original), página 13: «c) A lista das matrículas efetivadas na 4ª chamada de vagas remanescentes serão 
divulgadas no mural das Escolas Técnicas no dia 11/06/2026.»
