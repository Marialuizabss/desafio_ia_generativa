# RF08 — Visão e OCR

**Responsáveis pela revisão humana:** Maria Luiza (leitura estruturada, seções 1 a 6) e Ana Beatriz
Schuindt (integração ao fluxo e avaliação final, seções 7 a 10)

## Síntese

| Item do enunciado | Como é atendido | Seção |
|---|---|---|
| Rota de OCR ou visão multimodal | Visão multimodal (`gpt-4o`); PDF com camada de texto lido localmente (PyMuPDF) | 3, 7 |
| Preservar o arquivo original e o texto bruto | `dados/originais/` intacto; leituras em `dados/processados/` | 2, 7 |
| Versão corrigida sem alterar o sentido | `extracao_rf08_revisada.json`; no fluxo, correção pelo servidor na etapa 3 | 2, 7 |
| Identificar trechos ilegíveis ou incertos | Instrução `[ilegível]` na leitura; campos incertos marcados no gabarito | 7 |
| Comparar com gabarito e registrar acertos e erros | Seção 2 (primeira leitura) e seção 8 (avaliação final, 10/12) | 2, 8 |
| Justificar quando o processamento local seria preferível | Seção 9 | 9 |
| **Aceite:** dados críticos da imagem com confirmação humana | Conferência obrigatória de nome, protocolo e datas na etapa 3 | 7 |

## 1. Objetivo

Avaliar a extração de informações de uma ficha de matrícula digitalizada por meio de visão multimodal, verificando a estrutura do resultado, a identificação de campos ausentes e a necessidade de revisão humana.

## 2. Evidências da revisão manual do caso anterior

Os arquivos `extracao_rf08_original.json` e `extracao_rf08_revisada.json` registram uma extração anterior, baseada nos campos `codigo`, `nome`, `data_nascimento`, `nome_mae`, `email` e `data_matricula`, entre outros.

Na comparação entre os dois arquivos, foram registradas seis divergências:

- Código: `2022-000142` para `2026-000142`.
- Nome: `MARLON VINICIUS DE ALMEIDA SANTOS` para `MARCOS VINICIUS DE ALMEIDA SANTOS`.
- Data de nascimento: `12/05/2008` para `12/08/2008`.
- Nome da mãe: `LUCA HELENA DE ALMEIDA SANTOS` para `LUCIA HELENA DE ALMEIDA SANTOS`.
- E-mail: `MARLON.ALMEIDA.TESTE@EXEMPLO.COM` para `MARCOS.ALMEIDA.TESTE@EXEMPLO.COM`.
- Data da matrícula: `17/01/2026` para `14/10/2026`.

Esses arquivos são evidências da revisão manual anterior e não devem ser confundidos com a saída produzida pela implementação atual.

## 3. Implementação atual

O módulo `src/vision.py` processa a imagem `dados/processados/entrada_rf08_pagina1.png` e grava o resultado em `dados/processados/extracao_rf08.json`.

A implementação atual utiliza uma estrutura com identificação do caso, modalidade, arquivo de origem, campos extraídos com seus respectivos valores e fontes, lista de campos ausentes, metadados de execução e indicação de revisão humana pendente.

## 4. Tratamento de erros

Os testes automatizados específicos do RF08 verificam:

- Imagem inexistente: a função lança `FileNotFoundError`.
- Resposta vazia da API: a função lança `ValueError`.
- Extração simulada com sucesso: o resultado é validado conforme o formato esperado pela implementação atual.

**Resultado dos testes:** os três testes específicos do RF08 passaram na última execução.

## Falhas da API (RF04)

Quando a chamada à API falha, o módulo traduz o erro em uma mensagem em português que diz o motivo e
o que fazer, em vez de mostrar o erro técnico em inglês. As mensagens ficam em `src/erros_api.py` e
nunca citam a chave de acesso.

| Falha | Mensagem mostrada ao servidor |
|---|---|
| Chave recusada ou ausente | A chave de acesso não foi aceita (ou encontrada). Confira o arquivo `.env`. |
| Limite de uso da conta | O limite de uso foi atingido. Aguarde um pouco e tente de novo. |
| Tempo esgotado | O serviço demorou demais para responder. Tente de novo. |
| Sem conexão | Falha de conexão com o serviço. Confira a internet. |
| Modelo indisponível | O modelo configurado não está disponível para esta conta. Confira o `config.json`. |
| Arquivo ou texto recusado | O serviço recusou o arquivo ou o texto enviado. Confira o formato e o tamanho. |
| Erro do servidor | O serviço respondeu com erro (código). Tente de novo em instantes. |

Cada mensagem começa com o que não foi possível fazer ("a leitura do documento" ou "a leitura da ficha").

## 5. Segurança e revisão humana

A implementação atual instrui o modelo a não incluir CPF, RG, data de nascimento, nomes dos pais ou e-mail no resultado compartilhado com a minuta. Também trata instruções presentes no documento como conteúdo não confiável.

A revisão humana permanece obrigatória antes da utilização das informações em um processo administrativo.

## 6. Conclusão

O RF08 possui uma implementação funcional e testes automatizados aprovados. Os arquivos de extração original e revisada preservam evidências de uma revisão manual anterior, enquanto a saída atual segue um esquema diferente.

