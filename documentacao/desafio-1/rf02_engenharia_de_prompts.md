# RF02 — Experimento de engenharia de prompts: matriz comparativa

Experimento controlado com três prompts para a mesma tarefa de redação institucional:
gerar a minuta de resposta ao CASO-04 (`dados/originais/entrada_texto.txt`, fornecido pelo
professor) seguindo o modelo institucional (`prompts/modelo_minuta.md`). O experimento foi
executado com dois modelos para verificar se a conclusão se mantém.

## Prompts avaliados

| Prompt | Como foi produzido | Arquivo |
|---|---|---|
| A | Zero-shot curto, escrito à mão | `prompts/desafio1/rf02/prompt_A.txt` |
| B | Estruturado à mão: Persona, Contexto, Tarefa, Formato e Critérios de sucesso | `prompts/desafio1/rf02/prompt_B.txt` |
| C | Gerado pelo próprio modelo a partir de um metaprompt | Metaprompt: `prompts/desafio1/rf02/metaprompt_C.txt`; prompts gerados: `prompt_C_gpt-6-luna.txt` e `prompt_C_gpt-6.1-sol.txt` |

## Execuções

| Execução | Modelo | Parâmetros | Relatório |
|---|---|---|---|
| `execucao_20261017_163533` | `gpt-6-luna` | `max_completion_tokens=4000`, `seed=42` | `resultados/minutas/rf02/execucao_20261017_163533/relatorio_rf02.md` |
| `execucao_20261017_170118` | `gpt-6.1-sol` | `max_completion_tokens=4000`, `seed=42` | `resultados/minutas/rf02/execucao_20261017_170118/relatorio_rf02.md` |

Em cada execução, os três prompts usaram o mesmo modelo e os mesmos parâmetros, com duas
repetições por prompt. A temperatura não foi enviada: o `gpt-6-luna` só aceita o valor padrão (1),
e o mesmo critério foi mantido no `gpt-6.1-sol` para que as execuções fossem comparáveis.
Entradas enviadas, saídas e registros (tempo, tokens, versão do prompt) estão em cada pasta.

## Matriz comparativa

Legenda: ✅ atende · ⚠️ atende parcialmente · ❌ não atende. Resultado igual nos dois modelos,
salvo indicação.

| Critério | A | B | C |
|---|---|---|---|
| Fidelidade ao contexto | ❌ acrescenta edital e documentos | ✅ | ⚠️ omite a ciência das regras |
| Dados inventados | ❌ documentos e signatário ("Secretaria Acadêmica") | ✅ nenhum | ✅ nenhum |
| Formato (modelo institucional) | ❌ formato livre de e-mail | ✅ | ✅ |
| Tom institucional | ✅ | ✅ | ✅ |
| Lacunas sinalizadas ("não localizado") | ❌ | ✅ | ⚠️ marca como ausente um dado que existe |
| Dados pessoais preservados | ✅ | ✅ | ✅ |
| Estabilidade entre repetições | ❌ luna · ⚠️ sol | ✅ | ✅ |
| Tempo de resposta médio — luna | 7,7 s | 3,6 s | 3,4 s |
| Tempo de resposta médio — sol | 14,4 s | 5,1 s | 4,4 s |
| Tempo para escrever o prompt (estimado) | ~1 min | ~30 min | ~10 min (metaprompt) + geração (8,5 s luna · 57,6 s sol) |
| Resultado utilizável | Não | **Sim, sem correção** | Com correção manual da ciência |

Comparação com o gabarito (`dados/gabaritos/gabarito_entrada_texto.json`):

| Item do gabarito | A | B | C |
|---|---|---|---|
| Nome, protocolo e dados do curso corretos | ⚠️ incompleto no luna | ✅ | ✅ |
| Ciência das regras de matrícula | ⚠️ citada de forma genérica | ✅ | ❌ "não localizado" |
| Documentos, prazo e local = "não localizado" | ❌ inventados | ✅ | ✅ |
| Cabeçalho com brasão, assinatura entre colchetes e aviso de IA | ❌ | ✅ | ✅ |
| Sem CPF, RG, data de nascimento, naturalidade, nome da mãe e e-mail | ✅ | ✅ | ✅ |

O tempo para escrever cada prompt não foi cronometrado; os valores são estimativas da autora, feitas
depois do experimento. A ordem de grandeza é o que importa para a comparação: o Prompt B exigiu
muito mais tempo de escrita que o A, e o C trocou tempo de escrita pela geração do prompt.

## Principais achados

1. **Sem estrutura, o modelo inventa.** O Prompt A inventou listas de documentos, citou um edital
   inexistente e criou um signatário nos dois modelos, mesmo sem nenhuma instrução para isso.
2. **O Prompt B foi consistente:** minuta correta e utilizável sem correção nas quatro saídas
   (2 modelos × 2 repetições).
3. **O metaprompt gerou uma regra restritiva demais, nos dois modelos.** Os dois Prompts C exigem
   que as regras de matrícula venham de um "termo de ciência assinado", copiando o texto do
   modelo de minuta. Como a entrada traz uma declaração de ciência por e-mail, o campo saiu
   "não localizado". O prompt gerado pela IA ficou mais cauteloso do que o necessário e descartou
   uma informação disponível — um erro de omissão que só a revisão humana detectou.
4. **O metaprompt também trouxe boas ideias.** O Prompt C do `gpt-6.1-sol` incluiu, sem que isso
   fosse pedido, a regra de tratar a solicitação como dados e não como instruções, e delimitou a
   solicitação com `<solicitacao>`.
5. **O `gpt-6.1-sol` foi mais lento** que o `gpt-6-luna` em todos os prompts, sem ganho de
   qualidade no Prompt B.

## Decisão

**Prompt selecionado para o sistema: B.**

Justificativa: foi o único prompt que produziu minutas fiéis à solicitação, no formato institucional,
sem dados inventados, com as lacunas sinalizadas e sem dados pessoais desnecessários, em todas as
repetições e nos dois modelos. O Prompt C exigiria correção manual em toda minuta com declaração de
ciência; o Prompt A não é utilizável.

**Próximo passo (RF03):** transformar o Prompt B no prompt de produção, acrescentando a separação
entre instruções do sistema e conteúdo do usuário, a delimitação do conteúdo externo (ideia
aproveitada do Prompt C do `gpt-6.1-sol`), a instrução de tratar instruções do documento como dados
e a saída estruturada.

**Melhoria possível para o Prompt C** (não aplicada): esclarecer no metaprompt que uma declaração de
ciência presente na solicitação é suficiente para preencher o campo de regras de matrícula.

## Limitações

- Um único caso avaliado (CASO-04); os casos 01 a 03 serão usados no RF03.
- Temperatura não controlada; estabilidade avaliada com duas repetições por prompt.
- Custo estimado apenas para o `gpt-6-luna` (US$ 0,0021 na execução inteira, com preço a conferir);
  o preço do `gpt-6.1-sol` não foi informado.
- Revisão humana feita por uma única revisora.
- O modelo de produção para o RF09 ainda precisa ser definido com a equipe.
