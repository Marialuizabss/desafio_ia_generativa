# RF18 — Chunking e recuperação

## 1. Objetivo

Avaliar como o tamanho e a sobreposição dos chunks influenciam a recuperação de trechos do
acervo, com o mesmo modelo de embeddings, as mesmas perguntas e o mesmo top-k.

## 2. Método

- **Acervo:** nove documentos (edital, seis retificações e dois TXT fictícios).
- **Índice:** ChromaDB, distância cosseno, modelo
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões).
- **Unidade de tamanho e sobreposição:** caracteres.
- **Perguntas:** as cinco respondíveis (P01 a P05) de `dados/originais/perguntas_rag.json`.
- **Referências:** `dados/gabaritos/gabarito_rag.json`, elaborado antes das chamadas (documento,
  página e frase de referência).
- **Regra de acerto:** um trecho recuperado é "de referência" se for do mesmo documento, da mesma
  página e contiver a frase de referência inteira (espaços normalizados, sem distinção de
  maiúsculas). **Acerto@k** = perguntas com pelo menos um trecho de referência entre os k primeiros
  / 5.
- **Código:** `src/avaliacao_rf18.py`. Resultados em `resultados/metricas/rf18/`.

## 3. Configurações e resultados

| Configuração | Tamanho | Sobreposição | Chunks | Acerto@3 | Acerto@5 | Acerto@10 |
|---|---:|---:|---:|---:|---:|---:|
| pequena | 300 | 50 | 253 | 3/5 (60%) | 3/5 (60%) | 4/5 (80%) |
| média | 800 | 100 | 105 | 3/5 (60%) | 3/5 (60%) | 5/5 (100%) |
| grande | 1200 | 200 | 79 | 2/5 (40%) | 2/5 (40%) | 2/5 (40%) |

Posição do primeiro trecho de referência (— = fora do top-10):

| Pergunta | pequena | média | grande |
|---|---:|---:|---:|
| P01 | 3 | 2 | — |
| P02 | — | 9 | — |
| P03 | 6 | 9 | — |
| P04 | 1 | 1 | 1 |
| P05 | 2 | 1 | 2 |

Nas três configurações, as 7 frases de referência cabem inteiras em algum chunk (7/7). Nenhuma
referência é cortada ao meio, então as falhas vêm da busca.

## 4. Limite de entrada do modelo de embeddings

O modelo trunca o texto em 128 tokens ao gerar o vetor (`max_seq_length = 128`). O texto completo
continua guardado no índice, mas o vetor representa só o início do chunk.

| Configuração | Chunks acima de 128 tokens | Média de tokens por chunk |
|---|---:|---:|
| pequena | 0 de 253 (0%) | 73 |
| média | 76 de 105 (72%) | 163 |
| grande | 60 de 79 (76%) | 220 |

Posição, em tokens, em que termina a frase de referência dentro do chunk (`src/medir_frases.py`):

- **grande:** P01, P02 e P03 terminam entre os tokens 165 e 236, **fora** do limite. São as três
  perguntas que a configuração não recuperou. P04 e P05 têm um chunk com a frase terminando nos
  tokens 49 e 67 (dentro), e foram recuperadas.
- **média:** toda pergunta tem ao menos uma referência dentro do limite (a pior, no token 109).
- **pequena:** todas dentro do limite (tokens 18 a 68).

## 5. Configuração selecionada: média (800 / 100)

A escolha se apoia em:

1. Melhor Acerto@10 (5/5), e empate no melhor Acerto@3 e Acerto@5 (3/5).
2. 105 chunks, contra 253 da pequena: menos trechos para recuperar e menos dispersão do assunto.
3. Mais contexto por trecho (163 tokens em média, contra 73), útil quando a minuta cita o trecho.

A configuração grande foi descartada: perdeu três das cinco perguntas, e as três falhas coincidem
com frases fora da janela de 128 tokens do modelo.

**Esta escolha tem limites:**

- Pequena e média diferem por **uma** pergunta (4/5 contra 5/5). Com cinco perguntas, isso não
  prova que uma seja melhor que a outra.
- Na média, P02 e P03 só aparecem na posição 9, perto do corte do top-10. O `responder_rf19` usa
  `top_k` de 15 por padrão, o que dá folga, mas o Acerto@15 não foi medido.
- 72% dos chunks da média passam de 128 tokens, então a busca só "vê" o começo deles.

## 6. Falhas observadas e ajustes

| Falha | Observação | Ajuste |
|---|---|---|
| Grande: P01, P02 e P03 não recuperadas | A frase de referência termina depois do token 128 | Configuração descartada |
| Pequena: P02 não recuperada, P03 na posição 6 | Todas as frases estão dentro do limite, então o truncamento não explica. Hipótese: o vocabulário da pergunta ("a distância") difere do trecho ("presencialmente"); não testada | Sem ajuste; limitação |
| Média: P02 e P03 na posição 9 | Recuperação por pouco | `top_k` maior no RAG |
| Avaliação anterior | Usava perguntas sobre ACV-08 e ACV-09 e conferia o acerto pela seção do TXT, diferentes do gabarito | Substituída por `src/avaliacao_rf18.py` |

Possíveis ajustes futuros: uma configuração de cerca de 450 caracteres (cabe nos 128 tokens, com
mais contexto que a pequena), recuperação híbrida (palavras-chave mais semântica) e um modelo de
embeddings com janela maior.

## 7. Como reproduzir

Comandos, na raiz do projeto:

    python -m src.avaliacao_rf18 --cobertura
    python -m src.avaliacao_rf18
    python -m src.medir_tokens
    python -m src.medir_frases