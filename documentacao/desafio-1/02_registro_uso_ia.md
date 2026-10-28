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

**Ferramentas:** ChatGPT (OpenAI), durante a construção dos RF06, RF07, RF08 e RF10 em 17/17/1072026; e Claude (Anthropic), em 18/10/2026, na verificação final.

**Finalidade:** auxiliar o desenvolvimento dos requisitos dela (transcrição, voz, visão e imagem),
analisar erros, revisar o código, escrever testes e documentar; e, com o Claude, conferir o projeto
contra o enunciado, analisar as branches e corrigir o tratamento de falhas da API.

**Forma de trabalho:** a IA propunha e explicava; Maria decidia, aplicava no VS Code, rodava os
testes, testava pela interface com a chave real e fez os commits na branch `alteracoes-maria`. O
Claude preparava os arquivos numa cópia e testava sem chamar a API.

**Principais solicitações**

- Transcrição do áudio (RF06), voz da minuta (RF07), leitura da ficha em imagem (RF08) e peça visual
  (RF10), com testes e documentação de cada um.
- Conferência do projeto contra o enunciado e análise do que faltava em cada requisito.
- Comandos de Git para manter a branch atualizada sem criar branches novas.
- Mensagens claras em português para falhas da API (RF04) em áudio, voz e visão.

**Sugestões**

- **Aceitas:** voz `nova` e aviso de campos não localizados (RF07); instruções contra dados pessoais e
  contra comandos escritos na ficha (RF08); módulo `src/erros_api.py` com mensagens que não citam a
  chave; documentação só depois da funcionalidade.
- **Modificadas:** o RF07 passou do `tts-1-hd` para o `gpt-4o-mini-tts` com instruções de entonação,
  mantendo o `tts-1-hd` como alternativa; a escolha da versão do áudio veio da escuta de cada versão.
- **Rejeitadas:** peça do RF10 gerada e editada só pela IA (textos e brasão saíam distorcidos),
  trocada por textos diagramados por código; criar branches novas; enviar a chave ao chat.

**Erros encontrados:** transcrição repetindo "noturno" e sem o "@" do e-mail (RF06); pronúncia do
protocolo e naturalidade da voz (RF07); seis divergências na primeira leitura da ficha (RF08); erros de
texto, brasão e rodapé nas imagens (RF10); e, na orientação do Claude, análise feita só na `main`
desatualizada e comando de testes sem o `.` depois do `-t`. Todos corrigidos.

**Validação:** 173 testes automatizados (164 anteriores e 9 novos do tratamento de falhas), revisão
humana de cada transcrição, áudio e extração contra o original, e teste real pela interface com a
chave, conferindo os campos, a minuta aprovada, o PDF e o áudio.

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