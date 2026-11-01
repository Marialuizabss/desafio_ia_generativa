# Central Inteligente de Atendimento e Comunicação Institucional

**Desafio Prático 2 — Inteligência Artificial Generativa · FIC_DEV 2026**

**Equipe:** Ana Beatriz Schuindt do Amaral, Maria Luiza Batista de Souza e Felipe Ferreira Aguiar.

**Turma:** noturna.

Continuação do Desafio 1. A central que extraía os dados de solicitações fictícias de matrícula e
montava uma minuta agora valida a solicitação por esquema, resume e classifica, consulta um acervo
institucional indexado (RAG) com citação das fontes, aplica guardrails, classifica avaliações de
atendimento e registra cada etapa para auditoria.

> **Nenhuma resposta é enviada automaticamente ao cidadão.** Sem evidência no acervo, o sistema não
> inventa prazo, local nem autoridade: encaminha ao servidor, que corrige, aprova ou rejeita.

| Documento | Onde |
|---|---|
| Relatório técnico (arquitetura, provedor, métricas, custos, privacidade, limitações) | [`documentacao/desafio-2/01_relatorio_tecnico.md`](documentacao/desafio-2/01_relatorio_tecnico.md) |
| Registro do uso de IA | [`documentacao/desafio-2/02_registro_uso_ia.md`](documentacao/desafio-2/02_registro_uso_ia.md) |
| Matriz de testes T01–T15 e métricas do RF23 | [`documentacao/desafio-2/03_matriz_testes.md`](documentacao/desafio-2/03_matriz_testes.md) |
| Contratos de dados, regras e retenção | [`documentacao/desafio-2/contratos_dados.md`](documentacao/desafio-2/contratos_dados.md) |
| Documentação do Desafio 1 | [`documentacao/desafio-1/00_indice.md`](documentacao/desafio-1/00_indice.md) |

## 1. O que o sistema faz

```
 Ficha                                                              Revisão
 ─────────────────────────────────────────────────────────────────  ─────────────────────────
 solicitação  →  guardrails  →  compreensão  →  orientações  →  minuta  →  servidor corrige,
 (texto)         segredo,       JSON validado,   3 consultas     com fontes  edita e aprova
                 escopo,        resumo,          ao acervo       e aviso de  ou rejeita
                 tamanho        categoria e      (RAG) com       IA          (nada é enviado)
                                entidades        citações

 Acervo: indexar, incluir, excluir e restaurar documentos   Consulta e Fontes: pergunta livre,
 Painel: sentimentos das avaliações, com denominador        top-k e distância de cada trecho
```

Por trás: dados pessoais saem do texto antes do provedor; o conteúdo do cidadão e o do acervo são
tratados como dado, nunca como instrução; cada análise, consulta, bloqueio e decisão é gravada em
`resultados/logs/execucoes.jsonl`, sem chave de API e sem o texto da solicitação.

## 2. Requisitos do Desafio 2

| RF | O que entrega | Onde ver |
|---|---|---|
| RF14 | Contrato Pydantic estrito; validação de JSON, esquema e regras de negócio; minuta bloqueada se inválida | Relatório §2.2 · `src/schemas.py` |
| RF15 | Resumo, categoria e entidades, com conferência humana | Relatório §2.2 e §4 · `src/nlp.py` |
| RF16 | Moderação por regras: segredo, injeção, escopo, tipo e tamanho; teto de chamadas e tokens | Relatório §2.3 · `src/guardrails.py` |
| RF17 | Índice ChromaDB persistente, sem duplicação; top-k e distância na tela | Relatório §2.4 · `src/vector_store.py` |
| RF18 | Três configurações de chunking comparadas; 800/100 escolhida | Relatório §2.5 |
| RF19 | RAG com citações, vigência das retificações, abstenção e conflito | Relatório §2.6 · `src/rf19_complemento.py` |
| RF20 | Interface Streamlit com Ficha, Acervo, Consulta, Fontes e Painel | Relatório §2.7 · seção 7 abaixo |
| RF21 | Quatro configurações de geração com o mesmo índice; auditoria de cada consulta | Relatório §3 · `src/provider_adapter.py` |
| RF22 | 12 avaliações classificadas; painel com totais e denominador | Relatório §2.8 · `src/sentimentos.py`, `src/painel.py` |
| RF23 | Matriz T01–T15, métricas com numerador e denominador, regressão do Desafio 1 | Matriz · Relatório §4 |
| RF24 | Retenção, exclusão de documento que dura, revisão humana e IA identificada | Relatório §6 · `contratos_dados.md` §11 |

