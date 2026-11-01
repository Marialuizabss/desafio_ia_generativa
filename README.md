# Central Inteligente de Atendimento e Comunicação Institucional

**Desafio Prático 1 — Inteligência Artificial Generativa · FIC_DEV 2026**

Protótipo que recebe solicitações fictícias de matrícula por texto, áudio ou ficha digitalizada,
extrai os dados, monta uma minuta de resposta institucional e, depois da aprovação de um servidor,
entrega a minuta em PDF, uma versão em áudio e uma peça visual de orientação.

> **Nenhuma resposta é enviada automaticamente ao cidadão.** A decisão final é sempre do servidor
> responsável, e toda execução fica registrada.

Documentação completa e onde está cada requisito: [`documentacao/desafio-1/00_indice.md`](documentacao/desafio-1/00_indice.md).

## 1. O que o sistema faz

```
 1 Modelo        2 Envio                3 Revisão                      4 Minuta
 ───────────     ──────────────────     ───────────────────────────    ────────────────────────────
 escolhe o       texto, .txt, áudio     campos extraídos pela IA,      minuta montada com os campos;
 modelo e o      ou ficha (imagem       editáveis; em áudio e imagem,  servidor e cargo assinam;
 idioma          ou PDF), validados     conferência de nome,           Aprovar ou Rejeitar
                                        protocolo e datas com o
                                        original
                                                                       depois de aprovar:
                                                                       • PDF da minuta
                                                                       • áudio da minuta
                                                                       • peça "Passo a passo da matrícula"
```

Por trás das etapas: dados pessoais desnecessários (CPF, RG, e-mail, telefone, nascimento,
naturalidade e filiação) são removidos **antes** do envio ao provedor; o conteúdo do cidadão vai
delimitado e tratado como dado, não como instrução; e cada execução, revisão e decisão é gravada em
`resultados/logs/execucoes.jsonl`.

## 2. Stack de tecnologias

| Camada | Tecnologia | Versão | Para quê |
|---|---|---|---|
| Linguagem | Python | 3.13 | Todo o sistema |
| Interface | Streamlit | 1.66.0 | Tela em 4 etapas, revisão humana e downloads |
| IA (SDK) | OpenAI Python SDK (`openai`) | 3.33.0 | Todas as chamadas aos modelos |
| IA — texto | Responses API, `gpt-5.6-luna` | — | Extração dos campos com saída JSON estrita (`json_schema`) e `store: false` |
| IA — áudio | Audio API, `gpt-4o-transcribe` e `gpt-4o-mini-tts` | — | Transcrição da solicitação e voz da minuta aprovada |
| IA — visão | Chat Completions com imagem, `gpt-4o` | — | Leitura da ficha digitalizada |
| IA — imagem | Images API, `gpt-image-1` | — | Ilustração da peça de orientação |
| PDF | PyMuPDF | 1.28.2 | Leitura local de PDF com texto e geração do PDF da minuta |
| Imagem | Pillow | 12.3.0 | Montagem da peça com brasão e textos |
| Áudio | mutagen | 1.48.1 | Duração do áudio, sem chamar a API |
| Validação | Pydantic | 2.14.1 | Contrato da extração e validação estrita (RF14) |
| Índice vetorial | ChromaDB | 1.5.9 | Índice persistente do acervo (RF17) |
| Embeddings | sentence-transformers e PyTorch (só CPU) | 6.2.0 / 2.15.0 | Vetores dos trechos do acervo, sem chamar a API (RF17 a RF19) |
| Configuração | python-dotenv, JSON | 1.2.4 | Chave no `.env`; caminhos, modelos e parâmetros no `config.json` |
| Registro | JSON Lines | — | `resultados/logs/execucoes.jsonl`, uma linha por evento |
| Testes | pytest, unittest e `streamlit.testing` (AppTest) | 9.2.0 | Testes de regras, fluxo e cliques na interface, com a API simulada; rodam pelo pytest |
| Versionamento | Git e GitHub | — | Branches por integrante e entrega por `git archive` |
| Documentação | Markdown | — | README e `documentacao/` |

