"""RF14 — contrato de dados da solicitação (versão 2.0) e validação em três camadas.

A extração do modelo passa por três verificações, nesta ordem:

1. sintática: o texto é JSON;
2. esquema: chaves, tipos e valores conferem com o contrato (Pydantic, modo estrito);
3. regras de negócio: datas, presença no texto original e coerência interna.

Erro de sintaxe ou de esquema admite uma única nova tentativa; o que continuar
inválido é rejeitado. Regra de negócio violada não pede nova tentativa (o dado veio
assim da entrada): o caso vai para revisão. Nos dois casos a minuta fica bloqueada.

Este módulo não chama a API: quem gera o JSON é passado como parâmetro.
"""

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

try:
    from extracao import CAMPOS, CATEGORIAS, FONTE_AUSENTE, VALOR_AUSENTE
except ImportError:
    from src.extracao import CAMPOS, CATEGORIAS, FONTE_AUSENTE, VALOR_AUSENTE

BASE_DIR = Path(__file__).resolve().parent.parent
ACERVO = BASE_DIR / "dados" / "acervo" / "acervo.json"

VERSAO_ESQUEMA = "2.0"
LIMITE_PALAVRAS_RESUMO = 100

# Campos que podem ser null; campos_ausentes lista exatamente os que vierem null
CAMPOS_DA_SOLICITACAO = ("protocolo", "data_solicitacao", "solicitante", "assunto", "pedido")
CAMPOS_DO_CURSO = ("curso", "eixo", "carga_horaria", "turno", "data_inicio", "regras_ciencia")
CAMPOS_ANULAVEIS = CAMPOS_DA_SOLICITACAO + CAMPOS_DO_CURSO

# Tipo de erro do Pydantic -> categoria do RF14 (os demais tipos são "tipo_incorreto")
CATEGORIA_DO_ERRO = {
    "extra_forbidden": "chave_extra",
    "missing": "campo_obrigatorio_ausente",
    "literal_error": "valor_fora_do_dominio",
}

MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
_DATA_NUMERICA = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_DATA_POR_EXTENSO = re.compile(r"\b(\d{1,2})º?\s+de\s+([a-zç]+)\s+de\s+(\d{4})\b", re.IGNORECASE)


# ---------------------------------------------------------------- contrato

class _Modelo(BaseModel):
    # Chave a mais é erro e nenhum tipo é convertido ("sim" não vira True)
    model_config = ConfigDict(extra="forbid", strict=True)


class Entidade(_Modelo):
    texto: str
    origem: Literal["literal", "inferida"]


class Entidades(_Modelo):
    pessoas: list[Entidade]
    orgaos: list[Entidade]
    locais: list[Entidade]
    datas: list[Entidade]
    protocolos: list[Entidade]


class DadosCurso(_Modelo):
    curso: str | None
    eixo: str | None
    carga_horaria: str | None
    turno: str | None
    data_inicio: str | None
    regras_ciencia: str | None


class Solicitacao(_Modelo):
    """Contrato da solicitação, versão 2.0 (seção 9 de documentacao/desafio-2/contratos_dados.md)."""

    versao_esquema: Literal["2.0"]
    protocolo: str | None
    data_solicitacao: str | None
    solicitante: str | None
    assunto: str | None
    pedido: str | None
    categoria: Literal[CATEGORIAS]
    resumo: str
    entidades: Entidades
    dados_curso: DadosCurso
    campos_ausentes: list[Literal[CAMPOS_ANULAVEIS]]
    alertas_seguranca: list[str]
    requer_revisao: bool
    motivos_revisao: list[str]

    def valores(self) -> dict:
        """Os campos anuláveis num só nível: os da solicitação e os do curso."""
        return {
            **{nome: getattr(self, nome) for nome in CAMPOS_DA_SOLICITACAO},
            **self.dados_curso.model_dump(),
        }


