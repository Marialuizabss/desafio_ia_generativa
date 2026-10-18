# RF06 — Transcrição de áudio

## Síntese

| Item do enunciado | Como é atendido | Onde |
|---|---|---|
| Validar extensão e tamanho | mp3, wav, m4a, ogg e webm, até 25 MB (`config.json`); arquivo fora disso é recusado na etapa 2 | `src/interface.py` |
| Speech-to-text por API | `gpt-4o-transcribe` | `src/audio.py` |
| Transcrição bruta e versão revisada | `transcricao_rf06_original.txt` e `transcricao_rf06_revisada.txt`; no fluxo, a bruta em `transcricao_<arquivo>.txt` e a correção pelo servidor na etapa 3 | `dados/processados/` |
| Registrar idioma, modelo e duração | `metadados_rf06.json` e, em cada execução, o bloco `audio` do log (`duracao_segundos`, `idioma`, `modelo`) | Seção "No sistema entregue" |
| Comparar com texto de referência e apontar erros | Divergências abaixo; referência em `gabarito_entrada_audio.json` | Seções seguintes |
| **Aceite:** nome, protocolo e datas conferidos antes da minuta | Conferência obrigatória na etapa 3, antes de a minuta ser montada | Seção "No sistema entregue" |

## Primeira validação (Maria Luiza)


**Responsável:** Maria Luiza  
**Arquivo de entrada:** entrada_audio.mp3  
**Modelo:** gpt-4o-transcribe  
**Idioma:** Português (pt)

### Resultado

A transcrição automática identificou corretamente a maior parte das informações do áudio, incluindo protocolo, nome completo, datas, curso, carga horária e documentos.

### Divergências identificadas

**1. Turno**

- Fala original: “no turno noturno”.
- Transcrição automática: “noturno, noturno”.
- Classificação: erro leve de reconhecimento.

**2. E-mail**

- Transcrição automática: “marcos.almeida.teste.exemplo.com”.
- Problema: ausência do símbolo `@` e possível divergência na grafia do domínio.
- Classificação: erro relevante, exigindo confirmação humana.

### Revisão humana

A transcrição foi avaliada e foram identificadas divergências. O campo de turno pode ser corrigido conforme a escuta confirmada. O endereço eletrônico permanece pendente de conferência.

**Atualização da revisão humana — RF06**

- Turno corrigido para "no turno noturno".
- E-mail corrigido para "marcos.almeida.teste@exemplo.com", conforme confirmação humana.
- Transcrição original preservada sem alterações.
- Transcrição revisada salva separadamente.
- Não foi realizada nova chamada à API.
- Revisão textual concluída, com as duas divergências identificadas e corrigidas.

## No sistema entregue

- **Duração, idioma e modelo:** `entrada_audio.mp3` tem 89,16 s (medido do arquivo com `mutagen`, sem
  chamada à API). Cada execução de áudio grava no log `"audio": {"duracao_segundos", "idioma",
  "modelo"}`, inclusive quando a extração é reaproveitada, e a etapa 3 mostra "lido por
  gpt-4o-transcribe · duração 1min29s".
- **Conferência antes da minuta (critério de aceite):** na etapa 3, o servidor ouve o áudio original
  ali mesmo e marca nome do solicitante, protocolo, data da solicitação e data de início como
  conferidos. Corrigir um campo desmarca a conferência dele; a minuta só é montada com os quatro
  conferidos, e o log registra `dados_conferidos` no momento da montagem.
- **Avaliação final (RF13, 18/10/2026):** com a transcrição gerada de novo, o CASO-05 teve 12/12
  campos corretos; a data de início não é dita no áudio e ficou "não localizado", como no gabarito.
  A transcrição repetiu os dois erros já registrados ("noturno noturno" e o e-mail sem "@"); nenhum
  deles afeta a minuta, e o e-mail não é enviado ao modelo de extração (RF12).
