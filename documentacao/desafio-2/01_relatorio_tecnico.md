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

*A preencher — Maria Luiza.*

## 5. Provedor configurável e auditoria (RF21)

*A preencher — Maria Luiza.*

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
