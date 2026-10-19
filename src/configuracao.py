"""Lê os modelos e os parâmetros padrão de ``config/modelos.json``.

Um parâmetro com valor ``null`` não se aplica àquele modelo. A interface
mostra só os demais e guarda a escolha do usuário na sessão.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO = BASE_DIR / "config" / "modelos.json"

PARAMETROS = ("idioma", "temperatura", "tamanho", "qualidade")
OPCOES = ("idioma", "tamanho", "qualidade")


def carregar_modelos() -> dict:
    """Devolve a configuração validada."""
    try:
        bruto = ARQUIVO.read_text(encoding="utf-8")
    except OSError as erro:
        raise ValueError("Não foi possível ler a configuração dos modelos.") from erro
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError as erro:
        raise ValueError("A configuração dos modelos não é um JSON válido.") from erro
    if not isinstance(dados, dict):
        raise ValueError("A configuração dos modelos não é um objeto JSON.")
    _validar(dados)
    return dados


def obter_modelo(config: dict, modelo_id: str) -> dict:
    for modelo in config["modelos"]:
        if modelo["id"] == modelo_id:
            return modelo
    raise KeyError(modelo_id)


def parametros_aplicaveis(modelo: dict) -> dict:
    """Padrões do modelo, sem os parâmetros que não se aplicam."""
    return {
        nome: valor
        for nome, valor in modelo["padroes"].items()
        if valor is not None
    }


def rotulo_da_opcao(config: dict, parametro: str, valor: str) -> str:
    for opcao in config["opcoes"][parametro]:
        if opcao["valor"] == valor:
            return opcao["rotulo"]
    return valor


def _validar(dados: dict) -> None:
    opcoes = dados.get("opcoes")
    if not isinstance(opcoes, dict) or set(OPCOES) - set(opcoes):
        raise ValueError("A configuração não declara as opções de idioma, tamanho e qualidade.")
    for nome in OPCOES:
        valores = _valores_opcao(opcoes.get(nome), nome)
        opcoes[nome] = valores

    faixa = dados.get("temperatura")
    if not isinstance(faixa, dict):
        raise ValueError("A configuração não declara a faixa de temperatura.")
    minimo = _numero(faixa.get("minimo"), "temperatura.minimo")
    maximo = _numero(faixa.get("maximo"), "temperatura.maximo")
    passo = _numero(faixa.get("passo"), "temperatura.passo")
    if passo <= 0 or minimo > maximo:
        raise ValueError("A faixa de temperatura é inválida.")
    dados["temperatura"] = {"minimo": minimo, "maximo": maximo, "passo": passo}

    modelos = dados.get("modelos")
    if not isinstance(modelos, list) or not modelos:
        raise ValueError("A configuração não declara modelos.")

    vistos = set()
    for modelo in modelos:
        if not isinstance(modelo, dict):
            raise ValueError("Cada modelo precisa ser um objeto.")
        modelo_id = str(modelo.get("id") or "").strip()
        nome = str(modelo.get("nome") or "").strip()
        descricao = str(modelo.get("descricao") or "").strip()
        if not modelo_id or not nome or not descricao:
            raise ValueError("Cada modelo precisa de id, nome e descrição.")
        if modelo_id in vistos:
            raise ValueError(f"O modelo {modelo_id} está repetido.")
        vistos.add(modelo_id)
        modelo["id"] = modelo_id
        modelo["nome"] = nome
        modelo["descricao"] = descricao
        modelo["padroes"] = _padroes(modelo.get("padroes"), opcoes, dados["temperatura"], modelo_id)

    padrao = str(dados.get("modelo_padrao") or "").strip()
    if padrao not in vistos:
        raise ValueError("O modelo padrão não está na lista de modelos.")
    dados["modelo_padrao"] = padrao


def _valores_opcao(opcoes, nome: str) -> list[dict]:
    if not isinstance(opcoes, list) or not opcoes:
        raise ValueError(f"A configuração não declara opções de {nome}.")
    valores = []
    vistos = set()
    for opcao in opcoes:
        if not isinstance(opcao, dict):
            raise ValueError(f"Uma opção de {nome} é inválida.")
        valor = str(opcao.get("valor") or "").strip()
        rotulo = str(opcao.get("rotulo") or "").strip()
        if not valor or not rotulo or valor in vistos:
            raise ValueError(f"Uma opção de {nome} é inválida.")
        vistos.add(valor)
        valores.append({"valor": valor, "rotulo": rotulo})
    return valores


def _padroes(padroes, opcoes: dict, faixa: dict, modelo_id: str) -> dict:
    if not isinstance(padroes, dict) or set(padroes) != set(PARAMETROS):
        raise ValueError(
            f"O modelo {modelo_id} precisa declarar idioma, temperatura, tamanho e qualidade."
        )
    resultado = {}
    for nome in OPCOES:
        valor = padroes[nome]
        if valor is None:
            resultado[nome] = None
            continue
        valor = str(valor).strip()
        permitidos = {item["valor"] for item in opcoes[nome]}
        if valor not in permitidos:
            raise ValueError(f"O padrão de {nome} do modelo {modelo_id} não é uma opção válida.")
        resultado[nome] = valor

    temperatura = padroes["temperatura"]
    if temperatura is None:
        resultado["temperatura"] = None
    else:
        temperatura = _numero(temperatura, f"{modelo_id}.temperatura")
        if not faixa["minimo"] <= temperatura <= faixa["maximo"]:
            raise ValueError(f"A temperatura padrão de {modelo_id} está fora da faixa.")
        resultado["temperatura"] = temperatura
    return resultado


def _numero(valor, campo: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"O campo {campo} precisa ser numérico.")
    return float(valor)
