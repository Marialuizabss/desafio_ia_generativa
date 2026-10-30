# Relatório técnico

**Central Inteligente de Atendimento e Comunicação Institucional** — Desafio Prático 2, FIC_DEV 2026

Equipe: Ana Beatriz Schuindt do Amaral, Maria Luiza Batista de Souza e Felipe Ferreira Aguiar.

Visão técnica da evolução da central no Desafio 2: compreensão da solicitação, acervo e RAG,
guardrails, interface, sentimentos, auditoria, métricas, custos, privacidade e limitações. O
formato de todos os dados está em `contratos_dados.md`, nesta pasta.

## 1. Resumo

*A preencher pela equipe.*

## 2. Arquitetura e fluxo

*A preencher pela equipe.*

## 3. Compreensão da solicitação: extração, validação e NLP (RF14 e RF15)

*Responsável: Ana Beatriz.*

### 3.1 Visão geral

Cada solicitação passa por cinco etapas:

1. **Minimização** (RF12): CPF, RG, e-mail, telefone, nascimento, naturalidade e filiação saem
   do texto antes do envio ao provedor.
2. **Delimitação** (RF03): o texto vai entre `<solicitacao>` e `</solicitacao>` e é tratado como
   dado, nunca como instrução.
3. **Uma única chamada** ao modelo, com saída restrita por esquema, que devolve o objeto completo:
   campos da solicitação (RF14) e resumo, categoria e entidades (RF15). Uma chamada para os dois
   requisitos reduz custo e tempo.
4. **Validação** em três camadas (RF14), com no máximo uma nova tentativa.
5. **Comparação com o gabarito** e **conferência humana** do que a comparação automática não
   decide (RF15).

Código: `src/schemas.py` (RF14), `src/nlp.py` e `src/avaliacao_rf15.py` (RF15) e a função
`gerar_json_estrito` em `src/llm_client.py`.

### 3.2 Contrato e validação (RF14)

O contrato é o modelo Pydantic `Solicitacao`, versão `2.0`, em modo estrito: chave a mais é erro,
nenhum tipo é convertido (`"sim"` não vira `true`) e ausência é `null` no JSON e "não localizado"
na interface. O esquema enviado ao provedor é **gerado a partir do mesmo modelo**, então o que o
modelo recebe e o que o código valida não podem divergir.

| Camada | Categorias de erro | Exemplo |
|---|---|---|
| 1. Sintática | `json_invalido` | Resposta cortada |
| 2. Esquema | `chave_extra`, `tipo_incorreto`, `campo_obrigatorio_ausente`, `valor_fora_do_dominio` | `requer_revisao: "não"`; categoria fora das seis |
| 3. Regras de negócio | `data_impossivel`, `dado_nao_presente_no_original`, `data_incoerente`, `fato_sem_suporte`, `incoerencia_interna`, `resumo_longo` | 31/02/2026; protocolo que não está no texto; solicitação antes da abertura do processo seletivo |

- Erro de sintaxe ou de esquema gera **uma** nova tentativa, com a lista de erros no pedido; se
  persistir, a saída é **rejeitada**.
- Regra de negócio violada **não** gera nova tentativa (o dado veio assim da entrada): o caso vai
  para `revisar`.
- Rejeição ou regra violada **bloqueia a minuta**. O registro guarda o arquivo de entrada e o
  hash do texto (não o texto), os erros de cada tentativa e a decisão.
- A data de abertura do processo (31/03/2026) é lida do catálogo do acervo
  (`dados/acervo/acervo.json`), não fixada no código.
- Comparações com o texto ignoram acento, maiúsculas e espaços, porque OCR e transcrição variam
  nisso; datas são reconhecidas como `14/10/2026` e "14 de outubro de 2026".

### 3.3 Evidências do T01 e do T02

**T01 — JSON sintático × esquema** (`resultados/metricas/rf14_comparacao.md`). A extração correta
do CASO-08 foi alterada em oito versões, uma por defeito:

| Verificação | Versões aceitas |
|---|---|
| Só `json.loads` (sintaxe) | 7 de 8 |
| Esquema Pydantic | 3 de 8 |
| Regras de negócio | 1 de 8 |

