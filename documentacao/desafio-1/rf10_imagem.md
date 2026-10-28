# RF10 — Peça visual de orientação

Peça "Passo a passo da matrícula", entregue no quadro de cada atendimento aprovado. A ilustração é
gerada por IA; o brasão, os textos e o passo a passo são montados pelo código.

## Síntese

| Item do enunciado | Como é atendido | Seção |
|---|---|---|
| Peça visual de orientação relacionada a um caso | Passo a passo da matrícula com os dados do atendimento aprovado (curso, eixo, documentos, prazo, local e regra de frequência) | 1 |
| Prompt com sujeito, composição, estilo, iluminação, proporção e restrições | Os seis elementos rotulados no prompt | 2 |
| Gerar imagem nova ou editar | Ilustração nova com `gpt-image-1` | 2 |
| Verificar textos, símbolos, mãos, objetos e coerência | Checklist obrigatório na revisão da interface, com prévia da peça | 3 |
| Manter prompt, modelo e data | `resultados/logs/metadados_peca_orientacao.json`, por versão | 3 |
| Identificar como gerado por IA | Selo na peça: "Ilustração gerada por IA (gpt-image-1) e diagramada pela equipe" | 1, 4 |
| Não usar imagem de pessoa real | Prompt proíbe pessoas, rostos e mãos | 2 |
| **Aceite:** peça revisada e com nota de proveniência | Revisão registrada por versão; nota na seção 4 | 3, 4 |

## 1. A peça entregue

A peça (1024 × 1536) é montada por `src/peca_orientacao.py` com:

- **Cabeçalho:** brasão original e as linhas "GOVERNO DE MATO GROSSO / SECRETARIA DE ESTADO DE CIÊNCIA,
  TECNOLOGIA E INOVAÇÃO — SECITECI/MT / ESCOLA TÉCNICA ESTADUAL DE CUIABÁ";
- **Título:** "PASSO A PASSO DA MATRÍCULA", com o curso e o eixo do atendimento;
- **Ilustração gerada por IA**, numa faixa panorâmica;
- **Cinco passos**, preenchidos com os campos da minuta aprovada:

| Passo | Fonte | Quando o campo está "não localizado" |
|---|---|---|
| 1. Confira a resposta | Texto fixo | — |
| 2. O que levar | Campo "Documentos" (lista) | "A secretaria informará na resposta os documentos que você deve apresentar." |
| 3. Até quando | Campo "Prazo" | "Fique atento ao prazo informado pela secretaria." |
| 4. Onde ir | Campo "Local e horário" | "Procure a Secretaria Escolar da sua unidade." |
| 5. Depois da matrícula | Ciência das regras declarada na solicitação | Passo omitido |

- **Rodapé:** "Secretaria Escolar", o selo de IA e "Peça demonstrativa — Projeto FIC_DEV 2026 · Não
  constitui comunicado oficial".

**Nada é inventado:** o que a solicitação não traz, o servidor completa na revisão (etapa 3) ou a peça
orienta a procurar a secretaria. **Sem dados pessoais:** a peça não leva nome, CPF, protocolo nem
datas da solicitação. A peça de cada atendimento é salva em `resultados/imagens/orientacao/` e
registrada no log (evento `imagem_orientacao`, ação `peca`).

**Por que a IA não escreve os textos:** a primeira tentativa (seção 5) pediu ao modelo a peça inteira,
com os textos em português, e saiu com palavras distorcidas e sem o brasão real. Mesmo proibido de
escrever, o modelo inventou palavras (v01 e v02 abaixo). Com os textos montados pelo código, o
cidadão recebe exatamente a informação aprovada.

## 2. Prompt da ilustração

Modelo `gpt-image-1`, 1536 × 1024, qualidade média (configurável em `config.json`); cerca de US$ 0,06
por ilustração (estimativa a conferir com o provedor).