def esquema_saida_restrita() -> dict:
    """JSON Schema do contrato no formato exigido pela saída restrita do provedor.

    Gerado a partir dos modelos, para que o esquema enviado ao modelo e o validado
    localmente sejam o mesmo. Tira os títulos e troca ``const`` por ``enum``.
    """

    def ajustar(no):
        if isinstance(no, dict):
            no = {chave: ajustar(valor) for chave, valor in no.items() if chave != "title"}
            if "const" in no:
                no["enum"] = [no.pop("const")]
            return no
        if isinstance(no, list):
            return [ajustar(item) for item in no]
        return no

    return ajustar(Solicitacao.model_json_schema())


# ---------------------------------------------------------------- validação

@dataclass
class ErroValidacao:
    camada: Literal["sintaxe", "esquema", "regra"]
    categoria: str
    campo: str
    mensagem: str


def validar_estrutura(bruto: str) -> tuple[Solicitacao | None, list[ErroValidacao]]:
    """Camadas 1 e 2: o texto é JSON e o JSON segue o contrato."""
    try:
        dados = json.loads(bruto)
    except (json.JSONDecodeError, TypeError) as erro:
        return None, [ErroValidacao("sintaxe", "json_invalido", "", f"Não é JSON: {erro}")]
    try:
        # Validação em modo JSON: objetos aninhados chegam como dicionários
        return Solicitacao.model_validate_json(json.dumps(dados)), []
    except ValidationError as erro:
        return None, [
            ErroValidacao(
                "esquema",
                CATEGORIA_DO_ERRO.get(detalhe["type"], "tipo_incorreto"),
                ".".join(str(parte) for parte in detalhe["loc"]),
                detalhe["msg"],
            )
            for detalhe in erro.errors()
        ]


def validar_regras(
    solicitacao: Solicitacao,
    texto_original: str,
    data_minima: date | None = None,
    hoje: date | None = None,
) -> list[ErroValidacao]:
    """Camada 3: regras de negócio, conferidas contra o texto que o modelo recebeu.

    ``data_minima`` é a abertura do processo seletivo; sem ela, só se confere o futuro.
    """

    hoje = hoje or date.today()
    erros = []
    texto = comparavel(texto_original)
    datas_do_texto = datas_no_texto(texto_original)
    valores = solicitacao.valores()

    datas = {}
    for campo in ("data_solicitacao", "data_inicio"):
        valor = valores[campo]
        if valor is None:
            continue
        convertida = _ler_data(valor)
        if convertida is None:
            erros.append(ErroValidacao("regra", "data_impossivel", campo,
                                       f"{valor} não é uma data válida no formato DD/MM/AAAA."))
            continue
        datas[campo] = convertida
        if convertida not in datas_do_texto:
            erros.append(ErroValidacao("regra", "dado_nao_presente_no_original", campo,
                                       f"A data {valor} não aparece no texto original."))

    solicitada = datas.get("data_solicitacao")
    if solicitada and data_minima and solicitada < data_minima:
        erros.append(ErroValidacao("regra", "data_incoerente", "data_solicitacao",
                                   f"{solicitada:%d/%m/%Y} é anterior à abertura do processo seletivo ({data_minima:%d/%m/%Y})."))
    if solicitada and solicitada > hoje:
        erros.append(ErroValidacao("regra", "data_incoerente", "data_solicitacao",
                                   f"{solicitada:%d/%m/%Y} está no futuro."))
    inicio = datas.get("data_inicio")
    if solicitada and inicio and inicio < solicitada:
        erros.append(ErroValidacao("regra", "data_incoerente", "data_inicio",
                                   f"O início do curso ({inicio:%d/%m/%Y}) é anterior à solicitação ({solicitada:%d/%m/%Y})."))

    for campo in ("protocolo", "solicitante"):
        valor = valores[campo]
        if valor is not None and comparavel(valor) not in texto:
            erros.append(ErroValidacao("regra", "dado_nao_presente_no_original", campo,
                                       f"{campo} não aparece no texto original."))

    for tipo, entidades in solicitacao.entidades.model_dump().items():
        for indice, entidade in enumerate(entidades):
            if entidade["origem"] == "literal" and comparavel(entidade["texto"]) not in texto:
                erros.append(ErroValidacao("regra", "fato_sem_suporte", f"entidades.{tipo}.{indice}",
                                           f"Entidade marcada como literal não aparece no texto: {entidade['texto']}"))

    nulos = {nome for nome, valor in valores.items() if valor is None}
    if set(solicitacao.campos_ausentes) != nulos:
        erros.append(ErroValidacao("regra", "incoerencia_interna", "campos_ausentes",
                                   f"campos_ausentes {sorted(solicitacao.campos_ausentes)} difere dos campos nulos {sorted(nulos)}."))

    palavras = len(solicitacao.resumo.split())
    if palavras > LIMITE_PALAVRAS_RESUMO:
        erros.append(ErroValidacao("regra", "resumo_longo", "resumo",
                                   f"O resumo tem {palavras} palavras (limite {LIMITE_PALAVRAS_RESUMO})."))
    return erros