Cada defeito caiu na sua categoria: chave extra, tipo incorreto, campo ausente e valor fora do
domínio foram rejeitados após duas tentativas; data impossível e protocolo fora do texto foram
para revisão com uma tentativa. **JSON válido não garante esquema válido, e esquema válido não
garante dado correto.**

**T02 — dado incoerente, em execução real.** No CASO-06, a leitura da ficha manuscrita registrou a
data da matrícula como 17/01/2026 (a leitura humana indica 14/10/2026). A data existe no
calendário e está no texto lido, mas é anterior à abertura do processo seletivo: a regra
`data_incoerente` levou o caso a `revisar` com a minuta bloqueada **nas duas execuções reais**.

### 3.4 Ficha de compreensão (RF15)

O prompt (`prompts/desafio2/extracao_v2.1.md`) pede resumo de até 100 palavras só com fatos do
texto, uma das seis categorias documentadas (seção 8 de `contratos_dados.md`) e entidades
(pessoas, órgãos, locais, datas e protocolos) marcadas como `literal` ou `inferida`, sem completar
o que falta. A versão do prompt é o hash do prompt e do esquema e fica em cada registro.

| Item | Decidido automaticamente | Vai para a conferência humana |
|---|---|---|
| Categoria | acerto ou erro | — |
| Entidades | acerto, omissão, extra presente no texto (aceita), incorreta | parecidas e inferidas |
| Fatos essenciais | preservado, quando o trecho do gabarito aparece no resumo | o restante, porque o resumo parafraseia |
| Dados sem suporte | datas, protocolos e cargas horárias do resumo ausentes do texto | todos, para confirmação |

### 3.5 Avaliação

Sete solicitações: as seis do enunciado (quatro completas, entre elas as saídas reaproveitadas de
áudio e de leitura da ficha, uma incompleta e uma ambígua) e o CASO-08, coerente com o acervo. Os
gabaritos foram commitados em 28/10/2026 às 19:18 (commit `d8f9f4f`), **antes** da primeira
execução real, às 20:37. Modelo: `gpt-5.6-luna`. Revisora da conferência: Ana Beatriz.

| Métrica | Prompt v2 (28/10) | Prompt v2.1 (29/10) |
|---|---|---|
| Acurácia da categoria | 7/7 (100%); 6/6 no enunciado | 7/7 (100%); 6/6 no enunciado |
| Entidades esperadas encontradas | 29/29 (100%), 0 incorretas | 29/29 (100%), 0 incorretas |
| **Fatos essenciais preservados** | **35/44 (79,5%)**, 9 omitidos | **44/44 (100%)**, 0 omitidos |
| Fatos sem suporte | 0 | 0 |
| Saídas rejeitadas pelo RF14 | 0/7 | 0/7 |
| Itens conferidos por pessoa | 18 | 14 |
| Tamanho do resumo | 29 a 51 palavras | 51 a 70 palavras |

Resultados: `resultados/metricas/rf15/execucao_20261028_203614/` (v2) e
`resultados/metricas/rf15/execucao_20261029_105629/` (v2.1), cada uma com `matriz_rf15.md`,
`conferencia_rf15.json` e `metricas_rf15.md`.

### 3.6 Falhas e correções

| Falha | Como foi encontrada | Correção |
|---|---|---|
| O resumo do v2 omitiu 9 fatos: a declaração de ciência das regras (4 casos), a data de início (2), a carga horária (1), a escola (1) e a falta do protocolo (1) | Conferência humana | Prompt v2.1: a seção "Resumo" passou a pedir esses itens com regras genéricas, sem citar casos. O v2 foi guardado para reprodução |
| `esperado_do_gabarito` devolvia as entidades por referência ao gabarito: alterar uma resposta alterava o esperado | Teste do RF15 | Cópia do gabarito antes de montar a resposta e teste próprio no RF14 |
| Um teste usava um CPF com dígito verificador válido | Varredura de dados pessoais do RF12 | Troca por CPF com dígito inválido, como no resto do projeto |
| Uma execução do v2.1 teve chamadas de cerca de 247 s (tempo limite de 120 s estourado e repetição) | Tempo registrado em cada chamada | Execução incompleta descartada; a repetição rodou com 4 a 8 s por caso |

### 3.7 Custos e tempo

