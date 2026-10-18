# Relatório técnico

**Central Inteligente de Atendimento e Comunicação Institucional** — Desafio Prático 1, FIC_DEV 2026

Equipe: Ana Beatriz Schuindt do Amaral, Maria Luiza Batista de Souza e Felipe Ferreira Aguiar.

Este relatório dá a visão técnica de conjunto: arquitetura, modelos, custos, riscos, LGPD e
avaliação de qualidade. Os detalhes de cada requisito estão nos documentos `rfXX_*.md` desta pasta,
indicados em cada seção, e o índice geral está em `00_indice.md`.

## 1. Resumo

O protótipo recebe solicitações fictícias de matrícula por texto, áudio ou ficha digitalizada,
remove os dados pessoais desnecessários, extrai os campos com um modelo de linguagem e monta a minuta
no modelo institucional. Um servidor revisa os campos, confere com o original os dados lidos de
áudio e imagem e aprova ou rejeita. Só depois da aprovação o sistema entrega o PDF, a versão em
áudio e a peça visual de orientação, e tudo fica registrado.

Na avaliação dos 7 casos de teste no sistema entregue, **6 foram aprovados (86%)** e o sétimo, uma
ficha manuscrita lida com erro, foi **corrigido pelo servidor (100% após correção)**. Os dois
ataques de prompt injection foram ignorados e sinalizados. A suíte tem **164 testes automatizados**,
que rodam sem chamar a API. Um atendimento completo por texto custa cerca de **US$ 0,02**.

## 2. Problema e escopo

Uma secretaria pública fictícia recebe pedidos por texto, voz e formulário, e hoje responde
manualmente, sem padrão de verificação: há risco de omissão, invenção de informação, exposição de
dados e respostas inconsistentes.

| Dentro do escopo | Fora do escopo |
|---|---|
| Entrada por texto, `.txt`, áudio, imagem e PDF | Envio da resposta ao cidadão (sempre manual) |
| Extração de 12 campos e classificação em 6 categorias | Dados reais ou integração com sistemas acadêmicos |
| Minuta no modelo institucional, PDF, áudio e peça de orientação | Assinatura digital |
| Revisão humana com registro da decisão | Atendimento de outras categorias além de matrícula (testado) |
| Minimização de dados, registro e avaliação de qualidade | Uso em produção |

## 3. Arquitetura

```
                ┌──────────────────────── interface.py (Streamlit, 4 etapas) ────────────────────────┐
 entrada ──▶ 1 modelo ──▶ 2 envio ──────────▶ 3 revisão ──────────────────────▶ 4 minuta e decisão
                           │                    │   ▲                              │
                           ▼                    │   │ campos editáveis,             ├─▶ minuta_pdf.py ─▶ PDF
                     fluxo.py                   │   │ conferência dos              ├─▶ audio.py (voz) ─▶ MP3
            ┌─────────────┼──────────────┐      │   │ dados críticos               └─▶ peca_orientacao.py ─▶ PNG
            ▼             ▼              ▼      │   │
       texto direto   audio.py       vision.py  │   │
                      (transcrição)  (leitura)  │   │
            └─────────────┬──────────────┘      │   │
                          ▼                     │   │
                   privacidade.py  (remove CPF, RG, e-mail… antes do envio)
                          ▼                     │   │
                   llm_client.py  (prompt seguro, JSON estrito) ──▶ campos ──┘
                          │
                          ▼
                     audit.py ──▶ resultados/logs/execucoes.jsonl  (todas as etapas)
```

| Módulo | Responsabilidade |
|---|---|
| `main.py`, `interface.py` | Ponto de entrada e interface em 4 etapas; validação de arquivos; revisão, conferência, aprovação e saídas |
| `fluxo.py` | Orquestra entrada → leitura → minimização → extração; revisão dos campos; minuta aprovada; áudio da minuta; reaproveitamento |
| `audio.py` | Transcrição, duração do áudio e voz da minuta aprovada |
| `vision.py` | Leitura de PDF (local, quando tem texto) e de imagem (`gpt-4o`) |
| `privacidade.py` | Minimização de dados pessoais por formato e rótulo |
| `llm_client.py` | Prompt de produção, delimitação do conteúdo, chamada à API, custo e montagem da minuta |
| `extracao.py` | Os 12 campos, as 6 categorias e o formato do resultado |
| `minuta_pdf.py` | PDF com brasão, cabeçalho institucional e rodapé de origem |
| `peca_orientacao.py` | Ilustração por IA, versões, revisão e montagem da peça |
| `audit.py` | Registro estruturado de execuções, revisões, decisões, áudios e imagens |
| `configuracao.py`, `versoes.py` | `config.json`, modelos da interface e conferência de versões |

