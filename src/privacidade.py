"""Minimização de dados pessoais antes do envio ao provedor (RF12).

Remove do texto os dados pessoais que a minuta não usa — CPF, RG, e-mail,
telefone, data de nascimento, naturalidade e filiação — trocando cada um
por um marcador. Nome, protocolo, dados do curso e regras de ciência são
preservados, porque preenchem a minuta.

A remoção usa padrões de texto e rótulos ("CPF", "nome da mãe"...). Um dado
escrito de forma inesperada pode passar; a revisão humana continua necessária.
"""

import re

MARCADORES = {
    "cpf": "[CPF REMOVIDO]",
    "rg": "[RG REMOVIDO]",
    "email": "[E-MAIL REMOVIDO]",
    "telefone": "[TELEFONE REMOVIDO]",
    "data_nascimento": "[DATA DE NASCIMENTO REMOVIDA]",
    "naturalidade": "[NATURALIDADE REMOVIDA]",
    "filiacao": "[FILIAÇÃO REMOVIDA]",
}

_FLAGS = re.IGNORECASE

# Liga o rótulo ao valor sem passar para a linha seguinte:
# "CPF 123", "CPF: 123", "CPF é 123", "RG nº 123"
_LIGACAO = r"[ \t]*(?:n[º°o]\.?[ \t]*)?(?:é|:|-|,)?[ \t]*"

# Rótulo que não está dentro de um marcador já inserido ("[NATURALIDADE REMOVIDA]")
_INICIO = r"(?<!\[)\b"

_DATA = (
    r"\d{1,2}/\d{1,2}/\d{2,4}"
    r"|\d{1,2}º?[ \t]+de[ \t]+[a-zç]+[ \t]+de[ \t]+\d{4}"
)

# Valor de texto livre: começa por letra ou número e termina na pontuação, na
# quebra de linha ou antes do próximo rótulo de formulário em maiúsculas
# ("CUIABÁ UF:" -> "CUIABÁ"). Campo vazio não é alterado, nem quando é seguido
# de outro rótulo de uma palavra na mesma linha ("NOME DO PAI:  TURNO: ...").
_ATE_PONTUACAO = (
    r"(?=[^\W_])(?![A-ZÀ-Ú][A-ZÀ-Ú.]{0,30}:)"
    r"(?:(?![,;.\n]|[ \t]+[A-ZÀ-Ú][A-ZÀ-Ú. ]{0,30}:).)+"
)

_REGRAS = [
    # E-mail: primeiro com @ (aceita espaço em volta, comum em OCR de letra
    # manuscrita); depois pelo rótulo, inclusive transcrições que perderam o @
    ("email", re.compile(
        r"(?<![\w.+-])[\w.+-]{1,64}[ \t]?@[ \t]?[\w-]{1,63}(?:\.[\w-]{1,63})+", _FLAGS), None),
    ("email", re.compile(
        rf"({_INICIO}e-?mail{_LIGACAO})([\w.+-]{{1,64}}(?:\.[\w-]{{1,63}})+)", _FLAGS), 2),

    # CPF: formato numérico e, pelo rótulo, dígitos separados (fala transcrita)
    ("cpf", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), None),
    ("cpf", re.compile(rf"({_INICIO}CPF{_LIGACAO})(\d[\d.\- ]{{9,}}\d)", _FLAGS), 2),

    # RG: pelo rótulo (formatos variam por estado) e no formato 1234567-8
    ("rg", re.compile(rf"({_INICIO}RG{_LIGACAO})(\d[\dXx.\- ]{{4,}}[\dXx])", _FLAGS), 2),
    ("rg", re.compile(r"\b\d{7}-[\dXx]\b"), None),

    # Telefone: pelo rótulo e no formato (65) 99999-9999
    ("telefone", re.compile(
        rf"({_INICIO}(?:tel(?:efone)?\.?|celular|whatsapp)(?:[ \t]+(?:celular|residencial|fixo))?{_LIGACAO})"
        r"(\+?[\d() .\-]{8,}\d)", _FLAGS), 2),
    ("telefone", re.compile(r"\(\d{2}\)\s?9?\d{4}-?\d{4}\b"), None),

    # Data de nascimento: "nasci em ...", "nascido em ...", "data de nascimento: ..."
    ("data_nascimento", re.compile(
        rf"({_INICIO}nasci(?:do|da)?[ \t]+(?:em|no[ \t]+dia)[ \t]+)({_DATA})", _FLAGS), 2),
    ("data_nascimento", re.compile(
        rf"({_INICIO}data[ \t]+de[ \t]+nascimento{_LIGACAO})({_DATA})", _FLAGS), 2),

    # Naturalidade: logo após a data de nascimento removida, ou pelo rótulo
    ("naturalidade", re.compile(
        r"(\[DATA DE NASCIMENTO REMOVIDA\],?[ \t]+(?:em|na cidade de)[ \t]+)"
        r"([A-ZÀ-Ú][\wÀ-ú]*(?:[ \t-]+(?:d[aeo]s?|[A-ZÀ-Ú][\wÀ-ú]*))*)"), 2),
    ("naturalidade", re.compile(rf"({_INICIO}naturalidade{_LIGACAO})({_ATE_PONTUACAO})", _FLAGS), 2),

    # Filiação: "nome da mãe ...", "o nome da minha mãe é ...", "NOME DO PAI: ..."
    ("filiacao", re.compile(
        rf"({_INICIO}nome[ \t]+d[ao][ \t]+(?:minha[ \t]+|meu[ \t]+)?(?:m[ãa]e|pai){_LIGACAO})({_ATE_PONTUACAO})",
        _FLAGS), 2),
]


def minimizar_texto(texto: str) -> str:
    """Devolve o texto sem os dados pessoais que a minuta não usa."""
    resultado = texto or ""
    for categoria, padrao, grupo in _REGRAS:
        marcador = MARCADORES[categoria]
        if grupo is None:
            resultado = padrao.sub(marcador, resultado)
        else:
            resultado = padrao.sub(lambda m: m.group(1) + marcador, resultado)
    return resultado


def contar_remocoes(texto_minimizado: str) -> dict:
    """Quantos dados de cada categoria foram removidos (só as presentes)."""
    contagem = {
        categoria: texto_minimizado.count(marcador)
        for categoria, marcador in MARCADORES.items()
    }
    return {categoria: total for categoria, total in contagem.items() if total}
