"""RF10 — peça visual de orientação: passo a passo da matrícula.

A IA (gpt-image-1) gera só a ilustração, sem nenhuma letra; o código monta a
peça com o brasão, os textos exatos e o selo de conteúdo gerado por IA. Assim a
peça é sintética e continua legível.

Cada ilustração gerada é uma versão numerada e precisa de revisão humana antes
de valer. A versão aprovada mais recente é a vigente: ela entra na peça de todo
atendimento aprovado. Os passos (o que levar, até quando, onde ir e a regra de
frequência) vêm dos campos da minuta aprovada; o que estiver "não localizado"
vira uma orientação para procurar a secretaria. Nada é inventado e a peça não
leva dados pessoais. Nenhuma versão é apagada.

Uso pelo terminal:
    python -m src.peca_orientacao gerar
    python -m src.peca_orientacao revisar --versao 1 --decisao aprovada --revisor "Nome" --nota "..."
    python -m src.peca_orientacao revogar --versao 1 --revisor "Nome" --nota "motivo"
"""

import argparse
import base64
import json
import re
from datetime import datetime
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

try:
    from audit import registrar_evento
    from configuracao import CAMINHOS, CUSTOS, MODELOS, PARAMETROS_GERAIS
except ImportError:
    from src.audit import registrar_evento
    from src.configuracao import CAMINHOS, CUSTOS, MODELOS, PARAMETROS_GERAIS

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

MODELO_IMAGEM = MODELOS["imagem"]
TAMANHO = PARAMETROS_GERAIS["imagem_tamanho"]
QUALIDADE = PARAMETROS_GERAIS["imagem_qualidade"]
# Estimativa da tabela do provedor para o tamanho e a qualidade configurados; a conferir
CUSTO_ESTIMADO_USD = CUSTOS["imagem"]

PROMPT_ILUSTRACAO = """
Sujeito: balcão de atendimento de uma secretaria escolar com uma pasta fechada, um
calendário de mesa com a grade vazia (sem números), um porta-lápis e um vaso de planta;
ao fundo, a fachada estilizada de um prédio escolar, lisa, sem placa, faixa de letreiro
ou qualquer escrita.
Composição: panorâmica; todos os elementos dentro de uma faixa horizontal central que
ocupa só o terço do meio da altura da imagem; acima e abaixo dessa faixa, apenas fundo
liso de cor sólida, porque a imagem será recortada como faixa panorâmica (cerca de 2,5:1);
sem pessoas.
Estilo: ilustração vetorial plana, institucional e sóbria, sem nenhum elemento
tipográfico; paleta verde (#165C3F), amarelo-dourado discreto e branco; contornos suaves.
Iluminação: luz difusa e uniforme, de dia, sem sombras duras nem reflexos.
Proporção: 3:2 (1536 x 1024), com o conteúdo concentrado na faixa central.
Restrições: nenhuma letra, número, palavra, placa, letreiro, logotipo ou brasão em
nenhum lugar da imagem; nenhum papel com título ou cabeçalho; nenhuma pessoa, rosto ou
mão; nada que pareça documento oficial preenchido; sem dados pessoais.
""".strip()

# O que o servidor confere em cada ilustração nova antes de aprovar
CHECKLIST = (
    ("sem_texto", "Não tem letras, números ou palavras"),
    ("sem_simbolos", "Não tem logotipos, brasões ou símbolos oficiais"),
    ("objetos_coerentes", "Objetos coerentes, sem distorções"),
    ("sem_pessoas", "Sem pessoas, rostos ou mãos"),
)

SELO_IA = "Ilustração gerada por IA (gpt-image-1) e diagramada pela equipe"
RODAPE = "Peça demonstrativa — Projeto FIC_DEV 2026 · Não constitui comunicado oficial"
CABECALHO = (
    "GOVERNO DE MATO GROSSO",
    "SECRETARIA DE ESTADO DE CIÊNCIA, TECNOLOGIA E INOVAÇÃO — SECITECI/MT",
    "ESCOLA TÉCNICA ESTADUAL DE CUIABÁ",
)

LARGURA, ALTURA = 1024, 1536
VERDE = "#165C3F"
VERDE_ESCURO = "#1E4636"
TEXTO = "#334A3E"
CINZA = "#62756A"
CLARO = "#EFF5F0"
FUNDO = "#E9EEEA"