## 3. Requisitos

| RF | O que entrega | Onde ver |
|---|---|---|
| RF01 | `python -m src.main`, `config.json`, `.env` fora do git, versões registradas | Este README; `python -m src.versoes` |
| RF02 | Experimento com os prompts A, B e C; prompt B escolhido | `documentacao/desafio-1/rf02_engenharia_de_prompts.md` |
| RF03 | Prompt seguro, delimitação e testes de injection | `documentacao/desafio-1/rf03_prompt_seguro.md` |
| RF04 | Chamada à API com timeout, tratamento de falhas, tempo, tokens e custo; mensagens de falha em português também na transcrição, na voz e na leitura de imagem | `src/llm_client.py`, `src/erros_api.py` |
| RF05 | Extração estruturada em JSON com campos ausentes sinalizados | `src/extracao.py`, `dados/processados/` |
| RF06 | Transcrição com duração, idioma e modelo; conferência antes da minuta | `documentacao/desafio-1/rf06_transcricao.md` |
| RF07 | Áudio da minuta aprovada com instruções de entonação | `documentacao/desafio-1/rf07_voz_acessibilidade.md` |
| RF08 | Leitura da ficha por visão; confirmação humana dos dados críticos | `documentacao/desafio-1/rf08_visao_ocr.md` |
| RF09 | Minuta no modelo institucional, com origem e sem envio automático | `prompts/modelo_minuta.md`, `src/minuta_pdf.py` |
| RF10 | Peça de orientação com ilustração gerada por IA e revisada | `documentacao/desafio-1/rf10_imagem.md` |
| RF11 | Registro estruturado de execuções e decisões | `src/audit.py`, `resultados/logs/execucoes.jsonl` |
| RF12 | Minimização, inventário de dados pessoais e varredura da entrega | `documentacao/desafio-1/rf12_lgpd_privacidade.md` |
| RF13 | Protocolo de avaliação e avaliação dos 7 casos: 86% aprovados, 100% após correção | `documentacao/desafio-1/rf13_avaliacao_qualidade.md` |

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

Depois de criar o `.env`, abra o arquivo e preencha `OPENAI_API_KEY=` com a sua chave. O `.env` é
ignorado pelo git e **nunca** deve ser versionado nem mostrado.

No Windows, se a ativação for bloqueada, rode antes
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`.

O `python -m src.versoes` deve mostrar ✓ para o Python 3.13 e para cada biblioteca do
`requirements.txt` (versões na seção 2).

**PyTorch só para CPU.** O `requirements.txt` aponta o índice do PyTorch para CPU
(`--extra-index-url`), que instala cerca de 200 MB em vez dos mais de 3 GB da versão com CUDA; o
`src.versoes` mostra o torch como `2.15.0` mesmo instalado como `2.15.0+cpu`. Se a instalação
parar com "Não há espaço disponível no dispositivo", a pasta temporária do sistema encheu: rode
`mkdir -p ~/pip-tmp && TMPDIR=~/pip-tmp pip install -r requirements.txt` e depois apague `~/pip-tmp`.

## 5. Configuração

| Arquivo | O que define | Versionado? |
|---|---|---|
| `.env` | Só a chave `OPENAI_API_KEY` | **Não** |
| `config.json` | Caminhos das pastas, modelos de transcrição, leitura, voz e imagem, idioma, timeout, voz e instruções de entonação, limites de upload e custos estimados. Item ausente usa o valor padrão | Sim |
| `config/modelos.json` | Modelos de análise oferecidos na tela (padrão `gpt-5.6-luna`), com os parâmetros que cada um aceita | Sim |
| `prompts/modelo_minuta.md` | Modelo institucional da minuta | Sim |

## 6. Como usar

```bash
python -m src.main
```

O navegador abre em `http://localhost:8501`. Para experimentar, use os arquivos de
`dados/originais/`:

