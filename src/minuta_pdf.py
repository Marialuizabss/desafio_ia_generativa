"""Gera o PDF da minuta com o brasão e o texto preenchido."""

import re
from html import escape
from pathlib import Path

import pymupdf

MARCADOR_BRASAO = "[CABEÇALHO COM BRASÃO — dados/originais/brasao.png]"

LARGURA = 595
ALTURA = 842
MARGEM = 56
_MARCADOR_TRECHO = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*)")

_CSS = """
p { font-family: sans-serif; font-size: 11pt; color: #172033; margin: 0 0 8px; }
ul { font-family: sans-serif; font-size: 11pt; color: #172033; margin: 0 0 8px; padding-left: 16px; }
li { margin: 0 0 2px; }
strong { color: #2746C4; }
em { color: #5C6B86; font-size: 9.5pt; }
"""


def gerar_pdf_minuta(minuta: str, brasao: Path | None = None) -> bytes:
    """Monta um PDF A4 com o brasão no topo e o texto da minuta."""
    texto = _sem_marcador(minuta)
    blocos = _blocos_html(texto)
    documento = pymupdf.open()
    try:
        pagina, cursor = _nova_pagina(documento, brasao, com_brasao=True)
        for bloco in blocos:
            coube, cursor = _colocar(pagina, cursor, bloco)
            if coube:
                continue
            pagina, cursor = _nova_pagina(documento, brasao, com_brasao=False)
            coube, cursor = _colocar(pagina, cursor, bloco, forcar=True)
            if not coube:
                cursor = ALTURA - MARGEM
        return documento.tobytes()
    finally:
        documento.close()


def _sem_marcador(minuta: str) -> str:
    texto = (minuta or "").strip()
    if texto.startswith(MARCADOR_BRASAO):
        texto = texto.removeprefix(MARCADOR_BRASAO).strip()
    return texto


def _blocos_html(texto: str) -> list[str]:
    blocos = []
    lista: list[str] = []

    def fechar_lista() -> None:
        if not lista:
            return
        itens = "".join(f"<li>{_inline(item)}</li>" for item in lista)
        blocos.append(f"<ul>{itens}</ul>")
        lista.clear()

    for linha in texto.splitlines():
        bruto = linha.strip()
        if not bruto:
            fechar_lista()
            continue
        if bruto.startswith("- "):
            lista.append(bruto[2:].strip())
            continue
        fechar_lista()
        if bruto.startswith("**") and bruto.endswith("**") and len(bruto) > 4:
            blocos.append(f"<p><strong>{escape(bruto[2:-2])}</strong></p>")
            continue
        for parte in _quebrar(bruto):
            blocos.append(f"<p>{_inline(parte)}</p>")
    fechar_lista()
    return blocos


def _quebrar(texto: str, limite: int = 320) -> list[str]:
    palavras = texto.split()
    if not palavras:
        return []
    partes = []
    atual = ""
    for palavra in palavras:
        tentativa = f"{atual} {palavra}".strip()
        if len(tentativa) <= limite:
            atual = tentativa
            continue
        if atual:
            partes.append(atual)
        atual = palavra
    if atual:
        partes.append(atual)
    return partes


def _inline(texto: str) -> str:
    partes = []
    for trecho in _MARCADOR_TRECHO.split(texto):
        if trecho.startswith("**") and trecho.endswith("**") and len(trecho) > 4:
            partes.append(f"<strong>{escape(trecho[2:-2])}</strong>")
        elif trecho.startswith("*") and trecho.endswith("*") and len(trecho) > 2:
            partes.append(f"<em>{escape(trecho[1:-1])}</em>")
        else:
            partes.append(escape(trecho))
    return "".join(partes)


def _nova_pagina(documento, brasao: Path | None, com_brasao: bool):
    pagina = documento.new_page(width=LARGURA, height=ALTURA)
    cursor = MARGEM
    if com_brasao and brasao is not None and Path(brasao).is_file():
        lado = 108
        esquerda = (LARGURA - lado) / 2
        topo = 40
        pagina.insert_image(
            pymupdf.Rect(esquerda, topo, esquerda + lado, topo + lado),
            filename=str(brasao),
            keep_proportion=True,
        )
        cursor = topo + lado + 18
    return pagina, cursor


def _colocar(pagina, cursor: float, html: str, forcar: bool = False) -> tuple[bool, float]:
    fundo = ALTURA - MARGEM
    if cursor >= fundo - 24:
        return False, cursor
    rect = pymupdf.Rect(MARGEM, cursor, LARGURA - MARGEM, fundo)
    sobra, _escala = pagina.insert_htmlbox(
        rect,
        html,
        css=_CSS,
        scale_low=0 if forcar else 1,
    )
    if sobra < 0:
        return False, cursor
    return True, cursor + (rect.height - sobra) + 2
