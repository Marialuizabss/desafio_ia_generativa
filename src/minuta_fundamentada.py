"""Minuta de matrícula fundamentada no acervo (RF19 e RF24).

A ficha vem da extração validada do caso. As orientações (documentos, local e período)
vêm do RAG, com uma consulta por assunto: uma pergunta que junta os três assuntos deixa o
trecho do período fora do top-15 (posição 35 no CASO-08).

As três consultas são as mesmas para toda solicitação de matrícula (regra por categoria de
pedido, não por caso). A minuta é salva como pendente: quem aprova é o servidor, pela
interface. Nada aqui grava decisão humana.

Uso: python -m src.minuta_fundamentada --caso CASO-08 [--configuracao principal]
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from src.consulta_acervo import _linhas_de_fonte, classificar_consulta, linhas_da_ficha, minuta_do_atendimento
from src.rf19_complemento import responder_rf19

BASE_DIR = Path(__file__).resolve().parent.parent

ASSUNTOS = (
    ("documentos", "Quais documentos devo apresentar para efetivar a matrícula{chamada}?"),
    ("local", "Onde devo comparecer para efetivar a matrícula{chamada}?"),
    ("período", "Qual o período de matrícula{chamada}?"),
)
ORDEM_PIOR = ("conflito", "sem_evidencia", "indice_desatualizado", "bloqueio", "falha")


def _chamada(linhas):
    achado = re.search(r"\d+ª\s+chamada", str((linhas or {}).get("resumo") or ""), re.IGNORECASE)
    return f" da {achado.group(0)}" if achado else ""


def perguntas_de_matricula(linhas):
    chamada = _chamada(linhas)
    return [(assunto, modelo.format(chamada=chamada)) for assunto, modelo in ASSUNTOS]


def _linha(parte, com_fontes):
    consulta = parte["consulta"]
    rotulo = parte["assunto"].capitalize()
    if consulta.get("tipo") == "fundamentada":
        texto = (consulta.get("resposta") or "").strip()
        if com_fontes:
            fontes = _linhas_de_fonte(consulta.get("fontes") or [])
            texto += "".join("\n  " + linha for linha in fontes)
    else:
        texto = (consulta.get("texto") or "").strip()
    return f"- **{rotulo}:** {texto}"


def combinar(partes):
    consultas = [parte["consulta"] for parte in partes]
    todas = all(c.get("tipo") == "fundamentada" for c in consultas)

    fontes, vistos = [], set()
    for consulta in consultas:
        for fonte in consulta.get("fontes") or []:
            chave = fonte.get("chunk_id") if isinstance(fonte, dict) else None
            if chave is not None and chave in vistos:
                continue
            vistos.add(chave)
            fontes.append(fonte)

    base = dict(consultas[0])
    texto = "\n".join(_linha(parte, com_fontes=not todas) for parte in partes)
    if todas:
        tipo = "fundamentada"
        revisar = any(c.get("estado") == "revisar" for c in consultas)
    else:
        tipos = {c.get("tipo") for c in consultas}
        tipo = next((t for t in ORDEM_PIOR if t in tipos), "falha")
        revisar = True

    base.update({
        "tipo": tipo,
        "texto": texto,
        "resposta": texto if todas else None,
        "fontes": fontes,
        "estado": "revisar" if revisar else "pendente",
        "justificativa": " | ".join(c.get("justificativa") or "" for c in consultas).strip(" |"),
    })
    return base


def consultar_orientacoes(linhas, nome_configuracao="principal", responder=responder_rf19):
    partes = []
    for assunto, pergunta in perguntas_de_matricula(linhas):
        resultado = None
        try:
            resultado = responder(pergunta, top_k=15, nome_configuracao=nome_configuracao)
            consulta = classificar_consulta(resultado=resultado)
        except Exception as erro:
            consulta = classificar_consulta(erro=erro)
        partes.append({
            "assunto": assunto,
            "pergunta": pergunta,
            "consulta": consulta,
            "id_consulta": (resultado or {}).get("id_consulta") if isinstance(resultado, dict) else None,
        })
    return combinar(partes), partes


def gerar(caso, nome_configuracao="principal", responder=responder_rf19):
    from src.avaliacao_rf15 import GABARITOS
    from src.schemas import esperado_do_gabarito, validar_estrutura

    gabarito = json.loads((BASE_DIR / "dados" / "gabaritos" / GABARITOS[caso]).read_text(encoding="utf-8"))
    solicitacao, erros = validar_estrutura(json.dumps(esperado_do_gabarito(gabarito), ensure_ascii=False))
    if solicitacao is None:
        raise ValueError(f"A extração do {caso} não passou na validação: {erros}")

    ficha = {"linhas": linhas_da_ficha(solicitacao)}
    consulta, partes = consultar_orientacoes(ficha["linhas"], nome_configuracao, responder)
    minuta = minuta_do_atendimento(ficha, consulta)
    return {"caso": caso, "configuracao": nome_configuracao, "minuta": minuta, "consulta": consulta, "partes": partes}


def salvar(resultado):
    caso = resultado["caso"]
    pasta = BASE_DIR / "resultados" / "minutas" / "rag" / f"execucao_{datetime.now():%Y%m%d_%H%M%S}"
    pasta.mkdir(parents=True, exist_ok=True)

    aviso = (
        f"<!-- {caso}: minuta com orientações do RAG (uma consulta por assunto). "
        "Estado: pendente de revisão humana. A ficha vem da extração validada do gabarito. -->\n\n"
    )
    (pasta / f"{caso}_minuta.md").write_text(aviso + resultado["minuta"]["texto"] + "\n", encoding="utf-8")

    resumo = {
        "caso": caso,
        "configuracao": resultado["configuracao"],
        "minuta_pronta": resultado["minuta"]["pronta"],
        "estado": resultado["consulta"].get("estado"),
        "tipo_orientacoes": resultado["consulta"].get("tipo"),
        "consultas": [
            {
                "assunto": p["assunto"],
                "pergunta": p["pergunta"],
                "id_consulta": p["id_consulta"],
                "tipo": p["consulta"].get("tipo"),
                "fontes": p["consulta"].get("fontes"),
            }
            for p in resultado["partes"]
        ],
    }
    (pasta / f"{caso}_consultas.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return pasta


def main(argv=None):
    analisador = argparse.ArgumentParser()
    analisador.add_argument("--caso", default="CASO-08")
    analisador.add_argument("--configuracao", default="principal")
    argumentos = analisador.parse_args(argv)

    resultado = gerar(argumentos.caso, argumentos.configuracao)
    pasta = salvar(resultado)
    for parte in resultado["partes"]:
        fontes = [f.get("chunk_id") for f in parte["consulta"].get("fontes") or [] if isinstance(f, dict)]
        print(f"{parte['assunto']:<10} {parte['consulta'].get('tipo'):<14} {parte['id_consulta']} fontes={fontes}")
    print("minuta pronta:", resultado["minuta"]["pronta"], "| estado:", resultado["consulta"].get("estado"))
    print("salvo em:", pasta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())