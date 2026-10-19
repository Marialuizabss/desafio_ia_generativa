# Registro do uso de IA no desenvolvimento

Registro exigido pela seção 10 do enunciado. Trata do uso de IA **para desenvolver** o projeto; os
modelos usados pelo **sistema** estão no `01_relatorio_tecnico.md`.

## 1. Ana Beatriz Schuindt do Amaral

**Ferramenta:** Claude Code (Anthropic), extensão do VS Code, modelo Claude Opus 5.5, em 17 e
18/10/2026.

**Finalidade:** auxiliar o desenvolvimento, criar a estrutura de diretórios esperada, sugerir a
arquitetura e como documentar cada etapa, acompanhar os requisitos obrigatórios e manter o escopo.

**Forma de trabalho:** a IA propunha e explicava cada mudança; Ana aprovava, mudava ou rejeitava; a
IA aplicava numa cópia do projeto e testava; Ana testava e fez todos os commits.

**Principais solicitações**

- Análise dos 13 requisitos e plano de trabalho.
- Orientação para os casos de teste e gabaritos (arquivos criados pela Ana).
- Protocolo e avaliação dos casos (RF13).
- Conclusão do restante do projeto: registro (RF11), revisão humana, PDF, áudio, peça de
  orientação, README e documentação.

**Sugestões**

- **Aceitas:** prompt B; registro em JSONL sem o texto da solicitação; PDF, áudio e peça só após a
  aprovação; documentação centralizada.
- **Modificadas:** conferência dos dados movida para a etapa de revisão; edição livre da minuta
  trocada por campos de servidor e cargo; rodapé do PDF sem o caminho do arquivo; peça genérica
  trocada por passo a passo; regra do "aprovado com revisão" juntando as duas opções.
- **Rejeitadas:** reabrir atendimento aprovado ao reiniciar (contraria o RF11); "contexto
  institucional" inventado (o RF10 não exige); IA gerando a peça com os textos (saíam distorcidos);
  sequência de imagens (uma ilustração bastava).

**Erros encontrados:** padrões da minimização que apagavam o campo seguinte; parâmetros não aceitos
pelo modelo no RF02; prompt v2 do RF03 reescrevendo o texto fixo; textos indevidos na ilustração do
RF10. Todos corrigidos e testados.

**Validação:** 164 testes automatizados, testes reais pela interface feitos pela Ana, comparação
com os gabaritos (RF13), revisão humana de cada saída e varredura de dados pessoais (RF12).


## 2. Maria Luiza Batista de Souza

[A preencher: ferramenta e modelo, para que usou, sugestões aceitas, modificadas ou rejeitadas,
erros encontrados e como validou.]

## 3. Felipe Ferreira Aguiar

**Ferramenta:** Cursor, agente no editor, modelo Grok 4.7, em 17 e 18/10/2026.

**Finalidade:** auxiliar o núcleo dele — interface, chamada à API (RF04), extração (RF05), minuta e
primeira versão do PDF (RF09) — e o fluxo de revisão e decisão na tela. Além de analisar se o que era desenvolvido deixava de contemplar o solicitado pelos requisitos funcionais.

**Forma de trabalho:** Felipe pedia a análise ou a mudança; a IA lia o código, explicava e aplicava;
Felipe testava na interface, apontava o que falhava e pedia correção.

**Principais solicitações**

- Mapa do que já existia (áudio, visão, imagem e gabaritos)
- Interface web aberta, com texto, áudio e imagem.
- Objeto da extração, chamada ao modelo e gravação do JSON em `dados/processados/`.
- Parâmetros do modelo na tela e registro de tempo, tokens e custo.

**Sugestões**

- **Aceitas:** Streamlit, uma etapa por tela; modelos limitados a `gpt-5.6-luna`, `gpt-5.6-terra`,
  `o4-mini` e `gpt-4o-mini`; aprovar e rejeitar separados da edição; justificativa obrigatória e fora
  do próximo prompt; nome e cargo do servidor na assinatura; PDF com o brasão.
- **Modificadas:** a minuta deixou de ser reescrita pelo modelo a cada edição e passou a ser montada
  localmente com os campos confirmados; a temperatura só é enviada aos modelos que aceitam o
  parâmetro.
- **Rejeitadas:** Gradio no lugar da interface web; tratar a edição dos campos como substituta de
  aprovar e rejeitar; mandar a justificativa da rejeição como instrução da nova extração.

**Erros encontrados:** classe descrita com 13 campos, e o contrato tem 12; voltar de etapa apagava a
entrada e a edição; aprovação com "não localizado" gravada como aprovado, conferência que não
bloqueava e revisor vazio; nova extração gravava por cima do JSON rejeitado. Todos corrigidos e
testados.

**Validação:** testes da edição, da decisão e do PDF, uso da interface pelo Felipe e revisão do fluxo
contra o enunciado.

## 4. Declaração de responsabilidade

A equipe usou IA como apoio ao planejamento, à programação, aos testes e à documentação. Todas as
sugestões foram avaliadas, o código foi testado e o conteúdo, revisado. A equipe é responsável pelo
resultado entregue e é capaz de explicar e justificar cada decisão.

Ana Beatriz Schuindt do Amaral · Maria Luiza Batista de Souza · Felipe Ferreira Aguiar
