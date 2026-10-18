# RF07 — Síntese de voz e acessibilidade

Versão falada da minuta aprovada, gerada na própria interface depois da aprovação do servidor.

## Síntese

| Item do enunciado | Como é atendido | Seção |
|---|---|---|
| Versão falada da **minuta aprovada** | O áudio sai do arquivo da minuta aprovada e assinada, sob demanda, no quadro da aprovação | 1 |
| Text-to-speech por API | `gpt-4o-mini-tts` (OpenAI); `tts-1-hd` como alternativa registrada | 1 |
| Voz e instruções de entonação institucionais | Voz `nova` e instruções de tom institucional, cordial e calmo, com ritmo pausado | 1 |
| Não sintetizar "não localizado" sem aviso | Aviso falado no início quando a minuta tem campo não localizado | 1 |
| Arquivo em formato comum | MP3 em `resultados/audios/` | 1 |
| Documentar acessibilidade e limitações | Seções 2 e 3 | 2, 3 |
| **Aceite:** o áudio corresponde ao texto aprovado, sem acréscimos | Texto falado salvo ao lado do áudio; teste automático garante que nenhuma palavra do aprovado se perde | 1 |

## 1. Áudio da minuta aprovada

**Onde:** botão "Gerar áudio da minuta" no quadro da minuta aprovada (`src/interface.py`), que chama
`gerar_audio_da_minuta` (`src/fluxo.py`) e `sintetizar_minuta` (`src/audio.py`). O áudio só existe
depois da aprovação; na rejeição, o botão não aparece. Cada aprovação gera no máximo um áudio: se ele
já existe, é reaproveitado sem nova chamada.

**Configuração** (`config.json`):

| Item | Valor |
|---|---|
| Modelo | `gpt-4o-mini-tts`; se a chave não tiver acesso, `tts-1-hd` (sem instruções), registrado como `instrucoes_aplicadas: false` |
| Voz | `nova` (a mesma avaliada na primeira versão do RF07, seção 4) |
| Instruções de entonação | "Fale em português do Brasil, com tom institucional, cordial e calmo. Ritmo pausado. Leia números e datas com clareza, fazendo pausa entre os grupos do protocolo. Não acrescente nem omita palavras." |
| Formato | MP3 |

**Texto falado = texto aprovado, ajustado para a voz** (`preparar_texto_para_fala`). Os ajustes
são só de forma:

| Na minuta aprovada | No texto falado | Motivo |
|---|---|---|
| `[CABEÇALHO COM BRASÃO — …]`, `**`, `-`, `*` | removidos | Marcações visuais, sem sentido na fala |
| `2026-000142` | "2026, traço, 0 0 0 1 4 2" | A primeira versão do RF07 pronunciava mal o protocolo (seção 4) |
| `01/02/2027` | "1º de fevereiro de 2027" | Datas numéricas são lidas de forma ambígua |
| `Prezado(a)` · `O(a) solicitante` | "Prezado ou prezada" · "O solicitante" | A forma "(a)" é lida como letra solta |
| campo "não localizado" | aviso no início: "Atenção: esta minuta contém campos não localizados. Confira as informações antes de prosseguir." | Exigência do RF07 |

**Correspondência ao texto aprovado (critério de aceite):** o texto exato enviado à voz é salvo ao
lado do áudio (`…_texto_falado.txt`), e o teste `test_nenhuma_palavra_do_texto_aprovado_se_perde`
(`testes/test_audio.py`) confere, palavra por palavra, que tudo o que está na minuta aprovada aparece
no texto falado. O único acréscimo é o aviso exigido pelo próprio RF07.

**Arquivos e registro:** `resultados/audios/audio_minuta_<arquivo>_<id>.mp3` e
`…_texto_falado.txt`, sem sobrescrever; evento `audio_minuta` em `resultados/logs/execucoes.jsonl`
com o id da execução, modelo, voz, instruções, se foram aplicadas, duração do áudio, tempo de geração
e custo estimado (US$ 0,015 por minuto, tabela do provedor a conferir), ou o erro.

