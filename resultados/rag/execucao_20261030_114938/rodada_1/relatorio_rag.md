# RAG — oito perguntas de avaliação (RF19 e RF23)

Execução: 2026-10-30T11:51:36-04:00  
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
| Tokens | 80452 |
| Custo estimado (US$) | 0.022436 |

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

Resposta: Para efetivar a matrícula, apresente presencialmente, no local onde se inscreveu, conforme os endereços do Anexo I, 1 cópia simples e o documento original de cada item exigido: a) certificado de conclusão e histórico escolar do Ensino Médio (1º ao 3º ano), ou declaração de matrícula no ensino médio; b) documento oficial de identificação; c) CPF; d) certidão de nascimento ou casamento; e) uma foto 3x4 atual; f) comprovante de residência dos últimos três meses; g) título de eleitor; h) comprovação de quitação com a Justiça Eleitoral, para maiores de 18 anos; e i) prova de que está em dia com as obrigações militares, para candidatos do sexo masculino maiores de 18 anos. Candidatos inscritos na reserva de vagas para pessoas com deficiência devem apresentar também o documento original do laudo médico emitido nos últimos 12 meses a partir da publicação do edital. O documento oficial de identificação deve ser original, estar em perfeitas condições e permitir a identificação e a conferência da assinatura; não são aceitos imagem digital de cópia, protocolo de emissão ou documentos ilegíveis, não identificáveis ou danificados. Estudante estrangeiro deve apresentar visto de permanência como estudante ou RNE na condição de residência permanente, salvo beneficiários de acordos de cooperação internacional, com prazos de estada válidos.

Justificativa: O edital determina a apresentação presencial de toda a documentação do item 10.5, com uma cópia simples e o original. A relação documental inclui os documentos de escolaridade, identificação, CPF, certidão, foto, residência, eleitorais e militares. Há exigências adicionais para candidatos PcD e estudantes estrangeiros, além das condições de validade e aceitação do documento de identificação.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.4. Para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda a documentação listada no»
- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «a) Comprovante de Escolaridade - Certificado de conclusão e Histórico Escolar do Ensino Médio (1º ao 3º ano), ou declaração de matrícula no ensino médio. b) Documento Oficial de Identificação; c) CPF;»
- `ACV-01-p10-s1-c4` — ACV-01 (Edital original), página 10: «Certidão de Casamento; e) 01 (uma) foto 3x4 atual; f) Comprovante de Residência atual (últimos 3 (três) meses); g) Título de Eleitor; h) Comprovação de quitação com a Justiça Eleitoral, para maiores d»
- `ACV-01-p10-s1-c4` — ACV-01 (Edital original), página 10: «j) Candidatas/os que tenham se inscrito na reserva de vagas para pessoas com deficiência deverão apresentar, no ato da matrícula, o documento original do laudo médico emitido nos últimos 12 (doze) mes»
- `ACV-01-p11-s1-c2` — ACV-01 (Edital original), página 11: «Não será efetivada a matrícula de estudante estrangeira/o sem o visto de permanência como estudante ou sem apresentar Registro Nacional de Estrangeiro (RNE) na condição de residência permanente, salvo»
- `ACV-01-p11-s1-c2` — ACV-01 (Edital original), página 11: «São considerados Documentos Oficiais de Identificação: carteiras expedidas pelos Comandos Militares, pelas Secretarias de Segurança Pública, pelos Corpos de Bombeiros Militares, pelos Órgãos Fiscaliza»
- `ACV-01-p11-s1-c3` — ACV-01 (Edital original), página 11: «10.5.2.2. O Documento Oficial de Identificação deverá estar em perfeitas condições, de forma a permitir, com clareza, a identificação da/o candidata/o e sua assinatura. 10.5.2.3. Não será aceita image»
- `ACV-01-p11-s1-c4` — ACV-01 (Edital original), página 11: «10.5.2.3. Não será aceita imagem digital de cópia do Documento Oficial de Identificação, ainda que autenticada. Nem será aceito o protocolo de emissão do Documento Oficial de Identificação. 10.6. Caso»

### P02 — Posso efetivar a matrícula a distância ou preciso ir pessoalmente?

Status: **fundamentada** · decisão: **responder**

Resposta: Na matrícula regular, é preciso comparecer pessoalmente ao local onde você se inscreveu; não há previsão de efetivação totalmente a distância. Excepcionalmente, na 5ª chamada de vagas remanescentes, é possível procurar a escola presencialmente ou pelos canais oficiais, mas ainda será necessário apresentar a documentação e cumprir as demais condições.

Justificativa: O item 10.4 exige apresentação presencial no local de inscrição, com toda a documentação do item 10.5, incluindo uma cópia simples e o documento original. Para as vagas remanescentes da 5ª chamada, a retificação permite contato presencial ou por canais oficiais, mas condiciona a matrícula à existência de vaga, à conferência documental, ao atendimento dos requisitos e à validação da escola.

- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.4. Para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda a documentação listada no»
- `ACV-01-p10-s1-c3` — ACV-01 (Edital original), página 10: «10.5. Para a efetivação da MATRÍCULA, serão necessárias a entrega de 01 cópia simples + a apresentação do documento original conforme relação a seguir:»
- `ACV-06-p2-s1-c3` — ACV-06 (Retificação nº 05), página 2: «Os interessados deverão procurar a Escola Técnica Estadual responsável pela turma, de forma presencial ou por meio dos canais oficiais da unidade, para verificar a existência de vaga, apresentar a doc»
- `ACV-06-p2-s1-c3` — ACV-06 (Retificação nº 05), página 2: «A matrícula somente será efetivada mediante existência de vaga, conferência da documentação, atendimento aos requisitos de acesso ao curso e validação pela Escola Técnica Estadual responsável.»

### P03 — O que acontece se eu não fizer a matrícula no prazo?

Status: **fundamentada** · decisão: **responder**

Resposta: Se você não fizer a matrícula dentro do prazo determinado, perderá o direito à vaga. O candidato será considerado desistente, e a vaga será considerada remanescente.

Justificativa: O edital estabelece que a ausência de matrícula no prazo implica perda da vaga. Também prevê que não comparecer para efetivar a matrícula no período determinado, ou não apresentar toda a documentação exigida nesse período, caracteriza desistência e gera vaga remanescente.

- `ACV-01-p11-s1-c5` — ACV-01 (Edital original), página 11: «10.8. O candidato que não realizar sua matrícula nos prazos determinados, perderá o direito à vaga.»
- `ACV-01-p12-s1-c3` — ACV-01 (Edital original), página 12: «Os candidatos convocados para matrícula que não apresentarem toda a documentação exigida no período estabelecido pela Escola, ou que não comparecerem para efetivação da matrícula no período pré-determ»

### P04 — Quando começam as aulas de Agropecuária em Mimoso?

Status: **fundamentada** · decisão: **responder**

Resposta: As aulas de Agropecuária em Mimoso começam em 05 de outubro de 2026.

Justificativa: A Retificação nº 06 alterou a data de início das aulas para 05 de outubro de 2026 e listou o curso de Agropecuária em Mimoso entre os cursos abrangidos.

- `ACV-07-p1-s1-c2` — ACV-07 (Retificação nº 06), página 1: «Fica alterada para o dia 05 de outubro de 2026 a data de início das aulas dos seguintes cursos: ... Cuiabá 
Agropecuária 
Mimoso»

### P05 — Qual é o período de efetivação das matrículas da 4ª chamada?

Status: **fundamentada** · decisão: **responder**

Resposta: O período de efetivação das matrículas da 4ª chamada é de 03/07/2026 a 08/07/2026.

Justificativa: A Retificação nº 05 substituiu o período anteriormente previsto para a efetivação das matrículas da 4ª chamada.

- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «20 Efetivação das matrículas da 4ª chamada das vagas remanescentes 
03/07/2026 a 
08/07/2026»

### P06 — A ETEC oferece auxílio transporte ou bolsa para os alunos?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Os trechos disponibilizados tratam de pesquisa socioeconômica, matrícula e outros procedimentos, mas não informam a existência, os requisitos ou o procedimento para solicitar auxílio-transporte ou bolsa.


### P07 — Qual é o horário de atendimento da secretaria da ETEC?

Status: **sem_evidencia** · decisão: **revisar**

Resposta: Não há evidências suficientes para responder com segurança.

Justificativa: Há referências à secretaria da ETEC, mas nenhum trecho apresenta dias ou horários de atendimento.


### P08 — Quando é divulgada a lista das matrículas efetivadas na 4ª chamada?

Status: **conflito** · decisão: **revisar**

Resposta: Há informações documentais divergentes. É necessária revisão humana.

Justificativa: Os documentos ACV-01 e ACV-06 trazem valores diferentes para o mesmo fato e nenhuma retificação resolve a divergência. O ACV-06 informa divulgação em 09/07/2026, enquanto o ACV-01 informa 11/06/2026 para a lista das matrículas efetivadas na 4ª chamada.

- `ACV-06-p2-s1-c1` — ACV-06 (Retificação nº 05), página 2: «21 Divulgação/organização das matrículas efetivadas da 4ª chamada pelas Escolas Técnicas Estaduais 
09/07/2026»
- `ACV-01-p13-s1-c1` — ACV-01 (Edital original), página 13: «c) A lista das matrículas efetivadas na 4ª chamada de vagas remanescentes serão divulgadas no mural das Escolas Técnicas no dia 11/06/2026.»