# ---------------------------------------------------------------- ciclo com correção

@dataclass
class ResultadoValidacao:
    """Entrada, erros de cada tentativa e decisão: o que o RF14 manda preservar."""

    decisao: Literal["aceita", "revisar", "rejeitada"]
    solicitacao: Solicitacao | None
    tentativas: list[dict]
    erros_regras: list[ErroValidacao]
    entrada: dict
    saidas: list[str] = field(default_factory=list, repr=False)

    @property
    def minuta_bloqueada(self) -> bool:
        """Estrutura inválida ou dado incoerente: a minuta não é montada."""
        return self.decisao == "rejeitada" or bool(self.erros_regras)

    @property
    def motivos(self) -> list[str]:
        if self.decisao == "rejeitada":
            return [f"{e['categoria']} em {e['campo'] or 'JSON'}" for e in self.tentativas[-1]["erros"]]
        motivos = [f"{erro.categoria}: {erro.mensagem}" for erro in self.erros_regras]
        if self.solicitacao:
            motivos += [f"alerta de segurança: {alerta}" for alerta in self.solicitacao.alertas_seguranca]
            motivos += [f"modelo: {motivo}" for motivo in self.solicitacao.motivos_revisao]
        return motivos

    def para_registro(self) -> dict:
        """Versão para o log: sem o texto da entrada nem a saída do modelo (RF11)."""
        return {
            "versao_esquema": VERSAO_ESQUEMA,
            "entrada": self.entrada,
            "decisao": self.decisao,
            "minuta_bloqueada": self.minuta_bloqueada,
            "tentativas": self.tentativas,
            "erros_regras": [asdict(erro) for erro in self.erros_regras],
        }


def validar_com_correcao(
    gerar: Callable[[list[ErroValidacao] | None], str],
    texto_original: str,
    arquivo: str = "",
    data_minima: date | None = None,
    hoje: date | None = None,
) -> ResultadoValidacao:
    """Valida a saída do modelo, com no máximo uma nova tentativa.

    ``gerar(None)`` produz a primeira saída; ``gerar(erros)`` produz a correção,
    recebendo os erros da tentativa anterior para incluí-los no pedido.
    """

    entrada = {
        "arquivo": arquivo,
        "sha256_texto": hashlib.sha256((texto_original or "").encode("utf-8")).hexdigest(),
    }
    tentativas, saidas = [], []
    erros_anteriores = None
    solicitacao = None
    for numero in (1, 2):
        bruto = gerar(erros_anteriores)
        saidas.append(bruto)
        solicitacao, erros = validar_estrutura(bruto)
        tentativas.append({"numero": numero, "erros": [asdict(erro) for erro in erros]})
        if solicitacao is not None:
            break
        erros_anteriores = erros

    if solicitacao is None:
        return ResultadoValidacao("rejeitada", None, tentativas, [], entrada, saidas)

    erros_regras = validar_regras(solicitacao, texto_original, data_minima, hoje)
    revisar = erros_regras or solicitacao.alertas_seguranca or solicitacao.requer_revisao
    return ResultadoValidacao("revisar" if revisar else "aceita", solicitacao, tentativas, erros_regras, entrada, saidas)


