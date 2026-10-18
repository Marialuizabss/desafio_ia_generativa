# RF07 — Síntese de voz e acessibilidade

## Avaliação final — Terceira versão

Responsável pela revisão humana: Maria Luiza

- A primeira versão apresentou pronúncia inadequada do protocolo.
- A segunda versão melhorou a leitura do protocolo, mas apresentou problemas de naturalidade no encerramento.
- A terceira versão apresentou melhora significativa na pronúncia e na compreensão da mensagem.
- O áudio foi reproduzido com sucesso no reprodutor do Windows.
- A naturalidade ainda pode ser aprimorada.

**Resultado:** Aprovado para demonstração, com ressalva quanto à naturalidade da voz.

**Decisão:** Manter a terceira versão como resultado do RF07 e preservar as anteriores como evidências da avaliação humana.

## Testes de tratamento de erros — RF07

**Teste 1 — Arquivo inexistente**
- Método: simulação com `unittest.mock`.
- Resultado: APROVADO.
- Comportamento observado: a função lançou `FileNotFoundError`.

**Teste 2 — Texto vazio**
- Método: simulação com `unittest.mock`.
- Resultado: APROVADO.
- Comportamento observado: a função lançou `ValueError`.

**Conclusão:** Os dois testes de tratamento de erros foram aprovados. Não houve chamadas adicionais à API durante os testes.