| Arquivo | O que mostra |
|---|---|
| `entrada_texto.txt` | Caso completo do professor: 6 dados pessoais removidos, 12/12 campos |
| `entrada_audio.mp3` | Transcrição, duração e conferência dos dados com o áudio original |
| `entrada_pdf-imagem.pdf` | Ficha manuscrita: a leitura erra o protocolo e a data, e o servidor corrige na conferência |
| `caso3_solicitacao_prompt_injection.txt` | Alerta de segurança; o ataque não entra na minuta |
| `caso2_solicitacao_incompleta.txt` | Campos ausentes marcados como "não localizado" |

Fluxo: escolha o modelo → envie o arquivo → revise os campos (e, em áudio ou imagem, confira os
quatro dados críticos) → preencha servidor e cargo → **Aprovar** ou **Rejeitar**. Depois de aprovar:
**Baixar PDF**, **Gerar áudio da minuta** e a **peça de orientação**.

As saídas ficam em `resultados/minutas/aprovadas/` (minuta e PDF), `resultados/audios/`,
`resultados/imagens/orientacao/` e `resultados/logs/execucoes.jsonl`.

## 7. Testes e verificações

| O quê | Comando | Chama a API? |
|---|---|---|
| Todos os testes (556) | `python -m pytest testes -q` | Não |
| Versões do Python e das bibliotecas | `python -m src.versoes` | Não |
| Varredura de credenciais e dados pessoais (RF12) | `python -m src.varredura_rf12` | Não |
| Avaliação dos 7 casos (RF13) | `python -m src.avaliacao_rf13 --todos` | Sim, ~US$ 0,03 |
| Nova ilustração da peça (RF10) | `python -m src.peca_orientacao gerar` | Sim, ~US$ 0,06 |
| Experimentos de prompt (RF02 e RF03) | `python -m src.experimento_rf02` · `python -m src.experimento_rf03` | Sim |

Os testes usam respostas simuladas e pastas temporárias: não gastam créditos nem alteram os
resultados do projeto. **Rode sempre pelo pytest:** o `testes/conftest.py` desvia o log de
auditoria e o índice nos testes do RAG (RF16, RF19, RF21 e vigência), e esse isolamento não vale
com `python -m unittest`.

## 8. Modelos e custos

| Etapa | Modelo | Custo observado | Tempo observado |
|---|---|---|---|
| Extração dos campos | `gpt-5.6-luna` (padrão) | US$ 0,0011 a 0,0017 por solicitação | 5,6 a 9,0 s |
| Transcrição do áudio | `gpt-4o-transcribe` | não registrado pelo sistema | 4,3 s para 89 s de áudio |
| Leitura da ficha | `gpt-4o` | não registrado pelo sistema | — |
| Voz da minuta | `gpt-4o-mini-tts` (alternativa `tts-1-hd`) | ~US$ 0,021 para 84,5 s de áudio | 14 s |
| Ilustração da peça | `gpt-image-1` | ~US$ 0,06 por versão, gerada uma vez | 21 a 24 s |

Os custos são estimativas calculadas com a tabela de preços em `src/llm_client.py` e no
`config.json`, a conferir com o provedor. Um atendimento completo por texto (extração, PDF e áudio)
custa cerca de **US$ 0,02**; o PDF e a peça de orientação não chamam a API.

## 9. Estrutura do projeto

