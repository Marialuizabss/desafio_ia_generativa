# RF12 — Varredura de credenciais e dados pessoais

- Data: 18/10/2026 20:25
- Commit: `33112e6`
- Arquivos verificados: 264 (14 binários, verificados só quanto ao nome)
- Resultado: **1 pendência(s)**

## Credenciais
- Chaves de API nos arquivos: **nenhum**
- Variáveis de credencial preenchidas: **1**
  - `src/audit.py:29` — re.c…(12 caracteres)
- Arquivo .env versionado: **nenhum**
- Chaves de API no histórico do git (todas as branches): **nenhuma**

## Dados pessoais
- CPFs com dígito verificador válido (possivelmente reais): **nenhum**
- E-mails fora dos domínios fictícios: **nenhum**

## Dados fictícios encontrados (esperados)
- CPFs com dígito verificador inválido: 111.222.333-44, 11122233344, 123.456.789-00, 123456789-00, 222.333.444-55, 333.444.555-66, 444.555.666-77
- E-mails nos domínios fictícios (examplo.com, exemplo.com, exemplo.com.br): juliana.campos.teste@exemplo.com, marcos.almeida.teste@examplo.com, marcos.almeida.teste@exemplo.com, marlon.almeida.teste@exemplo.com

## Limites
- A busca é por padrões: um CPF falado dígito a dígito ("1-2-3-...") ou escrito por extenso,
  ou um dado dentro de imagem ou áudio, não é detectado.
- Arquivos binários (áudio, imagem, PDF) são conferidos só pelo nome.
- Valores sensíveis aparecem mascarados: chaves e CPFs pelos 4 primeiros caracteres e o tamanho;
  e-mails pelos 3 primeiros caracteres e o domínio.