**Onde ficam os dados:** entradas em `dados/originais/` (nunca alteradas); transcrições, leituras,
extrações e revisões em `dados/processados/`; minutas aprovadas, PDFs, áudios, imagens, avaliações e
o registro em `resultados/`.

## 4. Modelos e ferramentas

Os critérios do enunciado para escolher modelos são finalidade, custo, privacidade, abertura e
capacidade multimodal.

| Etapa | Modelo | Por que | Alternativa aberta ou local |
|---|---|---|---|
| Extração dos campos | `gpt-5.6-luna` (OpenAI) | Saída JSON estrita com esquema; segue as regras do prompt seguro; raciocínio de baixo esforço com custo de ~US$ 0,0015 por solicitação | Modelo aberto (Llama, Qwen, Mistral) executado localmente, com mais trabalho de validação do JSON |
| Transcrição | `gpt-4o-transcribe` | Português com boa precisão em nomes, protocolo e datas; rápido (4,3 s para 89 s de áudio) | Whisper executado localmente: evita enviar a voz |
| Leitura da ficha | `gpt-4o` (visão) | Lê letra manuscrita melhor que OCR tradicional, ainda que com erros | Tesseract ou PaddleOCR locais; piores em manuscrito |
| Voz | `gpt-4o-mini-tts` | Aceita instruções de entonação, exigidas pelo RF07; `tts-1-hd` como alternativa sem instruções | Piper ou outra voz local |
| Imagem | `gpt-image-1` | Gera a ilustração no estilo pedido; o texto é posto pelo código | Modelos de difusão abertos executados localmente |

**Abertura e dependência de fornecedor:** todos os modelos são de um único provedor, acessados por
API. A troca de modelo de análise é feita pela tela (`config/modelos.json`), e os demais modelos
estão no `config.json`. A alternativa local é a recomendada para voz e imagem do documento em
produção (seção 9).

**Ferramentas:** Python 3.13, Streamlit, PyMuPDF, Pillow, mutagen e unittest. A stack completa, com
versões, está no README.

## 5. Engenharia de prompts

- **Experimento (RF02):** três prompts para a mesma minuta, com o mesmo modelo e duas repetições
  cada, em dois modelos. O prompt A, zero-shot, inventou documentos, edital e signatário; o C, gerado
  por metaprompt, criou uma regra restritiva demais e omitiu a ciência das regras; **o B, estruturado
  com Persona, Contexto, Tarefa, Formato e Critérios, foi fiel em todas as repetições** e foi
  incorporado ao sistema (`rf02_engenharia_de_prompts.md`).
- **Prompt seguro (RF03):** instruções do sistema separadas do conteúdo; conteúdo do cidadão entre
  `<solicitacao>`; instruções do documento tratadas como dados; proibição de inventar fatos, prazos,
  autoridades e leis; "não localizado" para campo ausente; saída em JSON com esquema estrito. A
  revisão humana levou a duas correções (v1 → v3), e a delimitação foi reforçada no código contra
  variações de maiúsculas e espaços (`rf03_prompt_seguro.md`).
- **Minuta montada pelo código:** no sistema entregue, a IA extrai só os campos; o modelo
  institucional é preenchido pelo código. Isso elimina a reescrita do texto fixo e impede que um
  ataque reescreva a resposta.

## 6. Chamada à API e tratamento de falhas (RF04)

| Item | Como é feito |
|---|---|
| Modelo e parâmetros configuráveis | Modelo, idioma e temperatura (quando o modelo aceita) escolhidos na tela; `reasoning`, `store` e esquema montados na consulta |
| Timeout | 120 s (`config.json`), com até 2 novas tentativas automáticas |
| Chave ausente ou recusada | "A chave da API está ausente ou foi recusada. Confira OPENAI_API_KEY no arquivo .env." |
| Limite de requisições | "O limite de requisições da API foi atingido. Aguarde e tente de novo." |
| Tempo esgotado e conexão | Mensagens próprias para cada caso |
| Indisponibilidade | "O serviço do modelo está indisponível no momento." |
| Resposta vazia ou JSON inválido | Tratadas como erro, sem gravar extração |
| Credenciais nos logs | Não são gravadas; o registro mascara qualquer texto com formato de chave |
| Tempo, tokens e custo | Gravados em cada chamada e no registro |