| | v2 | v2.1 |
|---|---|---|
| Custo estimado (7 casos) | US$ 0,0069 | US$ 0,0068 |
| Custo por solicitação | cerca de US$ 0,001 | cerca de US$ 0,001 |
| Tempo por chamada | 4,3 a 8,5 s | 4,2 a 8,2 s |
| Tokens de saída por chamada | 316 a 734 | 326 a 719 |

Custos estimados com a tabela de preços de `src/llm_client.py`, não pela fatura do provedor. A
chamada usa `store: false`, tempo limite de 120 s e no máximo uma repetição por falha transitória.

### 3.8 Privacidade

O texto é minimizado antes do envio e delimitado no prompt. O registro de cada análise
(`resultados/logs/execucoes.jsonl`) guarda versão do prompt, chamadas, erros e decisão, com o hash
do texto e sem o texto; foi conferido que as linhas das execuções não contêm nomes de
solicitantes. As entidades esperadas nos gabaritos foram montadas sobre o texto já minimizado, de
modo que um dado removido (como o nome da mãe) não pode ser cobrado nem aceito como entidade.

### 3.9 Limitações e riscos residuais

- **Fato composto conferido em parte.** A comparação automática procura um trecho por fato; quando
  o fato junta duas informações, só uma é conferida. No v2.1, o resumo do CASO-08 perdeu a data da
  solicitação e o fato "Protocolo 2026-000201, de 12/06/2026" foi marcado como preservado.
- **Motivos de revisão do modelo variam entre execuções** (no CASO-05: "noturno noturno" no v2,
  falta da data de início no v2.1). As regras no código são estáveis; as do modelo, não.
- **O RF14 não conhece o acervo.** CASO-01 e CASO-04 saem como `aceita`; a divergência de semestre
  com o edital (2027/1 × 2026/2) é detectada pelo RAG (RF19).
- **Avaliação pequena:** sete casos, todos de matrícula, uma revisora e uma execução por versão de
  prompt.
- **Custos estimados**, não medidos na fatura.

### 3.10 Como reproduzir

| O quê | Comando | Chama a API? |
|---|---|---|
| Testes do RF14 (27) e do RF15 (18) | `python -m unittest testes.test_rf14 testes.test_rf15` | Não |
| Comparação do T01 | `python -m src.experimento_rf14` | Não |
| Avaliação simulada (resposta montada do gabarito) | `python -m src.avaliacao_rf15 --simulado` | Não |
| Avaliação real dos 7 casos | `python -m src.avaliacao_rf15 --todos` | Sim, cerca de US$ 0,007 |
| Métricas finais após a conferência | `python -m src.avaliacao_rf15 --consolidar PASTA` | Não |

## 4. Acervo, índice vetorial e RAG (RF17, RF18 e RF19)

*Responsável: Maria Luiza.*

### 4.1 Acervo

Nove documentos catalogados em `dados/acervo/acervo.json` (versão 1.2), cada um com identificador,
título, versão, formato e hash SHA-256: o edital nº 006/2026 da SECITECI-MT (ACV-01), seis
retificações (ACV-02 a ACV-07, em PDF) e dois documentos fictícios da equipe em TXT (ACV-08, sobre
frequência e cancelamento, e ACV-09, sobre a pesquisa socioeconômica). O catálogo traz o campo
`ordem` e o escopo de cada alteração (`altera`), usados nas regras de prevalência R1 a R4. A
indexação só aceita arquivo cujo hash confere com o catálogo (`hash_divergente` e `arquivo_ausente`
não entram no índice).

### 4.2 Índice vetorial (RF17)

| Item | Decisão |
|---|---|
| Armazenamento | ChromaDB persistente em `dados/indice_vetorial/` (fora do controle de versão; recriado a partir do acervo) |
| Modelo de embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, dimensão 384, executado localmente |
| Distância | Cosseno. A distância vai de 0 (mesma direção) a 2; a similaridade é `1 − distância`. Menor distância = trecho mais parecido |
| Metadados por vetor | `doc_id`, `titulo`, `versao`, `sha256`, `pagina` (0 = sem página), `secao` e o `chunk_id` (por exemplo `ACV-08-p0-s2-c1`) |
| Registro do modelo | Modelo e dimensão ficam nos metadados da coleção. Abrir o índice com outro modelo ou dimensão gera `IndiceDesatualizadoError` e exige reindexação |
| Sem duplicação | O `chunk_id` é estável. Um documento só é regravado se mudar o hash ou o texto de algum chunk; sem mudança, os embeddings nem são recalculados |
| Versão do índice | Hash curto de modelo, dimensão e, por documento, versão, hash e quantidade de chunks. Entra em cada registro de auditoria |
| top-k | Parâmetro de `buscar_chunks` e de `responder_rf19` (padrão 15) |

