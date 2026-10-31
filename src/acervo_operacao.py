"""Inclusão de documento e indexação a partir da interface (RF20).

O catálogo continua sendo a fonte da indexação. Um arquivo só entra com título,
versão, tipo aceito e tamanho dentro do limite. O hash é calculado aqui; a
indexação reutiliza o mesmo caminho do comando ``python -m src.indexar``.
"""

import json
import re
from pathlib import Path

from src.guardrails import BLOQUEAR
from src.ingestion import (
    CAMINHO_CATALOGO,
    PASTA_ACERVO,
    carregar_catalogo,
    carregar_exclusoes,
    gerar_chunks_documento,
    validar_documentos,
)

EXTENSOES = {".txt": "txt", ".pdf": "pdf"}


def mensagem_de_bloqueio_material(decisao) -> str:
    from src.consulta_acervo import mensagem_de_bloqueio as traduzir
    return traduzir(getattr(decisao, "motivos", ()))


def incluir_documento(
    conteudo: bytes,
    nome_arquivo: str,
    titulo: str,
    versao: str,
    catalogo: dict,
    pasta: Path,
) -> dict:
    """Grava o arquivo e devolve o item de catálogo. Não reescreve o JSON."""

    from src.guardrails import validar_material

    titulo = (titulo or "").strip()
    versao = (versao or "").strip()
    if not titulo or not versao:
        raise ValueError("Informe o título e a versão do documento.")
    if not isinstance(conteudo, (bytes, bytearray)) or not conteudo:
        raise ValueError("O arquivo está vazio.")

    nome = Path(str(nome_arquivo or "")).name
    if not nome or nome in {".", ".."} or nome != str(nome_arquivo or "").replace("\\", "/").split("/")[-1]:
        raise ValueError("O nome do arquivo não é aceito.")
    sufixo = Path(nome).suffix.casefold()
    if sufixo not in EXTENSOES:
        raise ValueError("Só é possível incluir TXT ou PDF.")

    modalidade = "texto" if sufixo == ".txt" else "imagem"
    decisao = validar_material(nome, len(conteudo), modalidade)
    if decisao.decisao == BLOQUEAR:
        raise ValueError(mensagem_de_bloqueio_material(decisao))

    sha = _sha_de_bytes(conteudo)
    for documento in catalogo.get("documentos", []):
        if documento.get("sha256") == sha:
            raise ValueError(f"Este arquivo já está no acervo ({documento['doc_id']}).")

    doc_id = proximo_doc_id(catalogo)
    arquivo = f"{doc_id}_{_slug(titulo)}{sufixo}"
    destino = Path(pasta) / arquivo
    if destino.exists():
        raise ValueError("Já existe um arquivo com esse nome no acervo.")
    destino.write_bytes(conteudo)

    documento = {
        "doc_id": doc_id,
        "titulo": titulo,
        "arquivo": arquivo,
        "versao": versao,
        "ordem": None,
        "origem": "equipe",
        "data_documento": None,
        "tema": "inclusao_interface",
        "formato": EXTENSOES[sufixo],
        "paginas": None,
        "documento_base": None,
        "altera": [],
        "sha256": sha,
        "observacoes": "Incluído pela interface. Documento fictício da equipe.",
    }
    catalogo.setdefault("documentos", []).append(documento)
    catalogo["versao_catalogo"] = _proxima_versao(catalogo.get("versao_catalogo"))
    historico = catalogo.setdefault("historico", [])
    historico.append(
        f"{catalogo['versao_catalogo']}: inclusão de {doc_id} pela interface ({arquivo})."
    )
    return documento


