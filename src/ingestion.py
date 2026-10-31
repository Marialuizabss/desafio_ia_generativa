import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
import pymupdf


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_ACERVO = RAIZ_PROJETO / "dados" / "acervo"
CAMINHO_CATALOGO = PASTA_ACERVO / "acervo.json"
CAMINHO_EXCLUSOES = PASTA_ACERVO / "exclusoes.json"
VERSAO_EXCLUSOES = "1.0"

DESCRICAO_EXCLUSOES = (
    "Documentos do acervo excluídos do índice de propósito (RF24). Enquanto constarem "
    "aqui, a indexação os pula e a conferência não os cobra."
)


def carregar_catalogo():
    with CAMINHO_CATALOGO.open("r", encoding="utf-8") as arquivo:
        catalogo = json.load(arquivo)

    if not isinstance(catalogo.get("documentos"), list):
        raise ValueError("Catálogo sem lista válida de documentos.")

    return catalogo


def carregar_exclusoes(caminho=None):
    """Exclusões em vigor (RF24), por doc_id. Sem o arquivo, nenhuma."""

    caminho = Path(caminho or CAMINHO_EXCLUSOES)

    if not caminho.is_file():
        return {}

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return {item["doc_id"]: item for item in dados["exclusoes"]}
    except (json.JSONDecodeError, KeyError, TypeError) as erro:
        raise ValueError(
            f"O registro de exclusões ({caminho.name}) está mal formado."
        ) from erro


def gravar_exclusoes(exclusoes, caminho=None):
    """Grava sempre no mesmo formato: excluir e restaurar devolve o arquivo idêntico."""

    dados = {
        "versao": VERSAO_EXCLUSOES,
        "descricao": DESCRICAO_EXCLUSOES,
        "exclusoes": [exclusoes[doc_id] for doc_id in sorted(exclusoes)],
    }
    Path(caminho or CAMINHO_EXCLUSOES).write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def registrar_exclusao(doc_id, motivo, responsavel, caminho=None):
    exclusoes = carregar_exclusoes(caminho)
    exclusoes[doc_id] = {
        "doc_id": doc_id,
        "data": datetime.now().astimezone().isoformat(timespec="seconds"),
        "motivo": motivo,
        "responsavel": responsavel,
    }
    gravar_exclusoes(exclusoes, caminho)
    return exclusoes[doc_id]


def remover_exclusao(doc_id, caminho=None):
    exclusoes = carregar_exclusoes(caminho)
    registro = exclusoes.pop(doc_id)
    gravar_exclusoes(exclusoes, caminho)
    return registro


def calcular_sha256(caminho):
    hash_arquivo = hashlib.sha256()

    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            hash_arquivo.update(bloco)

    return hash_arquivo.hexdigest()


def validar_documentos(catalogo):
    resultados = []

    for documento in catalogo["documentos"]:
        caminho = PASTA_ACERVO / documento["arquivo"]

        if not caminho.is_file():
            status = "arquivo_ausente"
        elif calcular_sha256(caminho) != documento["sha256"]:
            status = "hash_divergente"
        else:
            status = "valido"

        resultados.append({
            "doc_id": documento["doc_id"],
            "arquivo": documento["arquivo"],
            "status": status,
        })

    return resultados

def extrair_texto_documento(documento):
    caminho = PASTA_ACERVO / documento["arquivo"]
    partes = []

    if documento["formato"] == "pdf":
        with pymupdf.open(caminho) as pdf:
            for numero_pagina, pagina in enumerate(pdf, start=1):
                texto = pagina.get_text("text").strip()

                if texto:
                    partes.append({
                        "pagina": numero_pagina,
                        "texto": texto,
                    })

    elif documento["formato"] == "txt":
        texto = caminho.read_text(encoding="utf-8").strip()

        if texto:
            partes.append({
                "pagina": None,
                "texto": texto,
            })

    else:
        raise ValueError(
            f"Formato não suportado: {documento['formato']}"
        )

    return partes


def dividir_em_chunks(texto, tamanho=800, sobreposicao=100):
    if tamanho <= 0:
        raise ValueError("O tamanho do chunk deve ser positivo.")

    if sobreposicao < 0 or sobreposicao >= tamanho:
        raise ValueError("Sobreposição inválida.")

    chunks = []
    inicio = 0

    while inicio < len(texto):
        fim = min(inicio + tamanho, len(texto))
        trecho = texto[inicio:fim].strip()

        if trecho:
            chunks.append(trecho)

        if fim == len(texto):
            break

        inicio = fim - sobreposicao

    return chunks


def gerar_chunks_documento(documento, tamanho=800, sobreposicao=100):
    partes = extrair_texto_documento(documento)
    resultados = []

    for parte in partes:
        if documento["formato"] == "txt":
            blocos = separar_txt_por_secoes(parte["texto"])
        else:
            blocos = [{
                "secao": None,
                "texto": parte["texto"],
            }]

        for bloco_indice, bloco in enumerate(blocos, start=1):
            trechos = dividir_em_chunks(
                bloco["texto"],
                tamanho=tamanho,
                sobreposicao=sobreposicao,
            )

            for indice, trecho in enumerate(trechos, start=1):
                resultados.append({
                    "chunk_id": (
                        f"{documento['doc_id']}"
                        f"-p{parte['pagina'] or 0}"
                        f"-s{bloco_indice}-c{indice}"
                    ),
                    "doc_id": documento["doc_id"],
                    "titulo": documento["titulo"],
                    "versao": documento["versao"],
                    "sha256": documento["sha256"],
                    "pagina": parte["pagina"],
                    "secao": bloco["secao"],
                    "texto": trecho,
                })

    return resultados


def identificar_secoes_txt(texto):
    secoes = []
    secao_atual = None

    for linha in texto.splitlines():
        linha = linha.strip()

        if not linha:
            continue

        if re.match(r"^\d+\.\s+\S", linha):
            secao_atual = linha

        if secao_atual and secao_atual not in secoes:
            secoes.append(secao_atual)

    return secoes


def separar_txt_por_secoes(texto):
    partes = []
    secao_atual = None
    linhas_atuais = []

    for linha in texto.splitlines():
        if re.match(r"^\d+\.\s+\S", linha.strip()):
            if linhas_atuais:
                partes.append({
                    "secao": secao_atual,
                    "texto": "\n".join(linhas_atuais).strip(),
                })

            secao_atual = linha.strip()
            linhas_atuais = []

        linhas_atuais.append(linha)

    if linhas_atuais:
        partes.append({
            "secao": secao_atual,
            "texto": "\n".join(linhas_atuais).strip(),
        })

    return partes


if __name__ == "__main__":
    catalogo = carregar_catalogo()
    resultados = validar_documentos(catalogo)

    print(f"Versão do catálogo: {catalogo['versao_catalogo']}")

    for resultado in resultados:
        print(f"{resultado['doc_id']}: {resultado['status']}")

    print(
        f"Documentos válidos: "
        f"{sum(r['status'] == 'valido' for r in resultados)}/{len(resultados)}"
    )
