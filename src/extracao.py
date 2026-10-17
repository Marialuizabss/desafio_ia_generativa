"""Objeto da extração usada para preencher a minuta.

O formato é o de ``extracao_esperada`` nos gabaritos: cada campo tem
``valor`` e ``fonte``. Campo ausente fica ``"não localizado"`` com fonte
``"nenhuma"``, e o objeto continua completo.
"""

from dataclasses import dataclass, field

VALOR_AUSENTE = "não localizado"
FONTE_AUSENTE = "nenhuma"

CAMPOS_SOLICITACAO = (
    "solicitante",
    "protocolo",
    "data_solicitacao",
    "curso",
    "eixo",
    "carga_horaria",
    "turno",
    "data_inicio",
    "regras_ciencia",
)

CAMPOS_INSTITUCIONAIS = (
    "documentos_necessarios",
    "prazo_apresentacao",
    "local_horario",
)

CAMPOS = CAMPOS_SOLICITACAO + CAMPOS_INSTITUCIONAIS

CATEGORIAS = (
    "matricula",
    "documentacao",
    "frequencia_cancelamento",
    "informacao_geral",
    "reclamacao",
    "outros",
)


@dataclass
class Campo:
    """Um valor extraído e o arquivo de onde ele veio."""

    valor: str = VALOR_AUSENTE
    fonte: str = FONTE_AUSENTE

    def __post_init__(self) -> None:
        valor = "" if self.valor is None else str(self.valor).strip()
        if not valor or valor == VALOR_AUSENTE:
            self.valor = VALOR_AUSENTE
            self.fonte = FONTE_AUSENTE
            return
        self.valor = valor
        fonte = "" if self.fonte is None else str(self.fonte).strip()
        self.fonte = fonte or FONTE_AUSENTE

    @property
    def ausente(self) -> bool:
        return self.valor == VALOR_AUSENTE

    def para_dict(self) -> dict:
        return {"valor": self.valor, "fonte": self.fonte}

    @classmethod
    def de_item(cls, item) -> "Campo":
        if isinstance(item, cls):
            return item
        if isinstance(item, dict):
            return cls(item.get("valor"), item.get("fonte"))
        return cls(item)


@dataclass
class Extracao:
    """Os doze campos que preenchem o modelo da minuta."""

    solicitante: Campo = field(default_factory=Campo)
    protocolo: Campo = field(default_factory=Campo)
    data_solicitacao: Campo = field(default_factory=Campo)
    curso: Campo = field(default_factory=Campo)
    eixo: Campo = field(default_factory=Campo)
    carga_horaria: Campo = field(default_factory=Campo)
    turno: Campo = field(default_factory=Campo)
    data_inicio: Campo = field(default_factory=Campo)
    regras_ciencia: Campo = field(default_factory=Campo)
    documentos_necessarios: Campo = field(default_factory=Campo)
    prazo_apresentacao: Campo = field(default_factory=Campo)
    local_horario: Campo = field(default_factory=Campo)

    def __post_init__(self) -> None:
        for nome in CAMPOS:
            setattr(self, nome, Campo.de_item(getattr(self, nome)))

    def definir(self, nome: str, valor: str, fonte: str) -> None:
        if nome not in CAMPOS:
            raise KeyError(nome)
        setattr(self, nome, Campo(valor, fonte))

    @property
    def campos_ausentes(self) -> list[str]:
        return [nome for nome in CAMPOS if getattr(self, nome).ausente]

    def para_dict(self) -> dict:
        return {nome: getattr(self, nome).para_dict() for nome in CAMPOS}

    @classmethod
    def de_dict(cls, dados: dict | None) -> "Extracao":
        dados = dados or {}
        return cls(**{nome: dados[nome] for nome in CAMPOS if nome in dados})


@dataclass
class ResultadoExtracao:
    """Resposta completa da análise, com a extração que preenche a minuta."""

    extracao: Extracao
    categoria: str
    assunto: str
    pedido: str
    alertas_seguranca: list[str]
    requer_revisao: bool
    minuta: str

    @property
    def campos_ausentes(self) -> list[str]:
        return self.extracao.campos_ausentes

    def para_dict(self) -> dict:
        return {
            "categoria": self.categoria,
            "assunto": self.assunto,
            "pedido": self.pedido,
            "campos": self.extracao.para_dict(),
            "campos_ausentes": self.campos_ausentes,
            "alertas_seguranca": list(self.alertas_seguranca),
            "requer_revisao": True,
            "minuta": self.minuta,
        }


def resultado_de_dict(dados: dict | None, arquivo: str) -> ResultadoExtracao:
    """Monta o resultado a partir do JSON do modelo.

    A fonte de um campo preenchido passa a ser ``arquivo``. Campo ausente
    permanece com fonte ``"nenhuma"``.
    """

    dados = dados or {}
    campos = dados.get("campos")
    extracao = Extracao.de_dict(campos if isinstance(campos, dict) else {})
    for nome in CAMPOS:
        campo = getattr(extracao, nome)
        if not campo.ausente:
            campo.fonte = arquivo

    categoria = str(dados.get("categoria") or "").strip()
    if categoria not in CATEGORIAS:
        categoria = "outros"

    alertas = dados.get("alertas_seguranca") or []
    if not isinstance(alertas, list):
        alertas = [alertas]

    return ResultadoExtracao(
        extracao=extracao,
        categoria=categoria,
        assunto=_texto_ou_ausente(dados.get("assunto")),
        pedido=_texto_ou_ausente(dados.get("pedido")),
        alertas_seguranca=[
            item for item in (str(alerta).strip() for alerta in alertas) if item
        ],
        requer_revisao=True,
        minuta=str(dados.get("minuta") or "").strip(),
    )


def _texto_ou_ausente(valor) -> str:
    texto = "" if valor is None else str(valor).strip()
    return texto or VALOR_AUSENTE
