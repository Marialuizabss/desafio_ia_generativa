# RF02 — Relatório da execução 20261017_163533

Experimento controlado com três prompts para a mesma tarefa de redação institucional:
gerar a minuta de resposta ao CASO-04 seguindo o modelo institucional.

## Configuração

| Item | Valor |
|---|---|
| Data | 17/10/2026, 16:35 |
| Caso | CASO-04 — `dados/originais/entrada_texto.txt` (fornecido pelo professor) |
| Gabarito | `dados/gabaritos/gabarito_entrada_texto.json` |
| Modelo de minuta | `prompts/modelo_minuta.md` |
| Provedor / modelo | OpenAI / `gpt-6-luna` |
| Parâmetros (iguais nos três) | `max_completion_tokens=4000`, `seed=42` |
| Repetições | 2 por prompt |
| Script | `src/experimento_rf02.py` |
| Registro completo | `registro_rf02.json` (nesta pasta) |

**Temperatura:** o `gpt-6-luna` não aceita ajuste de `temperature` (só o valor padrão, 1).
Os três prompts foram executados com a temperatura padrão; por isso cada um foi executado
duas vezes, para observar a variação entre execuções.

## Prompts

| Prompt | Como foi produzido | Arquivo do prompt | Entrada enviada |
|---|---|---|---|
| A | Zero-shot curto, escrito à mão | `prompts/rf02/prompt_A.txt` | `entrada_prompt_A.txt` |
| B | Estruturado à mão (Persona, Contexto, Tarefa, Formato, Critérios de sucesso) | `prompts/rf02/prompt_B.txt` | `entrada_prompt_B.txt` |
| C | Gerado pelo modelo a partir do metaprompt `prompts/rf02/metaprompt_C.txt` | `prompts/rf02/prompt_C_gpt-6-luna.txt` | `entrada_prompt_C.txt` |

O Prompt C desta execução foi salvo como `prompts/rf02/prompt_C.txt` e renomeado depois para
`prompt_C_gpt-6-luna.txt`, porque cada modelo gera o seu próprio Prompt C. O `registro_rf02.json`
mantém o nome original da execução.

## Impressões da revisora (Ana)

- **A:** ficou bem vago, porque o prompt nem tinha as informações do modelo da minuta.
- **B:** ficou ótimo; seguiu tudo o que foi pedido e não inventou nada.
- **C:** foi bom e seguiu o modelo, mas não trouxe a ciência das regras de matrícula
  nas duas repetições, embora essa informação estivesse na entrada do professor.

## Observações verificadas nos arquivos

**Prompt A**
- Não segue o modelo institucional: sem cabeçalho com brasão, sem as seções do modelo,
  sem "não localizado" e sem o aviso de apoio de IA.
- **Inventou informações:** a repetição 1 lista cinco documentos que não constam da entrada
  (identificação, certidão, comprovante de endereço, histórico escolar, formulários do edital);
  a repetição 2 sugere documentos "em geral" exigidos. As duas citam um "edital" inexistente.
- **Inventou o signatário:** "Secretaria Acadêmica" (rep. 1) e "Secretaria de Matrículas" (rep. 2).
- Omitiu eixo e carga horária; a repetição 2 também omitiu o turno.
- As duas repetições são bem diferentes entre si: sem estrutura no prompt, a temperatura padrão
  produz mais variação.

**Prompt B**
- Seguiu o modelo integralmente, nas duas repetições.
- Todos os dados do gabarito presentes e corretos, inclusive a ciência das regras de matrícula.
- Documentos, prazo e local marcados como "não localizado"; nada inventado.
- Não reproduziu dados pessoais (CPF, RG, data de nascimento, naturalidade, nome da mãe, e-mail).
- Assinatura mantida entre colchetes e aviso de apoio de IA presente.
- Repetições praticamente idênticas: só a redação da frase da ciência variou
  ("se o solicitante faltar" × "se houver falta"); os fatos não mudaram.

