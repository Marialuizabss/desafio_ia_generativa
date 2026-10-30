# RF18 — Avaliação de Chunking e Recuperação

## 1. Objetivo

Avaliar a influência do tamanho e da sobreposição dos chunks na recuperação de informações do acervo documental, utilizando embeddings multilíngues e ChromaDB.

## 2. Configurações avaliadas

A unidade utilizada para tamanho e sobreposição foi **caracteres**.

| Configuração | Tamanho | Sobreposição | Total de chunks |
|---|---:|---:|---:|
| Pequena | 300 | 50 | 253 |
| Média | 800 | 100 | 105 |
| Grande | 1200 | 200 | 79 |

As três configurações utilizaram:

- Modelo de embeddings: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Banco vetorial: ChromaDB, com distância cosseno.
- Mesmo acervo de nove documentos.
- Metadados preservados: identificador do documento, título, versão, hash SHA-256, página e seção.
- As mesmas cinco perguntas respondíveis.

## 3. Resultados por pergunta

| Pergunta | Referência esperada | Pequena | Média | Grande |
|---|---|---|---|---|
| Quais faltas podem cancelar a matrícula? | ACV-08, seção 1 | Acerto | Acerto | Acerto |
| É permitido trancar a matrícula no primeiro semestre? | ACV-08, seção 3 | Acerto | Acerto | Acerto |
| A pesquisa socioeconômica é obrigatória? | ACV-09, seção 2 | Falha | Falha | Falha |
| Quais documentos são aceitos para justificar faltas? | ACV-08, seção 2 | Acerto | Acerto | Acerto |
| Como o estudante deve solicitar o trancamento da matrícula? | ACV-08, seção 3 | Acerto | Acerto | Acerto |

Os resultados por pergunta foram iguais para Hit@3, Hit@5 e Hit@10.

## 4. Taxas de acerto

A taxa de acerto foi calculada dividindo o número de perguntas com pelo menos um trecho da seção de referência recuperado entre os primeiros k resultados pelo total de cinco perguntas.

| Configuração | Hit@3 | Hit@5 | Hit@10 |
|---|---:|---:|---:|
| Pequena | 80% | 80% | 80% |
| Média | 80% | 80% | 80% |
| Grande | 80% | 80% | 80% |

Todas as configurações recuperaram corretamente a seção esperada em quatro das cinco perguntas.

## 5. Configuração selecionada

Foi selecionada a configuração **média**, com 800 caracteres de tamanho e 100 caracteres de sobreposição.

A escolha considera o equilíbrio entre a preservação de contexto e a quantidade de chunks gerados. Essa configuração produz menos chunks que a pequena, mantendo trechos menores que os da configuração grande.

As três configurações apresentaram a mesma taxa de acerto. Portanto, a seleção não representa superioridade comprovada na recuperação, mas uma decisão de compromisso entre granularidade e contexto.

## 6. Falhas identificadas e ajustes

A pergunta "A pesquisa socioeconômica é obrigatória?" não recuperou a seção esperada entre os dez primeiros resultados em nenhuma das configurações.

Na configuração média, a seção correta do documento ACV-09 apareceu na 11ª posição, com distância cosseno aproximada de 0,6450.

Foram realizados testes adicionais de formulação da pergunta e verificações de codificação dos caracteres acentuados. Confirmou-se que os acentos das perguntas armazenadas no arquivo Python estavam preservados.

A falha permaneceu na avaliação principal, indicando uma limitação da ordenação dos resultados da busca semântica.

Como possíveis ajustes futuros, podem ser avaliadas melhorias na formulação das consultas, inclusão de títulos e seções no texto usado para embeddings e estratégias de recuperação híbrida.

## 7. Conclusão

O RF18 comparou três configurações de chunking utilizando o mesmo acervo, modelo de embeddings, perguntas e valores de top-k.

Todas alcançaram 80% de acerto, e a configuração média foi selecionada como compromisso entre preservação de contexto e granularidade dos trechos.

A avaliação também identificou uma falha de recuperação que deverá ser considerada nas próximas etapas de desenvolvimento do sistema RAG.