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
