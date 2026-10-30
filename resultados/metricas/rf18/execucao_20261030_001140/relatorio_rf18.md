# RF18 — Chunking e recuperação

Execução: 2026-10-30T00:11:26-04:00  
Modelo de embeddings: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`  
Unidade de tamanho e sobreposição: **caracteres**  
Distância: cosseno (menor = mais parecido; similaridade = 1 − distância).  
Perguntas respondíveis: P01, P02, P03, P04, P05

## Parâmetros e acerto de recuperação

| Configuração | Tamanho | Sobreposição | Chunks | Acerto@3 | Acerto@5 | Acerto@10 |
|---|---:|---:|---:|---:|---:|---:|
| pequena | 300 | 50 | 253 | 3/5 (60%) | 3/5 (60%) | 4/5 (80%) |
| media | 800 | 100 | 105 | 3/5 (60%) | 3/5 (60%) | 5/5 (100%) |
| grande | 1200 | 200 | 79 | 2/5 (40%) | 2/5 (40%) | 2/5 (40%) |

## Posição do primeiro trecho de referência (— = fora do top-10)

| Pergunta | pequena | media | grande |
|---|---:|---:|---:|
| P01 | 3 | 2 | — |
| P02 | — | 9 | — |
| P03 | 6 | 9 | — |
| P04 | 1 | 1 | 1 |
| P05 | 2 | 1 | 2 |

## Cobertura das frases de referência pelos chunks

| Configuração | Referências com a frase inteira num chunk |
|---|---:|
| pequena | 7/7 |
| media | 7/7 |
| grande | 7/7 |

## Seleção e justificativa

*A preencher pela equipe com base nas tabelas acima: a configuração escolhida, o porquê (resultado e preservação de contexto) e as falhas observadas.*