| Elemento | Conteúdo |
|---|---|
| Sujeito | Balcão de atendimento de secretaria escolar com pasta fechada, calendário de mesa com grade vazia, porta-lápis e vaso de planta; ao fundo, fachada de prédio escolar lisa, sem placa ou letreiro |
| Composição | Panorâmica; todos os elementos numa faixa horizontal central, porque a imagem é recortada como faixa; sem pessoas |
| Estilo | Ilustração vetorial plana, institucional e sóbria, sem elemento tipográfico; verde (#165C3F), amarelo-dourado discreto e branco |
| Iluminação | Luz difusa e uniforme, de dia, sem sombras duras nem reflexos |
| Proporção | 3:2 (1536 × 1024), com o conteúdo na faixa central |
| Restrições | Nenhuma letra, número, palavra, placa, letreiro, logotipo ou brasão; nenhum papel com título; nenhuma pessoa, rosto ou mão; nada que pareça documento oficial preenchido; sem dados pessoais |

O texto completo está em `src/peca_orientacao.py` (`PROMPT_ILUSTRACAO`) e em cada versão dos metadados.

## 3. Versões e revisão humana

Cada ilustração gerada é uma versão pendente. Na interface, o servidor vê a **prévia da peça montada**
e a ilustração inteira, e só aprova com os quatro itens do checklist marcados: sem letras, números ou
palavras; sem logotipos, brasões ou símbolos oficiais; objetos coerentes, sem distorções; sem
pessoas, rostos ou mãos. Reprovar exige justificativa. A versão aprovada mais recente é a vigente;
uma versão aprovada pode ser revogada depois, com motivo. Nenhuma versão é apagada.

| Versão | Gerada em | Decisão | Revisão |
|---|---|---|---|
| v01 | 18/10/2026 18:12 | **Reprovada** | "Não orienta nada" — composição sem foco na orientação; havia ainda o texto "TECHNICAL SCHOOL" na fachada |
| v02 | 18/10/2026 18:25 | Aprovada e depois **revogada** | Texto "ENTULATION" no formulário, percebido depois da aprovação |
| v03 | 18/10/2026 18:34 | **Aprovada (vigente)** | Sem texto, objetos coerentes e dentro da faixa; prompt revisado sem formulário e sem letreiro |

As três revisões são de Ana Beatriz Schuindt. Arquivos: `resultados/imagens/orientacao/ilustracao_v0N.png`;
prompt, modelo, tamanho, qualidade, data, tempo, custo e revisão de cada versão em
`resultados/logs/metadados_peca_orientacao.json`; eventos de geração, revisão e revogação no log.

**O que a revisão mostrou:** o modelo coloca texto onde objetos "pedem" escrita (placa na fachada,
cabeçalho de formulário), mesmo com a proibição explícita. A correção foi tirar esses objetos do
prompt, não só reforçar a proibição.

## 4. Nota de proveniência (peça entregue)

- **Finalidade:** orientar o solicitante sobre os próximos passos da matrícula; peça demonstrativa do
  projeto FIC_DEV 2026, sem valor de comunicado oficial.
- **Gerado por IA:** a ilustração (`gpt-image-1`, OpenAI), na versão vigente v03.
- **Feito pela equipe, por código:** diagramação, brasão original de Mato Grosso, todos os textos e o
  passo a passo, preenchido com os campos da minuta aprovada pelo servidor.
- **Revisão humana:** ilustração revisada por versão com checklist; textos aprovados junto com a
  minuta.
- **Identificação na peça:** "Ilustração gerada por IA (gpt-image-1) e diagramada pela equipe".
- **Rastreabilidade:** prompt, modelo, data e revisão de cada versão nos metadados; cada peça montada
  ligada ao id da execução no log.
- **Restrições:** sem pessoas reais, sem dados pessoais e sem símbolos institucionais gerados por IA.

## 5. Primeiras tentativas (Maria Luiza)

As tentativas abaixo, com geração e edição da peça inteira pelo modelo, foram reprovadas e motivaram a
abordagem atual. Os arquivos continuam em `resultados/imagens/` e os metadados foram atualizados para
"reprovada". O `src/layout_rf10.py` (diagramação com Pillow) usa fontes do Windows e não roda em
outros sistemas; foi substituído por `src/peca_orientacao.py`, que funciona em Linux e Windows.

Responsável pela revisão humana: Maria Luiza
Modelo utilizado: gpt-image-1

### Geração inicial

Arquivo: imagem_rf10_original.png

A geração por IA produziu um comunicado institucional sobre matrículas, mas apresentou problemas de legibilidade, erros de grafia e ausência do brasão oficial.

### Edição por IA

Arquivo: imagem_rf10_editada.png

Foi solicitada a inclusão de uma linha amarelo-dourada abaixo da faixa verde, preservando o restante da composição.

A API concluiu a operação, mas o resultado apresentou falhas:

- Alteração indevida de textos.
- Distorção de palavras e caracteres.
- Modificação de detalhes do brasão.
- Perda de legibilidade do rodapé.
- Posicionamento inadequado do detalhe solicitado.

Resultado da revisão: REPROVADO para utilização como comunicado institucional.

### Correção e versão final

Arquivo: imagem_rf10_layout_formal.png

A versão final foi diagramada com Pillow, utilizando o brasão original de Mato Grosso e textos definidos diretamente no código.

Foram preservados:
- Cabeçalho institucional.
- Brasão original.
- Faixa verde com título.
- Orientações sobre documentação e acompanhamento.
- Aviso de que a solicitação não confirma a matrícula.
- Identificação de peça demonstrativa.

Resultado da revisão: APROVADO para demonstração.

### Conclusão

O RF10 demonstrou a geração e a edição de imagens por IA, incluindo limitações de fidelidade visual e textual.

A revisão humana identificou os problemas e orientou a utilização de uma versão diagramada programaticamente.

A peça é exclusivamente demonstrativa e não constitui comunicado oficial do Governo do Estado de Mato Grosso.


### Nota de proveniência das tentativas anteriores

**Finalidade:** produção de uma peça visual demonstrativa
sobre orientações para matrícula em cursos técnicos.

**Modelo de IA:** gpt-image-1 (OpenAI).

**Geração por IA:**
- Arquivo: imagem_rf10_original.png
- Prompt: registrado em metadados_rf10.json.
- Resultado: rejeitado para uso institucional devido a
  erros textuais e ausência do brasão original.

**Edição por IA:**
- Entrada: imagem_rf10_layout_formal.png
- Saída: imagem_rf10_editada.png
- Prompt: registrado em metadados_edicao_rf10.json.
- Resultado: rejeitado devido a distorções nos textos,
  no brasão e no rodapé.

**Versão final selecionada:**
- Arquivo: imagem_rf10_layout_formal.png
- Técnica: diagramação programática com Pillow.
- Brasão: arquivo original fornecido como referência.
- Conteúdo textual: inserido diretamente no código Python.
- Revisão humana: aprovada para demonstração.

**Rastreabilidade:**
- As datas das chamadas de IA estão registradas nos
  respectivos arquivos JSON de metadados.
- Os prompts e o modelo utilizado foram preservados.
- Os arquivos originais e editados foram mantidos para
  comparação e auditoria.

**Limitação identificada:**
A edição generativa não preservou integralmente os textos
e símbolos institucionais, mesmo com instruções explícitas.

**Identificação:**
A peça final foi diagramada com Pillow, com apoio de IA
durante o processo de desenvolvimento e avaliação.
Não deve ser apresentada como imagem integralmente
gerada por IA.

**Uso autorizado:**
Material exclusivamente demonstrativo para o projeto
FIC_DEV 2026. Não constitui comunicado oficial do
Governo do Estado de Mato Grosso.

### Avaliação visual e seleção da arte final

**Arte principal selecionada:** `imagem_rf10_layout_formal.png`

**Justificativa:** a versão diagramada programaticamente apresenta melhor legibilidade, alinhamento e organização das informações. A composição utiliza o brasão disponibilizado para o projeto, cores institucionais e indicação de material demonstrativo.

**Limitação identificada:** as imagens produzidas e editadas diretamente pelo modelo generativo apresentaram distorções em parte dos textos. Portanto, a geração e a edição por IA não garantiram fidelidade textual suficiente para utilizar essas versões como arte final.

**Solução adotada:** manter as imagens original e editada como evidências do processo e selecionar a versão diagramada com Pillow como principal resultado visual do RF10.

**Revisão humana:** a escolha da arte final foi realizada por inspeção visual. O material é demonstrativo, não constitui comunicado oficial e deve passar por revisão antes de qualquer utilização institucional real.
