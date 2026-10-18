# Índice da documentação

Onde está cada requisito e cada entregável do Desafio Prático 1 — Central Inteligente de
Atendimento e Comunicação Institucional. Todos os documentos ficam nesta pasta; as evidências
(saídas, registros e execuções) ficam em `resultados/` e `dados/`.

## Entregáveis gerais

| Entregável (seção 11) | Onde está |
|---|---|
| Código-fonte organizado e executável | `src/` (ponto de entrada: `python -m src.main`) |
| README com instalação, configuração, execução e limitações | `README.md` (raiz) |
| Dependências | `requirements.txt` e `.python-version` |
| `.env.example` e `.gitignore` | Raiz |
| Dados fictícios originais e gabaritos | `dados/originais/` e `dados/gabaritos/` (índice no Apêndice B de `rf13_avaliacao_qualidade.md`) |
| Prompts A, B e C, respostas e quadro comparativo | `rf02_engenharia_de_prompts.md`, `prompts/rf02/`, `resultados/minutas/rf02/` |
| Resultados de texto, áudio, OCR/visão e imagem | `resultados/minutas/`, `resultados/audios/`, `dados/processados/`, `resultados/imagens/` |
| Relatório técnico (arquitetura, modelos, custos, riscos, LGPD e avaliação) | `01_relatorio_tecnico.md` |
| Registro do uso de IA no desenvolvimento | `02_registro_uso_ia.md` |
| Contexto para agentes de codificação (opcional) | `AGENTS.md` (raiz) |

## Requisitos funcionais

| RF | Documento | Código | Evidências | Testes |
|---|---|---|---|---|
| **RF01** Inicialização e configuração | `README.md` | `src/main.py`, `src/configuracao.py`, `src/versoes.py` | `config.json`, `config/modelos.json`, `.env.example` | `test_configuracao_geral.py` |
| **RF02** Experimento de prompts | `rf02_engenharia_de_prompts.md` | `src/experimento_rf02.py` | `prompts/rf02/`, `resultados/minutas/rf02/execucao_*` | — |
| **RF03** Prompt seguro e injection | `rf03_prompt_seguro.md` | `src/llm_client.py` (prompt de produção e delimitação) | `dados/originais/caso3*.txt`, `resultados/minutas/rf03/execucao_*` | `test_rf03.py` |
| **RF04** Chamada de API e falhas | `01_relatorio_tecnico.md` | `src/llm_client.py` (timeout, erros, tokens e custo) | campo `chamada` em `dados/processados/extracao_*.json` | `test_rf03.py`, `test_rf11.py` |
| **RF05** Extração estruturada | `01_relatorio_tecnico.md`; categorias no Apêndice B de `rf13_avaliacao_qualidade.md` | `src/extracao.py`, `src/fluxo.py` | `dados/processados/extracao_*.json` | `test_rf11.py`, `test_rf12.py` |
| **RF06** Transcrição de áudio | `rf06_transcricao.md` | `src/audio.py` | `dados/processados/transcricao_*.txt`, `resultados/logs/metadados_rf06.json` | `test_audio.py` |
| **RF07** Voz e acessibilidade | `rf07_voz_acessibilidade.md` | `src/audio.py` (`sintetizar_minuta`) | `resultados/audios/` | `test_audio.py`, `test_decisao_ui.py` |
| **RF08** Visão e OCR | `rf08_visao_ocr.md` | `src/vision.py` | `dados/processados/extracao_rf08*.json`, `dados/processados/extracao_entrada_pdf-imagem.json` | `test_vision.py` |
| **RF09** Minuta institucional | `01_relatorio_tecnico.md` | `src/llm_client.py` (`montar_minuta`), `src/minuta_pdf.py` | `prompts/modelo_minuta.md`, `resultados/minutas/aprovadas/` | `test_edicao_minuta.py`, `test_minuta_pdf.py` |
| **RF10** Imagem de orientação | `rf10_imagem.md` | `src/peca_orientacao.py` | `resultados/imagens/orientacao/`, `resultados/logs/metadados_peca_orientacao.json` | `test_peca_orientacao.py` |
| **RF11** Registro e rastreabilidade | `01_relatorio_tecnico.md` | `src/audit.py` | `resultados/logs/execucoes.jsonl` | `test_rf11.py` |
| **RF12** LGPD e minimização | `rf12_lgpd_privacidade.md` | `src/privacidade.py`, `src/varredura_rf12.py` | `resultados/logs/varredura_rf12.md` | `test_rf12.py` |
| **RF13** Avaliação e revisão humana | `rf13_avaliacao_qualidade.md` (protocolo no Apêndice A) | `src/avaliacao_rf13.py`; revisão humana em `src/interface.py` | `resultados/avaliacao/execucao_20261018_184910/`, `dados/gabaritos/` | `test_rf13.py`, `test_decisao_ui.py` |

## Como verificar

| O quê | Comando |
|---|---|
| Rodar o sistema | `python -m src.main` |
| Rodar todos os testes (sem chamar a API) | `python -m unittest discover -s testes -t .` |
| Conferir Python e bibliotecas | `python -m src.versoes` |
| Varredura de credenciais e dados pessoais (RF12) | `python -m src.varredura_rf12` |
| Avaliação dos 7 casos (RF13, chama a API) | `python -m src.avaliacao_rf13 --todos` |
| Gerar ou revisar a ilustração da peça (RF10, chama a API) | `python -m src.peca_orientacao gerar` |