```
desafio_ia_generativa/
├── README.md, requirements.txt, .python-version, .env.example, .gitignore
├── config.json                 caminhos, modelos e parâmetros (RF01)
├── config/modelos.json         modelos de análise da interface
├── dados/
│   ├── originais/              entradas fictícias e brasão (nunca alteradas)
│   ├── acervo/                 documentos institucionais fictícios (Desafio 2)
│   ├── avaliacoes/             avaliações de atendimento fictícias (Desafio 2)
│   ├── gabaritos/              resultados esperados de cada caso
│   └── processados/            transcrições, leituras e extrações
├── prompts/
│   ├── modelo_minuta.md        modelo institucional da minuta
│   ├── desafio1/rf02/          prompts do experimento do RF02
│   └── desafio2/               prompts versionados do Desafio 2
├── indice/                     índice vetorial do acervo (Desafio 2)
├── src/
│   ├── main.py, interface.py   ponto de entrada e interface
│   ├── fluxo.py                entrada → extração → revisão → minuta → aprovação
│   ├── llm_client.py           prompt de produção, chamada à API e montagem da minuta
│   ├── audio.py, vision.py     transcrição, voz e leitura de documentos
│   ├── erros_api.py            mensagens em português para falhas da API
│   ├── peca_orientacao.py      peça de orientação (RF10)
│   ├── minuta_pdf.py           PDF da minuta
│   ├── privacidade.py          minimização de dados pessoais (RF12)
│   ├── audit.py                registro das execuções (RF11)
│   ├── schemas.py              contrato e validação da extração (RF14)
│   ├── nlp.py                  resumo, categoria e entidades (RF15)
│   ├── configuracao.py, versoes.py
│   └── experimento_*, avaliacao_rf13.py, avaliacao_rf15.py, varredura_rf12.py   experimentos e verificações
├── resultados/                 minutas, áudios, imagens, avaliações, métricas e logs
├── testes/                     testes automatizados (pytest)
└── documentacao/
    ├── desafio-1/              índice, relatório técnico, registro de uso de IA e um documento por requisito
    └── desafio-2/              documentação do Desafio 2
```

## 10. Decisões

- **Prompt B no sistema (RF02):** foi o único fiel ao contexto, sem dados inventados e no formato
  institucional em todas as repetições, com dois modelos.
- **A minuta é montada pelo código, não escrita pela IA:** a IA extrai os campos e o código preenche
  o modelo institucional. O texto fixo nunca é alterado e um ataque de injection não consegue
  reescrever a resposta.
- **Dados pessoais saem antes do envio (RF12):** a minimização roda localmente; o modelo só recebe o
  que a minuta usa.
- **Conferência obrigatória em áudio e imagem:** transcrição e leitura erram nomes, números e datas;
  o servidor confere os quatro dados críticos com o original antes de a minuta ser montada.
- **A IA não escreve texto na peça visual (RF10):** ela gera só a ilustração; brasão e textos são do
  código. As tentativas com texto gerado saíram com palavras distorcidas.
- **Cada envio é uma execução nova (RF11):** mesmo quando a extração é reaproveitada, para que cada
  atendimento tenha a sua revisão e a sua decisão no registro.
- **Reaproveitamento só com a mesma versão do prompt:** evita entregar uma extração feita com um
  prompt antigo.
- **`gpt-5.6-luna` como padrão:** modelo de raciocínio de baixo custo, escolhido na integração e
  avaliado nos 7 casos do RF13 (86% aprovados, 100% após correção). Os experimentos do RF02 e do RF03
  foram feitos com o `gpt-6-luna` e continuam documentados com ele.

## 11. Limitações

- **Letra manuscrita:** a leitura da ficha erra o ano do protocolo e a data de forma sistemática;
  a correção depende do servidor.
- **Envio ao provedor:** o áudio e a imagem da ficha vão inteiros para transcrição e leitura, e a
  minuta aprovada vai para a API de voz; processamento local seria preferível em produção (RF08 e
  RF12).
- **Transcrição:** erra nomes e símbolos (no áudio de teste, repetiu "noturno" e perdeu o "@" do
  e-mail); a conferência dos dados críticos com o áudio original é obrigatória.
- **Voz sintética:** não atende pessoas surdas; a naturalidade e a pronúncia de nomes ainda podem
  falhar.
- **Avaliação limitada:** 7 casos, todos de matrícula; resistência a injection medida em dois ataques
  e revisão feita por uma única revisora.
- **Verificação automática por padrões de texto:** não detecta invenção escrita de forma não prevista.
- **Custos estimados** pela tabela de preços, não pela fatura do provedor.
- **Acessibilidade da própria interface** não foi testada com leitores de tela.

