# RF12 — LGPD, privacidade e minimização

Tratamento de dados pessoais na Central Inteligente de Atendimento: quais dados o sistema recebe,
para que servem, o que é enviado ao provedor de IA, o que fica gravado e quais medidas reduzem o
risco. Todos os dados do projeto são fictícios; o inventário descreve como cada campo seria tratado
em um cenário real.

## Síntese

| Item do enunciado | Situação | Seção |
|---|---|---|
| Utilizar somente dados fictícios | Atendido: pessoas inventadas, CPFs com dígito verificador inválido, e-mails em domínios fictícios | 1 |
| Identificar quais campos seriam dados pessoais | Atendido: 17 itens inventariados, dos quais 16 são dados pessoais | 2 |
| Informar finalidade, necessidade e risco de cada campo | Atendido no inventário | 2 |
| Minimizar o envio de conteúdo ao provedor | Atendido para texto: CPF, RG, e-mail, telefone, data de nascimento, naturalidade e filiação são removidos antes do envio. Áudio e imagem continuam sendo enviados integralmente para transcrição e leitura | 3, 4, 5 |
| **Aceite:** nenhuma evidência com credencial ou dado pessoal real | Atendido: varredura de 179 arquivos e do histórico do git sem pendências | 7 |

## 1. Dados fictícios

| Arquivo de entrada | Origem | Pessoa | Evidência de que é fictício |
|---|---|---|---|
| `dados/originais/entrada_texto.txt` | Professor | Marcos Vinícius de Almeida Santos | Pessoa criada pelo professor; CPF 123.456.789-00 com dígito verificador inválido; e-mail em `examplo.com` |
| `dados/originais/entrada_audio.mp3` | Professor | Marcos Vinícius (mesmo caso, canal voz) | Mesma pessoa fictícia; voz gravada pelo professor para fins didáticos |
| `dados/originais/entrada_pdf-imagem.pdf` | Professor | Marcos Vinícius (mesmo caso, ficha) | Mesma pessoa fictícia; ficha preenchida e assinada pelo professor para fins didáticos |
| `dados/originais/caso1_solicitacao_completa.txt` | Equipe | Juliana Ferreira Campos | Pessoa inventada; CPF 111.222.333-44 com dígito inválido; e-mail em `exemplo.com` |
| `dados/originais/caso2_solicitacao_incompleta.txt` | Equipe | Roberto Alves Nunes | Pessoa inventada; CPF 222.333.444-55 com dígito inválido |
| `dados/originais/caso3_solicitacao_prompt_injection.txt` | Equipe | Patrícia Souza Ramos | Pessoa inventada; CPF 333.444.555-66 com dígito inválido |
| `dados/originais/caso3b_solicitacao_injection_delimitador.txt` | Equipe | Renata Lima Duarte | Pessoa inventada; CPF 444.555.666-77 com dígito inválido |
| `dados/originais/brasao.png` | Professor | — | Símbolo institucional público; não contém dado pessoal |

A pessoa é fictícia, mas a **voz** do áudio e a **letra e assinatura** da ficha são de quem os
produziu. Foram fornecidas pelo professor como material didático, com essa finalidade.

## 2. Inventário de campos

"Necessário para a minuta" indica se o campo é usado no modelo de minuta institucional
(`prompts/modelo_minuta.md`). A coluna "Medida" descreve o que o sistema faz hoje.

