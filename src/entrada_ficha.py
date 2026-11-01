"""Áudio, imagem ou TXT na Ficha (RF20 e seção 1 do enunciado).

O arquivo passa pela validação de tipo e tamanho do RF16, ganha uma cópia em
``dados/originais/`` como no Desafio 1 e vira texto pela mesma transcrição ou
leitura do Desafio 1. O texto volta para a caixa da Ficha, onde o servidor
confere antes de analisar; daí em diante o caminho é o da solicitação digitada.
"""

from datetime import datetime
from pathlib import Path

from src.guardrails import BLOQUEAR, EXTENSOES, ORIGEM_ANALISE, registrar_bloqueio, validar_material

BASE_DIR = Path(__file__).resolve().parent.parent
# Pasta própria: a transcrição guardada do Desafio 1 (evidência do T15) não é sobrescrita.
PASTA_TRANSCRICOES = BASE_DIR / "dados" / "processados" / "ficha"

AVISOS = {
    "audio": (
        "Texto transcrito de {arquivo}. A transcrição erra nomes, números e datas: confira nome, "
        "protocolo e datas com o áudio original antes de analisar."
    ),
    "imagem": (
        "Texto lido de {arquivo}. A leitura erra datas e códigos, principalmente em letra "
        "manuscrita: confira nome, protocolo e datas com a ficha original antes de analisar."
    ),
    "texto": "Texto de {arquivo} carregado. Confira antes de analisar.",
}


class ArquivoBloqueado(ValueError):
    """Arquivo recusado pelo guardrail (tipo, tamanho ou vazio)."""


def extensoes_aceitas() -> list[str]:
    """Extensões do seletor de arquivo da Ficha, sem o ponto."""
    return sorted(extensao.lstrip(".") for extensoes in EXTENSOES.values() for extensao in extensoes)


def modalidade_do_arquivo(nome: str) -> str | None:
    sufixo = Path(str(nome or "")).suffix.casefold()
    for modalidade, extensoes in EXTENSOES.items():
        if sufixo in extensoes:
            return modalidade
    return None


def ler_arquivo_da_ficha(nome: str, conteudo: bytes) -> dict:
    """Valida, guarda a cópia e devolve o texto do arquivo com o aviso de conferência.

    Arquivo recusado grava ``bloqueio_guardrail`` (sem o nome do arquivo) e
    levanta ``ArquivoBloqueado``. Falha da transcrição ou da leitura chega como
    ``ValueError``, já em português.
    """
    from src.consulta_acervo import mensagem_de_bloqueio

    nome = Path(str(nome or "").replace("\\", "/")).name
    conteudo = bytes(conteudo or b"")
    modalidade = modalidade_do_arquivo(nome)
    decisao = validar_material(nome, len(conteudo), modalidade or "texto")
    if decisao.decisao == BLOQUEAR:
        registrar_bloqueio(decisao, ORIGEM_ANALISE, conteudo)
        raise ArquivoBloqueado(mensagem_de_bloqueio(decisao.motivos))

    copia = _guardar_copia(nome, conteudo)
    texto = (_texto_do_arquivo(modalidade, Path(copia["caminho"])) or "").strip()
    if not texto:
        raise ValueError("Não foi possível extrair texto deste arquivo.")
    return {
        "texto": texto,
        "modalidade": modalidade,
        "arquivo": copia["relativo"],
        "aviso": AVISOS[modalidade].format(arquivo=nome),
    }


def destino_da_transcricao(caminho: Path, quando: datetime | None = None) -> Path:
    momento = (quando or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return PASTA_TRANSCRICOES / f"transcricao_{Path(caminho).stem}_{momento}.txt"


def _guardar_copia(nome: str, conteudo: bytes) -> dict:
    """A mesma cópia do Desafio 1: em dados/originais, sem sobrescrever arquivo existente."""
    try:
        from interface import guardar_copia
    except ImportError:
        from src.interface import guardar_copia
    return guardar_copia(nome, conteudo)


def _texto_do_arquivo(modalidade: str, caminho: Path) -> str:
    if modalidade == "texto":
        try:
            return caminho.read_text(encoding="utf-8")
        except UnicodeDecodeError as erro:
            raise ValueError("O arquivo de texto precisa estar em UTF-8.") from erro
    if modalidade == "audio":
        try:
            from audio import transcrever_audio
        except ImportError:
            from src.audio import transcrever_audio
        return transcrever_audio(caminho, destino_texto=destino_da_transcricao(caminho))
    try:
        from vision import ler_texto_visual
    except ImportError:
        from src.vision import ler_texto_visual
    return ler_texto_visual(caminho)
