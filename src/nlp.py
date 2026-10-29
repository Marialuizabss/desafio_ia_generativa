"""RF15 — ficha de compreensão da solicitação: resumo, categoria e entidades.

Uma única chamada ao modelo devolve o objeto completo do RF14 (campos, resumo, categoria
e entidades). O texto vai minimizado (RF12) e delimitado (RF03), e a saída passa pela
validação do RF14, com no máximo uma correção.

A comparação com o gabarito é automática onde o critério é objetivo (categoria,
entidades, datas e protocolos inventados) e deixa "a conferir" o que depende de leitura
humana (fato parafraseado no resumo, entidade parecida, entidade inferida).
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# _embrulhar é a delimitação da solicitação do RF03, já testada: reaproveitada, não copiada
try:
    import llm_client
    from llm_client import _embrulhar
    from privacidade import minimizar_texto
    from schemas import (
        ResultadoValidacao, Solicitacao, data_abertura_processo, datas_no_texto,
        esquema_saida_restrita, validar_com_correcao, comparavel,
    )
except ImportError:
    from src import llm_client
    from src.llm_client import _embrulhar
    from src.privacidade import minimizar_texto
    from src.schemas import (
        ResultadoValidacao, Solicitacao, data_abertura_processo, datas_no_texto,
        esquema_saida_restrita, validar_com_correcao, comparavel,
    )

BASE_DIR = Path(__file__).resolve().parent.parent
# Prompt em uso. O v2 (extracao_v2.md) fica guardado: a execução real de 28/10/2026 foi feita com ele
CAMINHO_PROMPT = BASE_DIR / "prompts" / "desafio2" / "extracao_v2.1.md"
TIPOS_DE_ENTIDADE = ("pessoas", "orgaos", "locais", "datas", "protocolos")

_PROTOCOLO = re.compile(r"\b\d{4}-\d{6}\b")
_CARGA_HORARIA = re.compile(r"\b(\d{1,2}\.?\d{3})\s*h", re.IGNORECASE)

# Decisões aceitas na conferência humana, por tipo de item
DECISOES_DA_CONFERENCIA = {
    "fato": ("preservado", "omitido"),
    "entidade_parecida": ("equivalente", "diferente"),
    "entidade_inferida": ("sustentada", "sem_suporte"),
    "sem_suporte": ("confirmado", "falso_alarme"),
}


# ---------------------------------------------------------------- análise

def carregar_prompt() -> str:
    return CAMINHO_PROMPT.read_text(encoding="utf-8").strip()


def arquivo_do_prompt() -> str:
    """Nome do arquivo do prompt em uso, para o registro dizer qual versão foi usada."""
    return CAMINHO_PROMPT.name


def versao_do_prompt() -> str:
    """Muda quando muda o prompt ou o esquema enviado ao modelo."""
    conteudo = carregar_prompt() + json.dumps(esquema_saida_restrita(), sort_keys=True)
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:12]


def montar_entrada(texto_minimizado: str, arquivo: str, erros=None) -> str:
    """Texto delimitado como no RF03; na correção, acrescenta os erros da tentativa anterior."""
    entrada = _embrulhar(texto_minimizado, arquivo)
    if erros:
        lista = "\n".join(f"- {erro.categoria} em {erro.campo or 'JSON'}: {erro.mensagem}" for erro in erros)
        entrada += (
            "\n\n# Correção\nA resposta anterior foi rejeitada pela validação. "
            f"Corrija estes erros e responda de novo com o JSON completo:\n{lista}"
        )
    return entrada


@dataclass
class Analise:
    validacao: ResultadoValidacao
    texto_minimizado: str
    versao_prompt: str
    chamadas: list[dict] = field(default_factory=list)


def analisar_solicitacao(
    texto: str,
    arquivo: str,
    chamar: Callable[[str, str, dict], tuple[str, dict]] | None = None,
    data_minima: date | None = None,
    hoje: date | None = None,
) -> Analise:
    """Minimiza, delimita, chama o modelo uma vez (mais uma correção, se preciso) e valida.

    ``chamar(instrucoes, entrada, esquema)`` devolve (texto, dados da chamada); o padrão é a
    API do provedor configurado (``llm_client.gerar_json_estrito``).
    """

    chamar = chamar or llm_client.gerar_json_estrito
    minimizado = minimizar_texto(texto)
    instrucoes, esquema = carregar_prompt(), esquema_saida_restrita()
    chamadas = []

    def gerar(erros):
        bruto, chamada = chamar(instrucoes, montar_entrada(minimizado, arquivo, erros), esquema)
        chamadas.append(chamada)
        return bruto

    validacao = validar_com_correcao(
        gerar, minimizado, arquivo, data_minima or data_abertura_processo(), hoje
    )
    return Analise(validacao, minimizado, versao_do_prompt(), chamadas)


# ---------------------------------------------------------------- comparação com o gabarito

def _mesma_entidade(tipo: str, esperada: str, obtida: str) -> bool:
    if tipo == "datas":
        datas_esperadas, datas_obtidas = datas_no_texto(esperada), datas_no_texto(obtida)
        if datas_esperadas and datas_obtidas:
            return datas_esperadas == datas_obtidas
    return comparavel(esperada).strip(" .,;") == comparavel(obtida).strip(" .,;")


def _parecidas(esperada: str, obtida: str) -> bool:
    a, b = comparavel(esperada), comparavel(obtida)
    return bool(a and b) and (a in b or b in a)


def comparar_entidades(obtidas: dict, esperadas: dict, texto: str) -> dict:
    """Acertos, omissões, parecidas a conferir, extras do texto, incorretas e inferidas a conferir."""
    texto_comparavel = comparavel(texto)
    resultado = {chave: [] for chave in ("acertos", "omissoes", "parecidas", "extras_no_texto", "incorretas", "inferidas")}
    for tipo in TIPOS_DE_ENTIDADE:
        restantes = list(obtidas.get(tipo, []))
        for esperada in esperadas.get(tipo, []):
            igual = next((o for o in restantes if _mesma_entidade(tipo, esperada["texto"], o["texto"])), None)
            if igual:
                restantes.remove(igual)
                resultado["acertos"].append({"tipo": tipo, "texto": esperada["texto"]})
                continue
            parecida = next((o for o in restantes if _parecidas(esperada["texto"], o["texto"])), None)
            if parecida:
                restantes.remove(parecida)
                resultado["parecidas"].append({"tipo": tipo, "esperada": esperada["texto"], "obtida": parecida["texto"]})
            else:
                resultado["omissoes"].append({"tipo": tipo, "texto": esperada["texto"]})
        for obtida in restantes:
            item = {"tipo": tipo, "texto": obtida["texto"]}
            if obtida["origem"] == "inferida":
                resultado["inferidas"].append(item)
            elif comparavel(obtida["texto"]) in texto_comparavel:
                resultado["extras_no_texto"].append(item)
            else:
                resultado["incorretas"].append(item)
    return resultado


def sem_suporte_no_resumo(resumo: str, texto: str) -> list[str]:
    """Datas, protocolos e cargas horárias do resumo que não estão no texto."""
    achados = [f"data {d:%d/%m/%Y}" for d in sorted(datas_no_texto(resumo) - datas_no_texto(texto))]
    achados += [f"protocolo {p}" for p in _PROTOCOLO.findall(resumo) if p not in texto]
    cargas_do_texto = {c.replace(".", "") for c in _CARGA_HORARIA.findall(texto)}
    achados += [f"carga horária {c}" for c in _CARGA_HORARIA.findall(resumo) if c.replace(".", "") not in cargas_do_texto]
    return achados


def comparar_com_gabarito(solicitacao: Solicitacao | None, gabarito: dict, texto: str) -> dict:
    """Comparação de um caso com o gabarito 2.0 (RF15)."""
    esperadas = gabarito["entidades_esperadas"]
    if solicitacao is None:
        omitidas = [{"tipo": t, "texto": e["texto"]} for t in TIPOS_DE_ENTIDADE for e in esperadas[t]]
        return {
            "rejeitada": True,
            "categoria": {"esperada": gabarito["categoria_esperada"], "obtida": None, "acerto": False},
            "entidades": {"acertos": [], "omissoes": omitidas, "parecidas": [], "extras_no_texto": [], "incorretas": [], "inferidas": []},
            "fatos": {"preservados": [], "a_conferir": [f["fato"] for f in gabarito["fatos_essenciais"]]},
            "sem_suporte": [],
            "palavras_resumo": 0,
        }
    resumo = comparavel(solicitacao.resumo)
    preservados, a_conferir = [], []
    for fato in gabarito["fatos_essenciais"]:
        (preservados if comparavel(fato["evidencia"]) in resumo else a_conferir).append(fato["fato"])
    return {
        "rejeitada": False,
        "categoria": {
            "esperada": gabarito["categoria_esperada"],
            "obtida": solicitacao.categoria,
            "acerto": solicitacao.categoria == gabarito["categoria_esperada"],
        },
        "entidades": comparar_entidades(solicitacao.entidades.model_dump(), esperadas, texto),
        "fatos": {"preservados": preservados, "a_conferir": a_conferir},
        "sem_suporte": sem_suporte_no_resumo(solicitacao.resumo, texto),
        "palavras_resumo": len(solicitacao.resumo.split()),
    }


# ---------------------------------------------------------------- métricas

def fracao(numerador: int, denominador: int) -> dict:
    """Numerador e denominador sempre visíveis; sem denominador, o percentual fica vazio."""
    return {
        "numerador": numerador,
        "denominador": denominador,
        "percentual": round(100 * numerador / denominador, 1) if denominador else None,
    }


def agregar(comparacoes: dict, gabaritos: dict) -> dict:
    """Métricas dos casos. ``comparacoes`` e ``gabaritos`` são indexados pelo caso."""
    do_enunciado = [caso for caso in comparacoes if not gabaritos[caso].get("acrescimo_ao_minimo")]

    def soma(chave, sub):
        return sum(len(c[chave][sub]) for c in comparacoes.values())

    esperadas = sum(len(e) for caso in comparacoes for e in gabaritos[caso]["entidades_esperadas"].values())
    fatos = sum(len(gabaritos[caso]["fatos_essenciais"]) for caso in comparacoes)
    return {
        "acuracia_categoria": fracao(sum(c["categoria"]["acerto"] for c in comparacoes.values()), len(comparacoes)),
        "acuracia_categoria_seis_do_enunciado": fracao(sum(comparacoes[c]["categoria"]["acerto"] for c in do_enunciado), len(do_enunciado)),
        "entidades_acertos": fracao(soma("entidades", "acertos"), esperadas),
        "entidades_omissoes": soma("entidades", "omissoes"),
        "entidades_parecidas_a_conferir": soma("entidades", "parecidas"),
        "entidades_extras_no_texto": soma("entidades", "extras_no_texto"),
        "entidades_incorretas": soma("entidades", "incorretas"),
        "entidades_inferidas_a_conferir": soma("entidades", "inferidas"),
        "fatos_preservados_automatico": fracao(soma("fatos", "preservados"), fatos),
        "fatos_a_conferir": soma("fatos", "a_conferir"),
        "resumo_sem_suporte": sum(len(c["sem_suporte"]) for c in comparacoes.values()),
        "rejeitadas": fracao(sum(c["rejeitada"] for c in comparacoes.values()), len(comparacoes)),
    }


# ---------------------------------------------------------------- conferência humana

def itens_para_conferencia(comparacoes: dict) -> list[dict]:
    """O que depende de leitura humana, com as decisões aceitas para cada tipo."""
    itens = []

    def item(caso, tipo, descricao):
        itens.append({"caso": caso, "tipo": tipo, "descricao": descricao,
                      "opcoes": list(DECISOES_DA_CONFERENCIA[tipo]), "decisao": None, "observacao": ""})

    for caso, c in comparacoes.items():
        for fato in c["fatos"]["a_conferir"]:
            item(caso, "fato", f"O resumo preserva o fato \"{fato}\"?")
        for p in c["entidades"]["parecidas"]:
            item(caso, "entidade_parecida", f"{p['tipo']}: esperada \"{p['esperada']}\", obtida \"{p['obtida']}\"")
        for i in c["entidades"]["inferidas"]:
            item(caso, "entidade_inferida", f"{i['tipo']} inferida \"{i['texto']}\": o texto sustenta?")
        for s in c["sem_suporte"]:
            item(caso, "sem_suporte", f"Resumo cita {s}, que não está no texto")
    return itens


def consolidar(metricas: dict, itens: list[dict]) -> dict:
    """Métricas finais com as decisões da conferência humana. Exige todas as decisões."""
    pendentes = [i for i in itens if i["decisao"] not in DECISOES_DA_CONFERENCIA[i["tipo"]]]
    if pendentes:
        raise ValueError(f"Conferência incompleta: {len(pendentes)} item(ns) sem decisão válida.")

    def conta(tipo, decisao):
        return sum(1 for i in itens if i["tipo"] == tipo and i["decisao"] == decisao)

    final = json.loads(json.dumps(metricas))
    fatos = final["fatos_preservados_automatico"]
    final["fatos_preservados"] = fracao(fatos["numerador"] + conta("fato", "preservado"), fatos["denominador"])
    final["fatos_omitidos"] = conta("fato", "omitido")
    acertos = final["entidades_acertos"]
    final["entidades_acertos"] = fracao(acertos["numerador"] + conta("entidade_parecida", "equivalente"), acertos["denominador"])
    final["entidades_omissoes"] += conta("entidade_parecida", "diferente")
    final["entidades_inferidas_sem_suporte"] = conta("entidade_inferida", "sem_suporte")
    final["resumo_sem_suporte"] = conta("sem_suporte", "confirmado")
    final["fatos_sem_suporte"] = final["resumo_sem_suporte"] + final["entidades_inferidas_sem_suporte"] + final["entidades_incorretas"]
    for chave in ("fatos_a_conferir", "entidades_parecidas_a_conferir", "entidades_inferidas_a_conferir"):
        final.pop(chave)
    final["conferencia_humana"] = {"itens": len(itens)}
    return final