## 3. Stack

| Camada | Tecnologia | Versão | Para quê |
|---|---|---|---|
| Linguagem | Python | 3.13 | Todo o sistema |
| Interface | Streamlit | 1.66.0 | Telas e revisão humana |
| IA | OpenAI Python SDK | 3.33.0 | Análise da solicitação (`gpt-5.6-luna`); RAG e sentimentos (`gpt-4o-mini`, configurável) |
| Validação | Pydantic | 2.14.1 | Contrato estrito (RF14) |
| Índice vetorial | ChromaDB | 1.5.9 | Índice persistente do acervo (RF17) |
| Embeddings | sentence-transformers e PyTorch (só CPU) | 6.2.0 / 2.15.0 | `paraphrase-multilingual-MiniLM-L12-v2`, local, sem API |
| PDF | PyMuPDF | 1.28.2 | Texto dos PDFs do acervo |
| Configuração | python-dotenv, JSON | 1.2.4 | Chave no `.env`; o resto no `config.json` |
| Testes | pytest e `streamlit.testing` (AppTest) | 9.2.0 | 567 testes, com a API simulada |

O áudio, a visão e a imagem do Desafio 1 continuam no projeto (seção 13).

## 4. Instalação

**Pré-requisitos:** Python 3.13, git e uma chave da API da OpenAI.

| Passo | Linux / macOS | Windows (PowerShell) |
|---|---|---|
| Baixar o projeto | `git clone https://github.com/Marialuizabss/desafio_ia_generativa.git`<br>`cd desafio_ia_generativa` | o mesmo |
| Criar o ambiente | `python3.13 -m venv .venv` | `py -3.13 -m venv .venv` |
| Ativar o ambiente | `source .venv/bin/activate` | `.\.venv\Scripts\Activate.ps1` |
| Instalar as dependências | `pip install -r requirements.txt` | o mesmo |
| Criar o `.env` | `cp .env.example .env` | `Copy-Item .env.example .env` |
| Conferir as versões | `python -m src.versoes` | o mesmo |

Abra o `.env` e preencha `OPENAI_API_KEY=` com a sua chave. O `.env` é ignorado pelo git e **nunca**
deve ser versionado nem mostrado.

O `requirements.txt` instala o PyTorch só para CPU (cerca de 200 MB, em vez de mais de 3 GB). Se a
instalação parar com "Não há espaço disponível no dispositivo", rode
`mkdir -p ~/pip-tmp && TMPDIR=~/pip-tmp pip install -r requirements.txt` e depois apague `~/pip-tmp`.
No Windows, se a ativação for bloqueada, rode antes
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`.

## 5. Configuração

| Arquivo | O que define | Versionado? |
|---|---|---|
| `.env` | Só a chave `OPENAI_API_KEY` | **Não** |
| `config.json` | `adaptador_llm`: as configurações de geração (`principal`, `alternativa`, `forte` e `simulada`), tempo limite e repetição. `guardrails`: teto de chamadas e tokens por atendimento. `parametros`: limites de texto e de arquivo. Também caminhos e modelos do Desafio 1 | Sim |
| `config/modelos.json` | Modelo da análise da solicitação (padrão `gpt-5.6-luna`) | Sim |
| `dados/acervo/acervo.json` | Catálogo do acervo: título, versão, ordem, o que cada retificação altera e hash | Sim |
| `dados/acervo/exclusoes.json` | Documentos excluídos, com data, motivo e responsável | Sim |

## 6. Indexação

O índice fica em `dados/indice_vetorial/`, fora do git. **Indexe antes do primeiro uso.** Na primeira
vez, o modelo de embeddings é baixado; depois roda na máquina.

```bash
python -m src.indexar                    # indexa o acervo (pode repetir: não duplica)
python -m src.indexar --status           # documentos, trechos, versão e conferência com o catálogo
python -m src.indexar --excluir ACV-09 --motivo "retenção encerrada" --responsavel "Nome"
python -m src.indexar --restaurar ACV-09 # tira da lista de excluídos e reindexa
```

Antes de cada consulta, o índice é conferido com o catálogo. Índice vazio, documento não indexado,
desatualizado ou fora do catálogo bloqueiam a consulta, com o motivo e o que fazer. A exclusão dura:
reindexar não traz o documento de volta, só a restauração. A tela Acervo faz o mesmo que esses
comandos.

## 7. Uso no Streamlit

```bash
python -m src.main
```

O navegador abre em `http://localhost:8501`. A barra lateral tem as áreas:

