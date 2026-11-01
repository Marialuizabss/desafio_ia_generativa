# RF12 — Varredura de credenciais e dados pessoais

- Data: 01/11/2026 11:40
- Commit: `48b6b54`
- Arquivos verificados: 473 (23 binários, verificados só quanto ao nome)
- Resultado: **aprovado**

## Credenciais
- Chaves de API nos arquivos: **nenhum**
- Variáveis de credencial preenchidas: **nenhum**
- Arquivo .env versionado: **nenhum**
- Chaves de API no histórico do git (todas as branches): **nenhuma**

## Dados pessoais
- CPFs com dígito verificador válido (possivelmente reais): **nenhum**
- E-mails fora dos domínios fictícios: **nenhum**

## Dados fictícios encontrados (esperados)
- CPFs com dígito verificador inválido: 111.222.333-44, 11122233344, 123.456.789-00, 123456789-00, 222.333.444-55, 333.444.555-66, 444.555.666-77
- E-mails nos domínios fictícios (examplo.com, exemplo.com, exemplo.com.br): ana.teste@exemplo.com, ana@exemplo.com, juliana.campos.teste@exemplo.com, marcos.almeida.teste@examplo.com, marcos.almeida.teste@exemplo.com, marlon.almeida.teste@exemplo.com
- Chaves falsas de teste nos arquivos: `testes/test_rf16.py:46`, `testes/test_rf20_telas.py:98`, `testes/test_rf21_auditoria.py:31`
- Chaves falsas de teste no histórico do git: 3

## Limites
- Chave falsa de teste é a que começa com um marcador logo depois de `sk-` (`TESTE`, `segredo`, `falsa`, `exemplo`). Qualquer outra chave conta como pendência.
- Valor só com letras minúsculas e sublinhado (código interno, como `teto_tokens`) não conta
  como credencial.
- A busca é por padrões: um CPF falado dígito a dígito ("1-2-3-...") ou escrito por extenso,
  ou um dado dentro de imagem ou áudio, não é detectado.
- Arquivos binários (áudio, imagem, PDF) são conferidos só pelo nome.
- Valores sensíveis aparecem mascarados: chaves e CPFs pelos 4 primeiros caracteres e o tamanho;
  e-mails pelos 3 primeiros caracteres e o domínio.