## 12. Segurança e privacidade

- Somente dados fictícios.
- Chave da API só no `.env`, fora do git; o registro mascara qualquer texto com formato de chave.
- Conteúdo do cidadão delimitado e tratado como dado; alertas de injection destacados na revisão.
- Nenhum envio automático; a minuta só é salva depois da aprovação do servidor.
- Entrega gerada com `git archive --format=zip -o entrega.zip HEAD`, que não inclui o `.env`.
- Retenção (RF24): prazo, destino e forma de cada dado na seção 11 de [`documentacao/desafio-2/contratos_dados.md`](documentacao/desafio-2/contratos_dados.md).

Detalhes em [`documentacao/desafio-1/rf12_lgpd_privacidade.md`](documentacao/desafio-1/rf12_lgpd_privacidade.md).

## 13. Equipe e uso de IA

| Integrante | Responsabilidades |
|---|---|
| Ana Beatriz Schuindt do Amaral | Casos de teste e gabaritos; experimento de prompts (RF02); prompt seguro (RF03); registro e rastreabilidade (RF11); LGPD (RF12); avaliação de qualidade (RF13); integração final: revisão humana na interface, conferência dos dados críticos, PDF da minuta aprovada, áudio da minuta e peça de orientação; documentação |
| Maria Luiza Batista de Souza | Transcrição (RF06), síntese de voz (RF07), visão e OCR (RF08) e primeiras versões da imagem (RF10); mensagens de falha da API em português nesses módulos (`src/erros_api.py`); testes reais pela interface |
| Felipe Ferreira Aguiar | Inicialização e configuração (RF01), chamada à API (RF04), extração (RF05), minuta e primeira versão do PDF (RF09) e interface em etapas |

O desenvolvimento teve apoio de ferramentas de IA. Ana Beatriz usou o **Claude Code** para auxiliar
o desenvolvimento, criar a estrutura de diretórios esperada, sugerir a arquitetura, sugerir como
documentar cada etapa, acompanhar os requisitos funcionais obrigatórios e manter o trabalho dentro
do escopo. Maria Luiza usou o **ChatGPT** na construção dos RF06, RF07, RF08 e RF10 (análise de erros,
revisão de código, testes e documentação) e o **Claude** na verificação final, na análise das branches e
no tratamento de falhas da API. Todo código e todo conteúdo gerado com apoio de IA foram revisados e
testados pela equipe.
O registro completo está em [`documentacao/desafio-1/02_registro_uso_ia.md`](documentacao/desafio-1/02_registro_uso_ia.md).

## 14. Desafio 2

Formato dos dados: [`documentacao/desafio-2/contratos_dados.md`](documentacao/desafio-2/contratos_dados.md).
Relatório: [`documentacao/desafio-2/01_relatorio_tecnico.md`](documentacao/desafio-2/01_relatorio_tecnico.md).

### Compreensão da solicitação (RF14 e RF15)

Uma chamada extrai campos, resumo, categoria e entidades. A saída é validada em três camadas (JSON,
esquema Pydantic e regras de negócio); inválida ou incoerente, a minuta é bloqueada.

| O quê | Comando | Chama a API? |
|---|---|---|
| Testes | `python -m pytest testes/test_rf14.py testes/test_rf15.py -q` | Não |
| JSON sintático × esquema (T01) | `python -m src.experimento_rf14` | Não |
| Avaliação simulada | `python -m src.avaliacao_rf15 --simulado` | Não |
| Avaliação real dos 7 casos | `python -m src.avaliacao_rf15 --todos` | Sim, ~US$ 0,007 |
| Métricas finais | `python -m src.avaliacao_rf15 --consolidar PASTA` | Não |

Conferência humana: rode `--todos`, preencha `decisao` no `conferencia_rf15.json` da pasta gerada e
rode `--consolidar` com essa pasta. Resultados em `resultados/metricas/rf14_comparacao.md` e
`resultados/metricas/rf15/execucao_*/`.

