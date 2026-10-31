# Registro de uso de IA — Estudante 3 (Felipe Ferreira Aguiar)

Desafio 2, parte de guardrails, interface, sentimentos e painel. O registro cobre o que foi feito com o agente do Cursor nesta sessão de 30/10/2026. O modelo da conversa é o Grok 4.7.

## Ferramentas

- Cursor, com agente de código, para ler o repositório, alterar a interface e os testes, executar a classificação real das doze avaliações e a regressão T15, e redigir o relatório.
- API da OpenAI, configuração `principal` (`gpt-4o-mini`), nas doze avaliações e nos dois casos da T15. Essas chamadas são o sistema em avaliação, não o assistente de programação.

## Solicitações relevantes

1. Cruzar o enunciado com o código e dizer o que ainda faltava nos requisitos funcionais.
2. Completar a interface: indexar e incluir documento no acervo, mostrar a minuta com as fontes e abrir o painel de sentimentos com denominador, filtro vazio e gráfico.
3. Rodar a classificação real das doze avaliações, a regressão de um caso de texto e um de áudio, e preencher a matriz T01–T15 e as seções abertas do relatório.

## Sugestões aceitas, modificadas e rejeitadas

- **Aceitas:** inclusão de TXT e PDF no catálogo, com hash e versão; minuta que não preenche documento, prazo e local sem consulta fundamentada; painel que recalcula totais pelo código e mostra "sem dados" com denominador 0; teto da análise (duas chamadas) também na classificação de sentimento.
- **Modificada:** o gráfico. A sugestão era `st.bar_chart`. Nesta instalação o import da biblioteca de gráficos quebra no Python 3.14, então o painel desenha as barras em HTML, com a mesma contagem.
- **Rejeitada:** reclassificar AV09 e AV10 no código para bater no gabarito. O erro é do modelo ao propor a situação, e o relatório deixa os 10/12. Também não foi escrito um diário de uso de IA em nome da Ana: não há, no repositório, as solicitações que ela fez.

## Erros encontrados e como foram validados

- O primeiro desenho do painel quebrava o teste porque `st.bar_chart` importava uma biblioteca incompatível com este Python. O teste da tela passou a procurar as barras em HTML.
- A execução real errou AV09 (`neutra` → `indeterminada`) e AV10 (`negativa` → `indeterminada`). Os JSON estão em `resultados/metricas/rf22/execucao_20261030_181951/`. Não houve correção para forçar o rótulo.
- Testes sem API: `python -m unittest testes.test_rf16 testes.test_rf20_regras testes.test_rf20_telas testes.test_rf22`.