# Fontes procuradas em Linux e Windows; sem nenhuma, usa a embutida do Pillow
_FONTES = {
    False: (
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ),
    True: (
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ),
}


def _pasta() -> Path:
    return BASE_DIR / CAMINHOS["imagens_orientacao"]


def _arquivo_versoes() -> Path:
    return BASE_DIR / CAMINHOS["logs"] / "metadados_peca_orientacao.json"


def _relativo(caminho: Path) -> str:
    return caminho.relative_to(BASE_DIR).as_posix()


def _agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def carregar_versoes() -> list[dict]:
    arquivo = _arquivo_versoes()
    if not arquivo.is_file():
        return []
    return json.loads(arquivo.read_text(encoding="utf-8")).get("versoes", [])


def _salvar_versoes(versoes: list[dict]) -> None:
    arquivo = _arquivo_versoes()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {
        "requisito": "RF10",
        "descricao": "Versões da ilustração da peça de orientação; a aprovada mais recente é a vigente.",
        "versoes": versoes,
    }
    arquivo.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def versao_vigente() -> dict | None:
    aprovadas = [v for v in carregar_versoes() if v.get("revisao_humana") == "aprovada"]
    return aprovadas[-1] if aprovadas else None


def versao_pendente() -> dict | None:
    pendentes = [v for v in carregar_versoes() if v.get("revisao_humana") == "pendente"]
    return pendentes[-1] if pendentes else None


def caminho(relativo: str) -> Path:
    return BASE_DIR / relativo


def gerar_ilustracao() -> dict:
    """Gera uma ilustração nova (versão pendente de revisão) e registra."""
    if versao_pendente():
        raise ValueError("Já existe uma ilustração aguardando revisão. Revise antes de gerar outra.")
    versoes = carregar_versoes()
    numero = max((v["versao"] for v in versoes), default=0) + 1
    destino = _pasta() / f"ilustracao_v{numero:02d}.png"
    destino.parent.mkdir(parents=True, exist_ok=True)

    inicio = perf_counter()
    try:
        cliente = OpenAI(timeout=max(180.0, float(PARAMETROS_GERAIS['timeout_segundos'])), max_retries=1)
        resposta = cliente.images.generate(
            model=MODELO_IMAGEM,
            prompt=PROMPT_ILUSTRACAO,
            size=TAMANHO,
            quality=QUALIDADE,
        )
        conteudo = resposta.data[0].b64_json if resposta.data else None
        if not conteudo:
            raise ValueError("A API retornou uma imagem vazia.")
        destino.write_bytes(base64.b64decode(conteudo))
    except Exception as erro:
        destino.unlink(missing_ok=True)
        registrar_evento("imagem_orientacao", {
            "acao": "geracao", "resultado": "erro", "versao": numero,
            "modelo": MODELO_IMAGEM, "erro": f"{type(erro).__name__}: {erro}",
        })
        raise

    versao = {
        "versao": numero,
        "arquivo": _relativo(destino),
        "modelo": MODELO_IMAGEM,
        "tamanho": TAMANHO,
        "qualidade": QUALIDADE,
        "prompt": PROMPT_ILUSTRACAO,
        "data_geracao": _agora(),
        "tempo_geracao_segundos": round(perf_counter() - inicio, 2),
        "custo_estimado_usd": CUSTO_ESTIMADO_USD,
        "revisao_humana": "pendente",
    }
    _salvar_versoes(versoes + [versao])
    registrar_evento("imagem_orientacao", {
        "acao": "geracao", "resultado": "sucesso",
        **{chave: versao[chave] for chave in (
            "versao", "arquivo", "modelo", "tamanho", "qualidade",
            "tempo_geracao_segundos", "custo_estimado_usd",
        )},
    })
    return versao