A validação integral da fidelidade da extração atual depende da conferência do resultado com o documento de entrada.

**Resultado:** aprovado nos cenários automatizados disponíveis, com conferência humana necessária para validar os dados extraídos.

## 7. No fluxo do sistema entregue

Quando a entrada é imagem ou PDF, o fluxo usa `ler_texto_visual` (`src/vision.py`):

- **PDF com camada de texto** (40 caracteres ou mais): lido localmente com PyMuPDF, sem enviar nada ao
  provedor.
- **Imagem ou PDF digitalizado:** a primeira página vai ao `gpt-4o` com instruções de transcrever o
  texto como está, marcar trechos ilegíveis como `[ilegível]` e tratar qualquer comando escrito no
  documento como texto, não como instrução. A ficha do projeto não tem camada de texto e segue por
  esse caminho.
- O texto lido passa pela minimização de dados pessoais (RF12) antes da extração dos campos.
- **Confirmação humana (critério de aceite):** na etapa 3 da interface, o servidor vê a ficha
  original ao lado e precisa marcar nome do solicitante, protocolo, data da solicitação e data de
  início como conferidos; corrigir um campo desmarca a conferência dele, e a minuta só é montada com os
  quatro conferidos. A conferência fica registrada no log (`dados_conferidos`).

## 8. Avaliação final (RF13, `gpt-5.6-luna`, 18/10/2026)

Na avaliação do sistema entregue (`resultados/avaliacao/execucao_20261018_184910/CASO-06_*`), a ficha
teve **10 de 12 campos corretos**:

| Campo | Gabarito | Lido | Resultado |
|---|---|---|---|
| Solicitante | Marcus Vinicius de Almeida Santos | MARCUS VINICIUS DE ALMEIDA SANTOS | Acerto |
| Protocolo | 2026-000142 | 2024-000142 | **Erro crítico** |
| Data da solicitação | 14/10/2026 | 17/01/2026 | **Erro crítico** |
| Curso, eixo, carga horária, turno, início e ciência | conforme a ficha | conforme a ficha | Acertos |
| Documentos, prazo e local | não localizado | não localizado | Acertos |

O erro no ano do protocolo e na data é **sistemático**: aparece em todas as leituras da letra
manuscrita desde a primeira (seção 2). Gerar de novo não corrige. A decisão foi **correção manual**:
o servidor corrige os dois campos a partir da ficha original na etapa 3.

**Nome na ficha:** a primeira revisão manual (seção 2) corrigiu o nome para "MARCOS". Na releitura da
imagem ampliada para o RF13, a letra depois de "MARC" foi lida como "U", e o gabarito passou a
"Marcus" (registrado em `revisao_gabarito` no `gabarito_entrada_pdf-imagem.json`). O texto do
professor traz "Marcos": a diferença entre os canais é justamente o que a conferência humana resolve.

**Limitação aceita:** a ficha foi preenchida à mão, com traços ambíguos nos dígitos, e a visão
multimodal não lê esses campos de forma confiável. Por isso o sistema não trata a leitura de
protocolo e datas como definitiva: a conferência humana na etapa 3 é obrigatória, e a minuta só é
montada depois dela.

## 9. Quando o processamento local seria preferível

O enunciado pede justificar quando seria preferível processar localmente por soberania ou
privacidade. Neste sistema, o processamento local seria preferível:

- **Documentos com assinatura, filiação e números de identificação:** a imagem da ficha vai inteira ao
  provedor, com assinatura e dados que a minimização só retira depois da leitura. Um OCR local
  (por exemplo, Tesseract, PaddleOCR ou um modelo de visão aberto executado na infraestrutura do
  órgão) evitaria esse envio.
- **Soberania dos dados públicos:** fichas de matrícula são documentos de um órgão público; mantê-las
  na infraestrutura do Estado evita transferência internacional (LGPD, art. 33) e dependência de um
  fornecedor estrangeiro.
- **Volume alto e custo previsível:** em produção, milhares de fichas por período de matrícula teriam
  custo por chamada; um OCR local tem custo fixo.
- **Funcionamento sem internet:** unidades com conexão instável continuariam lendo documentos.

**O que já é local:** PDFs com camada de texto são lidos com PyMuPDF sem envio ao provedor, e a
minimização roda localmente antes da extração. **Limitação:** OCR local tende a errar mais em letra
manuscrita, que é justamente o ponto fraco observado (seção 8); por isso a confirmação humana
continua obrigatória em qualquer rota.

## 10. Arquivos

| Arquivo | Conteúdo |
|---|---|
| `dados/originais/entrada_pdf-imagem.pdf` | Ficha original, intacta |
| `dados/processados/entrada_rf08_pagina1.png` | Página convertida em imagem |
| `dados/processados/extracao_rf08_original.json` e `extracao_rf08_revisada.json` | Primeira leitura e versão corrigida (seção 2) |
| `dados/processados/extracao_entrada_pdf-imagem.json` | Leitura e extração no fluxo do sistema entregue |
| `dados/gabaritos/gabarito_entrada_pdf-imagem.json` | Gabarito, com a revisão do nome |
| `resultados/avaliacao/execucao_20261018_184910/CASO-06_*` | Avaliação final |
| `testes/test_vision.py` | Testes de leitura e tratamento de erros |