| Campo | Onde aparece | Dado pessoal? | Sensível (LGPD, art. 5º, II)? | Finalidade | Necessário para a minuta? | Risco | Medida |
|---|---|---|---|---|---|---|---|
| Nome do solicitante | Texto, áudio, ficha | Sim | Não | Identificar o destinatário e a saudação | **Sim** | Associa a pessoa ao pedido | Enviado; aparece na minuta; revisão humana obrigatória |
| Protocolo | Texto, áudio, ficha | Sim, indireto (vinculado à pessoa) | Não | Vincular a resposta ao pedido | **Sim** | Baixo; permite localizar o pedido | Enviado; aparece na minuta |
| Data da solicitação | Texto, áudio, ficha | Sim, indireto | Não | Registro do pedido | Não (o modelo não tem esse campo) | Baixo | Enviado e extraído para conferência; não vai para a minuta |
| Curso, eixo, carga horária, turno e início | Texto, áudio, ficha | Sim, quando associados ao nome (vida acadêmica) | Não | Conteúdo da minuta | **Sim** | Baixo a médio: compõe perfil da pessoa | Enviado; aparece na minuta |
| Declaração de ciência das regras | Texto, áudio, ficha | Sim (declaração do titular) | Não | Registrar que o solicitante conhece as regras de cancelamento | **Sim** | Baixo | Enviado; na minuta, reescrito na voz da Secretaria |
| CPF | Texto, áudio, ficha | Sim (identificador único) | Não, mas de alto impacto | Identificação civil no processo real de matrícula | Não | **Alto**: fraude e cruzamento de bases | **Removido antes do envio** (`[CPF REMOVIDO]`) |
| RG e órgão expedidor | Texto, áudio, ficha | Sim | Não | Identificação civil | Não | Alto | **Removido antes do envio** (`[RG REMOVIDO]`) |
| Data de nascimento | Texto, áudio, ficha | Sim | Não; revela se o estudante é menor de idade | Verificação de idade no processo real | Não | Médio: com o nome, identifica a pessoa; indica menoridade | **Removida antes do envio** |
| Naturalidade e UF | Texto, áudio, ficha | Sim | Não | Cadastro | Não | Baixo a médio: combinada a outros dados, facilita a reidentificação | **Removida antes do envio** |
| Nome da mãe e do pai | Texto, áudio, ficha | Sim, inclusive de terceiros | Não | Cadastro e identificação | Não | Médio: dado de terceiros, usado em validações de identidade | **Removido antes do envio** (`[FILIAÇÃO REMOVIDA]`) |
| E-mail | Texto, áudio, ficha | Sim | Não | Canal de resposta | Não: a minuta não é enviada pelo sistema | Médio: phishing e contato indevido | **Removido antes do envio** |
| Telefone | Ficha | Sim | Não | Canal de contato | Não | Médio | **Removido antes do envio** |
| Voz | Áudio | Sim; potencialmente biométrico | Seria sensível se usada para identificar a pessoa; o sistema não faz isso | Canal de atendimento por voz | Não (só o conteúdo falado) | **Alto** | Áudio enviado integralmente para transcrição (seção 9) |
| Assinatura manuscrita | Ficha | Sim | Não | Comprovar a ciência no documento físico | Não | **Alto**: falsificação | Imagem da ficha enviada integralmente para leitura (seção 9) |
| Imagem do documento | Ficha | Sim (contém todos os campos acima) | Não | Leitura da ficha | Não, só o texto lido | Alto | Enviada integralmente; o texto lido é minimizado antes da extração |
| Transcrição ou leitura bruta | Áudio, ficha | Sim (contém todos os campos falados ou escritos) | Não | Revisão humana da transcrição (RF06) | Não | Médio: armazenamento local | Transcrição bruta do áudio gravada localmente; texto lido da imagem não é gravado bruto |
| Brasão institucional | Minuta | Não | — | Identidade visual da minuta | Sim | — | — |

## 3. Fluxo de dados