def revisar_ilustracao(
    versao: int,
    decisao: str,
    revisor: str,
    checklist: dict | None = None,
    nota: str = "",
) -> dict:
    """Aprova ou reprova uma ilustração pendente. Aprovar exige o checklist completo."""
    revisor = (revisor or "").strip()
    nota = (nota or "").strip()
    checklist = {chave: bool((checklist or {}).get(chave)) for chave, _ in CHECKLIST}
    if decisao not in ("aprovada", "reprovada"):
        raise ValueError(f"Decisão desconhecida: {decisao}")
    if not revisor:
        raise ValueError("Informe o nome de quem revisou a ilustração.")
    if decisao == "aprovada" and not all(checklist.values()):
        faltam = [rotulo for chave, rotulo in CHECKLIST if not checklist[chave]]
        raise ValueError("Para aprovar, confira: " + "; ".join(faltam) + ".")
    if decisao == "reprovada" and not nota:
        raise ValueError("Informe o motivo da reprovação.")

    versoes = carregar_versoes()
    alvo = next((v for v in versoes if v["versao"] == versao), None)
    if alvo is None:
        raise ValueError(f"Versão {versao} não encontrada.")
    if alvo.get("revisao_humana") != "pendente":
        raise ValueError(f"A versão {versao} já foi revisada.")
    alvo.update({
        "revisao_humana": decisao,
        "revisor": revisor,
        "data_revisao": _agora(),
        "checklist": checklist,
        "nota_revisao": nota,
    })
    _salvar_versoes(versoes)
    registrar_evento("imagem_orientacao", {
        "acao": "revisao", "versao": versao, "decisao": decisao,
        "revisor": revisor, "checklist": checklist, "nota_revisao": nota,
    })
    return alvo


def revogar_ilustracao(versao: int, revisor: str, nota: str) -> dict:
    """Retira de uso uma ilustração já aprovada (erro notado depois), sem apagar."""
    revisor = (revisor or "").strip()
    nota = (nota or "").strip()
    if not revisor or not nota:
        raise ValueError("Informe quem revogou e o motivo.")
    versoes = carregar_versoes()
    alvo = next((v for v in versoes if v["versao"] == versao), None)
    if alvo is None or alvo.get("revisao_humana") != "aprovada":
        raise ValueError(f"A versão {versao} não está aprovada.")
    alvo.update({
        "revisao_humana": "revogada",
        "revogada_por": revisor,
        "data_revogacao": _agora(),
        "motivo_revogacao": nota,
    })
    _salvar_versoes(versoes)
    registrar_evento("imagem_orientacao", {
        "acao": "revogacao", "versao": versao, "revisor": revisor, "motivo_revogacao": nota,
    })
    return alvo


def peca_do_atendimento(registro: dict) -> dict | None:
    """Monta (uma vez) a peça do atendimento aprovado com a ilustração vigente."""
    vigente = versao_vigente()
    id_execucao = (registro.get("id_execucao") or "").strip()
    if vigente is None or not id_execucao:
        return None
    origem = Path(registro.get("arquivo_origem") or "atendimento").stem
    destino = _pasta() / f"peca_{origem}_{id_execucao[:8]}_v{vigente['versao']:02d}.png"
    if not destino.is_file():
        dados = dados_da_peca(registro)
        compor_peca(caminho(vigente["arquivo"]), destino, dados)
        registrar_evento("imagem_orientacao", {
            "acao": "peca", "id_execucao": id_execucao, "versao": vigente["versao"],
            "arquivo": _relativo(destino), "curso": dados["curso"], "eixo": dados["eixo"],
            "passos_com_dado_do_atendimento": [chave for chave in ("documentos", "prazo", "local", "ciencia") if dados[chave]],
        })
    return {"arquivo": _relativo(destino), "versao": vigente}


def dados_da_peca(registro: dict) -> dict:
    """Só os campos que orientam a matrícula; nome, protocolo e datas não entram."""
    campos = registro.get("campos") or {}
    return {
        "curso": _valor(campos, "curso"),
        "eixo": _valor(campos, "eixo"),
        "documentos": _valor(campos, "documentos_necessarios"),
        "prazo": _valor(campos, "prazo_apresentacao"),
        "local": _valor(campos, "local_horario"),
        "ciencia": _valor(campos, "regras_ciencia"),
    }


