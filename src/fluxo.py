"""Lê a entrada confirmada, extrai o texto e grava o objeto em processados."""

import json
from pathlib import Path

try:
    from audio import transcrever_audio
    from llm_client import extrair_campos
    from vision import ler_texto_visual
except ImportError:
    from src.audio import transcrever_audio
    from src.llm_client import extrair_campos
    from src.vision import ler_texto_visual

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_PROCESSADOS = BASE_DIR / "dados" / "processados"


MODELOS_ANALISE = {"gpt-6-luna", "gpt-4o"}


def processar_entrada(entrada: dict, forcar: bool = False, configuracao: dict | None = None) -> dict:
    """Extrai o texto da entrada, monta o objeto e salva o JSON.

    ``entrada`` é o material confirmado na interface, com ``modalidade``,
    ``caminho_copia`` e, no texto, o próprio ``texto``.
    """

    arquivo = (entrada.get("caminho_copia") or "").strip()
    modalidade = entrada.get("modalidade")
    if not arquivo:
        raise ValueError("A cópia da entrada não foi encontrada.")
    if modalidade not in {"texto", "audio", "imagem"}:
        raise ValueError("Forma de envio desconhecida.")

    caminho = BASE_DIR / arquivo
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    PASTA_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    saida = PASTA_PROCESSADOS / f"extracao_{caminho.stem}.json"
    modelo_id, temperatura, idioma = _configuracao(configuracao)
    if saida.is_file() and not forcar:
        registro = json.loads(saida.read_text(encoding="utf-8"))
        if (
            registro.get("arquivo_origem") == arquivo
            and registro.get("modelo") == modelo_id
        ):
            registro["arquivo_extracao"] = saida.relative_to(BASE_DIR).as_posix()
            return registro

    texto = _extrair_texto(modalidade, caminho, entrada, idioma)
    resultado = extrair_campos(texto, arquivo, modelo=modelo_id, temperatura=temperatura)
    registro = resultado.para_dict()
    registro["modalidade"] = modalidade
    registro["arquivo_origem"] = arquivo
    registro["modelo"] = modelo_id
    registro["texto_extraido"] = texto

    saida.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    registro["arquivo_extracao"] = saida.relative_to(BASE_DIR).as_posix()
    return registro


def _configuracao(configuracao: dict | None) -> tuple[str, float | None, str | None]:
    try:
        from llm_client import MODELO
    except ImportError:
        from src.llm_client import MODELO

    dados = configuracao or {}
    modelo = str(dados.get("modelo") or MODELO).strip()
    if modelo not in MODELOS_ANALISE:
        modelo = MODELO
    parametros = dados.get("parametros") or {}
    temperatura = parametros.get("temperatura")
    idioma = parametros.get("idioma")
    return modelo, temperatura, idioma or None


def _extrair_texto(modalidade: str, caminho: Path, entrada: dict, idioma: str | None) -> str:
    if modalidade == "texto":
        texto = (entrada.get("texto") or "").strip()
        if not texto:
            texto = caminho.read_text(encoding="utf-8").strip()
    elif modalidade == "audio":
        destino = PASTA_PROCESSADOS / f"transcricao_{caminho.stem}.txt"
        texto = transcrever_audio(caminho, destino_texto=destino, idioma=idioma)
    else:
        texto = ler_texto_visual(caminho)

    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Não foi possível extrair texto desta entrada.")
    return texto