| Etapa | Módulo | O que vai ao provedor | Modelo | Dados pessoais enviados | O que fica gravado localmente |
|---|---|---|---|---|---|
| Recebimento | `interface.py` (`guardar_copia`) | Nada | — | — | Cópia integral do arquivo recebido em `dados/originais/` |
| Transcrição do áudio | `audio.py` (`transcrever_audio`) | Arquivo de áudio inteiro | `gpt-4o-transcribe` | Voz e todos os dados falados | Transcrição bruta em `dados/processados/transcricao_<arquivo>.txt` |
| Leitura de imagem ou PDF | `vision.py` (`ler_texto_visual`) | PDF com texto (≥ 40 caracteres): nada, leitura local com PyMuPDF. Imagem ou PDF digitalizado: a primeira página como imagem | `gpt-4o` | Imagem com todos os dados, inclusive assinatura. A ficha do projeto não tem camada de texto (0 caracteres) e é enviada como imagem | Nada além da extração final |
| **Minimização** | `privacidade.py`, chamada em `fluxo.py` | Nada (processamento local) | — | — | — |
| Extração e minuta | `llm_client.py` (`extrair_campos`) | Texto **já minimizado**, entre `<solicitacao>`, com `store: False` | `gpt-6-luna` | Só os campos da minuta (nome, protocolo, datas e dados do curso, declaração de ciência) | `dados/processados/extracao_<arquivo>.json` com o texto minimizado, os campos, a minuta e `dados_removidos` |
| Leitura estruturada da ficha (RF08) | `vision.py` (`extrair_ficha`) | Imagem da ficha | `gpt-4o` | Imagem com todos os dados | `dados/processados/extracao_rf08.json`. O pedido atual solicita só os 12 campos da minuta |
| Síntese de voz (RF07) | `audio.py` (`gerar_audio`) | Texto da minuta | `tts-1-hd` | Nome, protocolo e dados do curso | Áudio sintético em `resultados/audios/` |
| Imagem institucional (RF10) | `image_generation.py` | Prompt descritivo | `gpt-image-1` | Nenhum | Imagens em `resultados/imagens/` |

O parâmetro `store: False` está configurado na chamada de extração (Responses API). As demais
chamadas (transcrição, leitura de imagem, voz e imagem) seguem a política de retenção do provedor
para uso por API.

## 4. Minimização implementada

**Onde:** `src/privacidade.py`, função `minimizar_texto`, chamada em `src/fluxo.py` logo após a
extração do texto (digitado, transcrito ou lido da imagem) e antes de `extrair_campos`. O
`texto_extraido` gravado em `dados/processados/` já é o texto minimizado, e o campo
`dados_removidos` registra quantos dados de cada tipo foram retirados.

**O que remove:** CPF, RG, e-mail, telefone, data de nascimento, naturalidade e filiação, cada um
trocado por um marcador (`[CPF REMOVIDO]`, `[FILIAÇÃO REMOVIDA]`…). Os dados que a minuta usa — nome,
protocolo, datas e dados do curso, declaração de ciência — são preservados.

**Como reconhece:** por formato (ex.: `123.456.789-00`, `(65) 99876-5432`, endereço com `@`) e por
rótulo, removendo o valor que vem depois de "CPF", "RG", "e-mail", "nome da mãe", "nasci em",
"NATURALIDADE:" etc. O reconhecimento por rótulo cobre as formas em que os dados aparecem nas
entradas do projeto:

| Forma | Exemplo da entrada | Resultado |
|---|---|---|
| Texto digitado | `CPF 123.456.789-00; RG 1234567-8; nome da mãe, Lúcia Helena…` | `CPF [CPF REMOVIDO]; RG [RG REMOVIDO]; nome da mãe, [FILIAÇÃO REMOVIDA]` |
| Fala transcrita | `Meu CPF é 1-2-3-4-5-6-7-8-9-00`, e-mail transcrito sem `@` | `Meu CPF é [CPF REMOVIDO]`, `[E-MAIL REMOVIDO]` |
| Formulário (OCR) | `NATURALIDADE: CUIABÁ UF:`, `NOME DO PAI:` vazio | `NATURALIDADE: [NATURALIDADE REMOVIDA] UF:`; campo vazio mantido |

**Cuidados validados por teste:** não ultrapassa a quebra de linha (um campo vazio não apaga a linha
seguinte); não reprocessa marcadores já inseridos; mantém intactos textos sem dado pessoal, como
"os documentos são RG, CPF e comprovante" ou "Canal: E-mail"; extrações antigas, feitas sem
minimização, são refeitas na próxima vez que a entrada for processada.

**Testes:** `testes/test_rf12.py`, 11 testes sem chamada à API — remoção de cada dado em cada forma;
preservação de todos os campos do gabarito nos 5 casos de texto; integração com o `fluxo.py`
(o modelo recebe o texto minimizado e o registro guarda `dados_removidos`). Suíte completa do
projeto: 48 testes.

## 5. Evidências

### 5.1 Teste pelo sistema real (interface, `gpt-6-luna`, prompt v3)