# ---------------------------------------------------------------- apoio

def data_abertura_processo(acervo: Path = ACERVO) -> date | None:
    """Data do edital (documento base, ordem 0) no catálogo do acervo."""
    try:
        catalogo = json.loads(Path(acervo).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for documento in catalogo.get("documentos", []):
        if documento.get("ordem") == 0 and documento.get("documento_base") is None and documento.get("data_documento"):
            return date.fromisoformat(documento["data_documento"])
    return None


def datas_no_texto(texto: str) -> set[date]:
    """Datas escritas como 14/10/2026 ou "14 de outubro de 2026"."""
    encontradas = set()
    for dia, mes, ano in _DATA_NUMERICA.findall(texto or ""):
        encontradas.add(_data_ou_none(ano, mes, dia))
    for dia, mes, ano in _DATA_POR_EXTENSO.findall(texto or ""):
        if mes.casefold() in MESES:
            encontradas.add(_data_ou_none(ano, MESES[mes.casefold()], dia))
    encontradas.discard(None)
    return encontradas


def para_exibicao(valor) -> str:
    """Ausência é null no JSON e "não localizado" na interface."""
    texto = "" if valor is None else str(valor).strip()
    return texto or VALOR_AUSENTE


def para_campos_v1(solicitacao: Solicitacao, arquivo: str) -> dict:
    """Converte para os campos do Desafio 1 ({valor, fonte}), usados pela minuta atual.

    Documentos, prazo e local não vêm da solicitação: no Desafio 2 saem do acervo.
    """
    valores = solicitacao.valores()
    campos = {}
    for nome in CAMPOS:
        valor = valores.get(nome)
        campos[nome] = (
            {"valor": str(valor), "fonte": arquivo} if valor not in (None, "")
            else {"valor": VALOR_AUSENTE, "fonte": FONTE_AUSENTE}
        )
    return campos


def esperado_do_gabarito(gabarito: dict) -> dict:
    """Monta, a partir de um gabarito 2.0, o JSON que uma extração correta devolveria.

    Trabalha sobre uma cópia: alterar o resultado não pode alterar o gabarito.
    """
    gabarito = json.loads(json.dumps(gabarito))
    extracao = gabarito["extracao_esperada"]

    def valor(nome):
        bruto = extracao[nome]["valor"]
        return None if bruto == VALOR_AUSENTE else bruto

    def opcional(texto):
        return None if texto in (None, "", VALOR_AUSENTE) else texto

    dados = {
        "versao_esquema": VERSAO_ESQUEMA,
        **{nome: valor(nome) for nome in ("protocolo", "data_solicitacao", "solicitante")},
        "assunto": opcional(gabarito["assunto_esperado"]),
        "pedido": opcional(gabarito["pedido_esperado"]),
        "categoria": gabarito["categoria_esperada"],
        "resumo": gabarito["resumo_referencia"],
        "entidades": gabarito["entidades_esperadas"],
        "dados_curso": {nome: valor(nome) for nome in CAMPOS_DO_CURSO},
        "alertas_seguranca": [],
        "requer_revisao": False,
        "motivos_revisao": [],
    }
    nulos = [nome for nome in CAMPOS_DA_SOLICITACAO if dados[nome] is None]
    nulos += [nome for nome in CAMPOS_DO_CURSO if dados["dados_curso"][nome] is None]
    dados["campos_ausentes"] = nulos
    return dados


def comparavel(texto: str) -> str:
    """Sem acento, sem maiúsculas e com espaços normalizados (OCR e transcrição variam nisso)."""
    sem_acento = "".join(
        letra for letra in unicodedata.normalize("NFKD", texto or "") if not unicodedata.combining(letra)
    )
    return re.sub(r"\s+", " ", sem_acento).strip().casefold()


def _ler_data(valor: str) -> date | None:
    try:
        return datetime.strptime(valor.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _data_ou_none(ano, mes, dia) -> date | None:
    try:
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None