Código: `src/vector_store.py` (índice e busca), `src/indexar.py` (indexação e exclusão) e
`src/ingestion.py` (extração e chunking).

**Evidência (T06).** `testes/test_rf17_indice.py`: reindexar o mesmo acervo mantém a contagem e os
ids (a segunda passada devolve `sem_alteracoes`); após "reiniciar" (nova conexão com a mesma pasta)
o índice é reutilizado, com a mesma versão, e a busca devolve trechos com documento, versão, hash e
`chunk_id`; troca de modelo ou de dimensão é recusada. Na execução real, `python -m src.indexar`
repetido devolveu `sem_alteracoes` em todos os documentos, com 105 chunks e a mesma versão do índice.

### 4.3 Chunking e recuperação (RF18)

Unidade de tamanho e sobreposição: **caracteres**. Três configurações, mesmo acervo, mesmo modelo,
mesmas perguntas e mesmo top-k (3, 5 e 10). Perguntas: as cinco respondíveis (P01 a P05); referências
do `gabarito_rag.json`, elaborado antes das chamadas. Um trecho recuperado é "de referência" quando é
do mesmo documento, da mesma página e contém a frase de referência inteira. Detalhes e a tabela por
pergunta: `documentacao/desafio-2/avaliacao_rf18.md`.

| Configuração | Tamanho | Sobreposição | Chunks | Acerto@3 | Acerto@5 | Acerto@10 |
|---|---:|---:|---:|---:|---:|---:|
| pequena | 300 | 50 | 253 | 3/5 | 3/5 | 4/5 |
| média | 800 | 100 | 105 | 3/5 | 3/5 | 5/5 |
| grande | 1200 | 200 | 79 | 2/5 | 2/5 | 2/5 |

**Achado.** O modelo de embeddings trunca o texto em 128 tokens (`max_seq_length = 128`), e 72% dos
chunks da configuração média e 76% dos da grande passam disso, então o vetor representa só o começo
do chunk. Na grande, as três perguntas não recuperadas (P01, P02 e P03) são exatamente aquelas cuja
frase de referência termina depois do token 128 (tokens 165 a 236). A pequena não tem nenhum chunk
acima do limite e ainda assim falha na P02, então o truncamento não explica tudo (hipótese não
testada: o vocabulário da pergunta, "a distância", difere do trecho, "presencialmente").

**Configuração escolhida: média (800 / 100)**, pelo melhor Acerto@10 (5/5), por ter menos chunks que
a pequena (105 contra 253) e mais contexto por trecho. Limites: pequena e média diferem por uma
pergunta (com cinco perguntas isso não prova superioridade), P02 e P03 aparecem só na posição 9 na
média e o Acerto@15 (o `top_k` usado no RAG) não foi medido.

**Avaliação anterior, substituída.** A primeira avaliação (`src/avaliacao_chunking.py`) usou cinco
perguntas sobre ACV-08 e ACV-09 e conferia o acerto pela seção do TXT. Ela não correspondia às
perguntas respondíveis do gabarito (P01 a P05, sobre os PDFs, que não têm seção) e foi mantida só
como histórico.

### 4.4 Geração fundamentada com RAG (RF19)

`responder_rf19` (em `src/rf19_complemento.py`) segue as mesmas etapas para qualquer pergunta. Não há
regra escrita para uma pergunta, um curso ou uma data específicos.

1. Recupera os `top_k` trechos mais próximos no índice.
2. **Quarentena de instruções em documentos.** Um trecho que mande o assistente "desconsiderar as
   regras", confirmar matrícula, enviar a resposta sem revisão ou listar variáveis de ambiente sai do
   contexto e vira um alerta (o registro guarda o motivo, não o texto). A resposta só vai para revisão
   se citar o mesmo documento em que a instrução apareceu. É o caso do ADV-02 (nota ao assistente no
   ACV-09). Os padrões foram conferidos contra os 105 trechos do acervo: só o trecho do ataque é
   sinalizado.