| | CASO-04 sem minimização (RF03, execução E4) | CASO-04 com minimização (interface) | Áudio com minimização (interface) |
|---|---|---|---|
| Dados pessoais removidos antes do envio | 0 | 6 (CPF, RG, e-mail, data de nascimento, naturalidade, filiação) | 6 (os mesmos, da fala transcrita) |
| Dados pessoais enviados ao provedor na extração | 6 | **0** | **0** |
| Campos corretos em relação ao gabarito | 12/12 | **12/12** | **12/12** |
| Alertas de segurança | Nenhum | Nenhum | Nenhum |
| Dados pessoais no JSON gravado | — | Nenhum | Nenhum |
| Tokens de entrada | 1.981 | 2.008 | 1.967 |

- A minimização não alterou a extração nem a minuta. A única diferença na minuta do CASO-04 foi
  "O(a) solicitante" → "O solicitante", variação já observada no RF03 sem minimização.
- **Tokens:** a minimização não reduziu o tamanho da entrada; os marcadores ocupam mais tokens que
  os valores que substituem (+27 tokens no CASO-04, cerca de US$ 0,000003 por chamada). O objetivo da
  medida é não enviar dado pessoal, não reduzir custo.
- Arquivos: `dados/processados/extracao_entrada_texto.json` e `extracao_entrada_audio.json`.

### 5.2 Outras evidências

- **Minutas sem dados pessoais:** as 21 minutas do prompt seguro no RF03 não contêm CPF, RG, e-mail,
  data de nascimento, naturalidade nem nome da mãe (`documentacao/rf03_prompt_seguro.md`).
  A minuta é protegida por duas camadas: o dado não é enviado (minimização) e, se for, o prompt
  proíbe reproduzi-lo.
- **Leitura da ficha (RF08):** o pedido atual ao modelo solicita apenas os 12 campos da minuta; CPF,
  RG e filiação não são pedidos.

## 6. Outras medidas existentes

- `store: False` na chamada de extração: a resposta não é armazenada pelo provedor para reutilização.
- Revisão humana obrigatória (`requer_revisao` sempre verdadeiro); nenhuma minuta é enviada ao
  cidadão pelo sistema.
- Credenciais fora do código: chave em `.env`, ignorado pelo git; `.env.example` sem valor.
- Prompt de produção proíbe reproduzir CPF, RG, data de nascimento, naturalidade, nome da mãe e
  e-mail na minuta.

## 7. Varredura da entrega (critério de aceite)

`src/varredura_rf12.py` confere todos os arquivos que iriam na entrega — versionados e novos, exceto
os ignorados pelo `.gitignore` — e o histórico do git. Procura chaves de API, variáveis de
credencial preenchidas, `.env` versionado, CPFs com dígito verificador válido e e-mails fora dos
domínios fictícios. Valores encontrados aparecem mascarados no relatório, e o script sai com código
1 se houver pendência.

Resultado de 18/10/2026 (`resultados/logs/varredura_rf12.md`):

| Verificação | Resultado |
|---|---|
| Arquivos verificados | 179 (11 binários, conferidos só pelo nome), incluindo este documento |
| Chaves de API nos arquivos | Nenhuma |
| Variáveis de credencial preenchidas | Nenhuma |
| `.env` versionado | Não |
| Chaves de API no histórico do git (todas as branches) | Nenhuma |
| CPFs com dígito verificador válido | Nenhum |
| E-mails fora dos domínios fictícios | Nenhum |
| CPFs fictícios encontrados (dígito inválido) | 7 |
| E-mails fictícios encontrados | 4 (`exemplo.com`, `examplo.com`) |
| **Resultado** | **Aprovado** |

Antes de a varredura existir, ela foi validada com problemas inseridos de propósito em uma cópia do
projeto: chave, CPF válido, e-mail real, `.env` versionado e chave apagada mas presente no histórico
foram detectados, e nenhum valor apareceu por inteiro no relatório.

**Para a entrega:** rodar `python -m src.varredura_rf12` no último commit e gerar o arquivo com
`git archive --format=zip -o entrega.zip HEAD`. O arquivo `.env`, com a chave, existe na pasta local
e é ignorado pelo git; compactar a pasta diretamente o incluiria no pacote.

### 7.1 Arquivos versionados com dados pessoais fictícios