**Prompt C**
- Seguiu o modelo, não inventou e não reproduziu dados pessoais.
- **Omitiu a ciência das regras** nas duas repetições ("não localizado"). O Prompt C *menciona*
  esse campo, mas com uma regra restritiva demais criada pelo metaprompt: "use apenas regras que
  constem expressamente de termo de ciência **assinado** pelo solicitante". A entrada traz uma
  declaração de ciência, não um termo assinado, e o modelo interpretou a regra ao pé da letra.
- Repetições idênticas.

## Matriz comparativa

Legenda: ✅ atende · ⚠️ atende parcialmente · ❌ não atende

| Critério | A | B | C |
|---|---|---|---|
| Fidelidade ao contexto | ❌ acrescenta edital e documentos | ✅ | ⚠️ omite a ciência das regras |
| Dados inventados | ❌ documentos e signatário | ✅ nenhum | ✅ nenhum |
| Formato (modelo institucional) | ❌ | ✅ | ✅ |
| Tom institucional | ✅ formal | ✅ formal | ✅ formal |
| Lacunas sinalizadas ("não localizado") | ❌ | ✅ | ⚠️ marca como ausente um dado que existe |
| Dados pessoais preservados | ✅ | ✅ | ✅ |
| Estabilidade entre repetições | ❌ muito variável | ✅ | ✅ |
| Tempo de resposta (média) | 7,7 s | 3,6 s | 3,4 s |
| Tempo para escrever o prompt | [preencher] min | [preencher] min | [preencher] min (metaprompt) + 8,5 s (geração) |
| Resultado utilizável? | Não | **Sim, sem correção** | Com correção manual da ciência |

## Números da execução

| Chamada | Tempo (s) | Tokens de entrada | Tokens de saída | Tokens de raciocínio | Custo estimado (US$) |
|---|---|---|---|---|---|
| Geração do Prompt C | 8,48 | 444 | 825 | 264 | 0,000457 |
| A — rep. 1 | 7,02 | 260 | 620 | 378 | 0,000336 |
| A — rep. 2 | 8,41 | 260 | 717 | 468 | 0,000385 |
| B — rep. 1 | 3,25 | 784 | 341 | 85 | 0,000249 |
| B — rep. 2 | 3,91 | 784 | 347 | 93 | 0,000252 |
| C — rep. 1 | 3,60 | 794 | 307 | 93 | 0,000233 |
| C — rep. 2 | 3,26 | 794 | 302 | 88 | 0,000230 |
| **Total** | | | | | **0,002142** |

Custos calculados com US$ 0,10 (entrada) e US$ 0,50 (saída) por milhão de tokens; conferir na
tabela de preços da OpenAI. Os tokens de raciocínio estão incluídos nos tokens de saída.

O Prompt A, apesar de ser o mais curto, gastou mais tokens de raciocínio e mais tempo: sem
instruções, o modelo precisou "decidir" o formato e o conteúdo da resposta.

## Decisão

**Prompt selecionado: B.**

Foi o único que produziu uma minuta utilizável sem correção nas duas repetições: seguiu o modelo
institucional, trouxe todos os dados da solicitação, sinalizou as lacunas sem inventar e preservou
os dados pessoais. O C chegou perto, mas a regra gerada pelo metaprompt fez o modelo descartar uma
informação disponível, o que exigiria correção manual. O A não é utilizável: não segue o modelo e
inventa documentos e signatário.

O Prompt B será a base do prompt de produção do RF03, que acrescentará a separação entre instruções
do sistema e conteúdo do usuário, a delimitação do conteúdo externo e a saída estruturada.

## Limitações

- Um único caso (CASO-04) avaliado; os casos 01 a 03 serão usados nos testes do RF03.
- Temperatura não controlável no `gpt-6-luna`; a estabilidade foi avaliada com só duas repetições.
- O cabeçalho com brasão aparece como marcador de texto; a inserção da imagem é feita no RF09.