| Área | O que faz |
|---|---|
| **Ficha** (padrão) | Fluxo oficial: analisa o texto, mostra a ficha e os alertas, busca as orientações no acervo (pedidos de matrícula), monta a minuta e registra a decisão. Na revisão, o servidor corrige campos e edita a minuta |
| **Acervo** | Situação de cada documento no índice; indexar, incluir TXT ou PDF fictício, remover do índice, excluir e restaurar |
| **Consulta** | Pergunta livre ao acervo, com top-k (padrão 15). Não entra na minuta |
| **Fontes** | Trechos citados na última consulta, com distância e similaridade (quanto menor a distância, mais parecido; não é garantia de verdade) |
| **Painel** | Sentimentos das 12 avaliações: totais, fração, denominador e gráfico, com filtros |
| **Atendimento anterior** | O fluxo do Desafio 1 (texto, áudio e ficha digitalizada), com aviso de que não passa pela validação, pelo acervo nem pela moderação |

**Roteiro de demonstração** (a Ficha recebe texto digitado; cole o conteúdo dos arquivos de
`dados/originais/`):

1. **Ficha** com `caso8_solicitacao_coerente_acervo.txt` → Analisar → Buscar orientações no acervo →
   conferir a minuta com as fontes → Aprovar com nome e cargo. A minuta assinada vai para
   `resultados/minutas/rf20/`.
2. **Ficha** com `caso3_solicitacao_prompt_injection.txt` → alerta vermelho (🚨) e caso em revisão.
3. **Ficha** ou **Consulta** com `adv03_tentativa_segredo.txt` ou "Vocês vendem uniforme?" → bloqueado
   (🚫) sem chamar o modelo.
4. **Consulta** "Quando começam as aulas de Agropecuária em Mimoso?" → resposta fundamentada; em
   **Fontes**, o trecho do ACV-07 com a distância.
5. **Acervo**: excluir o ACV-09 com motivo → consultar a pesquisa socioeconômica → restaurar.
6. **Painel**: filtrar por canal e ver "sem dados" num filtro vazio.

## 8. Testes e avaliações

| O quê | Comando | Chama a API? |
|---|---|---|
| Todos os testes (567) | `python -m pytest testes -q` | Não |
| Varredura de credenciais e dados pessoais (RF12) | `python -m src.varredura_rf12` | Não |
| JSON sintático × esquema (T01) | `python -m src.experimento_rf14` | Não |
| Ficha: 7 solicitações (RF15) | `python -m src.avaliacao_rf15 --todos` (ou `--simulado`) | Sim, cerca de US$ 0,007 (simulado: não) |
| Chunking: 3 configurações (RF18) | `python -m src.avaliacao_rf18` | Não (baixa o modelo de embeddings) |
| RAG: 8 perguntas, 3 rodadas (RF19) | `python -m src.avaliacao_rag --repeticoes 3` (`--configuracao forte`, `--top-k N`) | Sim, cerca de US$ 0,04 |
| Reavaliar respostas gravadas | `python -m src.reavaliar_elementos PASTA` | Não |
| Minuta fundamentada do CASO-08 | `python -m src.minuta_fundamentada --caso CASO-08` | Sim, 3 consultas |
| Sentimentos: 12 avaliações (RF22) | `python -m src.avaliacao_rf22 --todos` (ou `--simulado`) | Sim, cerca de US$ 0,002 (simulado: não) |
| Regressão do Desafio 1 (T15) | `python -m src.regressao_t15` | Sim, 2 análises |