def gravar_catalogo(catalogo: dict, caminho: Path = CAMINHO_CATALOGO) -> None:
    Path(caminho).write_text(
        json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def incluir_no_acervo(conteudo: bytes, nome_arquivo: str, titulo: str, versao: str) -> dict:
    """Inclui no catálogo real e devolve o documento novo."""
    catalogo = carregar_catalogo()
    documento = incluir_documento(conteudo, nome_arquivo, titulo, versao, catalogo, PASTA_ACERVO)
    gravar_catalogo(catalogo)
    return documento


def indexar_ids(doc_ids: list[str]) -> dict:
    """Indexa só os documentos pedidos. Repetir não duplica trechos."""
    if not doc_ids:
        raise ValueError("Selecione ao menos um documento para indexar.")
    catalogo = carregar_catalogo()
    por_id = {documento["doc_id"]: documento for documento in catalogo["documentos"]}
    desconhecidos = [doc_id for doc_id in doc_ids if doc_id not in por_id]
    if desconhecidos:
        raise ValueError("Documento fora do catálogo: " + ", ".join(desconhecidos))

    from src.vector_store import (
        calcular_versao_indice,
        carregar_modelo_embeddings,
        indexar_documento,
        obter_colecao,
    )

    validacao = {item["doc_id"]: item["status"] for item in validar_documentos(catalogo)}
    exclusoes = carregar_exclusoes()
    modelo = carregar_modelo_embeddings()
    colecao = obter_colecao()
    relatorio = []
    for doc_id in doc_ids:
        documento = por_id[doc_id]
        if doc_id in exclusoes:
            # Excluído (RF24) só volta pela restauração.
            relatorio.append({"doc_id": doc_id, "status": "excluido", "chunks": 0})
            continue
        status_arquivo = validacao[doc_id]
        if status_arquivo != "valido":
            relatorio.append({"doc_id": doc_id, "status": status_arquivo, "chunks": 0})
            continue
        chunks = gerar_chunks_documento(documento)
        relatorio.append(indexar_documento(documento, chunks, modelo, colecao))
    return {
        "itens": relatorio,
        "total_chunks": colecao.count(),
        "versao_indice": calcular_versao_indice(colecao),
    }


def situacao_do_indice() -> dict:
    """Conferência catálogo × índice para a tela, sem carregar o modelo nem criar o índice."""
    from src.vector_store import conferir_indice, obter_colecao_se_existir

    exclusoes = carregar_exclusoes()
    conferencia = conferir_indice(carregar_catalogo(), obter_colecao_se_existir(), exclusoes)
    for documento in conferencia["documentos"]:
        if documento["doc_id"] in exclusoes:
            documento["exclusao"] = exclusoes[documento["doc_id"]]
    return conferencia


def mensagem_do_indice() -> str:
    """Motivo do bloqueio e o que fazer, ou vazio quando o índice confere com o catálogo."""
    from src.vector_store import mensagem_de_pendencias

    return mensagem_de_pendencias(situacao_do_indice())


def remover_do_indice(doc_id: str) -> dict:
    """Tira do índice um documento que não deveria estar nele e registra na auditoria.

    Só vale para o que a conferência aponta para remover (fora do catálogo ou já
    excluído). Documento do acervo em uso não sai por aqui.
    """
    from src.audit import registrar_evento
    from src.vector_store import (
        calcular_versao_indice,
        conferir_indice,
        excluir_documento,
        obter_colecao,
    )

    colecao = obter_colecao()
    conferencia = conferir_indice(carregar_catalogo(), colecao, carregar_exclusoes())
    motivos = {
        item["doc_id"]: item["situacao"]
        for item in conferencia["pendencias"]
        if item["situacao"] in ("fora_do_catalogo", "excluido_no_indice")
    }
    if doc_id not in motivos:
        raise ValueError(f"{doc_id} não está entre os documentos a remover do índice.")

    resultado = excluir_documento(colecao, doc_id)
    resultado["versao_indice_apos"] = calcular_versao_indice(colecao)
    registrar_evento("remocao_do_indice", {
        "doc_id": doc_id,
        "chunks_removidos": resultado["chunks_removidos"],
        "motivo": motivos[doc_id],
        "versao_indice_apos": resultado["versao_indice_apos"],
    })
    return resultado


def excluir_pela_tela(doc_id: str, motivo: str, responsavel: str) -> dict:
    """Exclusão (RF24) pela tela Acervo: o mesmo registro e a mesma auditoria do terminal."""
    responsavel = (responsavel or "").strip()
    if not responsavel:
        raise ValueError("Informe o(a) servidor(a) responsável pela exclusão.")

    from src.indexar import excluir_e_registrar
    from src.vector_store import obter_colecao

    return excluir_e_registrar(obter_colecao(), doc_id, motivo, responsavel=responsavel)


def restaurar_pela_tela(doc_id: str, responsavel: str) -> dict:
    """Restauração pela tela Acervo: tira o registro e reindexa só o documento."""
    responsavel = (responsavel or "").strip()
    if not responsavel:
        raise ValueError("Informe o(a) servidor(a) responsável pela restauração.")

    from src.indexar import restaurar_e_registrar
    from src.vector_store import carregar_modelo_embeddings, obter_colecao

    return restaurar_e_registrar(
        obter_colecao(), doc_id, carregar_modelo_embeddings(), responsavel=responsavel
    )


def proximo_doc_id(catalogo: dict) -> str:
    numeros = []
    for documento in catalogo.get("documentos", []):
        encontrado = re.fullmatch(r"ACV-(\d+)", str(documento.get("doc_id", "")))
        if encontrado:
            numeros.append(int(encontrado.group(1)))
    return f"ACV-{(max(numeros) if numeros else 0) + 1:02d}"


def _sha_de_bytes(conteudo: bytes) -> str:
    import hashlib
    return hashlib.sha256(conteudo).hexdigest()


def _slug(titulo: str) -> str:
    import unicodedata
    sem_acento = "".join(
        letra for letra in unicodedata.normalize("NFKD", titulo)
        if not unicodedata.combining(letra)
    )
    slug = re.sub(r"[^A-Za-z0-9]+", "_", sem_acento).strip("_").lower()
    return (slug or "documento")[:40]


def _proxima_versao(atual) -> str:
    texto = str(atual or "1.0")
    partes = texto.split(".")
    if len(partes) == 2 and partes[0].isdigit() and partes[1].isdigit():
        return f"{partes[0]}.{int(partes[1]) + 1}"
    return texto + ".1"

