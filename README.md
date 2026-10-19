# Central Inteligente de Atendimento e Comunicação Institucional

**Desafio Prático 1 — Inteligência Artificial Generativa · FIC_DEV 2026**

Protótipo que recebe solicitações fictícias de matrícula por texto, áudio ou ficha digitalizada,
extrai os dados, monta uma minuta de resposta institucional e, depois da aprovação de um servidor,
entrega a minuta em PDF, uma versão em áudio e uma peça visual de orientação.

> **Nenhuma resposta é enviada automaticamente ao cidadão.** A decisão final é sempre do servidor
> responsável, e toda execução fica registrada.

Documentação completa e onde está cada requisito: [`documentacao/00_indice.md`](documentacao/00_indice.md).

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
| Configuração | python-dotenv, JSON | 1.2.4 | Chave no `.env`; caminhos, modelos e parâmetros no `config.json` |
| Registro | JSON Lines | — | `resultados/logs/execucoes.jsonl`, uma linha por evento |
| Testes | unittest e `streamlit.testing` (AppTest) | — | Testes de regras, fluxo e cliques na interface, com a API simulada |
| Versionamento | Git e GitHub | — | Branches por integrante e entrega por `git archive` |
| Documentação | Markdown | — | README e `documentacao/` |

## 3. Requisitos

| RF | O que entrega | Onde ver |
|---|---|---|
| RF01 | `python -m src.main`, `config.json`, `.env` fora do git, versões registradas | Este README; `python -m src.versoes` |
| RF02 | Experimento com os prompts A, B e C; prompt B escolhido | `documentacao/rf02_engenharia_de_prompts.md` |
| RF03 | Prompt seguro, delimitação e testes de injection | `documentacao/rf03_prompt_seguro.md` |
| RF04 | Chamada à API com timeout, tratamento de falhas, tempo, tokens e custo | `src/llm_client.py` |
| RF05 | Extração estruturada em JSON com campos ausentes sinalizados | `src/extracao.py`, `dados/processados/` |
| RF06 | Transcrição com duração, idioma e modelo; conferência antes da minuta | `documentacao/rf06_transcricao.md` |
| RF07 | Áudio da minuta aprovada com instruções de entonação | `documentacao/rf07_voz_acessibilidade.md` |
| RF08 | Leitura da ficha por visão; confirmação humana dos dados críticos | `documentacao/rf08_visao_ocr.md` |
| RF09 | Minuta no modelo institucional, com origem e sem envio automático | `prompts/modelo_minuta.md`, `src/minuta_pdf.py` |
| RF10 | Peça de orientação com ilustração gerada por IA e revisada | `documentacao/rf10_imagem.md` |
| RF11 | Registro estruturado de execuções e decisões | `src/audit.py`, `resultados/logs/execucoes.jsonl` |
| RF12 | Minimização, inventário de dados pessoais e varredura da entrega | `documentacao/rf12_lgpd_privacidade.md` |
| RF13 | Protocolo de avaliação e avaliação dos 7 casos: 86% aprovados, 100% após correção | `documentacao/rf13_avaliacao_qualidade.md` |

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
| Todos os testes (172) | `python -m unittest discover -s testes -t .` | Não |
| Versões do Python e das bibliotecas | `python -m src.versoes` | Não |
| Varredura de credenciais e dados pessoais (RF12) | `python -m src.varredura_rf12` | Não |
| Avaliação dos 7 casos (RF13) | `python -m src.avaliacao_rf13 --todos` | Sim, ~US$ 0,03 |
| Nova ilustração da peça (RF10) | `python -m src.peca_orientacao gerar` | Sim, ~US$ 0,06 |
| Experimentos de prompt (RF02 e RF03) | `python -m src.experimento_rf02` · `python -m src.experimento_rf03` | Sim |

Os testes usam respostas simuladas e pastas temporárias: não gastam créditos nem alteram os
resultados do projeto.

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
│   ├── gabaritos/              resultados esperados de cada caso
│   └── processados/            transcrições, leituras e extrações
├── prompts/                    modelo da minuta e prompts do RF02
├── src/
│   ├── main.py, interface.py   ponto de entrada e interface
│   ├── fluxo.py                entrada → extração → revisão → minuta → aprovação
│   ├── llm_client.py           prompt de produção, chamada à API e montagem da minuta
│   ├── audio.py, vision.py     transcrição, voz e leitura de documentos
│   ├── peca_orientacao.py      peça de orientação (RF10)
│   ├── minuta_pdf.py           PDF da minuta
│   ├── privacidade.py          minimização de dados pessoais (RF12)
│   ├── audit.py                registro das execuções (RF11)
│   ├── configuracao.py, versoes.py
│   └── experimento_*, avaliacao_rf13.py, varredura_rf12.py   experimentos e verificações
├── resultados/                 minutas, áudios, imagens, avaliações e logs
├── testes/                     testes automatizados (unittest)
└── documentacao/               índice, relatório técnico, registro de uso de IA e um documento por requisito
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

Detalhes em [`documentacao/rf12_lgpd_privacidade.md`](documentacao/rf12_lgpd_privacidade.md).

## 13. Equipe e uso de IA

| Integrante | Responsabilidades |
|---|---|
| Ana Beatriz Schuindt do Amaral | Casos de teste e gabaritos; experimento de prompts (RF02); prompt seguro (RF03); registro e rastreabilidade (RF11); LGPD (RF12); avaliação de qualidade (RF13); integração final: revisão humana na interface, conferência dos dados críticos, PDF da minuta aprovada, áudio da minuta e peça de orientação; documentação |
| Maria Luiza Batista de Souza | Transcrição (RF06), síntese de voz (RF07), visão e OCR (RF08) e primeiras versões da imagem (RF10) |
| Felipe Ferreira Aguiar | Inicialização e configuração (RF01), chamada à API (RF04), extração (RF05), minuta e primeira versão do PDF (RF09) e interface em etapas |

O desenvolvimento teve apoio de ferramentas de IA. Ana Beatriz usou o **Claude Code** para auxiliar
o desenvolvimento, criar a estrutura de diretórios esperada, sugerir a arquitetura, sugerir como
documentar cada etapa, acompanhar os requisitos funcionais obrigatórios e manter o trabalho dentro
do escopo. Todo código e todo conteúdo gerado com apoio de IA foram revisados e testados pela equipe.
O registro completo está em [`documentacao/02_registro_uso_ia.md`](documentacao/02_registro_uso_ia.md).

---

*Projeto desenvolvido para fins educacionais, com uso de inteligência artificial generativa e supervisão humana.*