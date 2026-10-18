"""Mostra as versões de Python e das bibliotecas e compara com o exigido (RF01).

Uso:
    python -m src.versoes
"""

import platform
import sys
from importlib import metadata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PYTHON_EXIGIDO = (BASE_DIR / ".python-version").read_text(encoding="utf-8").strip() \
    if (BASE_DIR / ".python-version").is_file() else "3.13"


def exigidas(requirements: Path | None = None) -> list[tuple[str, str]]:
    """(pacote, versão) de cada linha fixada com == no requirements.txt."""
    arquivo = Path(requirements or BASE_DIR / "requirements.txt")
    pacotes = []
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.split("#", 1)[0].strip()
        if "==" in linha:
            nome, versao = linha.split("==", 1)
            pacotes.append((nome.strip(), versao.strip()))
    return pacotes


def conferir(requirements: Path | None = None) -> list[dict]:
    resultado = []
    for nome, versao in exigidas(requirements):
        try:
            instalada = metadata.version(nome)
        except metadata.PackageNotFoundError:
            instalada = None
        resultado.append({
            "pacote": nome,
            "exigida": versao,
            "instalada": instalada,
            "ok": instalada == versao,
        })
    return resultado


def python_ok() -> bool:
    return platform.python_version().startswith(PYTHON_EXIGIDO + ".") or platform.python_version() == PYTHON_EXIGIDO


def main() -> int:
    marca = "✓" if python_ok() else "✗"
    print(f"Python {platform.python_version():<10} (exigido: {PYTHON_EXIGIDO}) {marca}")
    problemas = 0 if python_ok() else 1
    for item in conferir():
        if item["ok"]:
            situacao = "✓"
        elif item["instalada"] is None:
            situacao = "✗ não instalada"
        else:
            situacao = f"✗ instalada {item['instalada']}"
        print(f"{item['pacote']:<14} {item['exigida']:<10} {situacao}")
        problemas += 0 if item["ok"] else 1
    if problemas:
        print("\nRode: pip install -r requirements.txt")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