Toda falha aparece na tela com a mensagem acima, um botão "Tentar de novo" e um aviso vermelho, e
fica registrada no log com o tipo do erro.

## 7. Registro e rastreabilidade (RF11)

`resultados/logs/execucoes.jsonl` tem uma linha por evento, sem o texto da solicitação e sem chaves:

| Evento | Quando | Principais campos |
|---|---|---|
| `execucao` | Cada envio (nova extração, reaproveitamento ou erro) | id, data e hora, modalidade, arquivo de origem, provedor, modelo, parâmetros, versão do prompt, duração, tokens, custo, categoria, campos ausentes, alertas, dados removidos; no áudio, duração, idioma e modelo; `id_execucao_origem` no reaproveitamento |
| `revisao_campos` | Ao montar a minuta | campos alterados (só os nomes), arquivo da revisão, dados críticos conferidos |
| `decisao` | Aprovar, rejeitar ou gerar de novo | decisão, justificativa, servidor, cargo, conferência, arquivos da minuta e do PDF |
| `audio_minuta` | Geração do áudio | modelo, voz, instruções, duração, tempo, custo ou erro |
| `imagem_orientacao` | Geração, revisão, revogação da ilustração e montagem da peça | versão, modelo, revisor, checklist, motivo |

**Como reconstruir uma saída:** a partir do id da execução (que está no rodapé do PDF), o log dá o
arquivo de origem, o modelo, a versão do prompt e os parâmetros; o arquivo da extração e o da revisão
dão os campos antes e depois da revisão; a decisão aponta a minuta e o PDF aprovados. Extrações
substituídas são guardadas com o id no nome; nada é sobrescrito sem cópia.

## 8. Custos

Custos estimados com a tabela de preços do código (`src/llm_client.py`, `config.json`), a conferir
com a fatura do provedor.

| Item | Custo observado |
|---|---|
| Extração de uma solicitação (`gpt-5.6-luna`) | US$ 0,0011 a 0,0017 |
| Voz de uma minuta (`gpt-4o-mini-tts`, 84,5 s) | ~US$ 0,021 |
| Uma versão da ilustração (`gpt-image-1`, média qualidade) | ~US$ 0,063 |
| Transcrição e leitura de imagem | Não registrado pelo sistema |
| Experimento de prompts (RF02, execução com `gpt-6-luna`) | US$ 0,0021 |
| Testes do prompt seguro (RF03, quatro execuções e repetição do CASO-03b) | ~US$ 0,019 |
| Avaliação final dos 7 casos (RF13, extração) | ~US$ 0,010 |
| Três versões da ilustração (RF10) | ~US$ 0,19 |

**Por atendimento:** extração e PDF custam ~US$ 0,0015; com o áudio, ~US$ 0,02. A peça de
orientação não tem custo por atendimento, porque a ilustração vigente é reaproveitada.

**Projeção para 1.000 atendimentos por texto:** ~US$ 1,50 só com extração, ou ~US$ 22 com áudio em
todos; transcrição e leitura de imagem acrescentam um valor que não foi medido.

## 9. LGPD e privacidade

Resumo do `rf12_lgpd_privacidade.md`:

- Somente dados fictícios; CPFs com dígito verificador inválido e e-mails em domínios fictícios.
- Inventário de 18 itens com finalidade, necessidade e risco de cada um.
- **Minimização antes do envio:** CPF, RG, e-mail, telefone, data de nascimento, naturalidade e
  filiação são substituídos por marcadores; o modelo de extração só recebe o que a minuta usa.
- `store: false` na extração; nenhum envio automático; registro sem o texto da solicitação.
- **O que ainda vai ao provedor:** o áudio e a imagem da ficha inteiros (para transcrição e leitura)
  e a minuta aprovada (para a voz). Em produção, transcrição, leitura e voz locais eliminariam esses
  envios; a transferência internacional exige enquadramento no art. 33 da LGPD.
- Varredura de credenciais e dados pessoais da entrega (`python -m src.varredura_rf12`).

## 10. Avaliação de qualidade

Resumo do `rf13_avaliacao_qualidade.md`:

