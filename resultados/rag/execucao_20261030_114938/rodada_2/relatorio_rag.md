# RAG — oito perguntas de avaliação (RF19 e RF23)

Execução: 2026-10-30T11:53:14-04:00  
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
| Tokens | 79711 |
| Custo estimado (US$) | 0.021515 |

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

Resposta: Para efetivar a matrícula, o candidato deve apresentar presencialmente, no local onde se inscreveu, conforme os endereços do Anexo I, 1 cópia simples e o documento original de cada item: a) certificado de conclusão e histórico escolar do Ensino Médio (1º ao 3º ano), ou declaração de matrícula no Ensino Médio; b) documento oficial de identificação; c) CPF; d) certidão de nascimento ou casamento; e) uma foto 3x4 atual; f) comprovante de residência dos últimos três meses; g) título de eleitor; h) comprovante de quitação com a Justiça Eleitoral para maiores de 18 anos; i) prova de quitação das obrigações militares para candidatos do sexo masculino maiores de 18 anos; e j) para quem se inscreveu na reserva de vagas para pessoas com deficiência, o documento original do laudo médico emitido nos últimos 12 meses a partir da publicação do edital. Candidatos PcD também devem observar a exigência de laudo com indicação do tipo, grau ou nível da deficiência e referência ao CID. Documentos incompatíveis, incompletos, rasurados ou falsos impedem a matrícula.

Justificativa: A matrícula exige entrega presencial no local de inscrição e apresentação de uma cópia simples acompanhada do original. A documentação deve ser apresentada integralmente. Para candidatos PcD, há exigência adicional de laudo médico dentro do prazo indicado. O edital também prevê que documentos incompatíveis, incompletos, rasurados ou falsos impossibilitam a matrícula.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «Para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda a documentação listada no item »
- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «a) Comprovante de Escolaridade - Certificado de conclusão e Histórico Escolar do Ensino Médio (1º ao 3º ano), ou declaração de matrícula no ensino médio. b) Documento Oficial de Identificação; c) CPF;»
- `ACV-01-p10-s1-c4` — ACV-01 (Edital original), página 10: «Certidão de Casamento; e) 01 (uma) foto 3x4 atual; f) Comprovante de Residência atual (últimos 3 (três) meses); g) Título de Eleitor; h) Comprovação de quitação com a Justiça Eleitoral, para maiores d»
- `ACV-01-p3-s1-c2` — ACV-01 (Edital original), página 3: «O candidato aprovado para as vagas L4 (reservadas às Pessoas com Deficiência (PcD), ou seu procurador legalmente constituído) deverá entregar no ato de matrícula, além dos documentos citados no subite»
- `ACV-01-p11-s1-c4` — ACV-01 (Edital original), página 11: «Caso as documentações apresentadas sejam identificadas como incompatíveis, incompletas, rasuradas ou falsas, será invalidada a aprovação do candidato no Processo Seletivo e será impossibilitada a sua »

### P02 — Posso efetivar a matrícula a distância ou preciso ir pessoalmente?

Status: **fundamentada** · decisão: **responder**

Resposta: Para a matrícula regular, é necessário comparecer pessoalmente ao local onde você se inscreveu; não é prevista efetivação integral a distância. É obrigatório apresentar nesse local toda a documentação do item 10.5, com 1 cópia simples e o documento original. Para vagas remanescentes, é possível usar os canais oficiais da unidade para verificar a existência de vaga e manifestar interesse, mas a matrícula só será efetivada se houver vaga, conferência da documentação, atendimento aos requisitos e validação pela Escola Técnica.

Justificativa: O edital exige expressamente a apresentação presencial da documentação para efetivação da matrícula regular. A retificação posterior trata especificamente das vagas remanescentes e permite contato presencial ou pelos canais oficiais para verificar vaga e manifestar interesse, mas condiciona a efetivação à disponibilidade de vaga, à conferência documental, ao atendimento dos requisitos e à validação da unidade.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.4. Para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda a documentação listada no»
- `ACV-06-p2-s1-c3` — ACV-06 (Retificação nº 05), página 2: «11.3.2.3. Os interessados deverão procurar a Escola Técnica Estadual responsável pela turma, de forma presencial ou por meio dos canais oficiais da unidade, para verificar a existência de vaga, aprese»
- `ACV-06-p2-s1-c3` — ACV-06 (Retificação nº 05), página 2: «11.3.2.4. A matrícula somente será efetivada mediante existência de vaga, conferência da documentação, atendimento aos requisitos de acesso ao curso e validação pela Escola Técnica Estadual responsáve»