3. **Vigência** (`src/vigencia.py`). Duas detecções gerais, só com o texto dos trechos e `ordem` e
   `altera` do catálogo: o texto sob "Onde se lê:" é a versão substituída pelo "Leia-se"; e uma linha
   numerada de cronograma que aparece em dois documentos ligados pelo catálogo, com o mesmo texto e
   números diferentes, é substituída pela do documento de maior `ordem` (regra R2). O modelo recebe um
   aviso do que foi substituído.
4. O modelo responde em JSON com status, resposta, justificativa, citações e prevalência.
5. **Validação no código:** cada citação precisa existir, letra por letra, num trecho recuperado
   (aceita reticências entre fragmentos literais; se o modelo erra o `chunk_id`, a citação é atribuída
   ao trecho certo e o erro fica registrado); as datas da resposta precisam estar nas citações; a
   declaração de prevalência precisa estar completa.
6. Se a resposta se apoia em texto substituído, pede **uma** nova resposta com a correção; se persistir,
   encaminha para revisão.
7. **Segunda leitura.** Com trechos de pelo menos dois documentos, o modelo é consultado de novo: há
   outro documento vigente com valor diferente para o mesmo fato? O código só aceita se os dois trechos
   citados existirem, vierem de documentos diferentes, nenhum estiver substituído, tratarem do mesmo
   assunto (palavras de conteúdo em comum) e os números divergirem. Então o status é `conflito`.
8. Sem evidência ou em conflito, não responde: encaminha à revisão humana. Nenhuma resposta é enviada
   ao cidadão.

Status: `fundamentada`, `sem_evidencia` e `conflito`.

**Resultados das oito perguntas** (conferência automática contra o gabarito; execuções com a API real):

| Execução | O que mudou | Status correto | Respondíveis aprovadas | P06 e P07 | P08 |
|---|---|---:|---:|---:|---:|
| 002308 | Código inicial, com regras específicas para P04, P05 e P08 | 4/8 | 0/5 | 2/2 | 1/1 |
| 003236 | Validador de citações passa a juntar as quebras de linha dos PDFs | 5/8 | 1/5 | 2/2 | 1/1 |
| 004411 | Citação com reticências e identificador de trecho errado | 6/8 | 1/5 | 2/2 | 1/1 |
| 110414 | **Sem regras por pergunta** (vigência geral); P08 deixa de ter regra | 7/8 | 2/5 | 2/2 | 0/1 |
| 112136 | Segunda leitura e quarentena de instruções | 6/8 | 2/5 | 2/2 | 1/1 |
| 113120 (3 rodadas) | Correções gerais de citação e do avaliador | 8/8, 8/8, 8/8 | 3/5 nas três | 2/2 | 1/1, 1/1, 0/1 |
| 114047 (3 rodadas) | Alerta só leva à revisão se a resposta cita o documento alertado | 8/8, 8/8, 8/8 | 3/5 nas três | 2/2 | 1/1 nas três |
| 114938 (3 rodadas, `gpt-5.6-luna`) | Mesma lógica com um modelo mais forte | 8/8, 8/8, 8/8 | 3/5 nas três | 2/2 | 1/1 nas três |

Na última execução com o `gpt-4o-mini`, P03, P04 e P05 passaram nas três rodadas, e P01 e P02
reprovaram nas três (resposta correta, mas incompleta). Detalhe por pergunta:

| Pergunta | gpt-4o-mini (3 rodadas) | gpt-5.6-luna (3 rodadas, gabarito 1.2) |
|---|---|---|
| P01 | 0/3: omite "cópia simples e original" | 3/3 |
| P02 | 0/3: omite "onde se inscreveu" | 2/3 |
| P03, P04, P05 | 3/3 | 3/3 |
| P06, P07 (sem resposta) | 3/3 abstenção | 3/3 abstenção |
| P08 (contraditória) | 3/3 conflito | 3/3 conflito |