- **Protocolo:** cinco critérios (fidelidade, completude, formato, linguagem e segurança) com nota de
  0 a 2; gravidade crítica, maior ou menor; decisão em aprovado, aprovado com revisão, correção
  manual, nova geração ou rejeitado; gabarito feito antes da execução.
- **Sistema entregue (`gpt-5.6-luna`):** 7 casos gerados de novo; 6 com 12/12 campos; a ficha com
  10/12. Taxa de aprovação **86%**, **100%** após a correção manual da ficha.
- **Achados:** a leitura de letra manuscrita erra o ano do protocolo e a data de forma sistemática;
  a transcrição perde o "@" do e-mail; a revisão humana encontrou erros que a verificação automática
  não pegava (voz da ciência das regras, reescrita do texto fixo) e levou a correções no prompt e no
  código.
- **Demonstração:** caso aprovado (texto), caso corrigido (ficha) e caso rejeitado (injection).

## 11. Riscos e mitigações

| Risco | Como aparece | Mitigação | Risco residual |
|---|---|---|---|
| **Alucinação** | Modelo inventa documento, prazo, lei ou signatário (visto no prompt A do RF02) | Prompt seguro; "não localizado"; JSON estrito; minuta montada pelo código; revisão humana | Campo preenchido com valor plausível e errado; verificação por padrões não pega tudo |
| **Prompt injection** | Solicitação com ordens ao sistema ou fuga da delimitação (CASO-03 e 03b) | Delimitação neutralizada no código; instruções tratadas como dados; alertas destacados; justificativa obrigatória para aprovar com alerta | Testado em dois ataques; os alertas não descrevem a manobra técnica |
| **Exposição de dados** | Dados pessoais enviados ao provedor ou gravados | Minimização; `store: false`; registro sem texto; varredura da entrega; `.env` fora do git | Áudio, imagem e minuta aprovada ainda vão ao provedor |
| **Dependência de fornecedor** | Todos os modelos de um provedor, por API | Modelos configuráveis; minuta e PDF sem IA; testes sem API | Troca de provedor exige adaptar chamadas e reavaliar |
| **Erro de leitura** | Letra manuscrita e fala | Conferência obrigatória dos dados críticos antes da minuta | Depende da atenção do servidor |
| **Texto errado na imagem** | Modelo coloca palavras na ilustração | Textos pelo código; checklist e revisão por versão | Ilustração com detalhe incoerente não percebido |
| **Uso indevido da resposta** | Minuta usada sem revisão | Minuta final, PDF, áudio e peça só existem depois da aprovação; selo "elaborada com apoio de IA" na minuta | O servidor pode aprovar sem ler com atenção |

## 12. Limitações e melhorias propostas

**Limitações:** letra manuscrita não confiável; voz sintética não atende pessoas surdas; avaliação
com 7 casos, todos de matrícula, e uma única revisora; injection testada em dois ataques; custos
estimados pela tabela; interface não testada com leitores de tela.

**Melhorias propostas:**

1. Transcrição, leitura de documentos e voz executadas localmente, por privacidade e soberania.
2. OCR específico para letra manuscrita, ou formulários digitais no lugar de fichas em papel.
3. Contexto institucional oficial (documentos, prazos e locais por curso) para completar a minuta
   e a peça de orientação sem depender do servidor.
4. Mais casos de teste, outras categorias de atendimento e uma segunda revisora.
5. Assinatura digital do PDF e integração com o sistema acadêmico.
6. Alternativa em Libras ou texto simplificado para acessibilidade de pessoas surdas.

## 13. Conceitos aplicados no projeto

| Conceito | Onde aparece |
|---|---|
| Inteligência artificial | O sistema como um todo: automatiza tarefas de leitura, compreensão e redação |
| Aprendizado de máquina | Os modelos usados foram treinados a partir de dados; o sistema não treina modelos |
| Aprendizado profundo | Transcrição, visão, voz e imagem usam redes neurais profundas |
| IA generativa | Geração de voz, de imagem e do texto da resposta do modelo |
| Modelo de linguagem | Extração dos campos e classificação da solicitação (`gpt-5.6-luna`) |
| Modelo de raciocínio | `gpt-5.6-luna` com raciocínio de baixo esforço antes de responder |
| Modelo multimodal | `gpt-4o` lendo a imagem da ficha; modelos de áudio e imagem |
