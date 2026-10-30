"""Vigência dos trechos recuperados (RF19): regras gerais, sem referência a perguntas.

Retificações substituem partes de outros documentos. Dois sinais, ambos
deterministas, indicam que um trecho recuperado traz uma versão que não vale mais:

  1. "Onde se lê: ... Leia-se: ...": o texto sob "Onde se lê" é a versão substituída.
  2. Linhas numeradas de tabelas (cronogramas) que aparecem em dois documentos
     ligados pelo catálogo (um altera o outro, ou ambos alteram o mesmo item):
     se o texto da linha é o mesmo e os números mudam, a linha do documento de
     menor `ordem` é substituída pela do de maior `ordem` (regra R2 do catálogo).

Só usa o texto dos trechos e os campos `ordem` e `altera` do catálogo.
"""

import re
import unicodedata

_ONDE_SE_LE = re.compile(r"onde\s+se\s+l[eê]\s*:", re.IGNORECASE)
_LEIA_SE = re.compile(r"leia\s*-?\s*se\s*:", re.IGNORECASE)
# Início de linha numerada: número + palavra de 3 ou mais letras ("23 e 24/07/2026" não é linha).
_INICIO_LINHA = re.compile(r"(?m)^[ \t]*\d{1,2}\.?[ \t]+(?=[A-Za-zÀ-ú]{3})")
_LINHA_EM_BRANCO = re.compile(r"\n[ \t]*\n")

LIMIAR_SEMELHANCA = 0.8


def normalizar(texto):
    return re.sub(r"\s+", " ", texto or "").strip().casefold()


def _intervalos_onde_se_le(texto):
    """Trechos entre "Onde se lê:" e "Leia-se:" (ou o fim do trecho recuperado)."""

    intervalos = []
    posicao = 0

    while True:
        abertura = _ONDE_SE_LE.search(texto, posicao)

        if not abertura:
            break

        fechamento = _LEIA_SE.search(texto, abertura.end())
        fim = fechamento.start() if fechamento else len(texto)
        intervalos.append(texto[abertura.end():fim])
        posicao = fechamento.end() if fechamento else len(texto)

    return intervalos


def _linhas_numeradas(texto):
    marcas = [m.start() for m in _INICIO_LINHA.finditer(texto)]
    linhas = []

    for i, inicio in enumerate(marcas):
        fim = marcas[i + 1] if i + 1 < len(marcas) else len(texto)
        linha = texto[inicio:fim]
        # Uma linha de tabela termina na primeira linha em branco.
        linha = _LINHA_EM_BRANCO.split(linha, maxsplit=1)[0]
        linhas.append(linha)

    return linhas


def _forma_e_numeros(linha):
    """Texto da linha sem números (a "forma") e os números que ela traz."""

    sem_indice = re.sub(r"^[ \t]*\d{1,2}\.?[ \t]+", "", linha, count=1)
    com_ordinais = re.sub(r"(\d)\s*[ºª°]", r"\1ord", sem_indice)
    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", com_ordinais.casefold())
        if not unicodedata.combining(c)
    )
    forma = frozenset(re.findall(r"\d+ord|[a-z]{3,}", sem_acentos))
    numeros = frozenset(
        re.findall(r"\d+(?:[./]\d+)*", re.sub(r"\d\s*[ºª°]", "", sem_indice))
    )

    return forma, numeros


def _jaccard(a, b):
    if not a or not b:
        return 0.0

    return len(a & b) / len(a | b)


def _documentos_ligados(doc_a, doc_b):
    """`doc_b` altera `doc_a`, ou ambos alteram o mesmo item do mesmo documento."""

    for alteracao_b in doc_b.get("altera", []):
        if alteracao_b.get("doc_id") == doc_a.get("doc_id"):
            return True

        for alteracao_a in doc_a.get("altera", []):
            if (
                alteracao_a.get("doc_id") == alteracao_b.get("doc_id")
                and set(alteracao_a.get("itens", [])) & set(alteracao_b.get("itens", []))
            ):
                return True

    return False


def analisar_vigencia(evidencias, catalogo):
    """Mapa chunk_id -> versões substituídas encontradas no trecho.

    Cada item: {"tipo": "onde_se_le" | "linha_substituida", "texto": ...,
    "substituido_por": {"doc_id", "ordem", "texto"} (só em linha_substituida)}.
    """

    resultado = {}

    for evidencia in evidencias:
        texto = evidencia.get("texto", "")
        chunk_id = evidencia["chunk_id"]

        for intervalo in _intervalos_onde_se_le(texto):
            if intervalo.strip():
                resultado.setdefault(chunk_id, []).append({
                    "tipo": "onde_se_le",
                    "texto": re.sub(r"\s+", " ", intervalo).strip(),
                })

    linhas = []

    for evidencia in evidencias:
        doc_id = evidencia.get("metadados", {}).get("doc_id")
        documento = catalogo.get(doc_id)

        if not documento or documento.get("ordem") is None:
            continue

        for linha in _linhas_numeradas(evidencia.get("texto", "")):
            forma, numeros = _forma_e_numeros(linha)

            if len(forma) >= 3 and numeros:
                linhas.append((evidencia["chunk_id"], documento, linha, forma, numeros))

    for chunk_a, doc_a, linha_a, forma_a, numeros_a in linhas:
        for chunk_b, doc_b, linha_b, forma_b, numeros_b in linhas:
            if doc_a["doc_id"] == doc_b["doc_id"]:
                continue

            if doc_b["ordem"] <= doc_a["ordem"]:
                continue

            if not _documentos_ligados(doc_a, doc_b):
                continue

            if numeros_a == numeros_b or _jaccard(forma_a, forma_b) < LIMIAR_SEMELHANCA:
                continue

            resultado.setdefault(chunk_a, []).append({
                "tipo": "linha_substituida",
                "texto": re.sub(r"\s+", " ", linha_a).strip(),
                "substituido_por": {
                    "doc_id": doc_b["doc_id"],
                    "ordem": doc_b["ordem"],
                    "texto": re.sub(r"\s+", " ", linha_b).strip(),
                },
            })

    return resultado


def avisos_de_vigencia(vigencia):
    """Texto de aviso para o contexto enviado ao modelo."""

    avisos = []

    for chunk_id, itens in vigencia.items():
        for item in itens:
            if item["tipo"] == "onde_se_le":
                avisos.append(
                    f'No trecho {chunk_id}, o texto depois de "Onde se lê:" é a versão '
                    f'ANTIGA, substituída pelo "Leia-se". Não use: "{item["texto"][:240]}".'
                )
            else:
                novo = item["substituido_por"]
                avisos.append(
                    f'No trecho {chunk_id}, a linha "{item["texto"][:240]}" foi SUBSTITUÍDA '
                    f'pelo documento {novo["doc_id"]} (ordem {novo["ordem"]}, mais recente): '
                    f'"{novo["texto"][:240]}". Não use a linha substituída.'
                )

    if not avisos:
        return ""

    return "[AVISOS DE VIGÊNCIA]\n" + "\n".join(avisos) + "\n[/AVISOS DE VIGÊNCIA]"


def citacao_substituida(trecho_citado, segmentos, itens):
    """A citação cai inteira dentro de um texto substituído do mesmo trecho?"""

    for item in itens:
        texto = normalizar(item["texto"])

        if segmentos and all(normalizar(s) in texto for s in segmentos):
            return item

        if normalizar(trecho_citado) and normalizar(trecho_citado) in texto:
            return item

    return None