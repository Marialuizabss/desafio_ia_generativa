# Registro do uso de IA no desenvolvimento

Registro do uso de IA **para desenvolver** o Desafio 2; os modelos usados pelo **sistema** estão no
`01_relatorio_tecnico.md`. O registro do Desafio 1 está em `documentacao/desafio-1/02_registro_uso_ia.md`.

## 1. Ana Beatriz Schuindt do Amaral

**Ferramenta:** Claude Code (Anthropic), extensão do VS Code, modelo Claude Opus 5.5, de 28/10 a
01/11/2026.

**Finalidade:** planejar a parte da Estudante 1, suporte ao implementar e testar o RF14 e o RF15, integrar a
Ficha com o acervo e a revisão humana, verificar o projeto contra o enunciado e organizar a
documentação.

**Forma de trabalho:** antes de cada mudança, a IA apresentava possíveis planos (cada requisito, o que o
enunciado pedia, situação, o quê e como); Ana aprovava, mudava ou rejeitava. A IA aplicava, rodava os
testes sem API e sugeria os commits. Ana fez os testes reais pela interface (a IA não chamava a API
sem autorização) e todos os commits.

**Principais solicitações**

- Análise do enunciado, contratos de dados da equipe e dados fictícios.
- RF14 e RF15: contrato, validação, prompt v2.1 e avaliação.
- Correção do que os testes da Ana pela interface mostraram: erro com consultas simultâneas, índice
  diferente do catálogo e exclusão desfeita ao reindexar.
- Ficha completa: orientações do acervo, correção de campos, edição e aprovação da minuta e alertas.
- Retenção (RF24), top-k e distância na tela (RF17) e varredura do RF12.
- Verificações completas contra o enunciado; matriz, relatório técnico e README.

**Sugestões**

- **Aceitas:** trava na abertura do índice; consulta bloqueada quando o índice não confere com o
  catálogo; exclusões registradas em `exclusoes.json`; três consultas por assunto na Ficha; relatório
  organizado pelos temas do enunciado.
- **Modificadas:** avisos sem comandos de terminal, só com ações na interface; modelo de embeddings
  carregado uma vez só; aviso de sucesso e Ficha limpa também ao rejeitar, não só ao aprovar; alertas
  de segurança em vermelho, com emoji; integração completa das orientações na Ficha, em vez da parcial.
- **Descartadas:** mudar o prompt do RAG por causa do falso conflito de 01/11, o que exigiria refazer a
  avaliação (ficou como limitação).

**Erros da IA encontrados:** testes que montavam a análise com argumentos na ordem errada; a primeira
versão da aprovação deixava aprovar minuta com recado para o servidor (duas minutas ficaram como
histórico, e a trava veio depois); aviso de espera mesmo com o modelo já carregado; na documentação, a
pergunta de Mimoso atribuída à P05 (é a P04) e a tabela do T14 misturando duas demonstrações. Todos
corrigidos, os do código com teste.

**Validação:** 567 testes automatizados sem API, testes reais pela interface feitos pela Ana (log em
`resultados/logs/execucoes.jsonl`), conferência humana do RF15, métricas recalculadas dos arquivos de
resultado e varredura do RF12 aprovada.

## 2. Maria Luiza Batista de Souza

### Ferramentas

- Assistente de IA generativa (Claude, da Anthropic), em conversa de chat com envio de arquivos do
  projeto, usado para revisar código, propor implementações, escrever testes e rascunhar textos.
- O código sugerido foi colado e executado por mim; as execuções com a API (OpenAI) foram feitas na
  minha máquina.
- Modelo: Claude Sonnet 5.5 na sessão de 30 e 31/10. O modelo das sessões anteriores não foi registrado na época.

### Solicitações relevantes

1. **Revisão da minha parte do código** (índice, RAG e provedor) contra o enunciado: apontou lacunas
   (sem exclusão de documento, sem script de indexação, avaliação de chunking com perguntas diferentes
   do gabarito, auditoria incompleta, acentos gravados como `?`, dois padrões de expressão regular
   errados).
2. **Investigação das respostas ruins do RAG** (0/5 respondíveis na primeira execução real): a partir da
   saída bruta do modelo, identificou três causas diferentes (validador de citações rígido com as
   quebras de linha do PDF, identificador de trecho errado e citações com reticências).
3. **Remoção das regras específicas** para P04, P05 e P08 e substituição por métodos gerais
   (vigência, quarentena de instruções em documentos e segunda leitura de contradição).
4. **Seleção de geração e auditoria** (RF21): configuração escolhida por nome, provedor simulado
   identificado como tal, tratamento da falha do serviço e registro de cada consulta.
5. **Minuta fundamentada do CASO-08** (31/10): uma consulta ao acervo por assunto (documentos, local e período), com fontes, e geração da minuta pendente de revisão humana.
6. **Falsos conflitos no RAG** (31/10): a primeira minuta saiu com o período em conflito; a análise mostrou que o verificador comparava linhas de chamadas diferentes e que o conflito declarado pelo modelo não conferia a vigência. Duas correções gerais, com testes.

### Sugestões aceitas, modificadas e rejeitadas

- **Aceitas:** índice reproduzível por comando; avaliação de chunking com as perguntas do gabarito;
  correção dos acentos e das expressões regulares; segunda leitura de contradição; avaliação em várias
  rodadas (`--repeticoes`); consulta ao acervo por assunto na minuta (regra por categoria de pedido, não por caso);
  ajuste do gabarito para a versão 1.2, com variantes de redação em P01 e P02, feito depois de ver as
  respostas da API (declarado no relatório).
