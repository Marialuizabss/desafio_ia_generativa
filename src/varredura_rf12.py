"""RF12 — varredura da entrega em busca de credenciais e dados pessoais reais.

Confere todos os arquivos que iriam na entrega (versionados e novos, exceto
os ignorados pelo .gitignore) e o histórico do git:

- chaves de API e variáveis de credencial preenchidas;
- arquivo .env versionado;
- CPFs com dígito verificador válido (possivelmente reais);
- e-mails fora dos domínios fictícios usados no projeto.

Gera resultados/logs/varredura_rf12.md. Nenhum valor sensível encontrado é
gravado por inteiro no relatório. Sai com código 1 se houver pendência.

Uso:
    python -m src.varredura_rf12
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RELATORIO = BASE_DIR / "resultados" / "logs" / "varredura_rf12.md"

DOMINIOS_FICTICIOS = {"exemplo.com", "examplo.com", "exemplo.com.br"}

CHAVE = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
CREDENCIAL_PREENCHIDA = re.compile(
    r"\b[A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|PASSWORD|SENHA)[A-Z0-9_]*\s*=\s*['\"]?([^\s'\"#]{8,})"
)
CPF = re.compile(r"(?<![\w.-])\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?![\w-])")
EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")

# Identificadores de execução (UUID) contêm sequências de 11 dígitos que não são CPF
UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)


def git(*argumentos):
    resultado = subprocess.run(
        ["git", *argumentos], cwd=BASE_DIR, capture_output=True, text=True, check=True
    )
    return resultado.stdout


def arquivos_da_entrega():
    versionados = git("ls-files").splitlines()
    novos = git("ls-files", "--others", "--exclude-standard").splitlines()
    caminhos = sorted(set(versionados + novos))
    relatorio = RELATORIO.relative_to(BASE_DIR).as_posix()
    return [caminho for caminho in caminhos if caminho != relatorio]


def ler_texto(caminho):
    dados = (BASE_DIR / caminho).read_bytes()
    if b"\x00" in dados[:4096]:
        return None
    return dados.decode("utf-8", errors="ignore")


def cpf_valido(numero):
    digitos = [int(d) for d in re.sub(r"\D", "", numero)]
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for posicao in (9, 10):
        soma = sum(d * peso for d, peso in zip(digitos[:posicao], range(posicao + 1, 1, -1)))
        resto = soma % 11
        if digitos[posicao] != (0 if resto < 2 else 11 - resto):
            return False
    return True


def credenciais_da_linha(linha):
    """Valores preenchidos que parecem credencial.

    Código Python não conta: uma chave real não tem parêntese, e expressões
    como ``re.compile(`` ou ``os.getenv(`` geravam falso positivo.
    """
    return [valor for valor in CREDENCIAL_PREENCHIDA.findall(linha) if "(" not in valor]


def mascarar(valor):
    return f"{valor[:4]}…({len(valor)} caracteres)"


def mascarar_email(endereco):
    usuario, dominio = endereco.split("@", 1)
    return f"{usuario[:3]}…@{dominio}"


def varrer():
    arquivos = arquivos_da_entrega()
    achados = {"chaves": [], "credenciais": [], "env": [], "cpf_valido": [], "email": []}
    cpfs_ficticios = set()
    emails_ficticios = set()
    binarios = 0

    for caminho in arquivos:
        if caminho == ".env" or caminho.endswith("/.env"):
            achados["env"].append(caminho)

        texto = ler_texto(caminho)
        if texto is None:
            binarios += 1
            continue

        for numero_linha, linha in enumerate(texto.splitlines(), start=1):
            local = f"{caminho}:{numero_linha}"

            for chave in CHAVE.findall(linha):
                achados["chaves"].append((local, mascarar(chave)))
            for valor in credenciais_da_linha(linha):
                achados["credenciais"].append((local, mascarar(valor)))

            for cpf in CPF.findall(UUID.sub(" ", linha)):
                if cpf_valido(cpf):
                    achados["cpf_valido"].append((local, mascarar(cpf)))
                else:
                    cpfs_ficticios.add(cpf)

            for endereco in EMAIL.finditer(linha):
                dominio = endereco.group(1).casefold()
                if dominio in DOMINIOS_FICTICIOS:
                    emails_ficticios.add(endereco.group(0).casefold())
                else:
                    achados["email"].append((local, mascarar_email(endereco.group(0))))

    historico = git("log", "--all", "-p", "--no-color")
    chaves_no_historico = len(CHAVE.findall(historico))

    return {
        "arquivos": len(arquivos),
        "binarios": binarios,
        "achados": achados,
        "chaves_no_historico": chaves_no_historico,
        "cpfs_ficticios": sorted(cpfs_ficticios),
        "emails_ficticios": sorted(emails_ficticios),
    }


def escrever_relatorio(resultado):
    achados = resultado["achados"]
    pendencias = (
        len(achados["chaves"]) + len(achados["credenciais"]) + len(achados["env"])
        + len(achados["cpf_valido"]) + len(achados["email"]) + resultado["chaves_no_historico"]
    )

    def secao(titulo, itens):
        if not itens:
            return [f"- {titulo}: **nenhum**"]
        linhas = [f"- {titulo}: **{len(itens)}**"]
        linhas += [f"  - `{local}`" + (f" — {valor}" if valor else "") for local, valor in itens]
        return linhas

    linhas = [
        "# RF12 — Varredura de credenciais e dados pessoais",
        "",
        f"- Data: {datetime.now().astimezone().strftime('%d/%m/%Y %H:%M')}",
        f"- Commit: `{git('rev-parse', '--short', 'HEAD').strip()}`",
        f"- Arquivos verificados: {resultado['arquivos']} "
        f"({resultado['binarios']} binários, verificados só quanto ao nome)",
        f"- Resultado: **{'aprovado' if not pendencias else f'{pendencias} pendência(s)'}**",
        "",
        "## Credenciais",
        *secao("Chaves de API nos arquivos", achados["chaves"]),
        *secao("Variáveis de credencial preenchidas", achados["credenciais"]),
        *secao("Arquivo .env versionado", [(item, "") for item in achados["env"]]),
        f"- Chaves de API no histórico do git (todas as branches): "
        f"**{resultado['chaves_no_historico'] or 'nenhuma'}**",
        "",
        "## Dados pessoais",
        *secao("CPFs com dígito verificador válido (possivelmente reais)", achados["cpf_valido"]),
        *secao("E-mails fora dos domínios fictícios", achados["email"]),
        "",
        "## Dados fictícios encontrados (esperados)",
        f"- CPFs com dígito verificador inválido: {', '.join(resultado['cpfs_ficticios']) or 'nenhum'}",
        f"- E-mails nos domínios fictícios ({', '.join(sorted(DOMINIOS_FICTICIOS))}): "
        f"{', '.join(resultado['emails_ficticios']) or 'nenhum'}",
        "",
        "## Limites",
        "- A busca é por padrões: um CPF falado dígito a dígito (\"1-2-3-...\") ou escrito por extenso,",
        "  ou um dado dentro de imagem ou áudio, não é detectado.",
        "- Arquivos binários (áudio, imagem, PDF) são conferidos só pelo nome.",
        "- Valores sensíveis aparecem mascarados: chaves e CPFs pelos 4 primeiros caracteres e o tamanho;",
        "  e-mails pelos 3 primeiros caracteres e o domínio.",
    ]
    RELATORIO.parent.mkdir(parents=True, exist_ok=True)
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return pendencias


def main():
    resultado = varrer()
    pendencias = escrever_relatorio(resultado)
    print(f"Arquivos verificados: {resultado['arquivos']}")
    print(f"CPFs fictícios (dígito inválido): {len(resultado['cpfs_ficticios'])}")
    print(f"E-mails fictícios: {len(resultado['emails_ficticios'])}")
    print(f"Pendências: {pendencias}")
    print(f"Relatório: {RELATORIO.relative_to(BASE_DIR).as_posix()}")
    return 1 if pendencias else 0


if __name__ == "__main__":
    sys.exit(main())