**Gabarito 1.2.** Com o `gpt-5.6-luna`, P01 e P02 reprovavam pela conferência de palavras exatas
("escolaridade" × "histórico escolar"; "onde se inscreveu" × "onde você se inscreveu"). O gabarito foi
alterado para aceitar essas variantes, com registro no `historico` do arquivo (versão 1.2, 30/10/2026),
e as mesmas respostas já gravadas foram reavaliadas sem nova chamada à API
(`python -m src.reavaliar_elementos`). O modelo `gpt-4o-mini` continuou reprovando, porque omite de
fato esses requisitos. "Pessoalmente" não foi aceito como alternativa na P02, porque aparece na própria
pergunta.

**Instabilidade.** O resultado varia entre execuções (P02 com o modelo forte passou em 2 de 3). Por
isso a avaliação roda as perguntas várias vezes (`--repeticoes 3`) e relata em quantas cada uma passa.

### 4.5 Falhas encontradas e corrigidas

| Falha | Como foi encontrada | Correção |
|---|---|---|
| Letras acentuadas gravadas como `?` nos arquivos (`P?gina`, `Cita??o`), inclusive no contexto enviado ao modelo | Revisão do código | Textos corrigidos e teste do contexto |
| Expressões regulares com barra duplicada: o complemento de citação não dividia o texto em frases | Revisão do código e teste novo | Corrigidas |
| Divisão do texto do PDF em cada quebra de linha tornava o validador de citações rígido demais | Execução real (citação com palavras omitidas era recusada) | Junta as linhas antes de dividir em frases |
| Modelo atribuía a citação ao `chunk_id` errado ou inventava o identificador | Saída bruta do modelo (diagnóstico) | Atribuição pelo texto, com o erro registrado |
| Citação com reticências recusada | Saída bruta do modelo | Cada fragmento precisa existir literalmente no mesmo trecho |
| Regras escritas para P04, P05 e P08 (datas, documentos e reordenação dos trechos) | Revisão: o resultado dessas perguntas media o ajuste do código | **Removidas**; substituídas por vigência, quarentena e segunda leitura gerais |
| Resposta única para P08 sem as regras (data do ACV-06 entregue como certa) | Execução 110414 | Segunda leitura de contradição entre documentos |
| Trecho malicioso do ACV-09 tratado como documento e gerando um conflito falso na P02 | Execução 112136 | Quarentena de instruções em documentos e checagem de "mesmo assunto" |
| Perguntas comuns iam para revisão só porque o trecho malicioso foi recuperado | Execução 113120 | A revisão só vale se a resposta cita o documento alertado |
| Teste de caminho que passava no Linux e falhava no Windows | Execução local | Caminhos em formato único (`as_posix`) |
| Índice sem registro de modelo e dimensão | Revisão do código | Registro nos metadados e erro explícito |
| Não havia como excluir um documento nem reproduzir o índice por comando | Revisão do código | `src/indexar.py` e testes T06 e T14 |

### 4.6 Exclusão de documento (RF24, parte do índice) e retenção

`python -m src.indexar --excluir ACV-09` remove os vetores do documento, confere que nenhum restou,
grava o evento `exclusao_documento` no log (data, motivo, versão do índice e derivados) e avisa quais
arquivos de resultados citam o documento.

**Demonstração real (T14), busca "A pesquisa socioeconômica é obrigatória?" (top-5):**

| Etapa | Total no índice | ACV-09 na busca |
|---|---:|---|
| Antes da exclusão | 105 | sim, nas três primeiras posições (distâncias 0,397, 0,496 e 0,504) |
| Depois de excluir | 100 | não aparece em nenhum dos cinco resultados |
| Depois de reindexar | 105 | volta, nas mesmas posições e distâncias |

A versão do índice depois de reindexar (`3bb130336d90`) é idêntica à de antes da exclusão.

**Retenção.** A exclusão do índice não apaga os resultados derivados (relatórios e métricas que já
citaram o documento): eles aparecem na lista `derivados_a_revisar` e precisam de revisão manual.
Reindexar traz o documento de volta enquanto ele constar em `acervo.json`.

### 4.7 Como reproduzir