def passos_da_peca(dados: dict) -> list[tuple[str, list[str]]]:
    """(título, linhas) de cada passo. Campo ausente vira orientação, nunca invenção."""
    passos = [("CONFIRA A RESPOSTA", [
        "Confira na resposta da secretaria o seu nome, o curso e o turno.",
    ])]
    documentos = _itens(dados.get("documentos"))
    passos.append(("O QUE LEVAR", [f"• {item}" for item in documentos] if documentos else [
        "A secretaria informará na resposta os documentos que você deve apresentar.",
    ]))
    passos.append(("ATÉ QUANDO", [_frase(dados.get("prazo")) or "Fique atento ao prazo informado pela secretaria."]))
    passos.append(("ONDE IR", [_frase(dados.get("local")) or "Procure a Secretaria Escolar da sua unidade."]))
    ciencia = _regra_de_frequencia(dados.get("ciencia"))
    if ciencia:
        passos.append(("DEPOIS DA MATRÍCULA", [ciencia]))
    return passos


def _valor(campos: dict, nome: str) -> str:
    valor = ((campos.get(nome) or {}).get("valor") or "").strip()
    return "" if valor == "não localizado" else valor


def _itens(texto: str | None) -> list[str]:
    texto = (texto or "").strip()
    if not texto:
        return []
    partes = re.split(r"[;\n]+", texto)
    if len(partes) == 1:
        partes = re.split(r",\s*|\s+e\s+(?=[a-záéíóú])", texto)
    return [_frase(parte).rstrip(".") for parte in partes if parte.strip()]


def _frase(texto: str | None) -> str:
    texto = (texto or "").strip().strip("-• ").strip()
    return texto[:1].upper() + texto[1:] if texto else ""


def _regra_de_frequencia(texto: str | None) -> str:
    """A ciência declarada na solicitação, escrita para quem lê a peça."""
    texto = (texto or "").strip()
    texto = re.sub(r"^O\(a\) solicitante declarou estar ciente de que\s+", "", texto, flags=re.IGNORECASE)
    return _frase(texto)


def _fonte(tamanho: int, negrito: bool = False):
    for candidato in _FONTES[negrito]:
        if Path(candidato).is_file():
            return ImageFont.truetype(candidato, tamanho)
    return ImageFont.load_default(size=tamanho)


def compor_peca(ilustracao: Path, destino: Path, dados: dict | None = None) -> Path:
    """Diagrama a peça 1024x1536 e salva: brasão, cabeçalho, título, ilustração e passo a passo."""
    imagem = montar_imagem(ilustracao, dados)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    imagem.save(destino)
    return destino


def previa_da_peca(ilustracao: Path, registro: dict) -> bytes:
    """A peça montada com a ilustração em revisão, em memória, para o servidor ver antes de aprovar."""
    import io

    buffer = io.BytesIO()
    montar_imagem(ilustracao, dados_da_peca(registro)).save(buffer, format="PNG")
    return buffer.getvalue()


def montar_imagem(ilustracao: Path, dados: dict | None = None):
    dados = dados or {}
    passos = passos_da_peca(dados)
    # Diminui a letra até o passo a passo caber acima do rodapé
    imagem = None
    for tamanho in (21, 19, 17, 15):
        imagem = _desenhar(ilustracao, dados, passos, tamanho)
        if imagem is not None:
            break
    if imagem is None:
        # Texto excessivo: desenha na menor letra mesmo passando do limite
        imagem = _desenhar(ilustracao, dados, passos, 15, limite=10**6)
    return imagem