- **Modificadas:** a ideia de manter as regras específicas com um interruptor para comparar "com e sem"
  foi trocada por removê-las (os resultados anteriores já estavam gravados); a regra de enviar à revisão
  qualquer resposta com trecho suspeito recuperado foi restringida a respostas que citam o documento
  alertado.
- **Descartada:** aceitar "pessoalmente" como alternativa no gabarito da P02, porque a palavra aparece
  na própria pergunta (e o teste do projeto proíbe isso).

### Erros da IA encontrados e como foram tratados

- Uma correção de expressão regular ficou incompleta para PDFs (dividia o texto em cada quebra de
  linha) e deixou o validador de citações rígido demais; foi percebida na execução real e corrigida.
- Testes escritos num ambiente Linux falharam no Windows (separador de caminho); corrigido.
- Um bloco de instruções tinha crases dentro de outro bloco de código e chegou quebrado ao terminal;
  reenviado corrigido.
- Em um momento, a IA tratou as regras específicas por pergunta como se fossem de outra origem;
  foi corrigida, porque esse código da minha parte do RF19 foi escrito por mim.
- Uma hipótese da IA sobre a causa dos conflitos (diferença entre os símbolos `º` e `ª`) estava errada; foi descartada ao ler o código da vigência, que já normaliza os dois, e a causa real era outra.
- Um script colado no PowerShell gravou o arquivo da conferência humana com `?` no lugar dos acentos (o Python recebeu o script sem UTF-8); percebido na conferência do arquivo e corrigido com `$OutputEncoding` e `python -X utf8`.

### Como o código e o conteúdo foram validados

- Testes automáticos (473 na última execução), incluindo testes que quebram o código de propósito para
  confirmar que falham.
- Execuções reais com a API (três rodadas por configuração) e conferência das respostas e das
  citações; a conferência automática por palavras foi tratada como indicador, e a leitura humana,
  como decisão final.
- Evidência real separada de simulação: o provedor `simulado` e o codificador falso dos testes estão
  identificados como tais e não substituem as execuções reais.

### Limites declarados

- O resultado dos modelos varia entre execuções; por isso os números vêm de três rodadas.
- Os custos são estimativas pela tabela de preços do projeto.
- A minuta fundamentada depende de a busca trazer o trecho certo para cada assunto: a lista de documentos
  gerada com o `gpt-4o-mini` vai até a alínea f, e com a configuração `forte` a consulta de documentos se
  absteve (ver relatório).

## 3. Felipe Ferreira Aguiar

> **Pendente:** Felipe completa com o trabalho de 31/10 (regra de escopo, teto único com os dois
> nomes do módulo, T15 sem decisão gravada e Ficha como fluxo oficial).

Desafio 2, parte de guardrails, interface, sentimentos e painel. O registro cobre o que foi feito com o agente do Cursor nesta sessão de 30/10/2026. O modelo da conversa é o Grok 4.7.

### Ferramentas

- Cursor, com agente de código, para ler o repositório, alterar a interface e os testes, executar a classificação real das doze avaliações e a regressão T15, e redigir o relatório.
- API da OpenAI, configuração `principal` (`gpt-4o-mini`), nas doze avaliações e nos dois casos da T15. Essas chamadas são o sistema em avaliação, não o assistente de programação.

### Solicitações relevantes

1. Cruzar o enunciado com o código e dizer o que ainda faltava nos requisitos funcionais.
2. Completar a interface: indexar e incluir documento no acervo, mostrar a minuta com as fontes e abrir o painel de sentimentos com denominador, filtro vazio e gráfico.
3. Rodar a classificação real das doze avaliações, a regressão de um caso de texto e um de áudio, e preencher a matriz T01–T15 e as seções abertas do relatório.

### Sugestões aceitas, modificadas e rejeitadas

- **Aceitas:** inclusão de TXT e PDF no catálogo, com hash e versão; minuta que não preenche documento, prazo e local sem consulta fundamentada; painel que recalcula totais pelo código e mostra "sem dados" com denominador 0; teto da análise (duas chamadas) também na classificação de sentimento.
- **Modificada:** o gráfico. A sugestão era `st.bar_chart`. Nesta instalação o import da biblioteca de gráficos quebra no Python 3.14, então o painel desenha as barras em HTML, com a mesma contagem.
- **Rejeitada:** reclassificar AV09 e AV10 no código para bater no gabarito. O erro é do modelo ao propor a situação, e o relatório deixa os 10/12. Também não foi escrito um diário de uso de IA em nome da Ana: não há, no repositório, as solicitações que ela fez.

### Erros encontrados e como foram validados

- O primeiro desenho do painel quebrava o teste porque `st.bar_chart` importava uma biblioteca incompatível com este Python. O teste da tela passou a procurar as barras em HTML.
- A execução real errou AV09 (`neutra` → `indeterminada`) e AV10 (`negativa` → `indeterminada`). Os JSON estão em `resultados/metricas/rf22/execucao_20261030_181951/`. Não houve correção para forçar o rótulo.
- Testes sem API: `python -m unittest testes.test_rf16 testes.test_rf20_regras testes.test_rf20_telas testes.test_rf22`.

## 4. Declaração de responsabilidade

A equipe usou IA como apoio ao planejamento, à programação, aos testes e à documentação. Todas as
sugestões foram avaliadas, o código foi testado e o conteúdo, revisado. A equipe é responsável pelo
resultado entregue e é capaz de explicar e justificar cada decisão.
