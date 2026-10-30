"""Configuração não sensível do projeto (RF01).

- ``config.json`` (raiz): caminhos, modelos de transcrição, leitura, voz e
  imagem, e parâmetros. Item ausente usa o valor padrão abaixo.
- ``config/modelos.json``: os modelos de análise que a interface oferece.
  Um parâmetro com valor ``null`` não se aplica àquele modelo; a interface
  mostra só os demais e guarda a escolha do usuário na sessão.

A chave da API não fica em nenhum dos dois: vem do ``.env``.
"""

import json
from copy import deepcopy
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_GERAL = BASE_DIR / "config.json"

PADROES = {
    "caminhos": {
        "originais": "dados/originais",
        "processados": "dados/processados",
        "gabaritos": "dados/gabaritos",
        "minutas_aprovadas": "resultados/minutas/aprovadas",
        "audios": "resultados/audios",
        "imagens_orientacao": "resultados/imagens/orientacao",
        "logs": "resultados/logs",
        "registro": "resultados/logs/execucoes.jsonl",
        "modelo_minuta": "prompts/modelo_minuta.md",
        "brasao": "dados/originais/brasao.png",
        "modelos_analise": "config/modelos.json",
    },
    "modelos": {
        "transcricao": "gpt-4o-transcribe",
        "leitura_visual": "gpt-4o",
        "voz": "gpt-4o-mini-tts",
        "voz_alternativo": "tts-1-hd",
        "imagem": "gpt-image-1",
    },
    "parametros": {
        "idioma": "pt",
        "timeout_segundos": 120,
        "voz": "nova",
        "instrucoes_voz": (
            "Fale em português do Brasil, com tom institucional, cordial e calmo. "
            "Ritmo pausado. Leia números e datas com clareza, fazendo pausa entre os grupos "
            "do protocolo. Não acrescente nem omita palavras."
        ),
        "imagem_tamanho": "1536x1024",
        "imagem_qualidade": "medium",
        "limite_texto_caracteres": 20000,
        "limite_arquivo_texto_mb": 5,
        "limite_audio_mb": 25,
        "limite_imagem_mb": 20,
    },
    "custos_estimados_usd": {"voz_por_minuto": 0.015, "imagem": 0.063},
    "guardrails": {
        "max_chamadas_analise": 2,
        "teto_analise": 8000,
        "max_chamadas_rag": 3,
        "teto_rag": 60000,
    },
}


def carregar_config(arquivo: Path | None = None) -> dict:
    """Lê o config.json e completa com os padrões o que faltar."""
    arquivo = Path(arquivo or ARQUIVO_GERAL)
    config = deepcopy(PADROES)
    if not arquivo.is_file():
        return config
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ValueError(f"O {arquivo.name} não é um JSON válido (linha {erro.lineno}).") from erro
    if not isinstance(dados, dict):
        raise ValueError(f"O {arquivo.name} não é um objeto JSON.")
    for secao, valores in dados.items():
        if isinstance(valores, dict) and isinstance(config.get(secao), dict):
            config[secao].update(valores)
        elif not secao.startswith("_"):
            config[secao] = valores
    return config


CONFIG = carregar_config()
CAMINHOS = CONFIG["caminhos"]
MODELOS = CONFIG["modelos"]
PARAMETROS_GERAIS = CONFIG["parametros"]
CUSTOS = CONFIG["custos_estimados_usd"]

ARQUIVO = BASE_DIR / CAMINHOS["modelos_analise"]

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