def _desenhar(ilustracao: Path, dados: dict, passos, tamanho: int, limite: int = 1300):
    imagem = Image.new("RGB", (LARGURA, ALTURA), FUNDO)
    d = ImageDraw.Draw(imagem)
    d.rectangle((55, 40, 969, 1496), fill="#FFFFFF", outline="#CFD9D2", width=2)

    def centralizar(texto, y, fonte, cor):
        largura = d.textlength(texto, font=fonte)
        d.text(((LARGURA - largura) / 2, y), texto, font=fonte, fill=cor)

    def linhas(texto, x, y, fonte, cor, maximo, espaco=6):
        atual = ""
        for palavra in texto.split():
            tentativa = f"{atual} {palavra}".strip()
            if d.textlength(tentativa, font=fonte) <= maximo:
                atual = tentativa
                continue
            d.text((x, y), atual, font=fonte, fill=cor)
            y += fonte.size + espaco
            atual = ("  " if texto.startswith("•") else "") + palavra
        if atual:
            d.text((x, y), atual, font=fonte, fill=cor)
            y += fonte.size + espaco
        return y

    brasao = BASE_DIR / CAMINHOS["brasao"]
    if brasao.is_file():
        with Image.open(brasao) as original:
            selo = original.convert("RGBA")
            selo.thumbnail((104, 100))
            imagem.paste(selo, ((LARGURA - selo.width) // 2, 62), selo)

    centralizar(CABECALHO[0], 172, _fonte(21, True), VERDE_ESCURO)
    centralizar(CABECALHO[1], 202, _fonte(14), CINZA)
    centralizar(CABECALHO[2], 224, _fonte(16), CINZA)

    d.rectangle((90, 258, 934, 360), fill=VERDE)
    centralizar("PASSO A PASSO DA MATRÍCULA", 276, _fonte(36, True), "#FFFFFF")
    subtitulo = " · ".join(p for p in (dados.get("curso"), f"Eixo {dados['eixo']}" if dados.get("eixo") else "") if p)
    centralizar(subtitulo or "Cursos técnicos", 324, _fonte(19), "#D9E9DD")

    with Image.open(ilustracao) as arte:
        arte = arte.convert("RGB")
        largura, altura = 844, 340
        escala = max(largura / arte.width, altura / arte.height)
        arte = arte.resize((round(arte.width * escala), round(arte.height * escala)))
        esquerda = (arte.width - largura) // 2
        topo = (arte.height - altura) // 2
        imagem.paste(arte.crop((esquerda, topo, esquerda + largura, topo + altura)), (90, 372))

    titulo = _fonte(tamanho + 3, True)
    corpo = _fonte(tamanho)
    y = 740
    for numero, (nome, textos) in enumerate(passos, start=1):
        d.ellipse((96, y - 2, 140, y + 42), fill=VERDE)
        largura = d.textlength(str(numero), font=_fonte(24, True))
        d.text((118 - largura / 2, y + 6), str(numero), font=_fonte(24, True), fill="#FFFFFF")
        d.text((160, y + 4), nome, font=titulo, fill=VERDE_ESCURO)
        y += titulo.size + 16
        for texto in textos:
            y = linhas(texto, 160, y, corpo, TEXTO, 760)
        y += 18
        if y > limite:
            return None

    d.line((110, 1318, 914, 1318), fill="#D1DDD4", width=2)
    centralizar("Secretaria Escolar", 1334, _fonte(22, True), VERDE_ESCURO)
    centralizar(SELO_IA, 1376, _fonte(18, True), CINZA)
    centralizar(RODAPE, 1408, _fonte(16), CINZA)
    return imagem


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Peça de orientação do RF10")
    acoes = parser.add_subparsers(dest="acao", required=True)
    acoes.add_parser("gerar", help="gera uma ilustração nova, pendente de revisão")
    revisar = acoes.add_parser("revisar", help="aprova ou reprova uma ilustração pendente")
    revisar.add_argument("--versao", type=int, required=True)
    revisar.add_argument("--decisao", choices=("aprovada", "reprovada"), required=True)
    revisar.add_argument("--revisor", required=True)
    revisar.add_argument("--nota", default="")
    revogar = acoes.add_parser("revogar", help="retira de uso uma ilustração aprovada")
    revogar.add_argument("--versao", type=int, required=True)
    revogar.add_argument("--revisor", required=True)
    revogar.add_argument("--nota", required=True)
    argumentos = parser.parse_args(argv)

    if argumentos.acao == "gerar":
        versao = gerar_ilustracao()
        print(f"Ilustração v{versao['versao']:02d} gerada: {versao['arquivo']} (pendente de revisão)")
        return
    if argumentos.acao == "revogar":
        versao = revogar_ilustracao(argumentos.versao, argumentos.revisor, argumentos.nota)
        print(f"Versão {versao['versao']} revogada por {versao['revogada_por']}.")
        return
    checklist = {chave: True for chave, _ in CHECKLIST} if argumentos.decisao == "aprovada" else None
    versao = revisar_ilustracao(argumentos.versao, argumentos.decisao, argumentos.revisor, checklist, argumentos.nota)
    print(f"Versão {versao['versao']} {versao['revisao_humana']} por {versao['revisor']}.")


if __name__ == "__main__":
    main()