### Acervo, índice e RAG (RF17 a RF19, RF21 e RF24)

Acervo de nove documentos (edital, seis retificações e dois TXT fictícios) catalogados em
`dados/acervo/acervo.json`. O índice é um ChromaDB local em `dados/indice_vetorial/` (não vai para o
git), com embeddings `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões, distância cosseno, limite
de 128 tokens por trecho). O modelo é baixado na primeira execução e depois roda localmente.

```
pip install -r requirements.txt
python -m src.indexar                      # indexa o acervo (pode repetir: não duplica)
python -m src.indexar --status             # documentos, chunks e versão do índice
python -m src.indexar --excluir ACV-09 --motivo "retenção encerrada"   # motivo obrigatório
python -m src.indexar --restaurar ACV-09   # tira da lista de excluídos e reindexa
python -m src.avaliacao_rf18               # compara 3 configurações de chunking (RF18)
python -m src.avaliacao_rag --repeticoes 3 # oito perguntas do RAG, três rodadas (usa a API)
python -m pytest testes -q                 # testes (não usam a API nem baixam o modelo)
```

Consulta ao RAG, com a configuração de geração escolhida em `config.json`:

```python
from src.rf19_complemento import responder_rf19

resultado = responder_rf19("Quando começam as aulas de Agropecuária em Mimoso?", top_k=15)
# nome_configuracao="forte" usa outro modelo; "simulada" não chama a API (só se abstém)
print(resultado["status"], resultado["decisao"], resultado["fontes"], resultado["id_consulta"])
```

`status` é `fundamentada`, `sem_evidencia` ou `conflito`; `decisao` é `responder` ou `revisar`. Cada
consulta é gravada em `resultados/logs/execucoes.jsonl` (evento `consulta_rag`, com versões, trechos
recuperados, tempos e custos, sem chave de API e com identificadores mascarados). Trocar a
configuração de geração não reconstrói o índice. Detalhes, resultados e limitações:
`documentacao/desafio-2/01_relatorio_tecnico.md`, seções 4 e 5.

Antes de cada consulta, o índice é conferido com o catálogo (`doc_id` e hash de cada documento).
Índice vazio, documento não indexado, desatualizado ou fora do catálogo bloqueiam a consulta sem
chamar o modelo, com o motivo e o que fazer. A tela Acervo mostra a situação de cada documento, já
marca os pendentes em "Indexar selecionados" e oferece "Remover do índice" para o que está fora do
catálogo. `python -m src.indexar --status` traz a mesma conferência.

A exclusão de documento (RF24, T14) dura: fica registrada em `dados/acervo/exclusoes.json`, com
data, motivo e responsável, e a indexação pula o documento até ele ser restaurado. A tela Acervo
também exclui (com responsável, motivo e confirmação) e restaura, e lista os resultados derivados
que citam o documento excluído. A aplicação não tem login: o responsável é declarado, não
autenticado.

### Sentimentos e painel (RF22)

O classificador pede ao modelo a situação e a polaridade, e o código aplica as regras de mensagem
mista, ironia, falta de contexto e instrução no texto. A confiança fica registrada como estimativa
não calibrada e não entra no percentual. O painel calcula totais, fração e denominador; filtro
vazio mostra "sem dados".

| O quê | Comando | Chama a API? |
|---|---|---|
| Testes | `python -m pytest testes/test_rf22.py -q` | Não |
| Avaliação simulada das 12 | `python -m src.avaliacao_rf22 --simulado` | Não |
| Avaliação real | `python -m src.avaliacao_rf22 --todos` | Sim, configuração `principal` |

Resultados em `resultados/metricas/rf22/execucao_*/`. Detalhes na seção 8 de
`documentacao/desafio-2/01_relatorio_tecnico.md`.

### Guardrails (RF16)

A moderação é por regras, em `src/guardrails.py`, sem chamada extra ao modelo. Vale para a análise da solicitação e para a pergunta do RAG. Segredo, texto vazio, tipo errado ou tamanho acima do limite bloqueiam e o modelo não é chamado. Injeção na solicitação ou na pergunta segue o atendimento, com alerta e revisão. Resposta com valor no formato de chave de API é descartada. Cada bloqueio fica em `resultados/logs/execucoes.jsonl` (motivo, origem e hash do texto, sem o trecho).

O teto é por atendimento: análise e cada classificação de sentimento, 2 chamadas e 8 000 tokens; RAG, 3 chamadas e 60 000 tokens. A repetição de rede continua uma. A segunda chamada do sentimento é a correção da saída inválida.

| O quê | Comando | Chama a API? |
|---|---|---|
| Testes | `python -m pytest testes/test_rf16.py -q` | Não |

Detalhes na seção 6 de `documentacao/desafio-2/01_relatorio_tecnico.md`.

### Interface (RF20)

`python -m src.main` abre a interface. A barra lateral tem Ficha, Acervo, Consulta, Fontes, Painel e Atendimento anterior. A Ficha é a área padrão e o fluxo oficial; o atendimento do Desafio 1 fica em "Atendimento anterior", com aviso de que não passa pela validação, pelo acervo nem pela moderação. A Ficha recebe só texto digitado; áudio e imagem ainda entram pelo Atendimento anterior. No acervo dá para indexar os documentos selecionados e incluir um TXT ou PDF fictício. A ficha mostra ausência como "não localizado" e a minuta, com a participação da IA no rodapé. Em pedido de matrícula, "Buscar orientações no acervo" faz três consultas (documentos, local e período) só para aquela ficha e mostra a pergunta, o status e as fontes de cada uma; as respostas fundamentadas entram na minuta com as fontes, e sem evidência ou conflito vai para revisão, sem resposta inventada. Sem essa busca, a minuta não preenche documento, prazo nem local; nas outras categorias a busca não se aplica e a ficha vai para revisão. Na revisão, o servidor corrige os campos da ficha (data impossível ou incoerente bloqueia; o que não está no texto original fica como "informado pelo servidor") e pode editar o texto da minuta, sem tirar o aviso de participação da IA. Se as orientações não vieram todas fundamentadas, a seção Orientações traz um recado para o servidor e só aprova depois de reescrita. Ao aprovar, a minuta é assinada e salva em `resultados/minutas/rf20/`, sem sobrescrever. Analisar outra solicitação começa um atendimento novo, e aprovar ou rejeitar na Ficha encerra o atendimento: aparece um aviso de sucesso e a Ficha volta vazia. A área Consulta é livre e não entra na minuta. Alerta de segurança aparece numa caixa vermelha (🚨), com uma linha para o que a regra detectou e outra para o que o modelo apontou; na Consulta, a caixa avisa quando um trecho do acervo com instrução ao assistente foi retirado do contexto. Entrada bloqueada aparece em vermelho com 🚫. Falha do serviço e índice desatualizado aparecem em português e não geram resposta. O painel conta polaridade, fração e denominador, desenha o gráfico e, com filtro vazio, mostra "sem dados". A decisão do servidor é `pendente`, `aprovada`, `rejeitada` ou `revisar`; `aprovada` e `rejeitada` encerram o atendimento e o registro não é reescrito.

| O quê | Comando | Chama a API? |
|---|---|---|
| Testes | `python -m pytest testes/test_rf20_regras.py testes/test_rf20_telas.py -q` | Não |
| Interface | `python -m src.main` | Só ao analisar ou consultar |

Código: `src/consulta_acervo.py`, `src/acervo_operacao.py`, `src/painel.py` e `src/telas_rf20.py`. A matriz T01–T15 está em `documentacao/desafio-2/03_matriz_testes.md`. Detalhes nas seções 7 a 13 de `documentacao/desafio-2/01_relatorio_tecnico.md`.

---

*Projeto desenvolvido para fins educacionais, com uso de inteligência artificial generativa e supervisão humana.*