"""Gera o PDF da minuta com o brasão, o cabeçalho institucional e o texto preenchido."""

import re
from html import escape
from pathlib import Path

import pymupdf

MARCADOR_BRASAO = "[CABEÇALHO COM BRASÃO — dados/originais/brasao.png]"

# Linhas centralizadas abaixo do brasão, só na primeira página
CABECALHO = (
    "GOVERNO DE MATO GROSSO",
    "SECRETARIA DE ESTADO DE CIÊNCIA, TECNOLOGIA E INOVAÇÃO — SECITECI/MT",
    "ESCOLA TÉCNICA ESTADUAL DE CUIABÁ",
)

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

_CSS_CABECALHO = """
p { font-family: sans-serif; text-align: center; color: #172033; margin: 0 0 2px; font-size: 9pt; }
p.primeira { font-size: 10.5pt; font-weight: bold; }
"""

_CSS_RODAPE = """
p { font-family: sans-serif; text-align: center; color: #7A8499; margin: 0 0 1px; font-size: 7.5pt; }
"""


def gerar_pdf_minuta(
    minuta: str,
    brasao: Path | None = None,
    rodape: list[str] | tuple[str, ...] | None = None,
    cabecalho: tuple[str, ...] = CABECALHO,
) -> bytes:
    """Monta um PDF A4 com o brasão, o cabeçalho e o texto da minuta.

    ``rodape`` são as linhas do pé de cada página (origem, protocolo, quem
    aprovou); o número da página é acrescentado à última linha.
    """
    texto = _sem_marcador(minuta)
    blocos = _blocos_html(texto)
    documento = pymupdf.open()
    try:
        pagina, cursor = _nova_pagina(documento, brasao, com_brasao=True, cabecalho=cabecalho)
        for bloco in blocos:
            coube, cursor = _colocar(pagina, cursor, bloco)
            if coube:
                continue
            pagina, cursor = _nova_pagina(documento, brasao, com_brasao=False)
            coube, cursor = _colocar(pagina, cursor, bloco, forcar=True)
            if not coube:
                cursor = ALTURA - MARGEM
        if rodape:
            _colocar_rodape(documento, list(rodape))
        return documento.tobytes()
    finally:
        documento.close()


def _colocar_rodape(documento, linhas: list[str]) -> None:
    total = documento.page_count
    for numero, pagina in enumerate(documento, start=1):
        pagina.draw_line(
            pymupdf.Point(MARGEM, ALTURA - MARGEM + 8),
            pymupdf.Point(LARGURA - MARGEM, ALTURA - MARGEM + 8),
            color=(0.84, 0.87, 0.95),
            width=0.6,
        )
        texto = linhas[:-1] + [f"{linhas[-1]} · Página {numero} de {total}"]
        html = "".join(f"<p>{escape(linha)}</p>" for linha in texto)
        pagina.insert_htmlbox(
            pymupdf.Rect(MARGEM, ALTURA - MARGEM + 12, LARGURA - MARGEM, ALTURA - 8),
            html,
            css=_CSS_RODAPE,
            scale_low=0,
        )


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


def _nova_pagina(documento, brasao: Path | None, com_brasao: bool, cabecalho: tuple[str, ...] = ()):
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
    if com_brasao and cabecalho:
        cursor = _colocar_cabecalho(pagina, cursor - 8, cabecalho)
    return pagina, cursor


def _colocar_cabecalho(pagina, cursor: float, linhas: tuple[str, ...]) -> float:
    html = "".join(
        f'<p class="{"primeira" if indice == 0 else ""}">{escape(linha)}</p>'
        for indice, linha in enumerate(linhas)
    )
    rect = pymupdf.Rect(MARGEM, cursor, LARGURA - MARGEM, cursor + 60)
    sobra, _escala = pagina.insert_htmlbox(rect, html, css=_CSS_CABECALHO, scale_low=0)
    fim = cursor + (rect.height - max(sobra, 0)) + 6
    pagina.draw_line(
        pymupdf.Point(MARGEM + 60, fim),
        pymupdf.Point(LARGURA - MARGEM - 60, fim),
        color=(0.84, 0.87, 0.95),
        width=0.8,
    )
    return fim + 16


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