| O quê | Comando | Baixa o modelo? | Chama a API? |
|---|---|---|---|
| Testes | `python -m pytest testes -q` | Não | Não |
| Indexar o acervo | `python -m src.indexar` | Sim, na primeira vez | Não |
| Conteúdo e versão do índice | `python -m src.indexar --status` | Não | Não |
| Excluir um documento | `python -m src.indexar --excluir ACV-09 --motivo "..."` | Não | Não |
| Avaliação de chunking | `python -m src.avaliacao_rf18` | Sim | Não |
| Oito perguntas do RAG, três rodadas | `python -m src.avaliacao_rag --repeticoes 3` | Sim | Sim |
| Mesmas perguntas com outra geração | `python -m src.avaliacao_rag --repeticoes 3 --configuracao forte` | Sim | Sim |
| Reavaliar respostas gravadas | `python -m src.reavaliar_elementos PASTA` | Não | Não |

### 4.8 Limitações e riscos residuais

- **A conferência automática é um indicador.** Compara palavras com o gabarito; a leitura humana
  decide se a resposta está completa e sustentada. P01 e P02 mostram o limite do método.
- **O `gpt-4o-mini` omite condições** que o `gpt-5.6-luna` inclui (cópia simples e original; local da
  matrícula). O resultado do modelo forte também é instável.
- **A detecção de linha substituída só enxerga o que foi recuperado.** Se a retificação mais nova não
  vier no top-k, uma linha antiga pode passar. Ela assume linhas numeradas de tabela; substituições em
  texto corrido só são pegas pelo "Onde se lê / Leia-se".
- **A checagem de "mesmo assunto" é lexical.** Na P08, uma vez, o modelo declarou o conflito com o
  documento errado (efetivação das matrículas em vez da divulgação da lista), e o avaliador apontou que
  as datas esperadas não estavam na justificativa. Esse caso não se repetiu nas rodadas seguintes.
- **A quarentena usa padrões de texto** e só reconhece as formulações previstas; um ataque escrito de
  outra forma pode passar. O resultado do trecho segue como dado, nunca como instrução, e o modelo
  recebe o contexto delimitado.
- **PDF sem OCR:** a extração usa o texto embutido.
- **Busca puramente semântica,** com embeddings pequenos e truncados em 128 tokens (seção 4.3).
- **Avaliação pequena:** oito perguntas, uma revisora, três rodadas por configuração.
- **Custos estimados** pela tabela de preços do projeto, não pela fatura do provedor.

## 5. Provedor configurável e auditoria (RF21)

*Responsável: Maria Luiza.*

### 5.1 Configuração e adaptador

A geração fica isolada em `src/provider_adapter.py`; a recuperação (seção 4) não depende dele. Cada
configuração de `config.json` (`adaptador_llm.configuracoes`) define provedor, modelo, temperatura e,
opcionalmente, `max_tokens_saida`. O tempo limite (120 s) e a repetição única por falha transitória
valem para todas. `responder_rf19(..., nome_configuracao="...")` escolhe a configuração; a mesma vale
para a resposta e para a segunda leitura.

| Configuração | Provedor | Modelo | Observação |
|---|---|---|---|
| `principal` | openai | gpt-4o-mini, temperatura 0 | Uso normal |
| `alternativa` | openai | gpt-4o-mini, temperatura 0,5 | Mesmo modelo com outra temperatura; não é um segundo serviço |
| `forte` | openai | gpt-5.6-luna (sem temperatura) | Segunda configuração real, com modelo diferente |
| `simulada` | simulado | `simulado-abstencao-v1` | Não consulta modelo: responde sempre "sem evidência" e se identifica como simulada. Não tem equivalência de qualidade com um modelo real |

Para acrescentar outro serviço, basta registrar uma função em `PROVEDORES` e declarar o provedor na
configuração.

### 5.2 Trilha de auditoria

Cada consulta ao RAG grava um evento `consulta_rag` em `resultados/logs/execucoes.jsonl`
(`src/auditoria_rag.py`):