Os testes usam respostas simuladas e pastas temporárias. **Rode sempre pelo pytest:** o
`testes/conftest.py` desvia o log, o índice, as exclusões e as minutas, e esse isolamento não vale com
`python -m unittest`. Os resultados reais ficam em `resultados/` (seção 9).

## 9. Estrutura do projeto

```
desafio_ia_generativa/
├── README.md, requirements.txt, config.json, config/modelos.json, .env.example
├── dados/
│   ├── originais/           solicitações fictícias, ataque ADV-03 e perguntas do RAG
│   ├── acervo/              edital, 6 retificações, 2 TXT fictícios, acervo.json e exclusoes.json
│   ├── avaliacoes/          12 avaliações fictícias e o conjunto com duplicata
│   ├── gabaritos/           solicitações, RAG, ataques e avaliações
│   └── indice_vetorial/     índice ChromaDB (fora do git; recriado por src.indexar)
├── prompts/desafio2/        extração v2 e v2.1, sentimento v1
├── src/
│   ├── main.py, interface.py, telas_rf20.py         interface (RF20)
│   ├── consulta_acervo.py, acervo_operacao.py       regras das telas, inclusão e indexação
│   ├── schemas.py, nlp.py                           contrato, validação e ficha (RF14, RF15)
│   ├── guardrails.py, privacidade.py                moderação, limites e minimização (RF16)
│   ├── ingestion.py, vector_store.py, indexar.py    acervo, índice e exclusão (RF17, RF24)
│   ├── rag.py, rf19_complemento.py, vigencia.py     RAG com fontes (RF19)
│   ├── provider_adapter.py, auditoria_rag.py        provedor e auditoria (RF21)
│   ├── sentimentos.py, painel.py                    sentimentos e painel (RF22)
│   ├── avaliacao_*.py, regressao_t15.py, varredura_rf12.py   avaliações e verificações
│   └── fluxo.py, llm_client.py, audio.py, vision.py…  módulos do Desafio 1, reaproveitados
├── resultados/
│   ├── rag/                 execuções das 8 perguntas
│   ├── metricas/            RF14, RF15, RF18, RF22 e T15
│   ├── minutas/rf20/        minutas aprovadas na Ficha
│   └── logs/                execucoes.jsonl e varredura_rf12.md
├── testes/                  testes automatizados (pytest), sem API
└── documentacao/
    ├── desafio-2/           relatório, matriz, contratos de dados e registro de uso de IA
    └── desafio-1/           documentação do Desafio 1
```

## 10. Limitações

As principais; a lista completa está na seção 8 do relatório.

- **A Ficha recebe só texto.** Áudio e imagem entram pelo Atendimento anterior, do Desafio 1, que não
  passa pela validação do RF14, pelo acervo nem pela moderação.
- **Completude do RAG:** com o `gpt-4o-mini`, P01 e P02 omitem condições do edital (completas em 10/15
  respostas). Nada é inventado: as 15 respostas fundamentadas têm as afirmações sustentadas.
- **Falsos conflitos:** pergunta sem o curso, quando uma retificação muda só alguns cursos, vira
  conflito e vai para revisão. Com o curso na pergunta, a resposta sai fundamentada.
- **Guardrails por padrões:** o escopo cobre só venda ou preço de uniforme; a quarentena reconhece as
  formulações previstas; o teto de chamadas tem evidência só por teste.
- **Embeddings truncados em 128 tokens**, PDF lido sem OCR e busca só semântica.
- **Sentimentos:** a situação é proposta pelo modelo (AV09 e AV10 erradas) e a confiança não é
  calibrada.