São evidências de etapas do projeto e foram mantidos como estão. A varredura confirma que os CPFs
neles são fictícios.

| Arquivos | Por que contêm dados pessoais fictícios |
|---|---|
| `dados/originais/*.txt` | Entradas originais, mantidas inalteradas |
| `dados/gabaritos/gabarito_entrada_audio.json`, `gabarito_entrada_pdf-imagem.json` | Transcrição de referência e OCR esperado, usados para avaliar o RF06 e o RF08 |
| `dados/processados/transcricao_*.txt` | Transcrições brutas do áudio, usadas na revisão humana do RF06 |
| `dados/processados/extracao_rf08*.json` | Leituras da ficha no formato anterior à padronização do RF08 |
| `dados/processados/extracao_caso2_solicitacao_incompleta.json` | Extração anterior à minimização; será refeita na próxima vez que a entrada for processada |
| `resultados/minutas/rf02/*/entrada_prompt_*.txt`, `resultados/minutas/rf03/*/CASO-*_prompt_A_entrada.txt` e `registro_rf03.json` | Entradas enviadas nos experimentos de prompt, executados antes da minimização |
| `src/privacidade.py`, `testes/test_rf12.py`, `src/experimento_rf03.py`, `resultados/logs/varredura_rf12.md` | Exemplos e padrões usados para testar e verificar a minimização |

## 8. Cenário real

Em produção, com dados reais de cidadãos, o tratamento exigiria:

- **Base legal:** tratamento pelo poder público para execução de políticas públicas e atendimento de
  sua finalidade pública (LGPD, art. 7º, III, e art. 23), com transparência sobre o uso de IA no
  atendimento. A definição cabe ao encarregado de dados (art. 41) do órgão.
- **Estudantes menores de idade:** cursos técnicos recebem adolescentes, e a data de nascimento é o
  campo que revela essa condição. O tratamento deve observar o melhor interesse do titular (art. 14).
  O caso fictício do projeto tem 18 anos na data da matrícula.
- **Transferência internacional:** o provedor processa os dados fora do país. O envio de dados
  pessoais exige enquadramento nas hipóteses do art. 33 e avaliação contratual do provedor. A
  minimização reduz o que é transferido, mas não elimina a transferência de nome, protocolo e dados
  do curso, nem do áudio e da imagem.
- **Processamento local:** transcrição e leitura de documentos com modelos executados na
  infraestrutura do órgão evitariam enviar voz, assinatura e imagem do documento ao provedor. É a
  medida mais efetiva para os dois maiores riscos residuais deste sistema e também atende a
  preocupações de soberania sobre os dados.
- **Retenção e descarte:** definir prazos para `dados/originais/` (arquivos integrais),
  transcrições brutas e extrações, com descarte após a conclusão do atendimento ou o prazo legal de
  guarda do processo.
- **Direitos dos titulares (art. 18):** permitir localizar e excluir os registros de uma pessoa
  pelo protocolo.

## 9. Riscos residuais e recomendações

| # | Risco | Situação no protótipo | Recomendação |
|---|---|---|---|
| 1 | Voz enviada integralmente ao provedor | Áudio inteiro vai para a transcrição | Transcrição local; ou orientar o cidadão a não falar documentos no áudio |
| 2 | Imagem da ficha enviada integralmente, com assinatura | A ficha não tem camada de texto e vai inteira ao `gpt-4o` | OCR local; ou recortar e enviar apenas as áreas dos campos usados na minuta |
| 3 | Dado escrito de forma não prevista não é removido | A remoção usa padrões e rótulos (ex.: CPF por extenso, "minha genitora se chama…") | Manter a revisão humana; ampliar os padrões a partir dos casos reais encontrados |
| 4 | Dados pessoais gravados localmente sem prazo de descarte | Originais e transcrições brutas ficam em `dados/` | Política de retenção e descarte (seção 8) |
| 5 | Nome, protocolo e dados do curso continuam sendo enviados | São necessários para a minuta | Necessidade justificada no inventário; aceitar como risco residual |
| 6 | Pacote da entrega incluir o `.env` | Mitigado pela varredura e pelo uso de `git archive` | Rodar a varredura e gerar o pacote com `git archive` |