**Teste real (18/10/2026):** minuta do `entrada_texto.txt` aprovada e assinada; `gpt-4o-mini-tts` com
instruções aplicadas; 84,5 s de áudio gerados em 14,1 s; custo estimado US$ 0,021. Na escuta, o aviso
de campos não localizados, o protocolo por partes, as datas por extenso e a assinatura do servidor
foram lidos corretamente. Os áudios definitivos da entrega são gerados na demonstração final.

## 2. Como o recurso amplia a acessibilidade

- **Pessoas cegas ou com baixa visão:** recebem a resposta em áudio, sem depender de leitor de tela
  para interpretar um PDF com cabeçalho, listas e rodapé.
- **Pessoas com baixo letramento, dislexia ou dificuldade de leitura:** ouvem a resposta inteira,
  com datas por extenso e o protocolo pausado, que são os pontos onde a leitura costuma falhar.
- **Pessoas idosas e quem atende por telefone ou aplicativo de mensagens:** o MP3 toca em qualquer
  celular e pode ser enviado pelo servidor pelo mesmo canal em que o pedido chegou.
- **Transparência:** o aviso de campos não localizados e a frase "Minuta elaborada com apoio de IA"
  também são falados, então quem só ouve recebe as mesmas ressalvas de quem lê.
- **Fidelidade:** como o áudio sai da minuta já aprovada e assinada, o cidadão ouve exatamente o que
  o servidor aprovou.

## 3. Limitações que permanecem

- **Pessoas surdas ou com deficiência auditiva não são atendidas pelo áudio;** a acessibilidade para
  elas exigiria Libras ou texto simplificado, que o sistema não oferece.
- **Voz sintética:** a naturalidade ainda pode melhorar, e nomes próprios incomuns podem ser
  pronunciados de forma errada; a escuta do servidor antes de enviar continua necessária.
- **Neutralidade de gênero:** "O(a) solicitante" vira "O solicitante" na fala, que não é neutro.
- **Sem legenda sincronizada:** o áudio não acompanha o texto palavra a palavra.
- **Só português:** a voz e as instruções são em português do Brasil.
- **Dependência do provedor:** a minuta aprovada (com nome, protocolo e dados do curso) é enviada à
  API de voz; os riscos estão no `rf12_lgpd_privacidade.md`. Uma voz executada localmente evitaria o
  envio.
- **A interface não foi avaliada com leitores de tela;** a acessibilidade do próprio sistema para
  servidores com deficiência não foi testada.

## 4. Primeira versão: voz a partir de texto fixo (Maria Luiza)

Antes da integração ao fluxo, o RF07 foi construído com um texto fixo
(`resultados/minutas/texto_rf07.txt`) e a função `gerar_audio()`, que continua no código. Os áudios
dessa fase (`resultados/audios/audio_rf07*.mp3`) e a avaliação abaixo são o histórico que orientou a
leitura do protocolo por partes e a escolha da voz.

### Avaliação final — Terceira versão

Responsável pela revisão humana: Maria Luiza

- A primeira versão apresentou pronúncia inadequada do protocolo.
- A segunda versão melhorou a leitura do protocolo, mas apresentou problemas de naturalidade no encerramento.
- A terceira versão apresentou melhora significativa na pronúncia e na compreensão da mensagem.
- O áudio foi reproduzido com sucesso no reprodutor do Windows.
- A naturalidade ainda pode ser aprimorada.

**Resultado:** Aprovado para demonstração, com ressalva quanto à naturalidade da voz.

**Decisão:** Manter a terceira versão como resultado do RF07 e preservar as anteriores como evidências da avaliação humana.

### Testes de tratamento de erros — RF07

**Teste 1 — Arquivo inexistente**
- Método: simulação com `unittest.mock`.
- Resultado: APROVADO.
- Comportamento observado: a função lançou `FileNotFoundError`.

**Teste 2 — Texto vazio**
- Método: simulação com `unittest.mock`.
- Resultado: APROVADO.
- Comportamento observado: a função lançou `ValueError`.

**Conclusão:** Os dois testes de tratamento de erros foram aprovados. Não houve chamadas adicionais à API durante os testes.