- **T15:** os dois casos do Desafio 1 chegaram à minuta, mas a revisão humana deles não foi feita.
- **Avaliações pequenas** (7 solicitações, 8 perguntas, 12 avaliações, uma revisora) e **custos
  estimados** pela tabela de preços, não pela fatura.

## 11. Segurança e privacidade

- **Dados fictícios:** solicitações, avaliações, gabaritos e os TXT do acervo (ACV-08 e ACV-09). A
  exceção são o edital nº 006/2026 da SECITECI-MT e as seis retificações (ACV-01 a ACV-07):
  documentos oficiais públicos, anexados pelo professor como acervo. Não trazem dados de cidadãos,
  só contato institucional e a assinatura da autoridade.
- Chave da API só no `.env`, fora do git; o log mascara qualquer texto no formato de chave.
- Dados pessoais saem do texto antes do provedor; o log guarda o hash do texto da solicitação.
- Varredura do RF12 aprovada em 01/11/2026: sem chave, credencial ou CPF de dígito válido.
- Retenção (RF24): prazo, destino e forma de cada dado na seção 11 de
  [`contratos_dados.md`](documentacao/desafio-2/contratos_dados.md); exclusão de documento com motivo
  e responsável.
- Nenhum envio automático; a minuta identifica a participação da IA.
- Entrega gerada com `git archive --format=zip -o entrega.zip HEAD`, que não inclui o `.env`.

## 12. Equipe e uso de IA

| Integrante | Responsabilidades no Desafio 2 |
|---|---|
| Ana Beatriz Schuindt do Amaral | Estudante 1: dados fictícios e gabaritos; contrato e validação (RF14); resumo, categoria e entidades (RF15); integração da Ficha com o acervo, revisão humana e alertas (RF20); conferência do índice, exclusão que dura e top-k na tela (RF17, RF24); retenção (RF24); matriz e documentação (RF23) |
| Maria Luiza Batista de Souza | Estudante 2: acervo e catálogo; índice vetorial (RF17); chunking (RF18); RAG com fontes e minuta fundamentada (RF19); provedor configurável e auditoria (RF21); exclusão de documento (RF24) |
| Felipe Ferreira Aguiar | Estudante 3: guardrails, escopo e tetos (RF16); telas da interface (RF20); sentimentos e painel (RF22); regressão T15 (RF23) |

O desenvolvimento teve apoio de ferramentas de IA: Ana Beatriz usou o **Claude Code** (Claude Opus
5.5), Maria Luiza o **Claude** (Claude Sonnet 5.5) e Felipe o **Cursor** (Grok 4.7). Todo código e
conteúdo sugerido foi revisado e testado pela equipe. O registro está em
[`documentacao/desafio-2/02_registro_uso_ia.md`](documentacao/desafio-2/02_registro_uso_ia.md); o do
Desafio 1, em [`documentacao/desafio-1/02_registro_uso_ia.md`](documentacao/desafio-1/02_registro_uso_ia.md).

## 13. Desafio 1 em resumo

O Desafio 2 continua o protótipo do Desafio 1 e reaproveita a configuração, os prompts seguros, o
tratamento de falhas, a minimização de dados e o registro de execuções, como pede o enunciado.

No Desafio 1, a central recebia uma solicitação por texto, áudio ou ficha digitalizada, extraía os
campos, montava a minuta no modelo institucional e, depois da aprovação do servidor, gerava o PDF, a
versão em áudio e uma peça visual de orientação (RF01 a RF13). A avaliação dos 7 casos aprovou 86%,
e 100% depois da correção pelo servidor. Esse fluxo continua disponível na área "Atendimento
anterior".

Requisitos, decisões, custos e limitações do Desafio 1:
[`documentacao/desafio-1/00_indice.md`](documentacao/desafio-1/00_indice.md).

---

*Projeto desenvolvido para fins educacionais, com uso de inteligência artificial generativa e supervisão humana.*