### P03 — O que acontece se eu não fizer a matrícula no prazo?

Status: **fundamentada** · decisão: **responder**

Resposta: Se você for convocado e não apresentar toda a documentação exigida no período estabelecido ou não comparecer para efetivar a matrícula no prazo, será considerado desistente, perderá o direito à matrícula e sua vaga será considerada remanescente. De forma geral, quem não realizar a matrícula nos prazos determinados perderá o direito à vaga.

Justificativa: O edital estabelece expressamente as consequências do não cumprimento do prazo de matrícula e prevê a geração de vagas remanescentes.

- `ACV-01-p12-s1-c3` — ACV-01 (Edital original), página 12: «Os candidatos convocados para matrícula que não apresentarem toda a documentação exigida no período estabelecido pela Escola, ou que não comparecerem para efetivação da matrícula no período pré-determ»
- `ACV-01-p11-s1-c5` — ACV-01 (Edital original), página 11: «10.8. O candidato que não realizar sua matrícula nos prazos determinados, perderá o direito à vaga.»

### P04 — Quando começam as aulas de Agropecuária em Mimoso?

Status: **fundamentada** · decisão: **responder**

Resposta: As aulas de Agropecuária em Mimoso começam em 05 de outubro de 2026.

Justificativa: A Retificação nº 06 alterou a data de início das aulas para 05 de outubro de 2026 e incluiu o curso de Agropecuária em Mimoso entre os cursos abrangidos.

- `ACV-07-p1-s1-c2` — ACV-07 (Retificação nº 06), página 1: «1.1. Fica alterada para o dia 05 de outubro de 2026 a data de início das aulas dos seguintes cursos: ... Cuiabá 
Agropecuária 
Mimoso»

### P05 — Qual é o período de efetivação das matrículas da 4ª chamada?

Status: **fundamentada** · decisão: **responder**

Resposta: O período de efetivação das matrículas da 4ª chamada é de 03/07/2026 a 08/07/2026.

Justificativa: A Retificação nº 05 do ACV-06, de ordem mais recente, substituiu o período anterior e estabelece o novo período de efetivação das matrículas da 4ª chamada.

- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «20 Efetivação das matrículas da 4ª chamada das vagas remanescentes 
03/07/2026 a 
08/07/2026»

### P06 — A ETEC oferece auxílio transporte ou bolsa para os alunos?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Os trechos disponibilizados tratam de inscrições, distribuição de vagas, matrícula, desistência, trancamento, faltas e pesquisa socioeconômica, mas não apresentam regra vigente sobre auxílio-transporte ou bolsa estudantil.


### P07 — Qual é o horário de atendimento da secretaria da ETEC?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Os documentos mencionam procedimentos realizados na secretaria da ETEC, mas não informam seu horário de atendimento.


### P08 — Quando é divulgada a lista das matrículas efetivadas na 4ª chamada?

Status: **conflito** · decisão: **revisar**

Resposta: Há informações documentais divergentes. É necessária revisão humana.

Justificativa: Os documentos ACV-01 e ACV-06 trazem valores diferentes para o mesmo fato e nenhuma retificação resolve a divergência. O ACV-06 informa divulgação em 09/07/2026, enquanto o ACV-01 informa divulgação em 11/06/2026 para a lista das matrículas efetivadas na 4ª chamada.

- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «21 Divulgação/organização das matrículas efetivadas da 4ª chamada pelas Escolas Técnicas Estaduais 
09/07/2026»
- `ACV-01-p13-s1-c1` — ACV-01 (Edital original), página 13: «c) A lista das matrículas efetivadas na 4ª chamada de vagas remanescentes serão divulgadas no mural das Escolas Técnicas no dia 11/06/2026.»
