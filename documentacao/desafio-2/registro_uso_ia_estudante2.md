# Registro de uso de IA: Estudante 2 (Maria Luiza)

*Rascunho para a seção 13 do relatório. Conferir e ajustar antes de entregar: cada afirmação abaixo
deve refletir o que de fato aconteceu.*

## Ferramentas

- Assistente de IA generativa (Claude, da Anthropic), em conversa de chat com envio de arquivos do
  projeto, usado para revisar código, propor implementações, escrever testes e rascunhar textos.
- O código sugerido foi colado e executado por mim; as execuções com a API (OpenAI) foram feitas na
  minha máquina.
- Modelo: Claude Sonnet 5.5 na sessão de 30 e 31/10. O modelo das sessões anteriores não foi registrado na época.

## Solicitações relevantes

1. **Revisão da minha parte do código** (índice, RAG e provedor) contra o enunciado: apontou lacunas
   (sem exclusão de documento, sem script de indexação, avaliação de chunking com perguntas diferentes
   do gabarito, auditoria incompleta, acentos gravados como `?`, dois padrões de expressão regular
   errados).
2. **Investigação das respostas ruins do RAG** (0/5 respondíveis na primeira execução real): a partir da
   saída bruta do modelo, identificou três causas diferentes (validador de citações rígido com as
   quebras de linha do PDF, identificador de trecho errado e citações com reticências).
3. **Remoção das regras específicas** para P04, P05 e P08 e substituição por métodos gerais
   (vigência, quarentena de instruções em documentos e segunda leitura de contradição).
4. **Seleção de geração e auditoria** (RF21): configuração escolhida por nome, provedor simulado
   identificado como tal, tratamento da falha do serviço e registro de cada consulta.
5. **Minuta fundamentada do CASO-08** (31/10): uma consulta ao acervo por assunto (documentos, local e período), com fontes, e geração da minuta pendente de revisão humana.
6. **Falsos conflitos no RAG** (31/10): a primeira minuta saiu com o período em conflito; a análise mostrou que o verificador comparava linhas de chamadas diferentes e que o conflito declarado pelo modelo não conferia a vigência. Duas correções gerais, com testes.

## Sugestões aceitas, modificadas e rejeitadas

- **Aceitas:** índice reproduzível por comando; avaliação de chunking com as perguntas do gabarito;
  correção dos acentos e das expressões regulares; segunda leitura de contradição; avaliação em várias
  rodadas (`--repeticoes`); consulta ao acervo por assunto na minuta (regra por categoria de pedido, não por caso);
  ajuste do gabarito para a versão 1.2, com variantes de redação em P01 e P02, feito depois de ver as
  respostas da API (declarado no relatório).
- **Modificadas:** a ideia de manter as regras específicas com um interruptor para comparar "com e sem"
  foi trocada por removê-las (os resultados anteriores já estavam gravados); a regra de enviar à revisão
  qualquer resposta com trecho suspeito recuperado foi restringida a respostas que citam o documento
  alertado.
- **Descartada:** aceitar "pessoalmente" como alternativa no gabarito da P02, porque a palavra aparece
  na própria pergunta (e o teste do projeto proíbe isso).

## Erros da IA encontrados e como foram tratados

- Uma correção de expressão regular ficou incompleta para PDFs (dividia o texto em cada quebra de
  linha) e deixou o validador de citações rígido demais; foi percebida na execução real e corrigida.
- Testes escritos num ambiente Linux falharam no Windows (separador de caminho); corrigido.
- Um bloco de instruções tinha crases dentro de outro bloco de código e chegou quebrado ao terminal;
  reenviado corrigido.
- Em um momento, a IA tratou as regras específicas por pergunta como se fossem de outra origem;
  foi corrigida, porque esse código da minha parte do RF19 foi escrito por mim.
- Uma hipótese da IA sobre a causa dos conflitos (diferença entre os símbolos `º` e `ª`) estava errada; foi descartada ao ler o código da vigência, que já normaliza os dois, e a causa real era outra.
- Um script colado no PowerShell gravou o arquivo da conferência humana com `?` no lugar dos acentos (o Python recebeu o script sem UTF-8); percebido na conferência do arquivo e corrigido com `$OutputEncoding` e `python -X utf8`.

## Como o código e o conteúdo foram validados

- Testes automáticos (473 na última execução), incluindo testes que quebram o código de propósito para
  confirmar que falham.
- Execuções reais com a API (três rodadas por configuração) e conferência das respostas e das
  citações; a conferência automática por palavras foi tratada como indicador, e a leitura humana,
  como decisão final.
- Evidência real separada de simulação: o provedor `simulado` e o codificador falso dos testes estão
  identificados como tais e não substituem as execuções reais.

## Limites declarados

- O resultado dos modelos varia entre execuções; por isso os números vêm de três rodadas.
- Os custos são estimativas pela tabela de preços do projeto.
- A minuta fundamentada depende de a busca trazer o trecho certo para cada assunto: a lista de documentos
  gerada com o `gpt-4o-mini` vai até a alínea f, e com a configuração `forte` a consulta de documentos se
  absteve (ver relatório).