| Campo | Conteúdo |
|---|---|
| `id_execucao` | Identificador da consulta (devolvido como `id_consulta`). A decisão humana (`audit.registrar_decisao`) usa o mesmo |
| `inicio`, `fim`, `latencia_total_segundos`, `latencia_recuperacao_segundos` | Horários e tempos medidos |
| `versao_esquema_resposta`, `versao_prompt`, `versao_indice` | Versão do contrato (`rag-1.1`), do prompt (hash) e do índice |
| `pergunta`, `top_k` | Pergunta com CPF, RG, e-mail, telefone e protocolo mascarados |
| `ids_recuperados`, `ids_citados`, `alertas` | Trechos recuperados (com distância), trechos citados e alertas de instrução em documento (motivo, sem o texto) |
| `status`, `decisao`, `erro` | Resultado da consulta e erro, se houve |
| `geracao` | Provedor, modelo, configuração, se foi simulada, status da chamada, número de chamadas, tokens, custo estimado ou o motivo de não haver métrica |

O registro não guarda a chave da API (campos com nome de segredo e valores no formato de chave são
descartados) nem o texto dos trechos: com os `chunk_id` e a versão do índice, a passagem original é
conferida no próprio índice.

### 5.3 Evidências (T12)

**Execução real.** A mesma pergunta ("Qual é o período de efetivação das matrículas da 4ª chamada?")
foi respondida com as três configurações:

| Configuração | Modelo | Resultado | Tokens | Custo estimado | Versão do índice | Versão do prompt |
|---|---|---|---:|---:|---|---|
| principal | gpt-4o-mini | fundamentada | 12.813 | US$ 0,0021 | `3bb130336d90` | `6f34e1c76fec` |
| forte | gpt-5.6-luna | fundamentada | 12.939 | US$ 0,0031 | `3bb130336d90` | `6f34e1c76fec` |
| simulada | simulado (identificado) | sem_evidencia, revisar | indisponível | indisponível | `3bb130336d90` | `6f34e1c76fec` |

A versão do índice é a mesma antes e depois: trocar a geração não reconstrói o índice (o `--status`
seguinte continuou em 105 chunks).

**Testes** (`testes/test_rf21_auditoria.py`, sem API): trocar a configuração não reindexa (a indexação
fica proibida durante o teste) e as duas consultas recuperam os mesmos trechos; falha de conexão com
o serviço devolve abstenção para revisão, sem resposta inventada, com a falha e o tempo registrados;
erro inesperado do provedor não repassa a mensagem original (que poderia conter a chave); o log não
contém CPF, e-mail, protocolo nem chave de API; a decisão humana se liga à consulta.

### 5.4 Custos e tempo

Custos estimados pela tabela de preços de `src/llm_client.py`, sem fatura do provedor. Oito perguntas
por rodada (inclui a segunda leitura):

| Configuração | Tokens por rodada | Custo estimado por rodada |
|---|---:|---:|
| gpt-4o-mini | cerca de 71 mil a 77 mil | US$ 0,0118 a 0,0128 |
| gpt-5.6-luna | cerca de 80 mil | US$ 0,0215 a 0,0224 |

O modelo forte custa cerca de 1,75 vez mais por rodada. Na configuração simulada não há tokens nem
custo; o registro informa isso em `metricas_indisponiveis`. A recuperação roda localmente, sem custo.

### 5.5 Limitações

- A segunda configuração real troca o modelo da OpenAI; não foi testado outro provedor. O provedor
  simulado só se abstém e serve para demonstrar a troca e a tolerância a falhas.
- O limite de tokens por execução (`max_tokens_saida`) existe, mas está desligado por padrão.
- A auditoria registra a consulta e o resultado, não a decisão humana, que é gravada à parte pela
  interface com o mesmo identificador.
- O modelo de embeddings é recarregado a cada consulta (custo de tempo, não de correção).

## 6. Guardrails, moderação e limites (RF16)

*A preencher — Felipe.*

## 7. Interface e revisão humana (RF20)

*A preencher — Felipe.*

## 8. Sentimentos e painel (RF22)

*A preencher — Felipe.*

## 9. Avaliação integrada e regressão (RF23)

*A preencher pela equipe.*

## 10. Privacidade, retenção e revisão humana (RF24)

*A preencher pela equipe.*

## 11. Custos

*A preencher pela equipe (consolidar os custos de cada parte).*

## 12. Limitações

*A preencher pela equipe.*

## 13. Uso de IA no desenvolvimento

*A preencher pela equipe: cada integrante registra ferramentas, solicitações relevantes, sugestões
aceitas, modificadas ou rejeitadas e erros encontrados (seção 12 do enunciado).*
